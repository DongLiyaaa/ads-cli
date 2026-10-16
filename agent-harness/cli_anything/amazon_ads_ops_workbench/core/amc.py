"""Amazon Marketing Cloud (AMC) helpers shared by the CLI and the control plane.

AMC runs privacy-safe SQL over event-level ad data. Queries are asynchronous
workflow executions whose results are CSV files behind pre-signed S3 URLs.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, timedelta
from typing import Any

MARKETPLACE_IDS = {
    "US": "ATVPDKIKX0DER",
    "CA": "A2EUQ1WTGCTBG2",
    "MX": "A1AM78C64UM0Y8",
    "BR": "A2Q3Y263D00KWC",
    "UK": "A1F83G8C2ARO7P",
    "GB": "A1F83G8C2ARO7P",
    "DE": "A1PA6795UKMFR9",
    "FR": "A13V1IB3VIYZZH",
    "IT": "APJ6JRA9NG5V4",
    "ES": "A1RKKUPIHCS9HS",
    "NL": "A1805IZSGTT6HS",
    "SE": "A2NODRKZP88ZB9",
    "TR": "A33AVAJ2PDY3EV",
    "SA": "A17E79C6D8DWNP",
    "AE": "A2VIGQ35RCS4UG",
    "JP": "A1VC38T7YXB528",
    "AU": "A39IBJ37TRP1C6",
    "IN": "A21TJRUUN4KGV",
}

# AMC accepts long windows, but large windows are slow and hit privacy checks sooner.
MAX_WINDOW_DAYS = 366
MAX_SQL_LENGTH = 100_000
# Executions in these states will not change any more.
FINAL_FAILURE_STATUSES = {"FAILED", "REJECTED", "CANCELLED"}

# Templates use only columns verified against /dataSources. AMC has no LIMIT or
# top-level ORDER BY, and every output row must aggregate enough users.
TEMPLATES: dict[str, dict[str, Any]] = {
    "ad-product-combo": {
        "name": "广告类型组合与转化",
        "description": "按顾客看到过的 SP / SB / SD 组合分组，比较触达人数、购买人数和销售额，判断多种广告配合是否带来更高转化。",
        "sources": ["sponsored_ads_traffic", "amazon_attributed_events_by_traffic_time"],
        "sql": """
WITH exposure AS (
  SELECT user_id,
    MAX(CASE WHEN ad_product_type = 'sponsored_products' THEN 1 ELSE 0 END) AS sp,
    MAX(CASE WHEN ad_product_type = 'sponsored_brands' THEN 1 ELSE 0 END) AS sb,
    MAX(CASE WHEN ad_product_type = 'sponsored_display' THEN 1 ELSE 0 END) AS sd
  FROM sponsored_ads_traffic
  WHERE user_id IS NOT NULL AND impressions > 0
  GROUP BY user_id
),
combos AS (
  SELECT user_id,
    CASE
      WHEN sp = 1 AND sb = 1 AND sd = 1 THEN 'SP+SB+SD'
      WHEN sp = 1 AND sb = 1 THEN 'SP+SB'
      WHEN sp = 1 AND sd = 1 THEN 'SP+SD'
      WHEN sb = 1 AND sd = 1 THEN 'SB+SD'
      WHEN sp = 1 THEN 'SP'
      WHEN sb = 1 THEN 'SB'
      WHEN sd = 1 THEN 'SD'
      ELSE 'OTHER'
    END AS ad_product_combo
  FROM exposure
),
buyers AS (
  SELECT user_id, SUM(total_purchases) AS purchases, SUM(total_product_sales) AS product_sales
  FROM amazon_attributed_events_by_traffic_time
  WHERE user_id IS NOT NULL AND total_purchases > 0
  GROUP BY user_id
)
SELECT c.ad_product_combo,
  COUNT(DISTINCT c.user_id) AS reached_users,
  COUNT(DISTINCT b.user_id) AS purchasing_users,
  SUM(b.purchases) AS purchases,
  SUM(b.product_sales) AS product_sales
FROM combos c
LEFT JOIN buyers b ON c.user_id = b.user_id
GROUP BY c.ad_product_combo
""",
    },
    "time-to-conversion": {
        "name": "从点击/曝光到购买的时长",
        "description": "统计归因购买发生在广告接触后多久（1 小时内、1–6 小时……7 天以上），按广告类型拆分，用于判断归因窗口和分时竞价。",
        "sources": ["amazon_attributed_events_by_traffic_time"],
        "sql": """
WITH purchases AS (
  SELECT ad_product_type,
    CASE
      WHEN SECONDS_BETWEEN(traffic_event_dt, conversion_event_dt) < 3600 THEN '0-1h'
      WHEN SECONDS_BETWEEN(traffic_event_dt, conversion_event_dt) < 21600 THEN '1-6h'
      WHEN SECONDS_BETWEEN(traffic_event_dt, conversion_event_dt) < 86400 THEN '6-24h'
      WHEN SECONDS_BETWEEN(traffic_event_dt, conversion_event_dt) < 259200 THEN '1-3d'
      WHEN SECONDS_BETWEEN(traffic_event_dt, conversion_event_dt) < 604800 THEN '3-7d'
      ELSE '7d+'
    END AS time_to_purchase,
    total_purchases, total_units_sold, total_product_sales
  FROM amazon_attributed_events_by_traffic_time
  WHERE total_purchases > 0
)
SELECT ad_product_type, time_to_purchase,
  SUM(total_purchases) AS purchases,
  SUM(total_units_sold) AS units_sold,
  SUM(total_product_sales) AS product_sales
FROM purchases
GROUP BY ad_product_type, time_to_purchase
""",
    },
    "new-to-brand-by-campaign": {
        "name": "品牌新客（按广告活动）",
        "description": "每个广告活动带来的订单中，过去 12 个月没买过本品牌的新客占多少，包括订单数和销售额。需要品牌备案才有新客数据。",
        "sources": ["amazon_attributed_events_by_traffic_time"],
        "sql": """
SELECT ad_product_type, campaign,
  COUNT(DISTINCT user_id) AS purchasing_users,
  SUM(total_purchases) AS purchases,
  SUM(new_to_brand_total_purchases) AS ntb_purchases,
  SUM(total_product_sales) AS product_sales,
  SUM(new_to_brand_total_product_sales) AS ntb_product_sales
FROM amazon_attributed_events_by_traffic_time
WHERE total_purchases > 0
GROUP BY ad_product_type, campaign
""",
    },
    "frequency-vs-conversion": {
        "name": "曝光频次与购买率",
        "description": "按每位顾客在时间范围内看到广告的次数分组（1 次、2–3 次……21 次以上），比较购买人数，找到收益递减的频次。",
        "sources": ["sponsored_ads_traffic", "amazon_attributed_events_by_traffic_time"],
        "sql": """
WITH freq AS (
  SELECT user_id, SUM(impressions) AS imps
  FROM sponsored_ads_traffic
  WHERE user_id IS NOT NULL
  GROUP BY user_id
),
buyers AS (
  SELECT user_id, SUM(total_purchases) AS purchases
  FROM amazon_attributed_events_by_traffic_time
  WHERE user_id IS NOT NULL AND total_purchases > 0
  GROUP BY user_id
),
bucketed AS (
  SELECT f.user_id, b.purchases,
    CASE
      WHEN f.imps <= 1 THEN '01'
      WHEN f.imps <= 3 THEN '02-03'
      WHEN f.imps <= 6 THEN '04-06'
      WHEN f.imps <= 10 THEN '07-10'
      WHEN f.imps <= 20 THEN '11-20'
      ELSE '21+'
    END AS frequency_bucket
  FROM freq f
  LEFT JOIN buyers b ON f.user_id = b.user_id
  WHERE f.imps > 0
)
SELECT frequency_bucket,
  COUNT(DISTINCT user_id) AS reached_users,
  COUNT(DISTINCT CASE WHEN purchases > 0 THEN user_id END) AS purchasing_users,
  SUM(purchases) AS purchases
FROM bucketed
GROUP BY frequency_bucket
""",
    },
    "search-term-conversion": {
        "name": "搜索词：花费、购买与新客",
        "description": "按顾客真实搜索词汇总曝光、点击、花费和归因购买（含品牌新客），比后台搜索词报表多了跨广告类型的新客数据。",
        "sources": ["sponsored_ads_traffic", "amazon_attributed_events_by_traffic_time"],
        "sql": """
WITH traffic AS (
  SELECT customer_search_term,
    SUM(impressions) AS impressions, SUM(clicks) AS clicks, SUM(spend) AS spend_microcents
  FROM sponsored_ads_traffic
  WHERE customer_search_term IS NOT NULL
  GROUP BY customer_search_term
),
conv AS (
  SELECT customer_search_term,
    SUM(total_purchases) AS purchases,
    SUM(new_to_brand_total_purchases) AS ntb_purchases,
    SUM(total_product_sales) AS product_sales
  FROM amazon_attributed_events_by_traffic_time
  WHERE customer_search_term IS NOT NULL
  GROUP BY customer_search_term
)
SELECT t.customer_search_term,
  SUM(t.impressions) AS impressions,
  SUM(t.clicks) AS clicks,
  ROUND(SUM(t.spend_microcents) / 100000000.0, 2) AS spend,
  SUM(c.purchases) AS purchases,
  SUM(c.ntb_purchases) AS ntb_purchases,
  SUM(c.product_sales) AS product_sales
FROM traffic t
LEFT JOIN conv c ON t.customer_search_term = c.customer_search_term
GROUP BY t.customer_search_term
""",
    },
    "hour-of-day": {
        "name": "分时段表现",
        "description": "按广告接触发生的小时（账户时区 0–23 点）和广告类型汇总曝光、点击、花费、购买和销售额，用于分时调价。",
        "sources": ["sponsored_ads_traffic", "amazon_attributed_events_by_traffic_time"],
        "sql": """
WITH traffic AS (
  SELECT event_hour AS hour_of_day, ad_product_type,
    SUM(impressions) AS impressions, SUM(clicks) AS clicks, SUM(spend) AS spend_microcents
  FROM sponsored_ads_traffic
  GROUP BY event_hour, ad_product_type
),
conv AS (
  SELECT traffic_event_hour AS hour_of_day, ad_product_type,
    SUM(total_purchases) AS purchases, SUM(total_product_sales) AS product_sales
  FROM amazon_attributed_events_by_traffic_time
  GROUP BY traffic_event_hour, ad_product_type
)
SELECT t.hour_of_day, t.ad_product_type,
  SUM(t.impressions) AS impressions,
  SUM(t.clicks) AS clicks,
  ROUND(SUM(t.spend_microcents) / 100000000.0, 2) AS spend,
  SUM(c.purchases) AS purchases,
  SUM(c.product_sales) AS product_sales
FROM traffic t
LEFT JOIN conv c ON t.hour_of_day = c.hour_of_day AND t.ad_product_type = c.ad_product_type
GROUP BY t.hour_of_day, t.ad_product_type
""",
    },
}


def public_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": key,
            **{k: v for k, v in t.items() if k != "sql"},
            "sql": normalize_sql(t["sql"]),
            "sqlText": t["sql"].strip(),
        }
        for key, t in TEMPLATES.items()
    ]


def normalize_sql(sql: str) -> str:
    """Collapse a query to the single line AMC requires.

    Joining lines naively would let a `--` comment swallow the rest of the
    query, so comments are dropped first while quoted text is left intact.
    """
    out, i, n, quote = [], 0, len(sql), None
    while i < n:
        ch = sql[i]
        if quote:
            out.append(ch)
            if ch == quote:
                if i + 1 < n and sql[i + 1] == quote:  # escaped '' or ""
                    out.append(sql[i + 1])
                    i += 1
                else:
                    quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif sql.startswith("--", i):
            while i < n and sql[i] != "\n":
                i += 1
            out.append(" ")
            continue
        elif sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            if end < 0:
                raise ValueError("SQL 注释 /* 没有闭合")
            i = end + 2
            out.append(" ")
            continue
        else:
            out.append(" " if ch in "\r\n\t" else ch)
        i += 1
    if quote:
        raise ValueError("SQL 中的引号没有闭合")
    text = re.sub(r"\s+", " ", "".join(out)).strip().rstrip(";").strip()
    if not text:
        raise ValueError("SQL 不能为空")
    if len(text) > MAX_SQL_LENGTH:
        raise ValueError(f"SQL 超过 {MAX_SQL_LENGTH} 个字符")
    if ";" in _outside_quotes(text):
        raise ValueError("一次只能提交一条 SQL 语句")
    return text


def _outside_quotes(text: str) -> str:
    return re.sub(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"", "", text)


def resolve_query(template: str | None, sql: str | None) -> tuple[str, str | None]:
    if bool(template) == bool(sql):
        raise ValueError("请二选一：提供模板 template 或自定义 SQL")
    if template:
        if template not in TEMPLATES:
            raise ValueError("未知 AMC 模板: " + template)
        return normalize_sql(TEMPLATES[template]["sql"]), template
    return normalize_sql(sql or ""), None


def check_window(start_date: str, end_date: str) -> tuple[date, date]:
    try:
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    except (TypeError, ValueError):
        raise ValueError("请提供有效的起止日期 YYYY-MM-DD") from None
    if not 0 <= (end - start).days < MAX_WINDOW_DAYS:
        raise ValueError(f"AMC 查询时间范围需为 1–{MAX_WINDOW_DAYS} 天")
    return start, end


def build_execution_body(
    sql: str, start_date: str, end_date: str, time_zone: str | None = None
) -> dict[str, Any]:
    start, end = check_window(start_date, end_date)
    body: dict[str, Any] = {
        "workflow": {"sqlQuery": sql},
        "timeWindowType": "EXPLICIT",
        "timeWindowStart": f"{start.isoformat()}T00:00:00",
        # The window end is exclusive; include the whole end date.
        "timeWindowEnd": f"{(end + timedelta(days=1)).isoformat()}T00:00:00",
    }
    if time_zone:
        body["timeWindowTimeZone"] = time_zone
    return body


def pick_entity(ads_accounts: list[dict[str, Any]], marketplace: str, profile_id: str) -> str:
    """Return the sponsored ads entity ID (ENTITY…) that AMC expects as AdvertiserId."""
    by_profile, by_country = None, None
    for account in ads_accounts:
        for alt in account.get("alternateIds") or []:
            entity = alt.get("entityId")
            if not entity:
                continue
            if str(alt.get("profileId") or "") == str(profile_id):
                by_profile = by_profile or entity
            if (alt.get("countryCode") or "").upper() == marketplace.upper():
                by_country = by_country or entity
    entity = by_profile or by_country
    if not entity:
        raise RuntimeError("未找到该站点的广告实体 ID（ENTITY…），无法访问 AMC")
    return entity


def pick_instance(instances: list[dict[str, Any]], instance_id: str | None = None) -> dict[str, Any]:
    ready = [i for i in instances if i.get("creationStatus") in (None, "COMPLETED")]
    if instance_id:
        match = next((i for i in instances if i.get("instanceId") == instance_id), None)
        if not match:
            raise RuntimeError("AMC 实例不存在或无权访问: " + instance_id)
        return match
    if not ready:
        raise RuntimeError(
            "该账户还没有可用的 AMC 实例；请先登录 AMC 控制台接受条款，或等待实例创建完成"
        )
    return ready[0]


def summarize_instance(instance: dict[str, Any]) -> dict[str, Any]:
    keep = ("instanceId", "instanceName", "instanceType", "creationStatus", "creationDatetime", "entities")
    value = {k: instance.get(k) for k in keep if k in instance}
    value["optionalDatasets"] = [d.get("label") for d in instance.get("optionalDatasets") or []]
    return value


def summarize_data_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": s.get("dataSourceId"),
            "description": s.get("description", ""),
            "tags": [t.get("subtext") for t in s.get("tags") or [] if t.get("subtext")],
            "premium": bool(s.get("isPremium")),
            "audienceOnly": str(s.get("dataSourceId", "")).endswith("_for_audiences"),
            "columns": [
                {
                    "name": c.get("name"),
                    "type": c["dataType"] if isinstance(c.get("dataType"), str) else (c.get("dataType") or {}).get("type"),
                    "kind": c.get("columnType"),
                    "description": (c.get("description") or "")[:400],
                }
                for c in s.get("columns") or []
            ],
        }
        for s in sources
    ]


_INT = re.compile(r"-?\d+")
# "01", "007", "-02": labels such as buckets or postal codes, not numbers.
_LEADING_ZERO = re.compile(r"-?0\d")
_FLOAT = re.compile(r"-?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?")


def parse_csv_rows(text: str) -> list[dict[str, Any]]:
    """CSV to JSON-safe rows. IDs stay strings so 18-digit values keep precision."""
    rows = []
    for record in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        row = {}
        for key, value in record.items():
            if key is None:
                continue
            if value is None or value == "":
                row[key] = None
            elif (
                key.endswith("id")
                or key.endswith("_id")
                or not _FLOAT.fullmatch(value)
                or _LEADING_ZERO.match(value)
            ):
                row[key] = value
            elif _INT.fullmatch(value) and abs(int(value)) < 2**53:
                row[key] = int(value)
            elif _INT.fullmatch(value):
                row[key] = value
            else:
                row[key] = float(value)
        rows.append(row)
    return rows

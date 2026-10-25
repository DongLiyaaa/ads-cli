"""Amazon Ads Reporting API v1 (unified) for ad products the v3 report types lack.

Full-funnel campaigns (console: 全流域广告活动) only report through this API. The
advertiser account is global (all marketplaces), so the worker scopes a report to
one profile by filtering on that profile's campaign IDs.
"""

from __future__ import annotations

from datetime import date
from typing import Any

FULL_FUNNEL = "FULL_FUNNEL"
TIME_FIELDS = {"DAILY": "date.value", "SUMMARY": "dateRange.value"}
FULL_FUNNEL_FIELDS = [
    "budgetCurrency.value",
    "campaign.id",
    "campaign.name",
    "metric.impressions",
    "metric.clicks",
    "metric.totalCost",
    "metric.sales",
    "metric.purchases",
    "metric.unitsSold",
    "metric.addToCart",
    "metric.detailPageViews",
    "metric.newToBrandPurchases",
    "metric.newToBrandSales",
]
# Unified field IDs to the column names the data table already labels.
RENAMES = {
    "date.value": "date",
    "dateRange.value": "dateRange",
    "budgetCurrency.value": "campaignBudgetCurrencyCode",
    "campaign.id": "campaignId",
    "campaign.name": "campaignName",
    "metric.totalCost": "cost",
}


def build_full_funnel_plan(start_date: str, end_date: str, time_unit: str = "DAILY") -> dict[str, Any]:
    unit = (time_unit or "DAILY").upper()
    if unit not in TIME_FIELDS:
        raise ValueError("time_unit 只能是 DAILY 或 SUMMARY")
    try:
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    except (TypeError, ValueError):
        raise ValueError("请提供 YYYY-MM-DD 格式的起止日期") from None
    if end < start:
        raise ValueError("结束日期不能早于开始日期")
    return {
        "unified": True,
        "adProduct": FULL_FUNNEL,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "fields": [TIME_FIELDS[unit], *FULL_FUNNEL_FIELDS],
    }


def build_report_body(plan: dict[str, Any], advertiser_account_id: str, campaign_ids: list[str]) -> dict[str, Any]:
    return {
        "reports": [
            {
                "format": "CSV",
                "periods": [{"datePeriod": {"startDate": plan["startDate"], "endDate": plan["endDate"]}}],
                "query": {
                    "fields": list(plan["fields"]),
                    "filter": {
                        "on": {
                            "field": "campaign.id",
                            "comparisonOperator": "IN",
                            "not": False,
                            "values": [str(c) for c in campaign_ids],
                        }
                    },
                },
            }
        ],
        "accessRequestedAccounts": [{"advertiserAccountId": advertiser_account_id}],
    }


def pick_advertiser_account(accounts: list[dict[str, Any]], profile_id: str) -> str:
    """The global advertiser account whose alternate IDs include this profile."""
    for account in accounts:
        if any(str(alt.get("profileId")) == str(profile_id) for alt in account.get("alternateIds") or []):
            return account["advertiserAccountId"]
    raise ValueError(f"没有找到包含配置文件 {profile_id} 的广告主账户")


def _squash(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _column(field: str) -> str:
    return RENAMES.get(field, field.removeprefix("metric."))


# The download's header spelling is undocumented: accept the field ID
# ("campaign.id"), a display name ("Campaign ID") or camelCase ("campaignId").
_ALIASES = {
    alias: _column(field)
    for field in [*TIME_FIELDS.values(), *FULL_FUNNEL_FIELDS]
    for alias in (
        _squash(field),
        _squash(field.removeprefix("metric.").removesuffix(".value")),
        _squash(_column(field)),
    )
}


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {_ALIASES.get(_squash(k), _column(k)): v for k, v in row.items()}
        for row in rows
    ]

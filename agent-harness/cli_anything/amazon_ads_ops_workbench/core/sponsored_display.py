from __future__ import annotations

from typing import Any

from .metadata import metadata_time_fields

SD_MEDIA_PATH_TOKENS = (
    "/sd/creatives",
    "/creative",
    "/creatives",
    "/assets",
    "assetlibrary",
    "customimage",
    "brandlogo",
    "video",
    "image",
    "logo",
    "media",
)

SD_MEDIA_PAYLOAD_TOKENS = (
    "creative",
    "asset",
    "image",
    "video",
    "logo",
    "media",
    "brandlogo",
    "customimage",
    "rectcustomimage",
    "squarecustomimage",
)


def assert_sd_raw_allowed(path: str, payload: Any | None = None) -> None:
    if not path.startswith("/sd/"):
        raise ValueError("Raw SD requests must use a path that starts with /sd/.")
    lowered_path = path.lower()
    for token in SD_MEDIA_PATH_TOKENS:
        if token in lowered_path:
            raise ValueError(
                "Raw SD requests to creative, asset, image, video, logo, or media paths are blocked."
            )
    blocked_key = find_blocked_media_payload_key(payload)
    if blocked_key:
        raise ValueError(
            f"Raw SD request payload contains blocked media/creative key: {blocked_key}"
        )


def find_blocked_media_payload_key(value: Any) -> str:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in SD_MEDIA_PAYLOAD_TOKENS):
                return str(key)
            nested = find_blocked_media_payload_key(child)
            if nested:
                return nested
    if isinstance(value, list):
        for child in value:
            nested = find_blocked_media_payload_key(child)
            if nested:
                return nested
    return ""


def build_sd_query_filter(
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    entity_id: str | None = None,
    state_filter: str | None = None,
    tactic: str | None = None,
    max_results: int | None = None,
    entity_key: str = "targetIdFilter",
) -> dict[str, str]:
    query: dict[str, str] = {}
    if campaign_id:
        query["campaignIdFilter"] = campaign_id
    if ad_group_id:
        query["adGroupIdFilter"] = ad_group_id
    if entity_id:
        query[entity_key] = entity_id
    if state_filter:
        query["stateFilter"] = _lower_state(state_filter)
    if tactic:
        query["tactic"] = tactic
    return query


def build_sd_campaign_create_payload(
    name: str,
    budget: float,
    start_date: str,
    tactic: str = "T00030",
    budget_type: str = "daily",
    cost_type: str = "cpc",
    state: str = "paused",
    end_date: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "budgetType": budget_type.lower(),
        "budget": _money_string(budget),
        "startDate": _sd_date(start_date),
        "costType": cost_type.lower(),
        "state": _lower_state(state),
        "tactic": tactic,
    }
    if end_date:
        payload["endDate"] = _sd_date(end_date)
    return payload


def build_sd_campaign_update_payload(
    campaign_id: str,
    state: str | None = None,
    budget: float | None = None,
    name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    budget_type: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"campaignId": campaign_id}
    if state:
        payload["state"] = _lower_state(state)
    if budget is not None:
        payload["budget"] = _money_string(budget)
    if name:
        payload["name"] = name
    if start_date:
        payload["startDate"] = _sd_date(start_date)
    if end_date:
        payload["endDate"] = _sd_date(end_date)
    if budget_type:
        payload["budgetType"] = budget_type.lower()
    return payload


def build_sd_ad_group_create_payload(
    campaign_id: str,
    name: str,
    default_bid: float,
    bid_optimization: str = "clicks",
    state: str = "paused",
    creative_type: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "campaignId": campaign_id,
        "defaultBid": default_bid,
        "bidOptimization": bid_optimization.lower(),
        "state": _lower_state(state),
    }
    if creative_type:
        payload["creativeType"] = creative_type.upper()
    return payload


def build_sd_ad_group_update_payload(
    ad_group_id: str,
    state: str | None = None,
    default_bid: float | None = None,
    name: str | None = None,
    bid_optimization: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"adGroupId": ad_group_id}
    if state:
        payload["state"] = _lower_state(state)
    if default_bid is not None:
        payload["defaultBid"] = default_bid
    if name:
        payload["name"] = name
    if bid_optimization:
        payload["bidOptimization"] = bid_optimization.lower()
    return payload


def build_sd_product_ad_create_payload(
    campaign_id: str,
    ad_group_id: str,
    ad_name: str | None = None,
    sku: str | None = None,
    asin: str | None = None,
    landing_page_url: str | None = None,
    landing_page_type: str | None = None,
    state: str = "paused",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "state": _lower_state(state),
    }
    if ad_name:
        payload["adName"] = ad_name
    if sku:
        payload["sku"] = sku
    if asin:
        payload["asin"] = asin
    if landing_page_url:
        payload["landingPageURL"] = landing_page_url
    if landing_page_type:
        payload["landingPageType"] = landing_page_type.upper()
    return payload


def build_sd_product_ad_update_payload(
    product_ad_id: str,
    state: str | None = None,
    ad_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"adId": product_ad_id}
    if state:
        payload["state"] = _lower_state(state)
    if ad_name:
        payload["adName"] = ad_name
    return payload


def build_sd_target_payload(
    ad_group_id: str,
    expression: list[dict[str, Any]],
    bid: float | None = None,
    expression_type: str = "manual",
    state: str = "paused",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "adGroupId": ad_group_id,
        "expression": expression,
        "expressionType": expression_type.lower(),
        "state": _lower_state(state),
    }
    if bid is not None:
        payload["bid"] = _money_string(bid)
    return payload


def build_sd_target_update_payload(
    target_id: str,
    state: str | None = None,
    bid: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"targetId": target_id}
    if state:
        payload["state"] = _lower_state(state)
    if bid is not None:
        payload["bid"] = _money_string(bid)
    return payload


def build_sd_location_payload(
    ad_group_id: str,
    location_id: str,
    expression_type: str = "manual",
    state: str = "paused",
) -> dict[str, Any]:
    return {
        "adGroupId": ad_group_id,
        "expressionType": expression_type.lower(),
        "state": _lower_state(state),
        "expression": [{"type": "location", "value": location_id}],
    }


def build_sd_location_update_payload(
    location_target_id: str,
    state: str,
) -> dict[str, Any]:
    return {"targetId": location_target_id, "state": _lower_state(state)}


def normalize_sd_predicates(
    predicate: tuple[str, ...] | list[str],
    asin: str | None = None,
    category_id: str | None = None,
    audience_id: str | None = None,
) -> list[dict[str, Any]]:
    expression: list[dict[str, Any]] = []
    if asin:
        expression.append({"type": "asinSameAs", "value": asin})
    if category_id:
        expression.append({"type": "asinCategorySameAs", "value": category_id})
    if audience_id:
        expression.append(
            {
                "type": "audience",
                "value": [{"type": "audienceSameAs", "value": audience_id}],
            }
        )
    for raw_predicate in predicate:
        raw = raw_predicate.strip()
        if not raw:
            continue
        if "=" in raw:
            predicate_type, value = raw.split("=", 1)
        elif ":" in raw:
            predicate_type, value = raw.split(":", 1)
        else:
            predicate_type, value = raw, ""
        item: dict[str, Any] = {"type": predicate_type.strip()}
        if value.strip():
            item["value"] = value.strip()
        expression.append(item)
    if not expression:
        raise ValueError(
            "At least one of --asin, --category-id, --audience-id, or --predicate is required."
        )
    return expression


def build_sd_audience_taxonomy_payload(
    category_path: tuple[str, ...] | list[str],
    ad_type: str = "SD",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"adType": ad_type}
    if category_path:
        payload["categoryPath"] = list(category_path)
    return payload


def build_sd_audience_discovery_payload(
    category_path: tuple[str, ...] | list[str] = (),
    audience_name: str | None = None,
    ad_type: str = "SD",
) -> dict[str, Any]:
    filters: list[dict[str, Any]] = []
    if category_path:
        filters.append({"field": "categoryPath", "values": list(category_path)})
    if audience_name:
        filters.append({"field": "audienceName", "values": [audience_name]})
    return {"adType": ad_type, "filters": filters}


def build_sd_snapshot_payload(tactic: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if tactic:
        payload["tactic"] = tactic
    return payload


def build_sd_budget_rule_create_payload(
    name: str,
    rule_type: str,
    increase_type: str,
    increase_value: float,
    recurrence_type: str = "DAILY",
    start_date: str | None = None,
    end_date: str | None = None,
    metric_name: str | None = None,
    threshold: float | None = None,
    comparison_operator: str | None = None,
) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "name": name,
        "ruleType": rule_type.upper(),
        "recurrence": {"type": recurrence_type.upper()},
        "budgetIncreaseBy": {
            "type": increase_type.upper(),
            "value": increase_value,
        },
    }
    if start_date or end_date:
        date_range: dict[str, str] = {}
        if start_date:
            date_range["startDate"] = _sd_date(start_date)
        if end_date:
            date_range["endDate"] = _sd_date(end_date)
        rule["duration"] = {"dateRangeTypeRuleDuration": date_range}
    if metric_name and threshold is not None and comparison_operator:
        rule["performanceMeasureCondition"] = {
            "metricName": metric_name.upper(),
            "threshold": threshold,
            "comparisonOperator": comparison_operator.upper(),
        }
    return {"budgetRulesDetails": [rule]}


def build_sd_budget_rule_update_payload(
    rule_id: str,
    state: str | None = None,
    name: str | None = None,
    increase_type: str | None = None,
    increase_value: float | None = None,
) -> dict[str, Any]:
    rule: dict[str, Any] = {"ruleId": rule_id}
    if state:
        rule["ruleState"] = state.upper()
    if name:
        rule["name"] = name
    if increase_type and increase_value is not None:
        rule["budgetIncreaseBy"] = {
            "type": increase_type.upper(),
            "value": increase_value,
        }
    return {"budgetRulesDetails": [rule]}


def build_sd_budget_rule_association_payload(rule_id: str) -> dict[str, Any]:
    return {"budgetRuleIds": [rule_id]}


def build_sd_budget_usage_payload(campaign_ids: tuple[str, ...] | list[str]) -> dict[str, Any]:
    return {"campaignIds": list(campaign_ids)}


def normalize_sd_campaign_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = _pick(
        row,
        (
            "campaignId",
            "name",
            "state",
            "tactic",
            "budget",
            "budgetType",
            "costType",
            "startDate",
            "endDate",
        ),
    )
    normalized.update(metadata_time_fields(row))
    return normalized


def normalize_sd_ad_group_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = _pick(
        row,
        (
            "adGroupId",
            "campaignId",
            "name",
            "state",
            "defaultBid",
            "bidOptimization",
            "creativeType",
        ),
    )
    normalized.update(metadata_time_fields(row))
    return normalized


def normalize_sd_product_ad_row(row: dict[str, Any]) -> dict[str, Any]:
    return _pick(
        row,
        (
            "adId",
            "productAdId",
            "campaignId",
            "adGroupId",
            "adName",
            "state",
            "sku",
            "asin",
            "landingPageType",
            "landingPageURL",
        ),
    )


def normalize_sd_target_row(row: dict[str, Any]) -> dict[str, Any]:
    return _pick(
        row,
        (
            "targetId",
            "campaignId",
            "adGroupId",
            "state",
            "bid",
            "expressionType",
            "expression",
            "resolvedExpression",
        ),
    )


def normalize_sd_budget_rule_row(row: dict[str, Any]) -> dict[str, Any]:
    return _pick(
        row,
        (
            "ruleId",
            "name",
            "ruleState",
            "ruleType",
            "duration",
            "recurrence",
            "budgetIncreaseBy",
            "performanceMeasureCondition",
        ),
    )


def normalize_sd_report_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if key.endswith("Id") or key in {"campaignId", "adGroupId", "targetId", "adId"}:
            normalized[key] = str(value) if value is not None else ""
        elif key in {
            "impressions",
            "clicks",
            "purchases",
            "purchases14d",
            "unitsSold",
            "unitsSold14d",
        }:
            normalized[key] = _int(value)
        elif key in {"cost", "sales", "sales14d", "bid", "budget"}:
            normalized[key] = _float(value)
        else:
            normalized[key] = value
    return normalized


def _pick(row: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if key in row}


def _sd_date(value: str) -> str:
    return value.replace("-", "")


def _money_string(value: float) -> str:
    return f"{value:.2f}"


def _lower_state(value: str) -> str:
    return value.strip().lower()


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

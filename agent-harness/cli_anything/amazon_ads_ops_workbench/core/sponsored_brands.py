from __future__ import annotations

from typing import Any

from .metadata import metadata_time_fields

SB_MEDIA_PATH_TOKENS = (
    "/ads",
    "/creative",
    "/creatives",
    "/assets",
    "brandvideo",
    "productcollection",
    "storespotlight",
    "video",
    "image",
    "logo",
    "media",
)

SB_MEDIA_PAYLOAD_TOKENS = (
    "creative",
    "asset",
    "image",
    "video",
    "logo",
    "media",
    "brandlogo",
    "customimage",
    "landingpage",
)


def assert_sb_raw_allowed(path: str, payload: Any | None = None) -> None:
    if not path.startswith("/sb/"):
        raise ValueError("Raw SB requests must use a path that starts with /sb/.")
    lowered_path = path.lower()
    for token in SB_MEDIA_PATH_TOKENS:
        if token in lowered_path:
            raise ValueError(
                "Raw SB requests to ads, creative, asset, image, video, logo, or media paths are blocked."
            )
    blocked_key = find_blocked_media_payload_key(payload)
    if blocked_key:
        raise ValueError(
            f"Raw SB request payload contains blocked media/creative key: {blocked_key}"
        )


def find_blocked_media_payload_key(value: Any) -> str:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in SB_MEDIA_PAYLOAD_TOKENS):
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


def build_sb_campaigns_filter(
    campaign_id: str | None = None,
    state_filter: str | None = None,
    portfolio_id: str | None = None,
    name: str | None = None,
    max_results: int = 100,
    include_extended_data: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"maxResults": max_results}
    if campaign_id:
        payload["campaignIdFilter"] = {"include": [campaign_id]}
    if state_filter:
        payload["stateFilter"] = {"include": [_upper_state(state_filter)]}
    if portfolio_id:
        payload["portfolioIdFilter"] = {"include": [portfolio_id]}
    if name:
        payload["nameFilter"] = {"queryTermMatchType": "EXACT_MATCH", "include": [name]}
    if include_extended_data:
        payload["includeExtendedDataFields"] = True
    return payload


def build_sb_campaign_create_payload(
    name: str,
    budget: float,
    budget_type: str = "DAILY",
    state: str = "PAUSED",
    start_date: str | None = None,
    end_date: str | None = None,
    portfolio_id: str | None = None,
    brand_entity_id: str | None = None,
    cost_type: str | None = None,
    goal: str | None = None,
    product_location: str | None = None,
    smart_default: tuple[str, ...] | list[str] | None = None,
    bid_optimization: bool | None = None,
    bid_optimization_strategy: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "budget": budget,
        "budgetType": budget_type.upper(),
        "state": _upper_state(state),
    }
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    if portfolio_id:
        payload["portfolioId"] = portfolio_id
    if brand_entity_id:
        payload["brandEntityId"] = brand_entity_id
    if cost_type:
        payload["costType"] = cost_type.upper()
    if goal:
        payload["goal"] = goal.upper()
    if product_location:
        payload["productLocation"] = product_location.upper()
    if smart_default:
        payload["smartDefault"] = [item.upper() for item in smart_default]
    bidding = _build_sb_bidding(bid_optimization, bid_optimization_strategy)
    if bidding:
        payload["bidding"] = bidding
    return payload


def build_sb_campaign_update_payload(
    campaign_id: str,
    state: str | None = None,
    budget: float | None = None,
    name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    portfolio_id: str | None = None,
    clear_end_date: bool = False,
    clear_portfolio_id: bool = False,
    bid_optimization: bool | None = None,
    bid_optimization_strategy: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"campaignId": campaign_id}
    if state:
        payload["state"] = _upper_state(state)
    if budget is not None:
        payload["budget"] = budget
    if name:
        payload["name"] = name
    if start_date:
        payload["startDate"] = start_date
    if clear_end_date:
        payload["endDate"] = None
    elif end_date:
        payload["endDate"] = end_date
    if clear_portfolio_id:
        payload["portfolioId"] = None
    elif portfolio_id:
        payload["portfolioId"] = portfolio_id
    bidding = _build_sb_bidding(bid_optimization, bid_optimization_strategy)
    if bidding:
        payload["bidding"] = bidding
    return payload


def build_sb_campaign_archive_payload(campaign_id: str) -> dict[str, Any]:
    return {"campaignIdFilter": {"include": [campaign_id]}}


def build_sb_ad_groups_filter(
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    state_filter: str | None = None,
    name: str | None = None,
    max_results: int = 100,
    include_extended_data: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"maxResults": max_results}
    if campaign_id:
        payload["campaignIdFilter"] = {"include": [campaign_id]}
    if ad_group_id:
        payload["adGroupIdFilter"] = {"include": [ad_group_id]}
    if state_filter:
        payload["stateFilter"] = {"include": [_upper_state(state_filter)]}
    if name:
        payload["nameFilter"] = {"queryTermMatchType": "EXACT_MATCH", "include": [name]}
    if include_extended_data:
        payload["includeExtendedDataFields"] = True
    return payload


def build_sb_ad_group_create_payload(
    campaign_id: str,
    name: str,
    state: str = "PAUSED",
) -> dict[str, Any]:
    return {
        "campaignId": campaign_id,
        "name": name,
        "state": _upper_state(state),
    }


def build_sb_ad_group_update_payload(
    ad_group_id: str,
    state: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"adGroupId": ad_group_id}
    if state:
        payload["state"] = _upper_state(state)
    if name:
        payload["name"] = name
    return payload


def build_sb_ad_group_archive_payload(ad_group_id: str) -> dict[str, Any]:
    return {"adGroupIdFilter": {"include": [ad_group_id]}}


def build_sb_legacy_filter(
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    entity_id: str | None = None,
    state_filter: str | None = None,
    locale: str | None = None,
    entity_key: str = "keywordId",
) -> dict[str, str]:
    payload: dict[str, str] = {}
    if campaign_id:
        payload["campaignId"] = campaign_id
    if ad_group_id:
        payload["adGroupId"] = ad_group_id
    if entity_id:
        payload[entity_key] = entity_id
    if state_filter:
        payload["state"] = _lower_state(state_filter)
    if locale:
        payload["locale"] = locale
    return payload


def build_sb_keyword_create_payload(
    campaign_id: str,
    ad_group_id: str,
    keyword_text: str,
    match_type: str,
    bid: float | None = None,
    native_language_keyword: str | None = None,
    native_language_locale: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "keywordText": keyword_text,
        "matchType": _sb_match_type(match_type),
    }
    if bid is not None:
        payload["bid"] = bid
    if native_language_keyword:
        payload["nativeLanguageKeyword"] = native_language_keyword
    if native_language_locale:
        payload["nativeLanguageLocale"] = native_language_locale
    return payload


def build_sb_keyword_update_payload(
    keyword_id: str,
    bid: float | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"keywordId": keyword_id}
    if bid is not None:
        payload["bid"] = bid
    if state:
        payload["state"] = _lower_state(state)
    return payload


def build_sb_negative_keyword_payload(
    campaign_id: str,
    keyword_text: str,
    match_type: str,
    ad_group_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "keywordText": keyword_text,
        "matchType": _sb_negative_match_type(match_type),
    }
    if ad_group_id:
        payload["adGroupId"] = ad_group_id
    return payload


def build_sb_negative_keyword_update_payload(
    keyword_id: str,
    state: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"keywordId": keyword_id}
    if state:
        payload["state"] = _lower_state(state)
    return payload


def build_sb_target_payload(
    campaign_id: str,
    ad_group_id: str,
    expression: list[dict[str, Any]],
    bid: float | None = None,
    state: str = "enabled",
    expression_type: str = "manual",
) -> dict[str, Any]:
    if not expression:
        raise ValueError("At least one SB target expression is required.")
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "expression": expression,
        "expressionType": expression_type.lower(),
        "state": _lower_state(state),
    }
    if bid is not None:
        payload["bid"] = bid
    return payload


def build_sb_target_update_payload(
    target_id: str,
    bid: float | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"targetId": target_id}
    if bid is not None:
        payload["bid"] = bid
    if state:
        payload["state"] = _lower_state(state)
    return payload


def build_sb_negative_target_payload(
    campaign_id: str,
    expression: list[dict[str, Any]],
    ad_group_id: str | None = None,
    state: str = "enabled",
    expression_type: str = "manual",
) -> dict[str, Any]:
    if not expression:
        raise ValueError("At least one SB negative target expression is required.")
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "expression": expression,
        "state": _lower_state(state),
    }
    if ad_group_id:
        payload["adGroupId"] = ad_group_id
        payload["expressionType"] = expression_type.lower()
    return payload


def build_sb_negative_target_update_payload(
    target_id: str,
    state: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"targetId": target_id}
    if state:
        payload["state"] = _lower_state(state)
    return payload


def sb_asin_expression(asin: str) -> list[dict[str, Any]]:
    return [{"type": "asinSameAs", "value": asin}]


def sb_category_expression(category_id: str) -> list[dict[str, Any]]:
    return [{"type": "asinCategorySameAs", "value": category_id}]


def normalize_sb_predicates(
    predicates: tuple[str, ...],
    asin: str | None = None,
    category_id: str | None = None,
    brand_refinement_id: str | None = None,
) -> list[dict[str, Any]]:
    expression: list[dict[str, Any]] = []
    if asin:
        expression.extend(sb_asin_expression(asin))
    if category_id:
        expression.extend(sb_category_expression(category_id))
    if brand_refinement_id:
        expression.append({"type": "asinBrandSameAs", "value": brand_refinement_id})
    for raw_predicate in predicates:
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
            "At least one of --asin, --category-id, --brand-refinement-id, or --predicate is required."
        )
    return expression


def normalize_sb_campaign_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "campaignId": _string_id(row.get("campaignId") or row.get("id")),
        "name": str(row.get("name") or ""),
        "state": str(row.get("state") or ""),
        "budget": _coerce_float(row.get("budget")),
        "budgetType": str(row.get("budgetType") or ""),
        "startDate": str(row.get("startDate") or ""),
        "endDate": str(row.get("endDate") or ""),
        "portfolioId": _string_id(row.get("portfolioId")),
        "goal": str(row.get("goal") or ""),
        "costType": str(row.get("costType") or ""),
        "isMultiAdGroupsEnabled": row.get("isMultiAdGroupsEnabled"),
        **metadata_time_fields(row),
    }


def normalize_sb_ad_group_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "adGroupId": _string_id(row.get("adGroupId") or row.get("id")),
        "campaignId": _string_id(row.get("campaignId")),
        "name": str(row.get("name") or ""),
        "state": str(row.get("state") or ""),
        **metadata_time_fields(row),
    }


def normalize_sb_keyword_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "keywordId": _string_id(row.get("keywordId") or row.get("id")),
        "campaignId": _string_id(row.get("campaignId")),
        "adGroupId": _string_id(row.get("adGroupId")),
        "keywordText": str(row.get("keywordText") or row.get("keyword") or ""),
        "matchType": str(row.get("matchType") or ""),
        "state": str(row.get("state") or ""),
        "bid": _coerce_float(row.get("bid")),
    }


def normalize_sb_negative_keyword_row(row: dict[str, Any], scope: str) -> dict[str, Any]:
    return {
        "negativeKeywordId": _string_id(
            row.get("keywordId") or row.get("negativeKeywordId") or row.get("id")
        ),
        "campaignId": _string_id(row.get("campaignId")),
        "adGroupId": _string_id(row.get("adGroupId")),
        "keywordText": str(row.get("keywordText") or row.get("keyword") or ""),
        "matchType": str(row.get("matchType") or ""),
        "state": str(row.get("state") or ""),
        "scope": scope,
    }


def normalize_sb_target_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "targetId": _string_id(row.get("targetId") or row.get("targetingClauseId") or row.get("id")),
        "campaignId": _string_id(row.get("campaignId")),
        "adGroupId": _string_id(row.get("adGroupId")),
        "expressionType": str(row.get("expressionType") or ""),
        "expression": row.get("expression") or [],
        "resolvedExpression": row.get("resolvedExpression") or [],
        "state": str(row.get("state") or ""),
        "bid": _coerce_float(row.get("bid")),
    }


def normalize_sb_negative_target_row(row: dict[str, Any], scope: str) -> dict[str, Any]:
    return {
        "negativeTargetId": _string_id(
            row.get("targetId")
            or row.get("negativeTargetId")
            or row.get("negativeTargetingClauseId")
            or row.get("id")
        ),
        "campaignId": _string_id(row.get("campaignId")),
        "adGroupId": _string_id(row.get("adGroupId")),
        "expressionType": str(row.get("expressionType") or ""),
        "expression": row.get("expression") or [],
        "state": str(row.get("state") or ""),
        "scope": scope,
    }


def _build_sb_bidding(
    bid_optimization: bool | None,
    bid_optimization_strategy: str | None,
) -> dict[str, Any]:
    bidding: dict[str, Any] = {}
    if bid_optimization is not None:
        bidding["bidOptimization"] = bid_optimization
    if bid_optimization_strategy:
        bidding["bidOptimizationStrategy"] = bid_optimization_strategy.upper()
    return bidding


def _upper_state(state: str) -> str:
    return state.replace("-", "_").upper()


def _lower_state(state: str) -> str:
    return state.replace("_", "").replace("-", "").lower()


def _sb_match_type(match_type: str) -> str:
    normalized = match_type.strip().lower()
    aliases = {
        "broad": "broad",
        "phrase": "phrase",
        "exact": "exact",
    }
    return aliases.get(normalized, normalized)


def _sb_negative_match_type(match_type: str) -> str:
    normalized = match_type.strip().replace("_", "").replace("-", "").lower()
    aliases = {
        "negativeexact": "negativeExact",
        "exact": "negativeExact",
        "negativephrase": "negativePhrase",
        "phrase": "negativePhrase",
    }
    return aliases.get(normalized, match_type)


def _string_id(value: Any) -> str:
    return "" if value is None else str(value)


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

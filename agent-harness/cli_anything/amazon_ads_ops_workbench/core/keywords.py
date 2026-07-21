from __future__ import annotations

from typing import Any


def build_keywords_filter(
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    state_filter: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"maxResults": 100}
    if campaign_id:
        payload["campaignIdFilter"] = {"include": [campaign_id]}
    if ad_group_id:
        payload["adGroupIdFilter"] = {"include": [ad_group_id]}
    if state_filter:
        payload["stateFilter"] = {"include": [state_filter.upper()]}
    return payload


def build_ad_groups_filter(
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    state_filter: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"maxResults": 100}
    if campaign_id:
        payload["campaignIdFilter"] = {"include": [campaign_id]}
    if ad_group_id:
        payload["adGroupIdFilter"] = {"include": [ad_group_id]}
    if state_filter:
        payload["stateFilter"] = {"include": [state_filter.upper()]}
    return payload


def build_product_ads_filter(
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    product_ad_id: str | None = None,
    state_filter: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"maxResults": 100}
    if campaign_id:
        payload["campaignIdFilter"] = {"include": [campaign_id]}
    if ad_group_id:
        payload["adGroupIdFilter"] = {"include": [ad_group_id]}
    if product_ad_id:
        payload["productAdIdFilter"] = {"include": [product_ad_id]}
    if state_filter:
        payload["stateFilter"] = {"include": [state_filter.upper()]}
    return payload


def build_targets_filter(
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    target_id: str | None = None,
    state_filter: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"maxResults": 100}
    if campaign_id:
        payload["campaignIdFilter"] = {"include": [campaign_id]}
    if ad_group_id:
        payload["adGroupIdFilter"] = {"include": [ad_group_id]}
    if target_id:
        payload["targetIdFilter"] = {"include": [target_id]}
    if state_filter:
        payload["stateFilter"] = {"include": [state_filter.upper()]}
    return payload


def build_negative_list_filter(
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    state_filter: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"maxResults": 100}
    if campaign_id:
        payload["campaignIdFilter"] = {"include": [campaign_id]}
    if ad_group_id:
        payload["adGroupIdFilter"] = {"include": [ad_group_id]}
    if state_filter:
        payload["stateFilter"] = {"include": [state_filter.upper()]}
    return payload


def build_ad_group_create_payload(
    campaign_id: str,
    name: str,
    default_bid: float,
    state: str = "ENABLED",
) -> dict[str, Any]:
    return {
        "campaignId": campaign_id,
        "name": name,
        "defaultBid": default_bid,
        "state": state.upper(),
    }


def build_ad_group_state_payload(
    campaign_id: str,
    ad_group_id: str,
    state: str,
    default_bid: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "state": state.upper(),
    }
    if default_bid is not None:
        payload["defaultBid"] = default_bid
    return payload


def build_keyword_create_payload(
    campaign_id: str,
    ad_group_id: str,
    keyword_text: str,
    match_type: str,
    bid: float | None = None,
    state: str = "ENABLED",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "keywordText": keyword_text,
        "matchType": match_type.upper(),
        "state": state.upper(),
    }
    if bid is not None:
        payload["bid"] = bid
    return payload


def build_product_ad_create_payload(
    campaign_id: str,
    ad_group_id: str,
    sku: str | None = None,
    asin: str | None = None,
    state: str = "ENABLED",
) -> dict[str, Any]:
    if bool(sku) == bool(asin):
        raise ValueError("Exactly one of sku or asin is required.")
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "state": state.upper(),
    }
    if sku:
        payload["sku"] = sku
    if asin:
        payload["asin"] = asin
    return payload


def build_product_ad_state_payload(
    product_ad_id: str,
    state: str,
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "productAdId": product_ad_id,
        "state": state.upper(),
    }
    if campaign_id:
        payload["campaignId"] = campaign_id
    if ad_group_id:
        payload["adGroupId"] = ad_group_id
    return payload


def build_asin_target_create_payload(
    campaign_id: str,
    ad_group_id: str,
    asin: str,
    bid: float | None = None,
    state: str = "ENABLED",
    expression_type: str = "MANUAL",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "state": state.upper(),
        "expressionType": expression_type.upper(),
        "expression": [
            {
                "type": "ASIN_SAME_AS",
                "value": asin,
            }
        ],
    }
    if bid is not None:
        payload["bid"] = bid
    return payload


def build_target_state_payload(
    target_id: str,
    state: str,
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    bid: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "targetId": target_id,
        "state": state.upper(),
    }
    if campaign_id:
        payload["campaignId"] = campaign_id
    if ad_group_id:
        payload["adGroupId"] = ad_group_id
    if bid is not None:
        payload["bid"] = bid
    return payload


def build_ad_group_negative_payload(
    campaign_id: str,
    ad_group_id: str,
    keyword_text: str,
    match_type: str,
    state: str = "ENABLED",
) -> dict[str, Any]:
    return {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "keywordText": keyword_text,
        "matchType": match_type,
        "state": state,
    }


def build_campaign_negative_payload(
    campaign_id: str,
    keyword_text: str,
    match_type: str,
    state: str = "ENABLED",
) -> dict[str, Any]:
    return {
        "campaignId": campaign_id,
        "keywordText": keyword_text,
        "matchType": match_type,
        "state": state,
    }


def build_keyword_edit_payload(
    campaign_id: str,
    ad_group_id: str,
    keyword_id: str,
    bid: float,
    state: str = "ENABLED",
) -> dict[str, Any]:
    return {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "keywordId": keyword_id,
        "bid": bid,
        "state": state,
    }


def build_keyword_state_payload(
    campaign_id: str,
    ad_group_id: str,
    keyword_id: str,
    state: str,
    bid: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaignId": campaign_id,
        "adGroupId": ad_group_id,
        "keywordId": keyword_id,
        "state": state.upper(),
    }
    if bid is not None:
        payload["bid"] = bid
    return payload


def build_negative_state_payload(
    keyword_id: str,
    state: str,
) -> dict[str, Any]:
    return {
        "keywordId": keyword_id,
        "state": state.upper(),
    }


def normalize_keyword_row(row: dict[str, Any]) -> dict[str, Any]:
    keyword_id = row.get("keywordId") or row.get("keyword_id") or row.get("id")
    bid = row.get("bid")
    try:
        bid_value = float(bid) if bid is not None else None
    except (TypeError, ValueError):
        bid_value = None
    return {
        "keywordId": "" if keyword_id is None else str(keyword_id),
        "keywordText": str(row.get("keywordText") or row.get("keyword") or ""),
        "matchType": str(row.get("matchType") or ""),
        "bid": bid_value,
        "state": str(row.get("state") or ""),
        "campaignId": "" if row.get("campaignId") is None else str(row.get("campaignId")),
        "adGroupId": "" if row.get("adGroupId") is None else str(row.get("adGroupId")),
    }


def normalize_ad_group_row(row: dict[str, Any]) -> dict[str, Any]:
    default_bid = row.get("defaultBid")
    try:
        default_bid_value = float(default_bid) if default_bid is not None else None
    except (TypeError, ValueError):
        default_bid_value = None
    ad_group_id = row.get("adGroupId") or row.get("adGroup_id") or row.get("id")
    return {
        "adGroupId": "" if ad_group_id is None else str(ad_group_id),
        "campaignId": "" if row.get("campaignId") is None else str(row.get("campaignId")),
        "name": str(row.get("name") or ""),
        "defaultBid": default_bid_value,
        "state": str(row.get("state") or ""),
    }


def normalize_product_ad_row(row: dict[str, Any]) -> dict[str, Any]:
    product_ad_id = row.get("productAdId") or row.get("adId") or row.get("id")
    return {
        "productAdId": "" if product_ad_id is None else str(product_ad_id),
        "campaignId": "" if row.get("campaignId") is None else str(row.get("campaignId")),
        "adGroupId": "" if row.get("adGroupId") is None else str(row.get("adGroupId")),
        "sku": str(row.get("sku") or ""),
        "asin": str(row.get("asin") or ""),
        "state": str(row.get("state") or ""),
    }


def normalize_target_row(row: dict[str, Any]) -> dict[str, Any]:
    target_id = row.get("targetId") or row.get("targetingClauseId") or row.get("id")
    bid = row.get("bid")
    return {
        "targetId": "" if target_id is None else str(target_id),
        "campaignId": "" if row.get("campaignId") is None else str(row.get("campaignId")),
        "adGroupId": "" if row.get("adGroupId") is None else str(row.get("adGroupId")),
        "expressionType": str(row.get("expressionType") or ""),
        "expression": row.get("expression") or [],
        "bid": _coerce_float(bid),
        "state": str(row.get("state") or ""),
    }


def normalize_negative_row(row: dict[str, Any], scope: str) -> dict[str, Any]:
    keyword_id = (
        row.get("negativeKeywordId")
        or row.get("keywordId")
        or row.get("keyword_id")
        or row.get("id")
    )
    return {
        "negativeKeywordId": "" if keyword_id is None else str(keyword_id),
        "keywordText": str(row.get("keywordText") or row.get("keyword") or ""),
        "matchType": str(row.get("matchType") or ""),
        "state": str(row.get("state") or ""),
        "campaignId": "" if row.get("campaignId") is None else str(row.get("campaignId")),
        "adGroupId": "" if row.get("adGroupId") is None else str(row.get("adGroupId")),
        "scope": scope,
    }


def normalize_portfolio_row(row: dict[str, Any]) -> dict[str, Any]:
    portfolio_id = row.get("portfolioId") or row.get("portfolio_id") or row.get("id")
    budget = row.get("budget")
    try:
        budget_value = float(budget) if budget is not None else None
    except (TypeError, ValueError):
        budget_value = None
    budget_policy = ""
    currency_code = ""
    if isinstance(budget, dict):
        budget_value = budget_value or _coerce_float(budget.get("amount"))
        budget_policy = str(budget.get("policy") or "")
        currency_code = str(budget.get("currencyCode") or "")
    return {
        "portfolioId": "" if portfolio_id is None else str(portfolio_id),
        "name": str(row.get("name") or ""),
        "state": str(row.get("state") or ""),
        "budget": budget_value,
        "budgetPolicy": budget_policy,
        "currencyCode": currency_code,
        "inBudget": row.get("inBudget"),
    }


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

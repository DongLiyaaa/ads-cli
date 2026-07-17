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

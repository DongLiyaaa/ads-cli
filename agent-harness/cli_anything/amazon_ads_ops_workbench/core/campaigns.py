from __future__ import annotations

from typing import Any

PLACEMENT_PREDICATES = {
    "top_of_search": "PLACEMENT_TOP",
    "product_pages": "PLACEMENT_PRODUCT_PAGE",
    "rest_of_search": "PLACEMENT_REST_OF_SEARCH",
}


def build_campaign_state_payload(
    campaign_id: str,
    state: str,
) -> dict[str, Any]:
    return {
        "campaignId": campaign_id,
        "state": state.upper(),
    }


def build_campaign_create_payload(
    name: str,
    targeting_type: str,
    budget: float,
    start_date: str,
    budget_type: str = "DAILY",
    state: str = "ENABLED",
    strategy: str | None = None,
    portfolio_id: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "targetingType": targeting_type.upper(),
        "state": state.upper(),
        "budget": {
            "budgetType": budget_type.upper(),
            "budget": budget,
        },
        "startDate": start_date,
    }
    if strategy:
        payload["dynamicBidding"] = {"strategy": strategy.upper()}
    if portfolio_id:
        payload["portfolioId"] = portfolio_id
    if end_date:
        payload["endDate"] = end_date
    return payload


def build_campaign_budget_payload(
    campaign_id: str,
    budget: float,
    budget_type: str = "DAILY",
) -> dict[str, Any]:
    return {
        "campaignId": campaign_id,
        "budget": {
            "budgetType": budget_type.upper(),
            "budget": budget,
        },
    }


def build_campaign_placement_bid_payload(
    campaign_id: str,
    top_of_search: int | None = None,
    product_pages: int | None = None,
    rest_of_search: int | None = None,
    strategy: str | None = None,
) -> dict[str, Any]:
    placement_bidding = []
    placement_values = {
        "top_of_search": top_of_search,
        "product_pages": product_pages,
        "rest_of_search": rest_of_search,
    }
    for placement_key, percentage in placement_values.items():
        if percentage is None:
            continue
        if percentage < 0 or percentage > 900:
            raise ValueError(
                "Placement bid adjustment percentage must be between 0 and 900."
            )
        placement_bidding.append(
            {
                "placement": PLACEMENT_PREDICATES[placement_key],
                "percentage": int(percentage),
            }
        )

    if not placement_bidding:
        raise ValueError("At least one placement bid adjustment percentage is required.")

    dynamic_bidding: dict[str, Any] = {"placementBidding": placement_bidding}
    if strategy:
        dynamic_bidding["strategy"] = strategy.upper()

    return {
        "campaignId": campaign_id,
        "dynamicBidding": dynamic_bidding,
    }


def build_portfolio_create_payload(
    name: str,
    state: str = "ENABLED",
    budget: float | None = None,
    budget_policy: str | None = None,
    budget_start_date: str | None = None,
    budget_end_date: str | None = None,
    currency_code: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "state": state.upper(),
    }
    if budget is not None:
        budget_payload: dict[str, Any] = {"amount": budget}
        if budget_policy:
            budget_payload["policy"] = budget_policy
        if budget_start_date:
            budget_payload["startDate"] = budget_start_date
        if budget_end_date:
            budget_payload["endDate"] = budget_end_date
        if currency_code:
            budget_payload["currencyCode"] = currency_code.upper()
        payload["budget"] = budget_payload
    return payload


def build_portfolio_state_payload(
    portfolio_id: str,
    state: str,
) -> dict[str, Any]:
    return {
        "portfolioId": portfolio_id,
        "state": state.upper(),
    }

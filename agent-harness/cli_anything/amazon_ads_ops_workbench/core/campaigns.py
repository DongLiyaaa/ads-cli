from __future__ import annotations

from typing import Any


def build_campaign_state_payload(
    campaign_id: str,
    state: str,
) -> dict[str, Any]:
    return {
        "campaignId": campaign_id,
        "state": state.upper(),
    }


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


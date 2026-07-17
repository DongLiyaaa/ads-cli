from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AuthHealth:
    ok: bool
    mode: str
    status: str
    missing_credentials: list[str]
    region: str
    marketplace: str
    profile_id: str


@dataclass
class CampaignSummary:
    total: str
    budget_alerts: str
    transferable_budget: str
    high_risk: str
    note: str

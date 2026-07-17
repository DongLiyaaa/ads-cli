from __future__ import annotations

import os
from dataclasses import dataclass

REGION_ENDPOINTS = {
    "NA": "https://advertising-api.amazon.com",
    "EU": "https://advertising-api-eu.amazon.com",
    "FE": "https://advertising-api-fe.amazon.com",
}


@dataclass(frozen=True)
class AdsEnvironment:
    client_id: str
    client_secret: str
    refresh_token: str
    profile_id: str
    region: str
    marketplace: str


def normalize_region(region_value: str | None) -> str:
    region = (region_value or "NA").strip().upper()
    return region if region in REGION_ENDPOINTS else "NA"


def load_ads_environment(source: dict[str, str] | None = None) -> AdsEnvironment:
    raw = source or os.environ
    return AdsEnvironment(
        client_id=(raw.get("AMAZON_ADS_CLIENT_ID") or "").strip(),
        client_secret=(raw.get("AMAZON_ADS_CLIENT_SECRET") or "").strip(),
        refresh_token=(raw.get("AMAZON_ADS_REFRESH_TOKEN") or "").strip(),
        profile_id=(raw.get("AMAZON_ADS_PROFILE_ID") or "").strip(),
        region=normalize_region(raw.get("AMAZON_ADS_REGION")),
        marketplace=(raw.get("AMAZON_ADS_MARKETPLACE") or "US").strip().upper(),
    )


def get_region_base_url(region: str) -> str:
    return REGION_ENDPOINTS.get(region, REGION_ENDPOINTS["NA"])

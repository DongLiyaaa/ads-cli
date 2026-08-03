from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .client import AmazonAdsClient
from .env import AdsEnvironment
from .metadata import metadata_time_fields


def find_missing_credentials(env: AdsEnvironment) -> list[str]:
    missing = []
    if not env.client_id:
        missing.append("CLIENT_ID")
    if not env.client_secret:
        missing.append("CLIENT_SECRET")
    if not env.refresh_token:
        missing.append("REFRESH_TOKEN")
    return missing


def pick_profile_id(profiles: list[dict[str, Any]], marketplace: str) -> str:
    normalized_marketplace = marketplace.upper()
    direct_match = None
    for profile in profiles:
        country = str(profile.get("countryCode") or "").upper()
        marketplace_string = str(
            profile.get("marketplaceString") or profile.get("marketplaceStringId") or ""
        ).upper()
        if country == normalized_marketplace or normalized_marketplace in marketplace_string:
            direct_match = profile
            break
    chosen = direct_match or (profiles[0] if profiles else None)
    if not chosen:
        return ""
    profile_id = chosen.get("profileId")
    return "" if profile_id is None else str(profile_id)


def extract_campaign_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("campaigns", "results", "items"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def build_missing_credential_snapshot(
    env: AdsEnvironment,
    marketplace: str,
    missing_credentials: list[str],
) -> dict[str, Any]:
    return {
        "meta": {
            "mode": "mock",
            "status": "attention",
            "sourceLabel": "Mock fallback",
            "syncLabel": f"缺少 {' / '.join(missing_credentials)}",
            "detail": "Amazon Ads OAuth 参数不完整，CLI 回退到演示态结构。",
            "coverage": "等待 OAuth 完成",
            "missingCredentials": missing_credentials,
            "profileId": env.profile_id,
        },
        "data": {
            "campaignSummary": {
                "total": "0",
                "budgetAlerts": "0",
                "transferableBudget": "0",
                "highRisk": "0",
                "note": "缺少凭证，未触发实时拉取",
            },
            "campaigns": [],
            "connections": [
                {
                    "name": f"Amazon Ads OAuth / {marketplace}",
                    "status": "Pending",
                    "detail": "补齐 refresh token 后即可切到实时数据",
                }
            ],
        },
    }


def build_auth_health(env: AdsEnvironment) -> dict[str, Any]:
    missing = find_missing_credentials(env)
    if missing:
        return {
            "ok": False,
            "mode": "mock",
            "status": "attention",
            "missingCredentials": missing,
            "region": env.region,
            "marketplace": env.marketplace,
            "profileId": env.profile_id,
        }
    return {
        "ok": True,
        "mode": "live-ready",
        "status": "connected",
        "missingCredentials": [],
        "region": env.region,
        "marketplace": env.marketplace,
        "profileId": env.profile_id,
    }


def build_snapshot(env: AdsEnvironment, marketplace: str | None = None) -> dict[str, Any]:
    selected_marketplace = (marketplace or env.marketplace or "US").upper()
    missing = find_missing_credentials(env)
    if missing:
        return build_missing_credential_snapshot(env, selected_marketplace, missing)

    client = AmazonAdsClient(env)
    access_token = client.exchange_refresh_token()
    profiles = client.list_profiles(access_token)
    resolved_profile_id = env.profile_id or pick_profile_id(profiles, selected_marketplace)

    if not resolved_profile_id:
        return {
            "meta": {
                "mode": "mock",
                "status": "attention",
                "sourceLabel": "Mock fallback",
                "syncLabel": f"未找到 {selected_marketplace} 对应 profile",
                "detail": "OAuth 已可用，但当前账号下没有匹配站点的广告 profile。",
                "coverage": "OAuth 已连通，Profile 仍需确认",
                "missingCredentials": [],
                "profileId": "",
                "lastSyncedAt": format_sync_time(datetime.now(timezone.utc)),
            },
            "data": {
                "campaignSummary": {
                    "total": "0",
                    "budgetAlerts": "0",
                    "transferableBudget": "0",
                    "highRisk": "0",
                    "note": "未找到匹配 profile",
                },
                "campaigns": [],
            },
        }

    campaigns = client.list_campaigns(access_token, resolved_profile_id)
    normalized_campaigns = [
        row for row in (normalize_campaign_row(item, selected_marketplace) for item in campaigns) if row
    ]
    return {
        "meta": {
            "mode": "live",
            "status": "connected",
            "sourceLabel": f"Amazon Ads Live · {selected_marketplace}",
            "syncLabel": f"{len(normalized_campaigns)} 个 SP 活动已同步",
            "detail": "当前已接通 OAuth、Profiles 和 Sponsored Products Campaign metadata。",
            "coverage": "Profiles / SP Campaign metadata",
            "missingCredentials": [],
            "profileId": resolved_profile_id,
            "lastSyncedAt": format_sync_time(datetime.now(timezone.utc)),
        },
        "data": {
            "campaignSummary": build_campaign_summary(normalized_campaigns),
            "campaigns": normalized_campaigns,
        },
    }


def normalize_campaign_row(campaign: dict[str, Any], marketplace: str) -> dict[str, Any] | None:
    campaign_id = campaign.get("campaignId") or campaign.get("campaign_id") or campaign.get("id")
    campaign_name = campaign.get("name")
    if campaign_id is None or not campaign_name:
        return None
    state = str(
        campaign.get("state")
        or campaign.get("servingStatus")
        or campaign.get("effectiveStatus")
        or "UNKNOWN"
    ).upper()
    portfolio_id = campaign.get("portfolioId")
    budget = _extract_budget(campaign)
    return {
        "id": f"live-campaign-{campaign_id}",
        "campaignId": str(campaign_id),
        "status": map_campaign_status(state),
        "state": state,
        "campaign": str(campaign_name),
        "portfolio": f"Portfolio #{portfolio_id}" if portfolio_id else "未分配 Portfolio",
        "channel": "SP",
        "budget": budget,
        "startDate": str(campaign.get("startDate") or ""),
        "endDate": str(campaign.get("endDate") or ""),
        **metadata_time_fields(campaign),
        "spend": "需合并报表",
        "sales": "需合并报表",
        "acos": "需合并报表",
        "roas": "需合并报表",
        "topSearch": "需展示份额报表合并",
        "action": build_campaign_action(state),
        "marketplace": marketplace,
    }


def build_campaign_summary(campaigns: list[dict[str, Any]]) -> dict[str, str]:
    risk_count = sum(1 for campaign in campaigns if campaign["status"] in {"Watchlist", "Critical"})
    budget_alerts = sum(1 for campaign in campaigns if "预算" in str(campaign.get("action") or ""))
    paused_count = sum(1 for campaign in campaigns if campaign["status"] == "Watchlist")
    return {
        "total": str(len(campaigns)),
        "budgetAlerts": str(budget_alerts),
        "transferableBudget": str(paused_count),
        "highRisk": str(risk_count),
        "note": "当前 snapshot 为 campaign metadata 视角；绩效指标通过 reports create/status/download/parse 异步报表获取后合并。",
    }


def map_campaign_status(state: str) -> str:
    if state in {"ENABLED", "RUNNING"}:
        return "Stable"
    if state in {"PAUSED", "ARCHIVED"}:
        return "Watchlist"
    return "Review"


def build_campaign_action(state: str) -> str:
    if state in {"PAUSED", "ARCHIVED"}:
        return "恢复前先确认预算与投放目标"
    if state in {"ENABLED", "RUNNING"}:
        return "调用 reports 拉取绩效后复核"
    return "复核状态映射与投放设置"


def format_sync_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _extract_budget(campaign: dict[str, Any]) -> str:
    budget = campaign.get("budget")
    if isinstance(budget, dict):
        amount = budget.get("amount")
        budget_type = str(budget.get("type") or "DAILY").upper()
        if amount is not None:
            return f"{budget_type} ${float(amount):.2f}"
    if isinstance(budget, (int, float)):
        return f"DAILY ${float(budget):.2f}"
    daily_budget = campaign.get("dailyBudget")
    if isinstance(daily_budget, (int, float)):
        return f"DAILY ${float(daily_budget):.2f}"
    return "未返回预算"

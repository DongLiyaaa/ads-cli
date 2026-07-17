from __future__ import annotations

import json
import os
import shlex
from typing import Any

import click

from cli_anything.amazon_ads_ops_workbench import __version__
from cli_anything.amazon_ads_ops_workbench.core.campaigns import (
    build_campaign_budget_payload,
    build_campaign_state_payload,
)
from cli_anything.amazon_ads_ops_workbench.core.client import AmazonAdsClient
from cli_anything.amazon_ads_ops_workbench.core.env import load_ads_environment
from cli_anything.amazon_ads_ops_workbench.core.keywords import (
    build_ad_groups_filter,
    build_ad_group_negative_payload,
    build_campaign_negative_payload,
    build_keyword_edit_payload,
    build_keyword_state_payload,
    build_keywords_filter,
    build_negative_state_payload,
    build_negative_list_filter,
    normalize_ad_group_row,
    normalize_keyword_row,
    normalize_negative_row,
    normalize_portfolio_row,
)
from cli_anything.amazon_ads_ops_workbench.core.reports import (
    build_download_target_path,
    build_sp_campaign_placement_report_body,
    build_sp_keywords_report_body,
    build_sp_search_term_report_body,
    load_report_rows,
    normalize_report_status,
    normalize_sp_campaign_placement_report_row,
    normalize_search_term_report_row,
    normalize_sp_keyword_report_row,
    summarize_report_rows,
)
from cli_anything.amazon_ads_ops_workbench.core.snapshot import (
    build_auth_health,
    build_snapshot,
    pick_profile_id,
)


def emit(payload: Any, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, dict):
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(str(payload))


def load_live_context(marketplace: str | None):
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    health = build_auth_health(env)
    if not health["ok"]:
        return env, target_marketplace, None, None, None, health
    client = AmazonAdsClient(env)
    access_token = client.exchange_refresh_token()
    profiles = client.list_profiles(access_token)
    profile_id = env.profile_id or pick_profile_id(profiles, target_marketplace)
    return env, target_marketplace, client, access_token, profile_id, health


def build_domain_fallback(
    domain: str,
    health: dict[str, Any],
    data_key: str,
    requested: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "meta": {
            "mode": "mock",
            "status": "attention",
            "missingCredentials": health["missingCredentials"],
        },
        "data": {
            data_key: [],
            "requested": requested or {},
        },
        "domain": domain,
    }


@click.group(invoke_without_command=True)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON output.")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """Amazon Ads Ops Workbench CLI."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json
    if ctx.invoked_subcommand is None:
        repl(as_json)


@cli.group()
def auth() -> None:
    """Authentication and credential health commands."""


@auth.command("health")
@click.pass_context
def auth_health(ctx: click.Context) -> None:
    env = load_ads_environment()
    emit(build_auth_health(env), ctx.obj["json"])


@cli.group()
def profiles() -> None:
    """Profile discovery commands."""


@profiles.command("list")
@click.pass_context
def profiles_list(ctx: click.Context) -> None:
    env = load_ads_environment()
    client = AmazonAdsClient(env)
    access_token = client.exchange_refresh_token()
    emit(client.list_profiles(access_token), ctx.obj["json"])


@profiles.command("resolve")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.pass_context
def profiles_resolve(ctx: click.Context, marketplace: str | None) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    health = build_auth_health(env)
    if not health["ok"]:
        emit(
            {
                "marketplace": target_marketplace,
                "profileId": "",
                "missingCredentials": health["missingCredentials"],
            },
            ctx.obj["json"],
        )
        return
    client = AmazonAdsClient(env)
    access_token = client.exchange_refresh_token()
    profile_rows = client.list_profiles(access_token)
    emit(
        {
            "marketplace": target_marketplace,
            "profileId": env.profile_id or pick_profile_id(profile_rows, target_marketplace),
            "profiles": profile_rows,
        },
        ctx.obj["json"],
    )


@cli.group()
def campaigns() -> None:
    """Sponsored Products campaign commands."""


@campaigns.command("list")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.pass_context
def campaigns_list(ctx: click.Context, marketplace: str | None) -> None:
    snapshot = build_snapshot(load_ads_environment(), marketplace=marketplace)
    emit(snapshot["data"].get("campaigns", []), ctx.obj["json"])


@campaigns.command("set-state")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--state", required=True, help="ENABLED, PAUSED, or ARCHIVED.")
@click.pass_context
def campaigns_set_state(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    state: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "campaigns",
                health,
                "campaigns",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "state": state,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_campaign_state_payload(campaign_id=campaign_id, state=state)
    result = client.edit_campaign(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result},
        },
        ctx.obj["json"],
    )


@campaigns.command("edit-budget")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--budget", required=True, type=float, help="New campaign daily budget.")
@click.option("--budget-type", default="DAILY", help="Currently only DAILY is supported.")
@click.pass_context
def campaigns_edit_budget(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    budget: float,
    budget_type: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "campaigns",
                health,
                "campaigns",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "budget": budget,
                    "budgetType": budget_type,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_campaign_budget_payload(
        campaign_id=campaign_id,
        budget=budget,
        budget_type=budget_type,
    )
    result = client.edit_campaign(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result},
        },
        ctx.obj["json"],
    )


@cli.group("portfolios")
def portfolios() -> None:
    """Portfolio discovery commands."""


@portfolios.command("list")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--state", "state_filter", default=None, help="Optional portfolio state filter.")
@click.pass_context
def portfolios_list(
    ctx: click.Context,
    marketplace: str | None,
    state_filter: str | None,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "portfolios",
                health,
                "portfolios",
                {
                    "marketplace": target_marketplace,
                    "state": state_filter,
                },
            ),
            ctx.obj["json"],
        )
        return
    rows = client.list_portfolios(access_token, profile_id)
    normalized = [normalize_portfolio_row(row) for row in rows]
    if state_filter:
        normalized = [
            row for row in normalized if row["state"].upper() == state_filter.upper()
        ]
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"portfolios": normalized},
        },
        ctx.obj["json"],
    )


@cli.group("ad-groups")
def ad_groups() -> None:
    """Sponsored Products ad group commands."""


@ad_groups.command("list")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", default=None, help="Optional campaign id filter.")
@click.option("--ad-group-id", default=None, help="Optional ad group id filter.")
@click.option("--state", "state_filter", default="ENABLED", help="Ad group state filter.")
@click.pass_context
def ad_groups_list(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str | None,
    ad_group_id: str | None,
    state_filter: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "ad-groups",
                health,
                "adGroups",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "adGroupId": ad_group_id,
                    "state": state_filter,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_ad_groups_filter(campaign_id, ad_group_id, state_filter)
    rows = client.list_ad_groups(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"adGroups": [normalize_ad_group_row(row) for row in rows]},
        },
        ctx.obj["json"],
    )


@cli.group()
def keywords() -> None:
    """Sponsored Products keyword commands."""


@keywords.command("list")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", default=None, help="Optional campaign id filter.")
@click.option("--ad-group-id", default=None, help="Optional ad group id filter.")
@click.option("--state", "state_filter", default="ENABLED", help="Keyword state filter.")
@click.pass_context
def keywords_list(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str | None,
    ad_group_id: str | None,
    state_filter: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "keywords",
                health,
                "keywords",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "adGroupId": ad_group_id,
                    "state": state_filter,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_keywords_filter(campaign_id, ad_group_id, state_filter)
    rows = client.list_keywords(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {
                "keywords": [normalize_keyword_row(row) for row in rows],
            },
        },
        ctx.obj["json"],
    )


@keywords.command("edit-bid")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--ad-group-id", required=True, help="Ad group id.")
@click.option("--keyword-id", required=True, help="Keyword id.")
@click.option("--bid", required=True, type=float, help="New CPC bid.")
@click.pass_context
def keywords_edit_bid(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    ad_group_id: str,
    keyword_id: str,
    bid: float,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "keywords",
                health,
                "keywords",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "adGroupId": ad_group_id,
                    "keywordId": keyword_id,
                    "bid": bid,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_keyword_edit_payload(
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        keyword_id=keyword_id,
        bid=bid,
    )
    result = client.edit_keyword(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result},
        },
        ctx.obj["json"],
    )


@keywords.command("set-state")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--ad-group-id", required=True, help="Ad group id.")
@click.option("--keyword-id", required=True, help="Keyword id.")
@click.option("--state", required=True, help="ENABLED, PAUSED, or ARCHIVED.")
@click.pass_context
def keywords_set_state(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    ad_group_id: str,
    keyword_id: str,
    state: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "keywords",
                health,
                "keywords",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "adGroupId": ad_group_id,
                    "keywordId": keyword_id,
                    "state": state,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_keyword_state_payload(
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        keyword_id=keyword_id,
        state=state,
    )
    result = client.edit_keyword(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result},
        },
        ctx.obj["json"],
    )


@cli.group()
def negatives() -> None:
    """Negative keyword commands."""


@negatives.command("list")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", default=None, help="Optional campaign id filter.")
@click.option("--ad-group-id", default=None, help="Optional ad group id filter.")
@click.option("--scope", type=click.Choice(["adGroup", "campaign", "both"]), default="both")
@click.option("--state", "state_filter", default="ENABLED", help="Negative keyword state filter.")
@click.pass_context
def negatives_list(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str | None,
    ad_group_id: str | None,
    scope: str,
    state_filter: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "negatives",
                health,
                "negatives",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "adGroupId": ad_group_id,
                    "scope": scope,
                    "state": state_filter,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_negative_list_filter(campaign_id, ad_group_id, state_filter)
    rows = []
    if scope in {"adGroup", "both"}:
        rows.extend(
            normalize_negative_row(item, "adGroup")
            for item in client.list_negative_keywords(access_token, profile_id, payload)
        )
    if scope in {"campaign", "both"}:
        rows.extend(
            normalize_negative_row(item, "campaign")
            for item in client.list_campaign_negative_keywords(access_token, profile_id, payload)
        )
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"negatives": rows},
        },
        ctx.obj["json"],
    )


@negatives.command("add-ad-group")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--ad-group-id", required=True, help="Ad group id.")
@click.option("--keyword-text", required=True, help="Negative keyword text.")
@click.option("--match-type", required=True, help="NEGATIVE_EXACT or NEGATIVE_PHRASE.")
@click.pass_context
def negatives_add_ad_group(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    ad_group_id: str,
    keyword_text: str,
    match_type: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "negatives",
                health,
                "negatives",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "adGroupId": ad_group_id,
                    "keywordText": keyword_text,
                    "matchType": match_type,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_ad_group_negative_payload(
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        keyword_text=keyword_text,
        match_type=match_type,
    )
    result = client.create_negative_keyword(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result},
        },
        ctx.obj["json"],
    )


@negatives.command("add-campaign")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--keyword-text", required=True, help="Negative keyword text.")
@click.option("--match-type", required=True, help="NEGATIVE_EXACT or NEGATIVE_PHRASE.")
@click.pass_context
def negatives_add_campaign(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    keyword_text: str,
    match_type: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "negatives",
                health,
                "negatives",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "keywordText": keyword_text,
                    "matchType": match_type,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_campaign_negative_payload(
        campaign_id=campaign_id,
        keyword_text=keyword_text,
        match_type=match_type,
    )
    result = client.create_campaign_negative_keyword(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result},
        },
        ctx.obj["json"],
    )


@negatives.command("set-state")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--negative-keyword-id", required=True, help="Negative keyword id.")
@click.option("--scope", type=click.Choice(["adGroup", "campaign"]), required=True)
@click.option("--state", required=True, help="ENABLED, PAUSED, or PROPOSED.")
@click.pass_context
def negatives_set_state(
    ctx: click.Context,
    marketplace: str | None,
    negative_keyword_id: str,
    scope: str,
    state: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "negatives",
                health,
                "negatives",
                {
                    "marketplace": target_marketplace,
                    "negativeKeywordId": negative_keyword_id,
                    "scope": scope,
                    "state": state,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_negative_state_payload(
        keyword_id=negative_keyword_id,
        state=state,
    )
    if scope == "campaign":
        result = client.edit_campaign_negative_keyword(access_token, profile_id, payload)
    else:
        result = client.edit_negative_keyword(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result},
        },
        ctx.obj["json"],
    )


@cli.group()
def reports() -> None:
    """Reporting commands."""


@reports.command("create-sp-keywords")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--start-date", required=True, help="Report start date in YYYY-MM-DD.")
@click.option("--end-date", required=True, help="Report end date in YYYY-MM-DD.")
@click.option("--time-unit", default="DAILY", help="SUMMARY or DAILY.")
@click.pass_context
def reports_create_sp_keywords(
    ctx: click.Context,
    marketplace: str | None,
    start_date: str,
    end_date: str,
    time_unit: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "reports",
                health,
                "reports",
                {
                    "marketplace": target_marketplace,
                    "startDate": start_date,
                    "endDate": end_date,
                    "timeUnit": time_unit,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_sp_keywords_report_body(start_date, end_date, time_unit)
    result = client.create_report(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"report": normalize_report_status(result)},
        },
        ctx.obj["json"],
    )


@reports.command("create-sp-campaign-placement")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--start-date", required=True, help="Report start date in YYYY-MM-DD.")
@click.option("--end-date", required=True, help="Report end date in YYYY-MM-DD.")
@click.option("--time-unit", default="SUMMARY", help="SUMMARY or DAILY.")
@click.pass_context
def reports_create_sp_campaign_placement(
    ctx: click.Context,
    marketplace: str | None,
    start_date: str,
    end_date: str,
    time_unit: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "reports",
                health,
                "reports",
                {
                    "marketplace": target_marketplace,
                    "startDate": start_date,
                    "endDate": end_date,
                    "timeUnit": time_unit,
                    "reportTypeId": "spCampaigns",
                    "groupBy": ["campaignPlacement"],
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_sp_campaign_placement_report_body(start_date, end_date, time_unit)
    result = client.create_report(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"report": normalize_report_status(result)},
        },
        ctx.obj["json"],
    )


@reports.command("create-search-terms")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--start-date", required=True, help="Report start date in YYYY-MM-DD.")
@click.option("--end-date", required=True, help="Report end date in YYYY-MM-DD.")
@click.option("--time-unit", default="SUMMARY", help="SUMMARY or DAILY.")
@click.pass_context
def reports_create_search_terms(
    ctx: click.Context,
    marketplace: str | None,
    start_date: str,
    end_date: str,
    time_unit: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "reports",
                health,
                "reports",
                {
                    "marketplace": target_marketplace,
                    "startDate": start_date,
                    "endDate": end_date,
                    "timeUnit": time_unit,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_sp_search_term_report_body(start_date, end_date, time_unit)
    result = client.create_report(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"report": normalize_report_status(result)},
        },
        ctx.obj["json"],
    )


@reports.command("status")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--report-id", required=True, help="Report id.")
@click.pass_context
def reports_status(
    ctx: click.Context,
    marketplace: str | None,
    report_id: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "reports",
                health,
                "reports",
                {
                    "marketplace": target_marketplace,
                    "reportId": report_id,
                },
            ),
            ctx.obj["json"],
        )
        return
    result = client.get_report(access_token, profile_id, report_id)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"report": normalize_report_status(result)},
        },
        ctx.obj["json"],
    )


@reports.command("download")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--report-id", required=True, help="Report id.")
@click.option(
    "--output-dir",
    default=os.path.expanduser("~/Downloads"),
    help="Directory for the downloaded report file.",
)
@click.pass_context
def reports_download(
    ctx: click.Context,
    marketplace: str | None,
    report_id: str,
    output_dir: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "reports",
                health,
                "reports",
                {
                    "marketplace": target_marketplace,
                    "reportId": report_id,
                    "outputDir": output_dir,
                },
            ),
            ctx.obj["json"],
        )
        return
    status = client.get_report(access_token, profile_id, report_id)
    normalized = normalize_report_status(status)
    if not normalized["url"]:
        emit(
            {
                "meta": {
                    "mode": "live",
                    "status": "attention",
                    "profileId": profile_id,
                    "marketplace": target_marketplace,
                },
                "data": {"report": normalized},
            },
            ctx.obj["json"],
        )
        return
    report_type = normalized["reportTypeId"] or "report"
    output_path = build_download_target_path(output_dir, report_id, report_type)
    download_meta = client.download_report_file(normalized["url"], output_path)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {
                "report": normalized,
                "download": download_meta,
            },
        },
        ctx.obj["json"],
    )


@reports.command("parse-search-terms")
@click.option("--input-file", required=True, help="Downloaded search term report JSON path.")
@click.pass_context
def reports_parse_search_terms(ctx: click.Context, input_file: str) -> None:
    rows = [normalize_search_term_report_row(row) for row in load_report_rows(input_file)]
    emit(
        {
            "meta": {
                "mode": "local",
                "status": "parsed",
                "inputFile": input_file,
            },
            "data": {
                "summary": summarize_report_rows(rows),
                "rows": rows,
            },
        },
        ctx.obj["json"],
    )


@reports.command("parse-sp-keywords")
@click.option("--input-file", required=True, help="Downloaded SP keyword report JSON path.")
@click.pass_context
def reports_parse_sp_keywords(ctx: click.Context, input_file: str) -> None:
    rows = [normalize_sp_keyword_report_row(row) for row in load_report_rows(input_file)]
    emit(
        {
            "meta": {
                "mode": "local",
                "status": "parsed",
                "inputFile": input_file,
            },
            "data": {
                "summary": summarize_report_rows(rows),
                "rows": rows,
            },
        },
        ctx.obj["json"],
    )


@reports.command("parse-sp-campaign-placement")
@click.option("--input-file", required=True, help="Downloaded SP campaign placement report JSON path.")
@click.pass_context
def reports_parse_sp_campaign_placement(ctx: click.Context, input_file: str) -> None:
    rows = [
        normalize_sp_campaign_placement_report_row(row)
        for row in load_report_rows(input_file)
    ]
    emit(
        {
            "meta": {
                "mode": "local",
                "status": "parsed",
                "inputFile": input_file,
            },
            "data": {
                "summary": summarize_report_rows(rows),
                "rows": rows,
            },
        },
        ctx.obj["json"],
    )


@cli.command("snapshot")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.pass_context
def snapshot_command(ctx: click.Context, marketplace: str | None) -> None:
    emit(build_snapshot(load_ads_environment(), marketplace=marketplace), ctx.obj["json"])


def repl(as_json: bool) -> None:
    skin = None
    prompt_session = None
    try:
        from cli_anything.amazon_ads_ops_workbench.utils.repl_skin import ReplSkin

        skin = ReplSkin("amazon_ads_ops_workbench", version=__version__)
        skin.print_banner()
        prompt_session = skin.create_prompt_session()
    except Exception:
        click.echo("Amazon Ads Ops Workbench REPL. 输入 exit 退出。")

    while True:
        try:
            if skin and prompt_session:
                line = skin.get_input(
                    prompt_session,
                    project_name="amazon-ads",
                    modified=False,
                ).strip()
            else:
                line = input("amazon-ads> ").strip()
        except EOFError:
            click.echo()
            break
        if not line:
            continue
        if line in {"exit", "quit"}:
            if skin:
                skin.print_goodbye()
            break
        if line == "help":
            help_text = "可用命令: auth health | profiles list | profiles resolve --marketplace US | campaigns list | campaigns set-state | campaigns edit-budget | portfolios list | ad-groups list | keywords list | keywords edit-bid | keywords set-state | negatives list | negatives add-ad-group | negatives add-campaign | negatives set-state | reports create-sp-keywords | reports create-sp-campaign-placement | reports create-search-terms | reports status | reports download | reports parse-search-terms | reports parse-sp-keywords | reports parse-sp-campaign-placement | snapshot"
            if skin:
                skin.info(help_text)
            else:
                click.echo(help_text)
            continue
        args = ["--json"] + shlex.split(line) if as_json else shlex.split(line)
        try:
            cli.main(args=args, prog_name="cli-anything-amazon-ads-ops-workbench", standalone_mode=False)
        except SystemExit:
            continue
        except Exception as exc:  # pragma: no cover
            if skin:
                skin.error(str(exc))
            else:
                click.echo(f"error: {exc}", err=True)


if __name__ == "__main__":
    cli()

from __future__ import annotations

import json
import os
import shlex
from typing import Any

import click

from cli_anything.amazon_ads_ops_workbench import __version__
from cli_anything.amazon_ads_ops_workbench.core.campaigns import (
    build_campaign_budget_payload,
    build_campaign_create_payload,
    build_campaign_placement_bid_payload,
    build_campaign_state_payload,
    build_portfolio_create_payload,
    build_portfolio_state_payload,
)
from cli_anything.amazon_ads_ops_workbench.core.client import AmazonAdsClient
from cli_anything.amazon_ads_ops_workbench.core.env import load_ads_environment
from cli_anything.amazon_ads_ops_workbench.core.keywords import (
    build_ad_groups_filter,
    build_ad_group_create_payload,
    build_ad_group_negative_payload,
    build_ad_group_state_payload,
    build_asin_target_create_payload,
    build_campaign_negative_payload,
    build_keyword_create_payload,
    build_keyword_edit_payload,
    build_keyword_state_payload,
    build_keywords_filter,
    build_negative_state_payload,
    build_negative_list_filter,
    build_product_ad_create_payload,
    build_product_ad_state_payload,
    build_product_ads_filter,
    build_target_state_payload,
    build_targets_filter,
    normalize_ad_group_row,
    normalize_keyword_row,
    normalize_negative_row,
    normalize_portfolio_row,
    normalize_product_ad_row,
    normalize_target_row,
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


def emit_dry_run(
    ctx: click.Context,
    marketplace: str,
    payload: dict[str, Any],
    operation: str,
    policy: str = "user_supplied_values_only",
) -> None:
    emit(
        {
            "meta": {
                "mode": "dry-run",
                "status": "not_submitted",
                "marketplace": marketplace,
                "operation": operation,
            },
            "data": {
                "payload": payload,
                "policy": policy,
            },
        },
        ctx.obj["json"],
    )


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


@campaigns.command("create")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--name", required=True, help="Campaign name.")
@click.option(
    "--targeting-type",
    required=True,
    type=click.Choice(["MANUAL", "AUTO"], case_sensitive=False),
    help="Campaign targeting type.",
)
@click.option("--budget", required=True, type=float, help="Campaign daily budget.")
@click.option("--start-date", required=True, help="Start date in YYYY-MM-DD format.")
@click.option("--end-date", default=None, help="Optional end date in YYYY-MM-DD format.")
@click.option("--budget-type", default="DAILY", help="Currently only DAILY is supported.")
@click.option(
    "--state",
    default="ENABLED",
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="Initial campaign state.",
)
@click.option(
    "--strategy",
    default=None,
    type=click.Choice(
        ["AUTO_FOR_SALES", "LEGACY_FOR_SALES", "MANUAL"],
        case_sensitive=False,
    ),
    help="Optional dynamic bidding strategy.",
)
@click.option("--portfolio-id", default=None, help="Optional portfolio id.")
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def campaigns_create(
    ctx: click.Context,
    marketplace: str | None,
    name: str,
    targeting_type: str,
    budget: float,
    start_date: str,
    end_date: str | None,
    budget_type: str,
    state: str,
    strategy: str | None,
    portfolio_id: str | None,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_campaign_create_payload(
        name=name,
        targeting_type=targeting_type,
        budget=budget,
        start_date=start_date,
        budget_type=budget_type,
        state=state,
        strategy=strategy,
        portfolio_id=portfolio_id,
        end_date=end_date,
    )
    request_payload = {"campaigns": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "campaigns.create")
        return

    health = build_auth_health(env)
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "campaigns",
                health,
                "campaigns",
                {
                    "marketplace": target_marketplace,
                    "payload": request_payload,
                },
            ),
            ctx.obj["json"],
        )
        return
    client = AmazonAdsClient(env)
    access_token = client.exchange_refresh_token()
    profiles = client.list_profiles(access_token)
    profile_id = env.profile_id or pick_profile_id(profiles, target_marketplace)
    result = client.create_campaign(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
        },
        ctx.obj["json"],
    )


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


@campaigns.command("edit-placement-bids")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option(
    "--top-of-search",
    type=click.IntRange(0, 900),
    default=None,
    help="Top of search placement bid adjustment percentage, 0-900.",
)
@click.option(
    "--product-pages",
    type=click.IntRange(0, 900),
    default=None,
    help="Product pages placement bid adjustment percentage, 0-900.",
)
@click.option(
    "--rest-of-search",
    type=click.IntRange(0, 900),
    default=None,
    help="Rest of search placement bid adjustment percentage, 0-900.",
)
@click.option(
    "--strategy",
    type=click.Choice(
        ["AUTO_FOR_SALES", "LEGACY_FOR_SALES", "MANUAL"],
        case_sensitive=False,
    ),
    default=None,
    help="Optional bidding strategy to include in the update payload.",
)
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def campaigns_edit_placement_bids(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    top_of_search: int | None,
    product_pages: int | None,
    rest_of_search: int | None,
    strategy: str | None,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    try:
        payload = build_campaign_placement_bid_payload(
            campaign_id=campaign_id,
            top_of_search=top_of_search,
            product_pages=product_pages,
            rest_of_search=rest_of_search,
            strategy=strategy,
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc)) from exc

    request_payload = {"campaigns": [payload]}
    if dry_run:
        emit(
            {
                "meta": {
                    "mode": "dry-run",
                    "status": "not_submitted",
                    "marketplace": target_marketplace,
                },
                "data": {
                    "payload": request_payload,
                    "placementPolicy": "user_supplied_percentages_only",
                },
            },
            ctx.obj["json"],
        )
        return

    health = build_auth_health(env)
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "campaigns",
                health,
                "campaigns",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "topOfSearch": top_of_search,
                    "productPages": product_pages,
                    "restOfSearch": rest_of_search,
                    "strategy": strategy,
                    "payload": request_payload,
                },
            ),
            ctx.obj["json"],
        )
        return

    client = AmazonAdsClient(env)
    access_token = client.exchange_refresh_token()
    profiles = client.list_profiles(access_token)
    profile_id = env.profile_id or pick_profile_id(profiles, target_marketplace)
    result = client.edit_campaign(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {
                "result": result,
                "payload": request_payload,
                "placementPolicy": "user_supplied_percentages_only",
            },
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


@portfolios.command("create")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--name", required=True, help="Portfolio name.")
@click.option(
    "--state",
    default="ENABLED",
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="Initial portfolio state.",
)
@click.option("--budget", type=float, default=None, help="Optional portfolio budget amount.")
@click.option("--budget-policy", default=None, help="Optional budget policy.")
@click.option("--budget-start-date", default=None, help="Optional budget start date.")
@click.option("--budget-end-date", default=None, help="Optional budget end date.")
@click.option("--currency-code", default=None, help="Optional budget currency code.")
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def portfolios_create(
    ctx: click.Context,
    marketplace: str | None,
    name: str,
    state: str,
    budget: float | None,
    budget_policy: str | None,
    budget_start_date: str | None,
    budget_end_date: str | None,
    currency_code: str | None,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_portfolio_create_payload(
        name=name,
        state=state,
        budget=budget,
        budget_policy=budget_policy,
        budget_start_date=budget_start_date,
        budget_end_date=budget_end_date,
        currency_code=currency_code,
    )
    request_payload = {"portfolios": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "portfolios.create")
        return

    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "portfolios",
                health,
                "portfolios",
                {"marketplace": target_marketplace, "payload": request_payload},
            ),
            ctx.obj["json"],
        )
        return
    result = client.create_portfolio(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
        },
        ctx.obj["json"],
    )


@portfolios.command("set-state")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--portfolio-id", required=True, help="Portfolio id.")
@click.option(
    "--state",
    required=True,
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="ENABLED, PAUSED, or ARCHIVED.",
)
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def portfolios_set_state(
    ctx: click.Context,
    marketplace: str | None,
    portfolio_id: str,
    state: str,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_portfolio_state_payload(portfolio_id=portfolio_id, state=state)
    request_payload = {"portfolios": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "portfolios.set-state")
        return

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
                    "portfolioId": portfolio_id,
                    "state": state,
                    "payload": request_payload,
                },
            ),
            ctx.obj["json"],
        )
        return
    result = client.edit_portfolio(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
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


@ad_groups.command("create")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--name", required=True, help="Ad group name.")
@click.option("--default-bid", required=True, type=float, help="Default CPC bid.")
@click.option(
    "--state",
    default="ENABLED",
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="Initial ad group state.",
)
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def ad_groups_create(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    name: str,
    default_bid: float,
    state: str,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_ad_group_create_payload(
        campaign_id=campaign_id,
        name=name,
        default_bid=default_bid,
        state=state,
    )
    request_payload = {"adGroups": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "ad-groups.create")
        return

    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "ad-groups",
                health,
                "adGroups",
                {"marketplace": target_marketplace, "payload": request_payload},
            ),
            ctx.obj["json"],
        )
        return
    result = client.create_ad_group(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
        },
        ctx.obj["json"],
    )


@ad_groups.command("set-state")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--ad-group-id", required=True, help="Ad group id.")
@click.option(
    "--state",
    required=True,
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="ENABLED, PAUSED, or ARCHIVED.",
)
@click.option("--default-bid", type=float, default=None, help="Optional default bid to retain/update.")
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def ad_groups_set_state(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    ad_group_id: str,
    state: str,
    default_bid: float | None,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_ad_group_state_payload(
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        state=state,
        default_bid=default_bid,
    )
    request_payload = {"adGroups": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "ad-groups.set-state")
        return

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
                    "state": state,
                    "payload": request_payload,
                },
            ),
            ctx.obj["json"],
        )
        return
    result = client.edit_ad_group(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
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


@keywords.command("add")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--ad-group-id", required=True, help="Ad group id.")
@click.option("--keyword-text", required=True, help="Keyword text.")
@click.option(
    "--match-type",
    required=True,
    type=click.Choice(["BROAD", "PHRASE", "EXACT"], case_sensitive=False),
    help="Keyword match type.",
)
@click.option("--bid", type=float, default=None, help="Optional keyword CPC bid.")
@click.option(
    "--state",
    default="ENABLED",
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="Initial keyword state.",
)
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def keywords_add(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    ad_group_id: str,
    keyword_text: str,
    match_type: str,
    bid: float | None,
    state: str,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_keyword_create_payload(
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        keyword_text=keyword_text,
        match_type=match_type,
        bid=bid,
        state=state,
    )
    request_payload = {"keywords": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "keywords.add")
        return

    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "keywords",
                health,
                "keywords",
                {"marketplace": target_marketplace, "payload": request_payload},
            ),
            ctx.obj["json"],
        )
        return
    result = client.create_keyword(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
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


@cli.group("product-ads")
def product_ads() -> None:
    """Sponsored Products advertised product commands."""


@product_ads.command("list")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", default=None, help="Optional campaign id filter.")
@click.option("--ad-group-id", default=None, help="Optional ad group id filter.")
@click.option("--product-ad-id", default=None, help="Optional product ad id filter.")
@click.option("--state", "state_filter", default="ENABLED", help="Product ad state filter.")
@click.pass_context
def product_ads_list(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str | None,
    ad_group_id: str | None,
    product_ad_id: str | None,
    state_filter: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "product-ads",
                health,
                "productAds",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "adGroupId": ad_group_id,
                    "productAdId": product_ad_id,
                    "state": state_filter,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_product_ads_filter(campaign_id, ad_group_id, product_ad_id, state_filter)
    rows = client.list_product_ads(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"productAds": [normalize_product_ad_row(row) for row in rows]},
        },
        ctx.obj["json"],
    )


@product_ads.command("add")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--ad-group-id", required=True, help="Ad group id.")
@click.option("--sku", default=None, help="Advertised product SKU. Use either SKU or ASIN.")
@click.option("--asin", default=None, help="Advertised product ASIN. Use either SKU or ASIN.")
@click.option(
    "--state",
    default="ENABLED",
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="Initial product ad state.",
)
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def product_ads_add(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    ad_group_id: str,
    sku: str | None,
    asin: str | None,
    state: str,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    try:
        payload = build_product_ad_create_payload(
            campaign_id=campaign_id,
            ad_group_id=ad_group_id,
            sku=sku,
            asin=asin,
            state=state,
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc)) from exc
    request_payload = {"productAds": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "product-ads.add")
        return

    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "product-ads",
                health,
                "productAds",
                {"marketplace": target_marketplace, "payload": request_payload},
            ),
            ctx.obj["json"],
        )
        return
    result = client.create_product_ad(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
        },
        ctx.obj["json"],
    )


@product_ads.command("set-state")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--product-ad-id", required=True, help="Product ad id.")
@click.option("--campaign-id", default=None, help="Optional campaign id.")
@click.option("--ad-group-id", default=None, help="Optional ad group id.")
@click.option(
    "--state",
    required=True,
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="ENABLED, PAUSED, or ARCHIVED.",
)
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def product_ads_set_state(
    ctx: click.Context,
    marketplace: str | None,
    product_ad_id: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    state: str,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_product_ad_state_payload(
        product_ad_id=product_ad_id,
        state=state,
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
    )
    request_payload = {"productAds": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "product-ads.set-state")
        return

    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "product-ads",
                health,
                "productAds",
                {
                    "marketplace": target_marketplace,
                    "productAdId": product_ad_id,
                    "state": state,
                    "payload": request_payload,
                },
            ),
            ctx.obj["json"],
        )
        return
    result = client.edit_product_ad(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
        },
        ctx.obj["json"],
    )


@cli.group("targets")
def targets() -> None:
    """Sponsored Products product targeting commands."""


@targets.command("list")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", default=None, help="Optional campaign id filter.")
@click.option("--ad-group-id", default=None, help="Optional ad group id filter.")
@click.option("--target-id", default=None, help="Optional target id filter.")
@click.option("--state", "state_filter", default="ENABLED", help="Targeting clause state filter.")
@click.pass_context
def targets_list(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str | None,
    ad_group_id: str | None,
    target_id: str | None,
    state_filter: str,
) -> None:
    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "targets",
                health,
                "targets",
                {
                    "marketplace": target_marketplace,
                    "campaignId": campaign_id,
                    "adGroupId": ad_group_id,
                    "targetId": target_id,
                    "state": state_filter,
                },
            ),
            ctx.obj["json"],
        )
        return
    payload = build_targets_filter(campaign_id, ad_group_id, target_id, state_filter)
    rows = client.list_targets(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"targets": [normalize_target_row(row) for row in rows]},
        },
        ctx.obj["json"],
    )


@targets.command("add-asin")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--campaign-id", required=True, help="Campaign id.")
@click.option("--ad-group-id", required=True, help="Ad group id.")
@click.option("--asin", required=True, help="Target ASIN.")
@click.option("--bid", type=float, default=None, help="Optional target CPC bid.")
@click.option(
    "--state",
    default="ENABLED",
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="Initial target state.",
)
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def targets_add_asin(
    ctx: click.Context,
    marketplace: str | None,
    campaign_id: str,
    ad_group_id: str,
    asin: str,
    bid: float | None,
    state: str,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_asin_target_create_payload(
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        asin=asin,
        bid=bid,
        state=state,
    )
    request_payload = {"targetingClauses": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "targets.add-asin")
        return

    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "targets",
                health,
                "targets",
                {"marketplace": target_marketplace, "payload": request_payload},
            ),
            ctx.obj["json"],
        )
        return
    result = client.create_target(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
        },
        ctx.obj["json"],
    )


@targets.command("set-state")
@click.option("--marketplace", default=None, help="Marketplace such as US, CA, or MX.")
@click.option("--target-id", required=True, help="Target id.")
@click.option("--campaign-id", default=None, help="Optional campaign id.")
@click.option("--ad-group-id", default=None, help="Optional ad group id.")
@click.option("--bid", type=float, default=None, help="Optional target bid to retain/update.")
@click.option(
    "--state",
    required=True,
    type=click.Choice(["ENABLED", "PAUSED", "ARCHIVED"], case_sensitive=False),
    help="ENABLED, PAUSED, or ARCHIVED.",
)
@click.option("--dry-run", is_flag=True, help="Print the request payload without submitting.")
@click.pass_context
def targets_set_state(
    ctx: click.Context,
    marketplace: str | None,
    target_id: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    bid: float | None,
    state: str,
    dry_run: bool,
) -> None:
    env = load_ads_environment()
    target_marketplace = (marketplace or env.marketplace or "US").upper()
    payload = build_target_state_payload(
        target_id=target_id,
        state=state,
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        bid=bid,
    )
    request_payload = {"targetingClauses": [payload]}
    if dry_run:
        emit_dry_run(ctx, target_marketplace, request_payload, "targets.set-state")
        return

    env, target_marketplace, client, access_token, profile_id, health = load_live_context(
        marketplace
    )
    if not health["ok"]:
        emit(
            build_domain_fallback(
                "targets",
                health,
                "targets",
                {
                    "marketplace": target_marketplace,
                    "targetId": target_id,
                    "state": state,
                    "payload": request_payload,
                },
            ),
            ctx.obj["json"],
        )
        return
    result = client.edit_target(access_token, profile_id, payload)
    emit(
        {
            "meta": {
                "mode": "live",
                "status": "connected",
                "profileId": profile_id,
                "marketplace": target_marketplace,
            },
            "data": {"result": result, "payload": request_payload},
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
            help_text = "可用命令: auth health | profiles list | profiles resolve --marketplace US | portfolios list/create/set-state | campaigns list/create/set-state/edit-budget/edit-placement-bids | ad-groups list/create/set-state | keywords list/add/edit-bid/set-state | product-ads list/add/set-state | targets list/add-asin/set-state | negatives list/add-ad-group/add-campaign/set-state | reports create-sp-keywords/create-sp-campaign-placement/create-search-terms/status/download/parse-search-terms/parse-sp-keywords/parse-sp-campaign-placement | snapshot"
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

from __future__ import annotations

from typing import Any
import click
from .client import AmazonAdsClient


def execute_approved_operation(
    client: AmazonAdsClient,
    access_token: str,
    profile_id: str,
    plan: dict[str, Any],
) -> Any:
    operation = str(plan.get("operation") or "")
    payload = plan.get("payload")
    if not isinstance(payload, dict):
        raise click.UsageError("Approval plan payload must be a JSON object.")

    if operation == "campaigns.create":
        return client.create_campaign(access_token, profile_id, payload)
    if operation in {
        "campaigns.set-state",
        "campaigns.edit-budget",
        "campaigns.edit-bidding-strategy",
        "campaigns.edit-placement-bids",
    }:
        return client.edit_campaign(access_token, profile_id, payload)
    if operation == "portfolios.create":
        return client.create_portfolio(access_token, profile_id, payload)
    if operation == "portfolios.set-state":
        return client.edit_portfolio(access_token, profile_id, payload)
    if operation == "ad-groups.create":
        return client.create_ad_group(access_token, profile_id, payload)
    if operation in {"ad-groups.set-state", "ad-groups.edit-bid"}:
        return client.edit_ad_group(access_token, profile_id, payload)
    if operation == "keywords.add":
        return client.create_keyword(access_token, profile_id, payload)
    if operation in {"keywords.edit-bid", "keywords.set-state"}:
        return client.edit_keyword(access_token, profile_id, payload)
    if operation == "product-ads.add":
        return client.create_product_ad(access_token, profile_id, payload)
    if operation == "product-ads.set-state":
        return client.edit_product_ad(access_token, profile_id, payload)
    if operation in {
        "targets.add-asin",
        "targets.add-category",
        "targets.add-expression",
    }:
        return client.create_target(access_token, profile_id, payload)
    if operation in {"targets.edit-bid", "targets.set-state"}:
        return client.edit_target(access_token, profile_id, payload)
    if operation == "negatives.add-ad-group":
        return client.create_negative_keyword(access_token, profile_id, payload)
    if operation == "negatives.add-campaign":
        return client.create_campaign_negative_keyword(
            access_token, profile_id, payload
        )
    if operation == "negatives.set-state":
        if "campaignNegativeKeywords" in payload:
            return client.edit_campaign_negative_keyword(
                access_token, profile_id, payload
            )
        return client.edit_negative_keyword(access_token, profile_id, payload)
    if operation == "negative-targets.add-ad-group":
        return client.create_negative_target(access_token, profile_id, payload)
    if operation == "negative-targets.add-campaign":
        return client.create_campaign_negative_target(access_token, profile_id, payload)
    if operation == "negative-targets.set-state":
        if "campaignNegativeTargetingClauses" in payload:
            return client.edit_campaign_negative_target(
                access_token, profile_id, payload
            )
        return client.edit_negative_target(access_token, profile_id, payload)
    if operation == "sb-campaigns.create":
        return client.create_sb_campaign(access_token, profile_id, payload)
    if operation in {
        "sb-campaigns.set-state",
        "sb-campaigns.edit-budget",
        "sb-campaigns.edit-name",
        "sb-campaigns.edit-bidding",
    }:
        return client.edit_sb_campaign(access_token, profile_id, payload)
    if operation == "sb-campaigns.archive":
        return client.archive_sb_campaign(access_token, profile_id, payload)
    if operation == "sb-ad-groups.create":
        return client.create_sb_ad_group(access_token, profile_id, payload)
    if operation in {"sb-ad-groups.set-state", "sb-ad-groups.edit-name"}:
        return client.edit_sb_ad_group(access_token, profile_id, payload)
    if operation == "sb-ad-groups.archive":
        return client.archive_sb_ad_group(access_token, profile_id, payload)
    if operation == "sb-keywords.add":
        return client.create_sb_keyword(access_token, profile_id, payload)
    if operation in {"sb-keywords.edit-bid", "sb-keywords.set-state"}:
        return client.edit_sb_keyword(access_token, profile_id, payload)
    if operation == "sb-keywords.archive":
        return client.archive_sb_keyword(
            access_token, profile_id, str(payload.get("keywordId") or "")
        )
    if operation == "sb-negatives.add":
        return client.create_sb_negative_keyword(access_token, profile_id, payload)
    if operation == "sb-negatives.set-state":
        return client.edit_sb_negative_keyword(access_token, profile_id, payload)
    if operation == "sb-negatives.archive":
        return client.archive_sb_negative_keyword(
            access_token, profile_id, str(payload.get("keywordId") or "")
        )
    if operation in {
        "sb-targets.add-asin",
        "sb-targets.add-category",
        "sb-targets.add-expression",
    }:
        return client.create_sb_target(access_token, profile_id, payload)
    if operation in {"sb-targets.edit-bid", "sb-targets.set-state"}:
        return client.edit_sb_target(access_token, profile_id, payload)
    if operation == "sb-targets.archive":
        return client.archive_sb_target(
            access_token, profile_id, str(payload.get("targetId") or "")
        )
    if operation in {
        "sb-negative-targets.add-ad-group",
        "sb-negative-targets.add-campaign",
    }:
        return client.create_sb_negative_target(access_token, profile_id, payload)
    if operation == "sb-negative-targets.set-state":
        return client.edit_sb_negative_target(access_token, profile_id, payload)
    if operation == "sb-negative-targets.archive":
        return client.archive_sb_negative_target(
            access_token, profile_id, str(payload.get("targetId") or "")
        )
    if operation == "sd-campaigns.create":
        return client.create_sd_campaign(access_token, profile_id, payload)
    if operation in {
        "sd-campaigns.set-state",
        "sd-campaigns.edit-budget",
        "sd-campaigns.edit-name",
        "sd-campaigns.archive",
    }:
        return client.edit_sd_campaign(access_token, profile_id, payload)
    if operation == "sd-ad-groups.create":
        return client.create_sd_ad_group(access_token, profile_id, payload)
    if operation in {
        "sd-ad-groups.set-state",
        "sd-ad-groups.edit-bid",
        "sd-ad-groups.edit-name",
        "sd-ad-groups.archive",
    }:
        return client.edit_sd_ad_group(access_token, profile_id, payload)
    if operation == "sd-product-ads.add":
        return client.create_sd_product_ad(access_token, profile_id, payload)
    if operation in {
        "sd-product-ads.set-state",
        "sd-product-ads.edit-name",
        "sd-product-ads.archive",
    }:
        return client.edit_sd_product_ad(access_token, profile_id, payload)
    if operation in {
        "sd-targets.add-asin",
        "sd-targets.add-category",
        "sd-targets.add-audience",
        "sd-targets.add-expression",
    }:
        return client.create_sd_target(access_token, profile_id, payload)
    if operation in {
        "sd-targets.edit-bid",
        "sd-targets.set-state",
        "sd-targets.archive",
    }:
        return client.edit_sd_target(access_token, profile_id, payload)
    if operation == "sd-locations.add":
        return client.create_sd_location(access_token, profile_id, payload)
    if operation in {"sd-locations.set-state", "sd-locations.archive"}:
        return client.edit_sd_location(access_token, profile_id, payload)
    if operation == "sd-budget-rules.create":
        return client.create_sd_budget_rule(access_token, profile_id, payload)
    if operation == "sd-budget-rules.update":
        return client.update_sd_budget_rule(access_token, profile_id, payload)
    if operation == "sd-budget-rules.associate":
        campaign_id = str(payload.get("campaignId") or "")
        body = {"budgetRuleIds": payload.get("budgetRuleIds") or []}
        return client.associate_sd_budget_rule(
            access_token, profile_id, campaign_id, body
        )
    if operation == "sd-budget-rules.disassociate":
        return client.disassociate_sd_budget_rule(
            access_token,
            profile_id,
            str(payload.get("campaignId") or ""),
            str(payload.get("budgetRuleId") or ""),
        )
    if operation == "sp-raw.request":
        return client.send_sp_raw(
            access_token=access_token,
            profile_id=profile_id,
            method=str(payload.get("method") or "GET"),
            path=str(payload.get("path") or ""),
            payload=payload.get("payload"),
            accept=payload.get("accept")
            if isinstance(payload.get("accept"), str)
            else None,
            content_type=(
                payload.get("contentType")
                if isinstance(payload.get("contentType"), str)
                else None
            ),
        )
    if operation == "sd-raw.request":
        return client.send_sd_raw(
            access_token=access_token,
            profile_id=profile_id,
            method=str(payload.get("method") or "GET"),
            path=str(payload.get("path") or ""),
            payload=payload.get("payload"),
            accept=payload.get("accept")
            if isinstance(payload.get("accept"), str)
            else None,
            content_type=(
                payload.get("contentType")
                if isinstance(payload.get("contentType"), str)
                else None
            ),
        )
    if operation == "sb-raw.request":
        return client.send_sb_raw(
            access_token=access_token,
            profile_id=profile_id,
            method=str(payload.get("method") or "GET"),
            path=str(payload.get("path") or ""),
            payload=payload.get("payload"),
            accept=payload.get("accept")
            if isinstance(payload.get("accept"), str)
            else None,
            content_type=(
                payload.get("contentType")
                if isinstance(payload.get("contentType"), str)
                else None
            ),
        )
    raise click.UsageError(f"Unsupported approval operation: {operation}")

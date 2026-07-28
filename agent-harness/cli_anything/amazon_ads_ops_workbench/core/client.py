from __future__ import annotations

import json
import gzip
import os
from typing import Any
from urllib import error, parse, request

from .env import AdsEnvironment, get_region_base_url
from .sponsored_brands import assert_sb_raw_allowed
from .sponsored_display import assert_sd_raw_allowed


class AmazonAdsClient:
    def __init__(self, env: AdsEnvironment):
        self.env = env

    def exchange_refresh_token(self) -> str:
        payload = parse.urlencode(
            {
                "grant_type": "refresh_token",
                "refresh_token": self.env.refresh_token,
                "client_id": self.env.client_id,
                "client_secret": self.env.client_secret,
            }
        ).encode("utf-8")
        req = request.Request(
            "https://api.amazon.com/auth/o2/token",
            method="POST",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        data = self._send_json(req, "OAuth token exchange")
        token = data.get("access_token", "")
        if not isinstance(token, str) or not token:
            raise RuntimeError("OAuth token exchange failed: access_token missing")
        return token

    def list_profiles(self, access_token: str) -> list[dict[str, Any]]:
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/v2/profiles",
            headers=self._build_headers(access_token),
            method="GET",
        )
        data = self._send_json(req, "Profiles list")
        if not isinstance(data, list):
            raise RuntimeError("Profiles list failed: payload is not an array")
        return [item for item in data if isinstance(item, dict)]

    def list_campaigns(self, access_token: str, profile_id: str) -> list[dict[str, Any]]:
        return self._paginate_campaigns("/sp/campaigns/list", access_token, profile_id)

    def list_sb_campaigns(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sb/v4/campaigns/list", access_token, profile_id, payload)

    def create_sb_campaign(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sb/v4/campaigns",
            "POST",
            access_token,
            profile_id,
            self._wrap_campaign_payload(payload),
            "Create SB campaign",
        )

    def edit_sb_campaign(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sb/v4/campaigns",
            "PUT",
            access_token,
            profile_id,
            self._wrap_campaign_payload(payload),
            "Edit SB campaign",
        )

    def archive_sb_campaign(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sb/v4/campaigns/delete",
            "POST",
            access_token,
            profile_id,
            payload,
            "Archive SB campaign",
        )

    def create_campaign(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_campaign_payload(payload)
        return self._send_mutation(
            "/sp/campaigns",
            "POST",
            access_token,
            profile_id,
            body,
            "Create campaign",
        )

    def edit_campaign(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_campaign_payload(payload)
        return self._send_mutation(
            "/sp/campaigns",
            "PUT",
            access_token,
            profile_id,
            body,
            "Edit campaign",
        )

    def list_sd_campaigns(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list("/sd/campaigns", access_token, profile_id, query, "SD campaigns list")

    def create_sd_campaign(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/campaigns",
            "POST",
            access_token,
            profile_id,
            payload.get("campaigns") if "campaigns" in payload else [payload],
            "Create SD campaign",
            accept="application/json",
            content_type="application/json",
        )

    def edit_sd_campaign(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/campaigns",
            "PUT",
            access_token,
            profile_id,
            payload.get("campaigns") if "campaigns" in payload else [payload],
            "Edit SD campaign",
            accept="application/json",
            content_type="application/json",
        )

    def list_portfolios(self, access_token: str, profile_id: str) -> list[dict[str, Any]]:
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/portfolios/list",
            headers={
                **self._build_headers(access_token),
                "Content-Type": "application/json",
                "Amazon-Advertising-API-Scope": profile_id,
            },
            data=json.dumps({}).encode("utf-8"),
            method="POST",
        )
        data = self._send_json(req, "Portfolios list")
        if isinstance(data, dict):
            rows = data.get("portfolios")
            if isinstance(rows, list):
                return [item for item in rows if isinstance(item, dict)]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        raise RuntimeError("Portfolios list failed: payload is not an array")

    def create_portfolio(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/portfolios",
            "POST",
            access_token,
            profile_id,
            self._wrap_portfolio_payload(payload),
            "Create portfolio",
        )

    def edit_portfolio(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/portfolios",
            "PUT",
            access_token,
            profile_id,
            self._wrap_portfolio_payload(payload),
            "Edit portfolio",
        )

    def list_ad_groups(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sp/adGroups/list", access_token, profile_id, payload)

    def list_sb_ad_groups(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sb/v4/adGroups/list", access_token, profile_id, payload)

    def create_sb_ad_group(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sb/v4/adGroups",
            "POST",
            access_token,
            profile_id,
            self._wrap_ad_group_payload(payload),
            "Create SB ad group",
        )

    def edit_sb_ad_group(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sb/v4/adGroups",
            "PUT",
            access_token,
            profile_id,
            self._wrap_ad_group_payload(payload),
            "Edit SB ad group",
        )

    def archive_sb_ad_group(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sb/v4/adGroups/delete",
            "POST",
            access_token,
            profile_id,
            payload,
            "Archive SB ad group",
        )

    def create_ad_group(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/adGroups",
            "POST",
            access_token,
            profile_id,
            self._wrap_ad_group_payload(payload),
            "Create ad group",
        )

    def edit_ad_group(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/adGroups",
            "PUT",
            access_token,
            profile_id,
            self._wrap_ad_group_payload(payload),
            "Edit ad group",
        )

    def list_sd_ad_groups(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list("/sd/adGroups", access_token, profile_id, query, "SD ad groups list")

    def create_sd_ad_group(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/adGroups",
            "POST",
            access_token,
            profile_id,
            payload.get("adGroups") if "adGroups" in payload else [payload],
            "Create SD ad group",
            accept="application/json",
            content_type="application/json",
        )

    def edit_sd_ad_group(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/adGroups",
            "PUT",
            access_token,
            profile_id,
            payload.get("adGroups") if "adGroups" in payload else [payload],
            "Edit SD ad group",
            accept="application/json",
            content_type="application/json",
        )

    def list_keywords(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sp/keywords/list", access_token, profile_id, payload)

    def list_sb_keywords(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list(
            "/sb/keywords",
            access_token,
            profile_id,
            query,
            "SB keywords list",
            accept="application/vnd.sbkeyword.v3+json",
        )

    def create_sb_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sb/keywords",
            "POST",
            access_token,
            profile_id,
            payload.get("keywords") if "keywords" in payload else [payload],
            "Create SB keyword",
            content_type="application/json",
            accept="application/vnd.sbkeywordresponse.v3+json",
        )

    def edit_sb_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sb/keywords",
            "PUT",
            access_token,
            profile_id,
            payload.get("keywords") if "keywords" in payload else [payload],
            "Edit SB keyword",
            content_type="application/json",
            accept="application/vnd.sbkeywordresponse.v3+json",
        )

    def archive_sb_keyword(
        self,
        access_token: str,
        profile_id: str,
        keyword_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sb/keywords/{keyword_id}",
            "DELETE",
            access_token,
            profile_id,
            None,
            "Archive SB keyword",
            accept="application/json",
        )

    def create_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_keyword_edit_payload(payload)
        return self._send_mutation(
            "/sp/keywords",
            "POST",
            access_token,
            profile_id,
            body,
            "Create keyword",
        )

    def edit_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_keyword_edit_payload(payload)
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/sp/keywords",
            method="PUT",
            data=json.dumps(body).encode("utf-8"),
            headers={
                **self._build_headers(access_token, accept_path="/sp/keywords"),
                "Content-Type": self._content_media_type("/sp/keywords"),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        return self._send_json(req, "Edit keyword")

    def list_negative_keywords(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sp/negativeKeywords/list", access_token, profile_id, payload)

    def list_sb_negative_keywords(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list(
            "/sb/negativeKeywords",
            access_token,
            profile_id,
            query,
            "SB negative keywords list",
            accept="application/vnd.sbnegativekeyword.v3+json",
        )

    def create_sb_negative_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sb/negativeKeywords",
            "POST",
            access_token,
            profile_id,
            payload.get("negativeKeywords") if "negativeKeywords" in payload else [payload],
            "Create SB negative keyword",
            content_type="application/json",
            accept="application/vnd.sbnegativekeywordresponse.v3+json",
        )

    def edit_sb_negative_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sb/negativeKeywords",
            "PUT",
            access_token,
            profile_id,
            payload.get("negativeKeywords") if "negativeKeywords" in payload else [payload],
            "Edit SB negative keyword",
            content_type="application/json",
            accept="application/vnd.sbnegativekeywordresponse.v3+json",
        )

    def archive_sb_negative_keyword(
        self,
        access_token: str,
        profile_id: str,
        keyword_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sb/negativeKeywords/{keyword_id}",
            "DELETE",
            access_token,
            profile_id,
            None,
            "Archive SB negative keyword",
            accept="application/json",
        )

    def list_product_ads(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sp/productAds/list", access_token, profile_id, payload)

    def create_product_ad(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/productAds",
            "POST",
            access_token,
            profile_id,
            self._wrap_product_ad_payload(payload),
            "Create product ad",
        )

    def edit_product_ad(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/productAds",
            "PUT",
            access_token,
            profile_id,
            self._wrap_product_ad_payload(payload),
            "Edit product ad",
        )

    def list_sd_product_ads(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list("/sd/productAds", access_token, profile_id, query, "SD product ads list")

    def create_sd_product_ad(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/productAds",
            "POST",
            access_token,
            profile_id,
            payload.get("productAds") if "productAds" in payload else [payload],
            "Create SD product ad",
            accept="application/json",
            content_type="application/json",
        )

    def edit_sd_product_ad(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/productAds",
            "PUT",
            access_token,
            profile_id,
            payload.get("productAds") if "productAds" in payload else [payload],
            "Edit SD product ad",
            accept="application/json",
            content_type="application/json",
        )

    def list_targets(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sp/targets/list", access_token, profile_id, payload)

    def list_sb_targets(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list(
            "/sb/targets",
            access_token,
            profile_id,
            query,
            "SB targets list",
            accept="application/vnd.sbtargeting.v3+json",
        )

    def create_sb_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sb/targets",
            "POST",
            access_token,
            profile_id,
            payload.get("targets") if "targets" in payload else [payload],
            "Create SB target",
            content_type="application/json",
            accept="application/vnd.sbtargetingresponse.v3+json",
        )

    def edit_sb_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sb/targets",
            "PUT",
            access_token,
            profile_id,
            payload.get("targets") if "targets" in payload else [payload],
            "Edit SB target",
            content_type="application/json",
            accept="application/vnd.sbtargetingresponse.v3+json",
        )

    def archive_sb_target(
        self,
        access_token: str,
        profile_id: str,
        target_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sb/targets/{target_id}",
            "DELETE",
            access_token,
            profile_id,
            None,
            "Archive SB target",
            accept="application/json",
        )

    def create_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/targets",
            "POST",
            access_token,
            profile_id,
            self._wrap_target_payload(payload),
            "Create target",
        )

    def edit_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/targets",
            "PUT",
            access_token,
            profile_id,
            self._wrap_target_payload(payload),
            "Edit target",
        )

    def list_sd_targets(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list("/sd/targets", access_token, profile_id, query, "SD targets list")

    def create_sd_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/targets",
            "POST",
            access_token,
            profile_id,
            payload.get("targets") if "targets" in payload else [payload],
            "Create SD target",
            accept="application/json",
            content_type="application/json",
        )

    def edit_sd_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/targets",
            "PUT",
            access_token,
            profile_id,
            payload.get("targets") if "targets" in payload else [payload],
            "Edit SD target",
            accept="application/json",
            content_type="application/json",
        )

    def list_sd_locations(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list("/sd/locations", access_token, profile_id, query, "SD locations list")

    def create_sd_location(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/locations",
            "POST",
            access_token,
            profile_id,
            payload.get("locations") if "locations" in payload else [payload],
            "Create SD location target",
            accept="application/json",
            content_type="application/json",
        )

    def edit_sd_location(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/locations",
            "PUT",
            access_token,
            profile_id,
            payload.get("locations") if "locations" in payload else [payload],
            "Edit SD location target",
            accept="application/json",
            content_type="application/json",
        )

    def sd_audience_taxonomy(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/audiences/taxonomy/list",
            "POST",
            access_token,
            profile_id,
            payload,
            "SD audience taxonomy",
            accept="application/json",
            content_type="application/json",
        )

    def sd_audience_discovery(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/audiences/list",
            "POST",
            access_token,
            profile_id,
            payload,
            "SD audience discovery",
            accept="application/json",
            content_type="application/json",
        )

    def list_negative_targets(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sp/negativeTargets/list", access_token, profile_id, payload)

    def list_sb_negative_targets(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list(
            "/sb/negativeTargets",
            access_token,
            profile_id,
            query,
            "SB negative targets list",
            accept="application/vnd.sbtargeting.v3+json",
        )

    def create_sb_negative_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sb/negativeTargets",
            "POST",
            access_token,
            profile_id,
            payload.get("negativeTargets") if "negativeTargets" in payload else [payload],
            "Create SB negative target",
            content_type="application/json",
            accept="application/vnd.sbtargetingresponse.v3+json",
        )

    def edit_sb_negative_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sb/negativeTargets",
            "PUT",
            access_token,
            profile_id,
            payload.get("negativeTargets") if "negativeTargets" in payload else [payload],
            "Edit SB negative target",
            content_type="application/json",
            accept="application/vnd.sbtargetingresponse.v3+json",
        )

    def archive_sb_negative_target(
        self,
        access_token: str,
        profile_id: str,
        target_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sb/negativeTargets/{target_id}",
            "DELETE",
            access_token,
            profile_id,
            None,
            "Archive SB negative target",
            accept="application/json",
        )

    def create_negative_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/negativeTargets",
            "POST",
            access_token,
            profile_id,
            self._wrap_negative_target_payload(payload),
            "Create negative target",
        )

    def edit_negative_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/negativeTargets",
            "PUT",
            access_token,
            profile_id,
            self._wrap_negative_target_payload(payload),
            "Edit negative target",
        )

    def list_campaign_negative_keywords(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list(
            "/sp/campaignNegativeKeywords/list",
            access_token,
            profile_id,
            payload,
        )

    def create_negative_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_negative_keyword_payload(payload)
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/sp/negativeKeywords",
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={
                **self._build_headers(access_token, accept_path="/sp/negativeKeywords"),
                "Content-Type": self._content_media_type("/sp/negativeKeywords"),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        return self._send_json(req, "Create negative keyword")

    def create_campaign_negative_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_campaign_negative_keyword_payload(payload)
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/sp/campaignNegativeKeywords",
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={
                **self._build_headers(
                    access_token, accept_path="/sp/campaignNegativeKeywords"
                ),
                "Content-Type": self._content_media_type("/sp/campaignNegativeKeywords"),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        return self._send_json(req, "Create campaign negative keyword")

    def edit_negative_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_negative_keyword_payload(payload)
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/sp/negativeKeywords",
            method="PUT",
            data=json.dumps(body).encode("utf-8"),
            headers={
                **self._build_headers(access_token, accept_path="/sp/negativeKeywords"),
                "Content-Type": self._content_media_type("/sp/negativeKeywords"),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        return self._send_json(req, "Edit negative keyword")

    def edit_campaign_negative_keyword(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_campaign_negative_keyword_payload(payload)
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/sp/campaignNegativeKeywords",
            method="PUT",
            data=json.dumps(body).encode("utf-8"),
            headers={
                **self._build_headers(
                    access_token, accept_path="/sp/campaignNegativeKeywords"
                ),
                "Content-Type": self._content_media_type("/sp/campaignNegativeKeywords"),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        return self._send_json(req, "Edit campaign negative keyword")

    def list_campaign_negative_targets(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list(
            "/sp/campaignNegativeTargets/list",
            access_token,
            profile_id,
            payload,
        )

    def create_campaign_negative_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/campaignNegativeTargets",
            "POST",
            access_token,
            profile_id,
            self._wrap_campaign_negative_target_payload(payload),
            "Create campaign negative target",
        )

    def edit_campaign_negative_target(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_mutation(
            "/sp/campaignNegativeTargets",
            "PUT",
            access_token,
            profile_id,
            self._wrap_campaign_negative_target_payload(payload),
            "Edit campaign negative target",
        )

    def list_sd_budget_rules(
        self,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self._get_list("/sd/budgetRules", access_token, profile_id, query, "SD budget rules list")

    def get_sd_budget_rule(
        self,
        access_token: str,
        profile_id: str,
        rule_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sd/budgetRules/{rule_id}",
            "GET",
            access_token,
            profile_id,
            None,
            "Get SD budget rule",
            accept="application/json",
        )

    def create_sd_budget_rule(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/budgetRules",
            "POST",
            access_token,
            profile_id,
            payload,
            "Create SD budget rule",
            accept="application/json",
            content_type="application/json",
        )

    def update_sd_budget_rule(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/budgetRules",
            "PUT",
            access_token,
            profile_id,
            payload,
            "Update SD budget rule",
            accept="application/json",
            content_type="application/json",
        )

    def associate_sd_budget_rule(
        self,
        access_token: str,
        profile_id: str,
        campaign_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            f"/sd/campaigns/{campaign_id}/budgetRules",
            "POST",
            access_token,
            profile_id,
            payload,
            "Associate SD budget rule",
            accept="application/json",
            content_type="application/json",
        )

    def disassociate_sd_budget_rule(
        self,
        access_token: str,
        profile_id: str,
        campaign_id: str,
        rule_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sd/campaigns/{campaign_id}/budgetRules/{rule_id}",
            "DELETE",
            access_token,
            profile_id,
            None,
            "Disassociate SD budget rule",
            accept="application/json",
        )

    def list_sd_budget_rule_campaigns(
        self,
        access_token: str,
        profile_id: str,
        rule_id: str,
        query: dict[str, str],
    ) -> Any:
        query_string = parse.urlencode({key: value for key, value in query.items() if value})
        path = f"/sd/budgetRules/{rule_id}/campaigns"
        if query_string:
            path = f"{path}?{query_string}"
        return self._send_request_json(
            path,
            "GET",
            access_token,
            profile_id,
            None,
            "List SD budget rule campaigns",
            accept="application/json",
        )

    def list_sd_campaign_budget_rules(
        self,
        access_token: str,
        profile_id: str,
        campaign_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sd/campaigns/{campaign_id}/budgetRules",
            "GET",
            access_token,
            profile_id,
            None,
            "List SD campaign budget rules",
            accept="application/json",
        )

    def sd_budget_usage(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            "/sd/campaigns/budget/usage",
            "POST",
            access_token,
            profile_id,
            payload,
            "SD budget usage",
            accept="application/json",
            content_type="application/json",
        )

    def request_sd_snapshot(
        self,
        access_token: str,
        profile_id: str,
        record_type: str,
        payload: dict[str, Any],
    ) -> Any:
        return self._send_request_json(
            f"/sd/{record_type}/snapshot",
            "POST",
            access_token,
            profile_id,
            payload,
            "Request SD snapshot",
            accept="application/json",
            content_type="application/json",
        )

    def get_sd_snapshot(
        self,
        access_token: str,
        profile_id: str,
        snapshot_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sd/snapshots/{snapshot_id}",
            "GET",
            access_token,
            profile_id,
            None,
            "Get SD snapshot",
            accept="application/json",
        )

    def download_sd_snapshot(
        self,
        access_token: str,
        profile_id: str,
        snapshot_id: str,
    ) -> Any:
        return self._send_request_json(
            f"/sd/snapshots/{snapshot_id}/download",
            "GET",
            access_token,
            profile_id,
            None,
            "Download SD snapshot",
            accept="application/json",
        )

    def send_sp_raw(
        self,
        access_token: str,
        profile_id: str,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
        accept: str | None = None,
        content_type: str | None = None,
    ) -> Any:
        if not path.startswith("/sp/"):
            raise ValueError("Raw SP requests must use a path that starts with /sp/.")
        normalized_method = method.upper()
        data = None
        headers = {
            **self._build_headers(access_token, accept_path=path),
            "Amazon-Advertising-API-Scope": profile_id,
        }
        if accept:
            headers["Accept"] = accept
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = content_type or self._content_media_type(path)
        elif content_type:
            headers["Content-Type"] = content_type
        req = request.Request(
            f"{get_region_base_url(self.env.region)}{path}",
            method=normalized_method,
            data=data,
            headers=headers,
        )
        return self._send_json(req, f"Raw SP request {normalized_method} {path}")

    def send_sd_raw(
        self,
        access_token: str,
        profile_id: str,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
        accept: str | None = None,
        content_type: str | None = None,
    ) -> Any:
        assert_sd_raw_allowed(path, payload)
        normalized_method = method.upper()
        return self._send_request_json(
            path,
            normalized_method,
            access_token,
            profile_id,
            payload,
            f"Raw SD request {normalized_method} {path}",
            accept=accept,
            content_type=content_type,
        )

    def send_sb_raw(
        self,
        access_token: str,
        profile_id: str,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
        accept: str | None = None,
        content_type: str | None = None,
    ) -> Any:
        assert_sb_raw_allowed(path, payload)
        normalized_method = method.upper()
        return self._send_request_json(
            path,
            normalized_method,
            access_token,
            profile_id,
            payload,
            f"Raw SB request {normalized_method} {path}",
            accept=accept,
            content_type=content_type,
        )

    def create_report(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/reporting/reports",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                **self._build_headers(access_token),
                "Content-Type": "application/json",
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        data = self._send_json(req, "Create report")
        if not isinstance(data, dict):
            raise RuntimeError("Create report failed: payload is not an object")
        return data

    def get_report(self, access_token: str, profile_id: str, report_id: str) -> dict[str, Any]:
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/reporting/reports/{report_id}",
            method="GET",
            headers={
                **self._build_headers(access_token),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        data = self._send_json(req, "Get report status")
        if not isinstance(data, dict):
            raise RuntimeError("Get report status failed: payload is not an object")
        return data

    def download_report_file(self, url: str, output_path: str) -> dict[str, Any]:
        try:
            with request.urlopen(url, timeout=60) as resp:
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "")
        except error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Download report failed: {exc.code} {payload}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Download report failed: {exc.reason}") from exc

        data = raw
        if raw[:2] == b"\x1f\x8b" or "gzip" in content_type.lower():
            data = gzip.decompress(raw)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as fh:
            fh.write(data)
        return {
            "localPath": output_path,
            "bytesWritten": len(data),
        }

    def _paginate_campaigns(
        self,
        path: str,
        access_token: str,
        profile_id: str,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        next_token = ""
        for _ in range(4):
            body: dict[str, Any] = {"pageSize": 30}
            if next_token:
                body["nextToken"] = next_token
            req = request.Request(
                f"{get_region_base_url(self.env.region)}{path}",
                method="POST",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    **self._build_headers(access_token, accept_path=path),
                    "Content-Type": self._content_media_type(path),
                    "Amazon-Advertising-API-Scope": profile_id,
                },
            )
            payload = self._send_json(req, f"Campaign list {path}")
            page_records = []
            if isinstance(payload, dict):
                for key in ("campaigns", "results", "items"):
                    candidate = payload.get(key)
                    if isinstance(candidate, list):
                        page_records = [item for item in candidate if isinstance(item, dict)]
                        break
                next_token = str(payload.get("nextToken") or "")
            elif isinstance(payload, list):
                page_records = [item for item in payload if isinstance(item, dict)]
                next_token = ""
            else:
                page_records = []
                next_token = ""
            records.extend(page_records)
            if not next_token or not page_records:
                break
        return records

    def _post_list(
        self,
        path: str,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        req = request.Request(
            f"{get_region_base_url(self.env.region)}{path}",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                **self._build_headers(access_token, accept_path=path),
                "Content-Type": self._content_media_type(path),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        data = self._send_json(req, f"List request {path}")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            for key in (
                "campaigns",
                "adGroups",
                "keywords",
                "negativeKeywords",
                "campaignNegativeKeywords",
                "productAds",
                "targetingClauses",
                "negativeTargetingClauses",
                "campaignNegativeTargetingClauses",
                "portfolios",
                "budgetRulesDetails",
                "budgetRules",
                "locations",
                "audiences",
                "snapshots",
                "results",
                "items",
            ):
                candidate = data.get(key)
                if isinstance(candidate, list):
                    return [item for item in candidate if isinstance(item, dict)]
        return []

    def _get_list(
        self,
        path: str,
        access_token: str,
        profile_id: str,
        query: dict[str, str],
        label: str,
        accept: str | None = None,
    ) -> list[dict[str, Any]]:
        query_string = parse.urlencode(
            {key: value for key, value in query.items() if value}
        )
        url = f"{get_region_base_url(self.env.region)}{path}"
        if query_string:
            url = f"{url}?{query_string}"
        headers = {
            **self._build_headers(access_token, accept_path=path),
            "Amazon-Advertising-API-Scope": profile_id,
        }
        if accept:
            headers["Accept"] = accept
        req = request.Request(url, method="GET", headers=headers)
        data = self._send_json(req, label)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            for key in (
                "campaigns",
                "adGroups",
                "keywords",
                "negativeKeywords",
                "targets",
                "negativeTargets",
                "targetingClauses",
                "negativeTargetingClauses",
                "productAds",
                "budgetRulesDetails",
                "budgetRules",
                "locations",
                "audiences",
                "taxonomies",
                "results",
                "items",
            ):
                candidate = data.get(key)
                if isinstance(candidate, list):
                    return [item for item in candidate if isinstance(item, dict)]
        return []

    def _send_mutation(
        self,
        path: str,
        method: str,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
        label: str,
    ) -> Any:
        req = request.Request(
            f"{get_region_base_url(self.env.region)}{path}",
            method=method,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                **self._build_headers(access_token, accept_path=path),
                "Content-Type": self._content_media_type(path),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        return self._send_json(req, label)

    def _send_request_json(
        self,
        path: str,
        method: str,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any] | list[Any] | None,
        label: str,
        accept: str | None = None,
        content_type: str | None = None,
    ) -> Any:
        data = None
        headers = {
            **self._build_headers(access_token, accept_path=path),
            "Amazon-Advertising-API-Scope": profile_id,
        }
        if accept:
            headers["Accept"] = accept
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = content_type or self._content_media_type(path)
        elif content_type:
            headers["Content-Type"] = content_type
        req = request.Request(
            f"{get_region_base_url(self.env.region)}{path}",
            method=method,
            data=data,
            headers=headers,
        )
        return self._send_json(req, label)

    def _build_headers(
        self,
        access_token: str,
        accept_path: str | None = None,
    ) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": self.env.client_id,
        }
        accept = self._accept_media_type(accept_path)
        if accept:
            headers["Accept"] = accept
        return headers

    def _accept_media_type(self, path: str | None) -> str:
        media_types = {
            "/sp/campaigns/list": "application/vnd.spcampaign.v3+json",
            "/sp/campaigns": "application/vnd.spcampaign.v3+json",
            "/sp/adGroups/list": "application/vnd.spadgroup.v3+json",
            "/sp/adGroups": "application/vnd.spadgroup.v3+json",
            "/sp/keywords/list": "application/vnd.spkeyword.v3+json",
            "/sp/keywords": "application/vnd.spkeyword.v3+json",
            "/sp/productAds/list": "application/vnd.spproductad.v3+json",
            "/sp/productAds": "application/vnd.spproductad.v3+json",
            "/sp/targets/list": "application/vnd.sptargetingclause.v3+json",
            "/sp/targets": "application/vnd.sptargetingclause.v3+json",
            "/sp/negativeTargets/list": "application/vnd.spnegativetargetingclause.v3+json",
            "/sp/negativeTargets": "application/vnd.spnegativetargetingclause.v3+json",
            "/sp/negativeKeywords/list": "application/vnd.spnegativekeyword.v3+json",
            "/sp/negativeKeywords": "application/vnd.spnegativekeyword.v3+json",
            "/sp/campaignNegativeKeywords/list": "application/vnd.spcampaignnegativekeyword.v3+json",
            "/sp/campaignNegativeKeywords": "application/vnd.spcampaignnegativekeyword.v3+json",
            "/sp/campaignNegativeTargets/list": "application/vnd.spcampaignnegativetargetingclause.v3+json",
            "/sp/campaignNegativeTargets": "application/vnd.spcampaignnegativetargetingclause.v3+json",
            "/sb/v4/campaigns/list": "application/vnd.sbcampaignresource.v4+json",
            "/sb/v4/campaigns": "application/vnd.sbcampaignresource.v4+json",
            "/sb/v4/campaigns/delete": "application/vnd.sbcampaignresource.v4+json",
            "/sb/v4/adGroups/list": "application/vnd.sbadgroupresource.v4+json",
            "/sb/v4/adGroups": "application/vnd.sbadgroupresource.v4+json",
            "/sb/v4/adGroups/delete": "application/vnd.sbadgroupresource.v4+json",
            "/sb/targets/products/count": "application/vnd.sbtargeting.v4+json",
        }
        return media_types.get(path or "", "")

    def _content_media_type(self, path: str | None) -> str:
        return self._accept_media_type(path) or "application/json"

    def _wrap_keyword_edit_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "keywords" in payload else {"keywords": [payload]}

    def _wrap_campaign_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "campaigns" in payload else {"campaigns": [payload]}

    def _wrap_portfolio_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "portfolios" in payload else {"portfolios": [payload]}

    def _wrap_ad_group_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "adGroups" in payload else {"adGroups": [payload]}

    def _wrap_product_ad_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "productAds" in payload else {"productAds": [payload]}

    def _wrap_target_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "targetingClauses" in payload else {"targetingClauses": [payload]}

    def _wrap_negative_target_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "negativeTargetingClauses" in payload:
            return payload
        return {"negativeTargetingClauses": [payload]}

    def _wrap_negative_keyword_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "negativeKeywords" in payload else {"negativeKeywords": [payload]}

    def _wrap_campaign_negative_keyword_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "campaignNegativeKeywords" in payload:
            return payload
        return {"campaignNegativeKeywords": [payload]}

    def _wrap_campaign_negative_target_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "campaignNegativeTargetingClauses" in payload:
            return payload
        return {"campaignNegativeTargetingClauses": [payload]}

    def _send_json(self, req: request.Request, label: str) -> Any:
        try:
            with request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{label} failed: {exc.code} {payload}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"{label} failed: {exc.reason}") from exc

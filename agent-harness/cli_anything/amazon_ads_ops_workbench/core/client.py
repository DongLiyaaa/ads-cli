from __future__ import annotations

import json
import gzip
import os
from typing import Any
from urllib import error, parse, request

from .env import AdsEnvironment, get_region_base_url


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

    def edit_campaign(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> Any:
        body = self._wrap_campaign_payload(payload)
        req = request.Request(
            f"{get_region_base_url(self.env.region)}/sp/campaigns",
            method="PUT",
            data=json.dumps(body).encode("utf-8"),
            headers={
                **self._build_headers(access_token, accept_path="/sp/campaigns"),
                "Content-Type": self._content_media_type("/sp/campaigns"),
                "Amazon-Advertising-API-Scope": profile_id,
            },
        )
        return self._send_json(req, "Edit campaign")

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

    def list_ad_groups(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sp/adGroups/list", access_token, profile_id, payload)

    def list_keywords(
        self,
        access_token: str,
        profile_id: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._post_list("/sp/keywords/list", access_token, profile_id, payload)

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
                "adGroups",
                "keywords",
                "negativeKeywords",
                "campaignNegativeKeywords",
                "portfolios",
                "results",
                "items",
            ):
                candidate = data.get(key)
                if isinstance(candidate, list):
                    return [item for item in candidate if isinstance(item, dict)]
        return []

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
            "/sp/keywords/list": "application/vnd.spkeyword.v3+json",
            "/sp/keywords": "application/vnd.spkeyword.v3+json",
            "/sp/negativeKeywords/list": "application/vnd.spnegativekeyword.v3+json",
            "/sp/negativeKeywords": "application/vnd.spnegativekeyword.v3+json",
            "/sp/campaignNegativeKeywords/list": "application/vnd.spcampaignnegativekeyword.v3+json",
            "/sp/campaignNegativeKeywords": "application/vnd.spcampaignnegativekeyword.v3+json",
        }
        return media_types.get(path or "", "")

    def _content_media_type(self, path: str | None) -> str:
        return self._accept_media_type(path) or "application/json"

    def _wrap_keyword_edit_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "keywords" in payload else {"keywords": [payload]}

    def _wrap_campaign_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "campaigns" in payload else {"campaigns": [payload]}

    def _wrap_negative_keyword_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload if "negativeKeywords" in payload else {"negativeKeywords": [payload]}

    def _wrap_campaign_negative_keyword_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "campaignNegativeKeywords" in payload:
            return payload
        return {"campaignNegativeKeywords": [payload]}

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

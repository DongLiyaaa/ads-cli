from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def build_sp_keywords_report_body(
    start_date: str,
    end_date: str,
    time_unit: str = "DAILY",
) -> dict[str, Any]:
    return {
        "name": f"sp-keywords-{start_date}-{end_date}",
        "startDate": start_date,
        "endDate": end_date,
        "configuration": {
            "adProduct": "SPONSORED_PRODUCTS",
            "groupBy": ["adGroup"],
            "columns": [
                "date",
                "keywordId",
                "keywordText",
                "matchType",
                "impressions",
                "clicks",
                "cost",
                "purchases30d",
                "sales30d",
                "topOfSearchImpressionShare",
                "campaignBudgetCurrencyCode",
            ],
            "reportTypeId": "spKeywords",
            "timeUnit": time_unit.upper(),
            "format": "GZIP_JSON",
        },
    }


def build_sp_campaign_placement_report_body(
    start_date: str,
    end_date: str,
    time_unit: str = "SUMMARY",
) -> dict[str, Any]:
    normalized_time_unit = time_unit.upper()
    columns = [
        "campaignId",
        "campaignName",
        "campaignStatus",
        "placementClassification",
        "campaignBudgetAmount",
        "campaignBudgetType",
        "campaignBudgetCurrencyCode",
        "impressions",
        "clicks",
        "cost",
        "purchases30d",
        "sales30d",
        "topOfSearchImpressionShare",
    ]
    if normalized_time_unit == "DAILY":
        columns.insert(0, "date")
    return {
        "name": f"sp-campaign-placement-{start_date}-{end_date}",
        "startDate": start_date,
        "endDate": end_date,
        "configuration": {
            "adProduct": "SPONSORED_PRODUCTS",
            "groupBy": ["campaignPlacement"],
            "columns": columns,
            "reportTypeId": "spCampaigns",
            "timeUnit": normalized_time_unit,
            "format": "GZIP_JSON",
        },
    }


def build_sp_search_term_report_body(
    start_date: str,
    end_date: str,
    time_unit: str = "SUMMARY",
) -> dict[str, Any]:
    return {
        "name": f"sp-search-terms-{start_date}-{end_date}",
        "startDate": start_date,
        "endDate": end_date,
        "configuration": {
            "adProduct": "SPONSORED_PRODUCTS",
            "groupBy": ["searchTerm"],
            "columns": [
                "date",
                "searchTerm",
                "campaignId",
                "campaignName",
                "adGroupId",
                "adGroupName",
                "keywordId",
                "keyword",
                "matchType",
                "impressions",
                "clicks",
                "cost",
                "purchases30d",
                "sales30d",
            ],
            "reportTypeId": "spSearchTerm",
            "timeUnit": time_unit.upper(),
            "format": "GZIP_JSON",
        },
    }


def build_download_target_path(output_dir: str, report_id: str, report_type: str) -> str:
    filename = f"{report_type}-{report_id}.json"
    return os.path.join(output_dir, filename)


def normalize_report_status(report: dict[str, Any]) -> dict[str, Any]:
    configuration = report.get("configuration")
    report_type = ""
    if isinstance(configuration, dict):
        report_type = str(configuration.get("reportTypeId") or "")
    return {
        "reportId": str(report.get("reportId") or ""),
        "status": str(report.get("status") or ""),
        "url": str(report.get("url") or ""),
        "failureReason": str(report.get("failureReason") or ""),
        "fileSize": report.get("fileSize"),
        "createdAt": str(report.get("createdAt") or ""),
        "generatedAt": str(report.get("generatedAt") or ""),
        "reportTypeId": report_type,
    }


def normalize_search_term_report_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": str(row.get("date") or ""),
        "campaignId": "" if row.get("campaignId") is None else str(row.get("campaignId")),
        "campaignName": str(row.get("campaignName") or ""),
        "adGroupId": "" if row.get("adGroupId") is None else str(row.get("adGroupId")),
        "adGroupName": str(row.get("adGroupName") or ""),
        "keywordId": "" if row.get("keywordId") is None else str(row.get("keywordId")),
        "keyword": str(row.get("keyword") or row.get("keywordText") or ""),
        "searchTerm": str(row.get("searchTerm") or ""),
        "matchType": str(row.get("matchType") or ""),
        "impressions": _as_int(row.get("impressions")),
        "clicks": _as_int(row.get("clicks")),
        "cost": _as_float(row.get("cost")),
        "purchases30d": _as_float(row.get("purchases30d")),
        "sales30d": _as_float(row.get("sales30d")),
    }


def normalize_sp_keyword_report_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": str(row.get("date") or ""),
        "keywordId": "" if row.get("keywordId") is None else str(row.get("keywordId")),
        "keywordText": str(row.get("keywordText") or row.get("keyword") or ""),
        "matchType": str(row.get("matchType") or ""),
        "impressions": _as_int(row.get("impressions")),
        "clicks": _as_int(row.get("clicks")),
        "cost": _as_float(row.get("cost")),
        "purchases30d": _as_float(row.get("purchases30d")),
        "sales30d": _as_float(row.get("sales30d")),
        "topOfSearchImpressionShare": _as_float(row.get("topOfSearchImpressionShare")),
        "campaignBudgetCurrencyCode": str(row.get("campaignBudgetCurrencyCode") or ""),
    }


def normalize_sp_campaign_placement_report_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": str(row.get("date") or ""),
        "campaignId": "" if row.get("campaignId") is None else str(row.get("campaignId")),
        "campaignName": str(row.get("campaignName") or ""),
        "campaignStatus": str(row.get("campaignStatus") or ""),
        "placementClassification": str(row.get("placementClassification") or ""),
        "campaignBudgetAmount": _as_float(row.get("campaignBudgetAmount")),
        "campaignBudgetType": str(row.get("campaignBudgetType") or ""),
        "campaignBudgetCurrencyCode": str(row.get("campaignBudgetCurrencyCode") or ""),
        "impressions": _as_int(row.get("impressions")),
        "clicks": _as_int(row.get("clicks")),
        "cost": _as_float(row.get("cost")),
        "purchases30d": _as_float(row.get("purchases30d")),
        "sales30d": _as_float(row.get("sales30d")),
        "topOfSearchImpressionShare": _as_float(row.get("topOfSearchImpressionShare")),
    }


def load_report_rows(input_file: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(input_file).read_text())
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("rows", "items", "data"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []


def summarize_report_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(row.get("date") or "") for row in rows if row.get("date")})
    return {
        "rows": len(rows),
        "dateStart": dates[0] if dates else "",
        "dateEnd": dates[-1] if dates else "",
        "columns": sorted({key for row in rows for key in row.keys()}),
    }


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None

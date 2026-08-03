from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CREATED_AT_KEYS = (
    "createdAt",
    "createdDate",
    "creationDate",
    "creationTime",
    "createdTime",
    "createDate",
    "createTime",
)

UPDATED_AT_KEYS = (
    "lastUpdatedAt",
    "lastUpdatedDate",
    "lastUpdateDate",
    "updatedAt",
    "updatedDate",
    "lastModifiedAt",
    "lastModifiedDate",
)


def metadata_time_fields(row: dict[str, Any]) -> dict[str, str]:
    return {
        "createdAt": normalize_metadata_timestamp(_first_metadata_value(row, CREATED_AT_KEYS)),
        "lastUpdatedAt": normalize_metadata_timestamp(_first_metadata_value(row, UPDATED_AT_KEYS)),
    }


def normalize_metadata_timestamp(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return _epoch_to_utc(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            number = float(stripped)
            if number > 1_000_000_000:
                return _epoch_to_utc(number)
        return stripped
    return str(value)


def _first_metadata_value(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    extended_data = row.get("extendedData")
    if isinstance(extended_data, dict):
        for key in keys:
            value = extended_data.get(key)
            if value not in (None, ""):
                return value
    return ""


def _epoch_to_utc(value: int | float) -> str:
    seconds = float(value)
    if seconds > 10_000_000_000:
        seconds = seconds / 1000
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

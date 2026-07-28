from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

CONFIRMATION_TEXT = "确认"
CONFIRMATION_PROMPT = "是否执行？执行请回复“确认”，不执行则无需回复！"
APPROVAL_DIR_ENV = "AMAZON_ADS_APPROVAL_DIR"


def approval_dir() -> str:
    configured = os.environ.get(APPROVAL_DIR_ENV, "").strip()
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    return os.path.join(
        os.path.expanduser("~"),
        ".local",
        "state",
        "amazon_ads_ops_workbench",
        "approvals",
    )


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def payload_hash(operation: str, marketplace: str, payload: dict[str, Any]) -> str:
    canonical = canonical_json(
        {
            "operation": operation,
            "marketplace": marketplace.upper(),
            "payload": payload,
        }
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def count_changes(payload: dict[str, Any]) -> int:
    preferred_keys = (
        "campaigns",
        "portfolios",
        "adGroups",
        "keywords",
        "productAds",
        "targets",
        "targetingClauses",
        "locations",
        "negativeKeywords",
        "campaignNegativeKeywords",
        "negativeTargetingClauses",
        "campaignNegativeTargetingClauses",
        "budgetRulesDetails",
        "budgetRuleIds",
        "campaignIds",
        "campaignIdFilter",
        "adGroupIdFilter",
    )
    total = 0
    for key in preferred_keys:
        value = payload.get(key)
        if isinstance(value, list):
            total += len(value)
    if total:
        return total
    return 1 if payload else 0


def operation_risk_level(operation: str) -> str:
    if (
        operation.startswith("sp-raw.")
        or operation.startswith("sb-raw.")
        or operation.startswith("sd-raw.")
    ):
        return "critical"
    if any(token in operation for token in ("set-state", "edit", "add", "create", "archive")):
        return "high"
    return "medium"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _plan_path(plan_id: str, base_dir: str | None = None) -> str:
    return os.path.join(base_dir or approval_dir(), f"{plan_id}.json")


def write_approval_plan(
    *,
    operation: str,
    marketplace: str,
    payload: dict[str, Any],
    policy: str,
    cli_command: str = "cli-anything-amazon-ads-ops-workbench",
) -> dict[str, Any]:
    base_dir = approval_dir()
    os.makedirs(base_dir, exist_ok=True)
    digest = payload_hash(operation, marketplace, payload)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    plan_id = f"{timestamp}-{digest[:10]}"
    plan = {
        "schemaVersion": "amazon-ads-approval-plan/v1",
        "planId": plan_id,
        "createdAt": _utc_now(),
        "status": "awaiting_user_confirmation",
        "operation": operation,
        "marketplace": marketplace.upper(),
        "riskLevel": operation_risk_level(operation),
        "changeCount": count_changes(payload),
        "payloadHash": digest,
        "policy": policy,
        "confirmation": {
            "required": True,
            "prompt": CONFIRMATION_PROMPT,
            "expectedText": CONFIRMATION_TEXT,
        },
        "execution": {
            "command": (
                f"{cli_command} --json approvals execute "
                f"--plan-id {plan_id} --confirm-text {CONFIRMATION_TEXT}"
            )
        },
        "payload": payload,
    }
    path = _plan_path(plan_id, base_dir)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp_path, path)
    return {**plan, "_approvalPath": path}


def read_approval_plan(plan_id: str) -> dict[str, Any]:
    path = _plan_path(plan_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"approval plan not found: {plan_id}")
    with open(path, "r", encoding="utf-8") as fh:
        plan = json.load(fh)
    if not isinstance(plan, dict):
        raise ValueError(f"approval plan is not a JSON object: {plan_id}")
    return {**plan, "_approvalPath": path}


def list_approval_plans(status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    base_dir = approval_dir()
    if not os.path.isdir(base_dir):
        return []
    plans: list[dict[str, Any]] = []
    for filename in os.listdir(base_dir):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(base_dir, filename), "r", encoding="utf-8") as fh:
                plan = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(plan, dict):
            continue
        if status and plan.get("status") != status:
            continue
        plans.append(
            {
                "planId": plan.get("planId"),
                "createdAt": plan.get("createdAt"),
                "status": plan.get("status"),
                "operation": plan.get("operation"),
                "marketplace": plan.get("marketplace"),
                "riskLevel": plan.get("riskLevel"),
                "changeCount": plan.get("changeCount"),
                "payloadHash": plan.get("payloadHash"),
            }
        )
    plans.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
    return plans[: max(limit, 0)]


def assert_confirmation_text(confirm_text: str) -> None:
    if confirm_text != CONFIRMATION_TEXT:
        raise ValueError(f'confirmation must be exactly "{CONFIRMATION_TEXT}"')


def mark_approval_plan_executed(plan_id: str, result: Any) -> dict[str, Any]:
    plan = read_approval_plan(plan_id)
    plan["status"] = "executed"
    plan["executedAt"] = _utc_now()
    plan["result"] = result
    path = plan["_approvalPath"]
    persisted = {key: value for key, value in plan.items() if key != "_approvalPath"}
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(persisted, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp_path, path)
    return {**persisted, "_approvalPath": path}

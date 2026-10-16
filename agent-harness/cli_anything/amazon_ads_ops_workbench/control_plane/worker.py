"""Durable PostgreSQL queue; uncertain writes are never automatically replayed."""

from datetime import timedelta
import gzip
import io
import json
import re
import time
from urllib import request, parse
from sqlalchemy import select, delete, insert
from .models import Task, Account, Token, ReportRow, now, uid
from .security import Problem, bound_hash, redact
from .service import audit
from .contracts import invoke_contract
from ..core.amc import FINAL_FAILURE_STATUSES as AMC_FAILED, parse_csv_rows
from ..core.dispatch import execute_approved_operation


def mutation_outcome(result):
    good, bad = 0, 0

    def scan(value):
        nonlocal good, bad
        if isinstance(value, list):
            for child in value:
                scan(child)
        elif isinstance(value, dict):
            for key, child in value.items():
                if key in {"error", "errors"} and child:
                    bad += len(child) if isinstance(child, list) else 1
                elif key == "success" and child:
                    good += len(child) if isinstance(child, list) else 1
                elif key == "code":
                    if str(child).upper() in {"SUCCESS", "200", "201", "202", "204"}:
                        good += 1
                    else:
                        bad += 1
                elif (
                    key
                    in {
                        "campaignId",
                        "adGroupId",
                        "keywordId",
                        "adId",
                        "productAdId",
                        "targetId",
                        "portfolioId",
                        "budgetRuleId",
                    }
                    and child
                ):
                    good += 1
                elif isinstance(child, (dict, list)):
                    scan(child)

    scan(result)
    return (
        "PARTIAL"
        if good and bad
        else "FAILED"
        if bad
        else "SUCCEEDED"
        if good
        else "UNKNOWN"
    )


def validate_download_url(url):
    parts = parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    if (
        parts.scheme != "https"
        or parts.username
        or parts.password
        or parts.port not in (None, 443)
    ):
        raise ValueError("Invalid report download URL")
    if not (host.endswith(".amazonaws.com") or host.endswith(".amazonaws.com.cn")):
        raise ValueError("Report download host is not on the Amazon S3 allowlist")
    return url


class SafeRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_download_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_rows(url, max_bytes):
    validate_download_url(url)
    with request.build_opener(SafeRedirect()).open(url, timeout=60) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("Report exceeds configured compressed-size limit")
    if data[:2] == b"\x1f\x8b":
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("Report exceeds configured uncompressed-size limit")
    rows = json.loads(data)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Unexpected report JSON shape")
    if len(rows) > 250000:
        raise ValueError("Report exceeds 250000-row limit; split its date range")
    return rows


def download_amc_rows(urls, max_bytes):
    """AMC results are one or more CSV files behind pre-signed S3 URLs."""
    if not urls:
        raise ValueError("AMC execution succeeded but returned no download URL")
    rows = []
    for url in urls:
        validate_download_url(url)
        with request.build_opener(SafeRedirect()).open(url, timeout=60) as response:
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("AMC result exceeds configured size limit")
        if data[:2] == b"\x1f\x8b":
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                data = stream.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValueError("AMC result exceeds configured size limit")
        rows.extend(parse_csv_rows(data.decode("utf-8-sig")))
        if len(rows) > 250000:
            raise ValueError("AMC result exceeds 250000-row limit; narrow the query")
    return rows


def amc_error(result, status):
    detail = {k: result.get(k) for k in ("statusReason", "errorDetails", "error") if result.get(k)}
    return f"AMC 查询状态 {status}: " + (json.dumps(detail, ensure_ascii=False) if detail else "Amazon 未返回原因")


class Worker:
    def __init__(self, service):
        self.service, self.db = service, service.db
        self.id = uid()

    def recover_expired(self):
        with self.db.sessions.begin() as s:
            tasks = s.scalars(
                select(Task)
                .where(Task.lease_until < now(), Task.lease_owner.is_not(None))
                .with_for_update(skip_locked=True)
            ).all()
            for t in tasks:
                uncertain = t.status in {"EXECUTING", "SUBMITTING"}
                t.status = (
                    "UNKNOWN" if uncertain else "WAITING" if t.remote_id else "QUEUED"
                )
                t.retry_errors += 1
                if not uncertain and t.retry_errors >= 12:
                    t.status = "FAILED"
                t.error = (
                    "任务进程中断，远端结果待核实；不会自动重发" if uncertain else None
                )
                t.lease_owner, t.lease_until, t.next_run_at = None, None, now()
                audit(
                    s, t.owner_id, "task.lease_recovered", t.status, t.account_id, t.id
                )

    def claim(self):
        self.recover_expired()
        with self.db.sessions.begin() as s:
            t = s.scalar(
                select(Task)
                .where(
                    Task.status.in_(["QUEUED", "WAITING"]), Task.next_run_at <= now()
                )
                .order_by(Task.next_run_at, Task.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if not t:
                return None
            t.status = "PROCESSING"
            t.lease_owner = self.id
            t.lease_until = now() + timedelta(minutes=10)
            t.attempts += 1
            audit(s, t.owner_id, "task.claimed", "PROCESSING", t.account_id, t.id)
            return t

    def set_stage(self, task_id, status):
        with self.db.sessions.begin() as s:
            t = s.get(Task, task_id, with_for_update=True)
            if t.lease_owner != self.id or t.status != "PROCESSING":
                raise RuntimeError("Task lease lost")
            t.status = status
            audit(s, t.owner_id, "task." + status.lower(), status, t.account_id, t.id)

    def finish(
        self,
        task,
        status,
        *,
        result=None,
        error=None,
        remote_id=None,
        remote_status=None,
        rows=None,
    ):
        with self.db.sessions.begin() as s:
            t = s.get(Task, task.id, with_for_update=True)
            if t.lease_owner != self.id:
                return
            t.status = status
            t.error = str(redact(error))[:4000] if error else None
            t.retry_errors = t.retry_errors + 1 if error else 0
            if result is not None:
                t.result = redact(result)
            if remote_id:
                t.remote_id = remote_id
            if remote_status:
                t.remote_status = remote_status
            t.lease_owner, t.lease_until = None, None
            t.next_run_at = now() + timedelta(seconds=min(120, 15 * max(1, t.attempts)))
            if rows is not None:
                s.execute(delete(ReportRow).where(ReportRow.task_id == t.id))
                for offset in range(0, len(rows), 1000):
                    s.execute(
                        insert(ReportRow),
                        [
                            {"task_id": t.id, "row_no": i, "data": row}
                            for i, row in enumerate(
                                rows[offset : offset + 1000], start=offset
                            )
                        ],
                    )
                t.row_count = len(rows)
            audit(
                s,
                t.owner_id,
                "task.finished"
                if status not in {"WAITING", "QUEUED"}
                else "task.waiting",
                status,
                t.account_id,
                t.id,
                {
                    "remote_id": t.remote_id,
                    "remote_status": t.remote_status,
                    "row_count": t.row_count,
                    "error": t.error,
                },
            )

    def run_one(self):
        task = self.claim()
        if not task:
            return False
        sent = False
        try:
            with self.db.sessions() as s:
                a = s.get(Account, task.account_id)
                if not a or a.owner_id != task.owner_id:
                    raise Problem(403, "账户所属关系无效")
                if task.source_token_id:
                    token = s.get(Token, task.source_token_id)
                    required = {
                        "read": "ads:read",
                        "report": "reports:create",
                        "write": "changes:plan",
                    }[task.kind]
                    if (
                        not token
                        or token.revoked_at
                        or token.expires_at <= now()
                        or a.id not in token.account_ids
                        or required not in token.scopes
                    ):
                        raise Problem(403, "任务来源 Token 已过期、撤销或失去账户权限")
                if task.payload_hash != bound_hash(
                    task.owner_id, a.id, a.profile_id, task.operation, task.payload
                ):
                    raise Problem(409, "任务内容完整性检查失败")
                if task.kind == "write" and (
                    task.approved_by != task.owner_id
                    or not task.approved_at
                    or task.approval_expires_at <= now()
                ):
                    raise Problem(403, "缺少有效的用户确认")
                env = self.service.environment(a)
            with self.db.api_slot():
                client, access_token, profiles, _ = self.service.gateway.context(env)
                if task.kind == "write":
                    self.set_stage(task.id, "EXECUTING")
                    sent = True
                    result = execute_approved_operation(
                        client, access_token, env.profile_id, task.payload
                    )
                    status = mutation_outcome(result)
                    self.finish(
                        task,
                        status,
                        result=result,
                        error=None
                        if status == "SUCCEEDED"
                        else "请检查逐项 API 返回结果；不会自动重复执行",
                    )
                elif task.kind == "read":
                    result = invoke_contract(
                        task.operation,
                        task.arguments,
                        env,
                        "read",
                        access_token,
                        profiles,
                    )
                    self.finish(task, "SUCCEEDED", result=result)
                elif task.payload.get("amc"):
                    instance_id = (task.result or {}).get("instanceId") or task.payload.get("instanceId")
                    entity, instance = self.service.gateway.amc(env, client, access_token, instance_id)
                    instance_id = instance["instanceId"]
                    if not task.remote_id:
                        self.set_stage(task.id, "SUBMITTING")
                        sent = True
                        result = client.amc_create_execution(
                            access_token, entity, instance_id, task.payload["execution"]
                        )
                        self.finish(
                            task,
                            "WAITING",
                            result={"instanceId": instance_id, **result},
                            remote_id=result["workflowExecutionId"],
                            remote_status=result.get("status", "PENDING"),
                        )
                    else:
                        result = client.amc_get_execution(access_token, entity, instance_id, task.remote_id)
                        status = result.get("status", "UNKNOWN")
                        result = {"instanceId": instance_id, **result}
                        if status == "SUCCEEDED":
                            urls = client.amc_download_urls(access_token, entity, instance_id, task.remote_id)
                            rows = download_amc_rows(urls, self.service.settings.report_max_bytes)
                            self.finish(task, "SUCCEEDED", result=result, remote_status=status, rows=rows)
                        elif status in AMC_FAILED:
                            self.finish(task, "FAILED", result=result, remote_status=status, error=amc_error(result, status))
                        else:
                            self.finish(task, "WAITING", result=result, remote_status=status)
                elif not task.remote_id:
                    self.set_stage(task.id, "SUBMITTING")
                    sent = True
                    try:
                        result = client.create_report(
                            access_token, env.profile_id, task.payload
                        )
                    except RuntimeError as exc:
                        duplicate = re.search(
                            r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", str(exc)
                        )
                        if (
                            "425" in str(exc)
                            and "duplicate" in str(exc).lower()
                            and duplicate
                        ):
                            result = {
                                "reportId": duplicate.group(),
                                "status": "PENDING",
                            }
                        else:
                            raise
                    report_id = result.get("reportId")
                    if not report_id:
                        raise RuntimeError(
                            "Report submission response omitted reportId"
                        )
                    self.finish(
                        task,
                        "WAITING",
                        result=result,
                        remote_id=report_id,
                        remote_status=result.get("status", "PENDING"),
                    )
                else:
                    result = client.get_report(
                        access_token, env.profile_id, task.remote_id
                    )
                    status = result.get("status", "UNKNOWN")
                    if status == "COMPLETED":
                        rows = download_rows(
                            result["url"], self.service.settings.report_max_bytes
                        )
                        self.finish(
                            task,
                            "SUCCEEDED",
                            result=result,
                            remote_status=status,
                            rows=rows,
                        )
                    elif status in {"FAILED", "CANCELLED"}:
                        self.finish(
                            task,
                            "FAILED",
                            result=result,
                            remote_status=status,
                            error=result.get("failureReason", "Amazon report failed"),
                        )
                    else:
                        self.finish(
                            task, "WAITING", result=result, remote_status=status
                        )
        except Exception as exc:
            message = str(redact(str(exc)))
            if sent:
                rejected = bool(re.search(r"failed: 4\d\d\b", message))
                self.finish(task, "FAILED" if rejected else "UNKNOWN", error=message)
            elif isinstance(exc, Problem) and exc.status != 503:
                self.finish(task, "FAILED", error=message)
            elif task.retry_errors < 12:
                self.finish(
                    task, "WAITING" if task.remote_id else "QUEUED", error=message
                )
            else:
                self.finish(task, "FAILED", error=message)
        return True

    def run(self):
        while True:
            if not self.run_one():
                time.sleep(2)

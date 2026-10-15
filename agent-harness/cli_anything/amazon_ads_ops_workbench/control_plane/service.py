from datetime import timedelta
import hmac
import re
import secrets
import threading
import time
from sqlalchemy import delete, select, func, text
from sqlalchemy.exc import IntegrityError
from ..core.client import AmazonAdsClient
from ..core.env import AdsEnvironment
from .models import (
    User,
    Session,
    Account,
    Token,
    Task,
    Audit,
    ReportRow,
    LoginAttempt,
    now,
)
from .security import (
    Actor,
    Problem,
    SCOPES,
    token_hash,
    password_matches,
    password_hash,
    encrypt_config,
    decrypt_config,
    bound_hash,
    redact,
)
from .contracts import invoke_contract, validate_arguments


USERNAME = re.compile(r"[A-Za-z0-9._@-]{3,64}")


def audit(s, owner, action, status="OK", account=None, task=None, detail=None):
    s.add(
        Audit(
            owner_id=owner,
            action=action,
            status=status,
            account_id=account,
            task_id=task,
            detail=redact(detail or {}),
        )
    )


def account_json(a):
    return {
        "id": a.id,
        "label": a.label,
        "region": a.region,
        "marketplace": a.marketplace,
        "profile_id": a.profile_id,
        "verified_at": a.verified_at.isoformat() if a.verified_at else None,
        "currency": a.profile.get("currencyCode"),
        "timezone": a.profile.get("timezone"),
        "created_at": a.created_at.isoformat(),
    }


def task_json(t, detail=False):
    value = {
        "id": t.id,
        "account_id": t.account_id,
        "kind": t.kind,
        "operation": t.operation,
        "status": t.status,
        "remote_status": t.remote_status,
        "remote_id": t.remote_id,
        "row_count": t.row_count,
        "error": t.error,
        "payload_hash": t.payload_hash,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
        "approved_at": t.approved_at.isoformat() if t.approved_at else None,
    }
    if t.kind == "report":
        # Report arguments are just the date range; lists show it without detail.
        value["arguments"] = t.arguments
    if detail:
        result = t.result
        value.update(
            arguments=t.arguments,
            payload=redact(t.payload),
            result=redact(result[:50] if isinstance(result, list) else result),
            result_truncated=isinstance(result, list) and len(result) > 50,
        )
    return value


class Gateway:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def context(self, env):
        key = token_hash(
            env.client_id + env.client_secret + env.refresh_token + env.region
        )
        with self.lock:
            cached = self.cache.get(key)
        client = AmazonAdsClient(env)
        if cached and cached[0] > time.monotonic():
            token, profiles = cached[1:]
        else:
            token = client.exchange_refresh_token()
            profiles = client.list_profiles(token)
            with self.lock:
                self.cache[key] = (time.monotonic() + 300, token, profiles)
                if len(self.cache) > 200:
                    self.cache = {
                        k: v for k, v in self.cache.items() if v[0] > time.monotonic()
                    }
        selected = next(
            (p for p in profiles if str(p.get("profileId")) == env.profile_id), None
        )
        if not selected or selected.get("countryCode") != env.marketplace:
            raise Problem(400, "Profile 不属于指定站点或当前授权账户")
        return client, token, profiles, selected


class Service:
    def __init__(self, db, settings, gateway=None):
        self.db, self.settings = db, settings
        self.gateway = gateway or Gateway()
        self.dummy_hash = password_hash(secrets.token_urlsafe(24))

    def attempt(self, s, key, message):
        # The lock also covers the absent-row case on first attempt.
        s.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(key[:15], 16)}
        )
        attempt = s.get(LoginAttempt, key)
        if attempt is None:
            attempt = LoginAttempt(key=key, count=0, window_start=now())
            s.add(attempt)
        if now() - attempt.window_start > timedelta(minutes=15):
            attempt.count, attempt.window_start = 0, now()
        if attempt.count >= 10:
            raise Problem(429, message)
        return attempt

    def login(self, username, password, ip):
        with self.db.sessions.begin() as s:
            attempt = self.attempt(
                s, token_hash(ip), "登录尝试过多，请 15 分钟后重试"
            )
            user = s.scalar(select(User).where(User.username == username))
            valid = password_matches(
                password, user.password_hash if user else self.dummy_hash
            )
            if not valid or not user:
                attempt.count += 1
                failure = True
            else:
                failure = False
                attempt.count = 0
                raw = self.open_session(s, user)
                audit(s, user.id, "session.login")
        if failure:
            raise Problem(401, "用户名或密码不正确")
        return raw

    def open_session(self, s, user):
        raw = secrets.token_urlsafe(40)
        s.add(
            Session(
                token_hash=token_hash(raw),
                user_id=user.id,
                expires_at=now() + timedelta(hours=12),
            )
        )
        return raw

    def setup_state(self):
        with self.db.sessions() as s:
            empty = not s.scalar(select(func.count()).select_from(User))
        return {
            "needs_setup": empty,
            "token_required": bool(self.settings.setup_token),
            "available": bool(self.settings.setup_token) or self.settings.loopback,
        }

    def check_setup_token(self, setup_token):
        # Setup and password reset need no login. Without a setup token anyone
        # who reaches the page could take the admin account, so only loopback
        # deployments may skip it.
        expected = self.settings.setup_token
        if expected:
            if not hmac.compare_digest(setup_token.encode(), expected.encode()):
                raise Problem(403, "初始化口令不正确")
        elif not self.settings.loopback:
            raise Problem(403, "远程部署需先在 .env 设置 ADS_SETUP_TOKEN")

    @staticmethod
    def check_password(username, password):
        if len(password) < 12:
            raise Problem(422, "密码至少需要 12 位")
        if password.lower() == username.lower():
            raise Problem(422, "密码不能与用户名相同")

    def setup_admin(self, username, password, setup_token=""):
        self.check_setup_token(setup_token)
        if not USERNAME.fullmatch(username):
            raise Problem(422, "用户名需为 3–64 位字母、数字或 . _ @ -")
        self.check_password(username, password)
        with self.db.sessions.begin() as s:
            # Same lock as migrate(), so env bootstrap and concurrent setups serialize.
            s.execute(text("SELECT pg_advisory_xact_lock(6666, 1)"))
            if s.scalar(select(func.count()).select_from(User)):
                raise Problem(409, "控制台已完成初始化，请直接登录")
            user = User(username=username, password_hash=password_hash(password))
            s.add(user)
            s.flush()
            raw = self.open_session(s, user)
            audit(s, user.id, "setup.admin_created")
        return raw

    def reset_password(self, username, password, setup_token, ip):
        self.check_setup_token(setup_token)
        self.check_password(username, password)
        with self.db.sessions.begin() as s:
            attempt = self.attempt(
                s, token_hash("reset:" + ip), "重置尝试过多，请 15 分钟后重试"
            )
            user = s.scalar(select(User).where(User.username == username))
            if user:
                user.password_hash = password_hash(password)
                # Sign out everywhere: an old session must not survive a reset.
                s.execute(delete(Session).where(Session.user_id == user.id))
                audit(s, user.id, "password.reset")
                attempt.count = 0
            else:
                attempt.count += 1
        if not user:
            raise Problem(404, "用户名不存在")
        return {"reset": True}

    def change_password(self, actor, raw_session, password):
        with self.db.sessions.begin() as s:
            user = s.get(User, actor.user_id)
            self.check_password(user.username, password)
            user.password_hash = password_hash(password)
            # Keep the current session; sign out every other one.
            s.execute(
                delete(Session).where(
                    Session.user_id == user.id,
                    Session.token_hash != token_hash(raw_session),
                )
            )
            audit(s, user.id, "password.changed")
        return {"changed": True}

    def authenticate_session(self, raw):
        if not raw:
            raise Problem(401, "请先登录")
        with self.db.sessions() as s:
            row = s.get(Session, token_hash(raw))
            if not row or row.expires_at <= now():
                raise Problem(401, "登录已过期")
            user = s.get(User, row.user_id)
            return Actor(user.id, "session"), user.username

    def authenticate_token(self, raw):
        if not raw or not raw.startswith("amcp_"):
            raise Problem(401, "缺少 MCP Bearer Token")
        with self.db.sessions.begin() as s:
            t = s.scalar(select(Token).where(Token.token_hash == token_hash(raw)))
            if not t or t.revoked_at or t.expires_at <= now():
                raise Problem(401, "MCP Token 无效、过期或已撤销")
            t.last_used_at = now()
            return Actor(
                t.owner_id, "token", frozenset(t.scopes), tuple(t.account_ids), t.id
            )

    def account(self, s, actor, account_id):
        account = s.scalar(
            select(Account).where(
                Account.id == account_id, Account.owner_id == actor.user_id
            )
        )
        if not account or not actor.account_allowed(account_id):
            raise Problem(404, "账户不存在或不可访问")
        return account

    def environment(self, account):
        config = decrypt_config(
            account.credentials_ciphertext, self.settings.encryption_key
        )
        return AdsEnvironment(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            refresh_token=config["refresh_token"],
            profile_id=account.profile_id,
            region=account.region,
            marketplace=account.marketplace,
        )

    def accounts(self, actor):
        with self.db.sessions() as s:
            rows = s.scalars(
                select(Account)
                .where(Account.owner_id == actor.user_id)
                .order_by(Account.created_at.desc())
            ).all()
            return [account_json(a) for a in rows if actor.account_allowed(a.id)]

    def add_account(self, actor, data):
        if actor.kind != "session":
            raise Problem(403, "仅管理页面可配置账户")
        credentials = {
            key: data[key] for key in ("client_id", "client_secret", "refresh_token")
        }
        a = Account(
            owner_id=actor.user_id,
            label=data["label"],
            region=data["region"],
            marketplace=data["marketplace"],
            profile_id=data["profile_id"],
            credentials_ciphertext=encrypt_config(
                credentials, self.settings.encryption_key
            ),
        )
        try:
            with self.db.sessions.begin() as s:
                s.add(a)
                s.flush()
                audit(s, actor.user_id, "account.created", account=a.id)
        except IntegrityError:
            raise Problem(409, "该 Profile 已存在") from None
        return account_json(a)

    def verify_account(self, actor, account_id):
        actor.require("ads:read")
        with self.db.sessions() as s:
            a = self.account(s, actor, account_id)
        try:
            with self.db.api_slot():
                _, _, _, profile = self.gateway.context(self.environment(a))
        except Problem:
            raise
        except Exception as exc:
            raise Problem(502, str(redact(str(exc)))) from None
        with self.db.sessions.begin() as s:
            a = self.account(s, actor, account_id)
            a.verified_at, a.profile = now(), profile
            audit(s, actor.user_id, "account.verified", account=a.id)
        return account_json(a)

    def create_token(self, actor, name, scopes, account_ids, days):
        if actor.kind != "session":
            raise Problem(403, "仅管理页面可生成 Token")
        if not scopes or not set(scopes) <= SCOPES or not account_ids:
            raise Problem(400, "请选择权限及账户")
        raw = "amcp_" + secrets.token_urlsafe(40)
        with self.db.sessions.begin() as s:
            for account_id in account_ids:
                self.account(s, actor, account_id)
            t = Token(
                owner_id=actor.user_id,
                name=name,
                prefix=raw[:14],
                token_hash=token_hash(raw),
                scopes=sorted(set(scopes)),
                account_ids=sorted(set(account_ids)),
                expires_at=now() + timedelta(days=days),
            )
            s.add(t)
            s.flush()
            audit(
                s,
                actor.user_id,
                "token.created",
                detail={"token_id": t.id, "scopes": scopes},
            )
        return {
            "id": t.id,
            "token": raw,
            "prefix": t.prefix,
            "expires_at": t.expires_at.isoformat(),
        }

    def tokens(self, actor):
        with self.db.sessions() as s:
            rows = s.scalars(
                select(Token)
                .where(Token.owner_id == actor.user_id)
                .order_by(Token.created_at.desc())
            ).all()
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "prefix": t.prefix,
                    "scopes": t.scopes,
                    "account_ids": t.account_ids,
                    "expires_at": t.expires_at.isoformat(),
                    "revoked": bool(t.revoked_at),
                    "last_used_at": t.last_used_at.isoformat()
                    if t.last_used_at
                    else None,
                }
                for t in rows
            ]

    def revoke_token(self, actor, token_id):
        with self.db.sessions.begin() as s:
            t = s.scalar(
                select(Token)
                .where(Token.id == token_id, Token.owner_id == actor.user_id)
                .with_for_update()
            )
            if not t:
                raise Problem(404, "Token 不存在")
            t.revoked_at = now()
            audit(s, actor.user_id, "token.revoked", detail={"token_id": t.id})
        return {"revoked": True}

    def create_task(self, actor, account_id, operation, arguments, key, kind):
        if not isinstance(key, str) or not 8 <= len(key) <= 120:
            raise Problem(400, "幂等键长度需为 8–120")
        actor.require(
            {"read": "ads:read", "report": "reports:create", "write": "changes:plan"}[
                kind
            ]
        )
        entry = validate_arguments(operation, arguments)
        if entry["kind"] != kind:
            raise Problem(400, "操作类型不匹配")
        with self.db.sessions() as s:
            a = self.account(s, actor, account_id)
        env = self.environment(a)
        mode = {"read": "read", "report": "report_plan", "write": "plan"}[kind]
        payload = (
            arguments
            if kind == "read"
            else invoke_contract(operation, arguments, env, mode)
        )
        digest = bound_hash(actor.user_id, a.id, a.profile_id, operation, payload)
        try:
            with self.db.sessions.begin() as s:
                old = s.scalar(
                    select(Task).where(
                        Task.owner_id == actor.user_id, Task.idempotency_key == key
                    )
                )
                if old:
                    if old.payload_hash != digest:
                        raise Problem(409, "幂等键已用于不同操作")
                    return task_json(old, True)
                t = Task(
                    owner_id=actor.user_id,
                    account_id=a.id,
                    kind=kind,
                    operation=operation,
                    arguments=arguments,
                    payload=payload,
                    payload_hash=digest,
                    idempotency_key=key,
                    source_token_id=actor.token_id,
                    status="AWAITING_CONFIRMATION" if kind == "write" else "QUEUED",
                    approval_expires_at=now() + timedelta(hours=24)
                    if kind == "write"
                    else None,
                )
                s.add(t)
                s.flush()
                audit(
                    s,
                    actor.user_id,
                    "task.created",
                    t.status,
                    a.id,
                    t.id,
                    {
                        "operation": operation,
                        "arguments": arguments,
                        "payload_hash": digest,
                    },
                )
                return task_json(t, True)
        except IntegrityError:
            with self.db.sessions() as s:
                old = s.scalar(
                    select(Task).where(
                        Task.owner_id == actor.user_id, Task.idempotency_key == key
                    )
                )
                if not old or old.payload_hash != digest:
                    raise Problem(409, "幂等键冲突") from None
                return task_json(old, True)

    def owned_task(self, s, actor, task_id):
        t = s.scalar(
            select(Task).where(Task.id == task_id, Task.owner_id == actor.user_id)
        )
        if not t or not actor.account_allowed(t.account_id):
            raise Problem(404, "任务不存在或不可访问")
        if actor.kind == "token":
            actor.require(
                "reports:read"
                if t.kind == "report"
                else "changes:plan"
                if t.kind == "write"
                else "ads:read"
            )
        return t

    def task(self, actor, task_id):
        with self.db.sessions() as s:
            return task_json(self.owned_task(s, actor, task_id), True)

    def tasks(self, actor, status=None, offset=0, limit=50, kind=None, account_id=None):
        with self.db.sessions() as s:
            q = select(Task).where(Task.owner_id == actor.user_id)
            if actor.kind == "token":
                q = q.where(Task.account_id.in_(actor.account_ids))
            if status:
                q = q.where(Task.status == status)
            if kind:
                q = q.where(Task.kind == kind)
            if account_id:
                q = q.where(Task.account_id == account_id)
            rows = s.scalars(
                q.order_by(Task.created_at.desc()).offset(offset).limit(limit)
            ).all()
            if actor.kind == "token":
                rows = [
                    t
                    for t in rows
                    if {
                        "read": "ads:read",
                        "report": "reports:read",
                        "write": "changes:plan",
                    }[t.kind]
                    in actor.scopes
                ]
            return [task_json(t) for t in rows]

    def approve(self, actor, task_id, confirm_text, expected_hash):
        if actor.kind == "token" and "changes:approve" not in actor.scopes:
            raise Problem(403, "此 MCP Token 没有“确认执行变更”权限，请在管理页面确认")
        if confirm_text != "确认":
            raise Problem(400, "请输入“确认”")
        with self.db.sessions.begin() as s:
            t = s.scalar(
                select(Task)
                .where(Task.id == task_id, Task.owner_id == actor.user_id)
                .with_for_update()
            )
            if not t:
                raise Problem(404, "任务不存在")
            if t.kind != "write" or t.status != "AWAITING_CONFIRMATION":
                raise Problem(409, "计划已执行、已确认或不可确认")
            if t.approval_expires_at <= now():
                raise Problem(409, "计划已过期，请重新生成")
            a = self.account(s, actor, t.account_id)
            if actor.kind == "token" and t.source_token_id != actor.token_id:
                raise Problem(403, "只能确认本 Token 提交的计划，其他计划请在管理页面确认")
            actual = bound_hash(
                actor.user_id, a.id, a.profile_id, t.operation, t.payload
            )
            if expected_hash != t.payload_hash or actual != expected_hash:
                raise Problem(409, "计划内容已变化")
            t.approved_by, t.approved_at, t.status, t.next_run_at = (
                actor.user_id,
                now(),
                "QUEUED",
                now(),
            )
            audit(
                s,
                actor.user_id,
                "task.approved",
                "QUEUED",
                a.id,
                t.id,
                {
                    "payload_hash": actual,
                    "via": "mcp" if actor.kind == "token" else "web",
                    "token_id": actor.token_id,
                },
            )
            return task_json(t, True)

    def cancel(self, actor, task_id):
        if actor.kind != "session":
            raise Problem(403, "仅管理页面可取消任务")
        with self.db.sessions.begin() as s:
            t = s.scalar(
                select(Task)
                .where(Task.id == task_id, Task.owner_id == actor.user_id)
                .with_for_update()
            )
            if not t:
                raise Problem(404, "任务不存在")
            if t.status not in {"QUEUED", "WAITING", "AWAITING_CONFIRMATION"}:
                raise Problem(409, "任务已开始执行或已结束，不能取消")
            t.status = "CANCELLED"
            audit(s, actor.user_id, "task.cancelled", "CANCELLED", t.account_id, t.id)
            return task_json(t)

    def result_rows(self, actor, task_id, offset, limit):
        with self.db.sessions() as s:
            t = self.owned_task(s, actor, task_id)
            if t.kind != "report":
                data = (
                    t.result
                    if isinstance(t.result, list)
                    else [t.result]
                    if t.result is not None
                    else []
                )
                return {
                    "rows": redact(data[offset : offset + limit]),
                    "total": len(data),
                    "offset": offset,
                    "status": t.status,
                }
            data = s.scalars(
                select(ReportRow)
                .where(ReportRow.task_id == task_id)
                .order_by(ReportRow.row_no)
                .offset(offset)
                .limit(limit)
            ).all()
            return {
                "rows": [r.data for r in data],
                "total": t.row_count,
                "offset": offset,
                "status": t.status,
            }

    def logs(self, actor, offset=0, limit=50):
        with self.db.sessions() as s:
            q = select(Audit).where(Audit.owner_id == actor.user_id)
            if actor.kind == "token":
                q = q.where(Audit.account_id.in_(actor.account_ids))
            rows = s.scalars(
                q.order_by(Audit.created_at.desc()).offset(offset).limit(limit)
            ).all()
            return [
                {
                    "id": r.id,
                    "action": r.action,
                    "status": r.status,
                    "account_id": r.account_id,
                    "task_id": r.task_id,
                    "detail": r.detail,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]

    def overview(self, actor):
        with self.db.sessions() as s:
            counts = dict(
                s.execute(
                    select(Task.status, func.count())
                    .where(Task.owner_id == actor.user_id)
                    .group_by(Task.status)
                ).all()
            )
            return {
                "accounts": s.scalar(
                    select(func.count())
                    .select_from(Account)
                    .where(Account.owner_id == actor.user_id)
                ),
                "tasks_by_status": counts,
                "report_rows": s.scalar(
                    select(func.coalesce(func.sum(Task.row_count), 0)).where(
                        Task.owner_id == actor.user_id
                    )
                ),
                "mcp_endpoint": self.settings.public_origin + "/mcp/",
                "max_api_concurrency": self.settings.api_concurrency,
            }

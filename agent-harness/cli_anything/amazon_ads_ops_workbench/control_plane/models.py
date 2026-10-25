from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "ads_users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Session(Base):
    __tablename__ = "ads_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("ads_users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Account(Base):
    __tablename__ = "ads_accounts"
    __table_args__ = (UniqueConstraint("owner_id", "region", "profile_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("ads_users.id"), index=True)
    label: Mapped[str] = mapped_column(String(160))
    region: Mapped[str] = mapped_column(String(2))
    marketplace: Mapped[str] = mapped_column(String(2))
    profile_id: Mapped[str] = mapped_column(String(40))
    credentials_ciphertext: Mapped[str] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    profile: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # NULL = call Amazon directly; otherwise every call leaves from this relay server.
    relay_id: Mapped[str | None] = mapped_column(String(36), index=True)


class RelayServer(Base):
    """SSH-managed server that runs ads-relay; credentials are Fernet-encrypted."""

    __tablename__ = "ads_relay_servers"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("ads_users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    host: Mapped[str] = mapped_column(String(255))
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)
    username: Mapped[str] = mapped_column(String(64))
    auth_type: Mapped[str] = mapped_column(String(16))
    credentials_ciphertext: Mapped[str] = mapped_column(Text)
    # Trust-on-first-use SSH host key ("type base64"); cleared when host/port change.
    host_key: Mapped[str | None] = mapped_column(Text)
    relay_port: Mapped[int] = mapped_column(Integer, default=8787)
    relay_secret_ciphertext: Mapped[str | None] = mapped_column(Text)
    relay_fingerprint: Mapped[str | None] = mapped_column(String(64))
    relay_version: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="NEW")
    status_detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Token(Base):
    __tablename__ = "ads_mcp_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("ads_users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    prefix: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes: Mapped[list] = mapped_column(JSONB)
    account_ids: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Fernet-encrypted plaintext so the owner can copy it again; wiped on revoke.
    token_ciphertext: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Task(Base):
    __tablename__ = "ads_tasks"
    __table_args__ = (
        UniqueConstraint("owner_id", "idempotency_key"),
        Index("ads_tasks_claim", "status", "next_run_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("ads_users.id"), index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("ads_accounts.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    operation: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="QUEUED")
    arguments: Mapped[dict] = mapped_column(JSONB, default=dict)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(120))
    source_token_id: Mapped[str | None] = mapped_column(ForeignKey("ads_mcp_tokens.id"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("ads_users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    remote_id: Mapped[str | None] = mapped_column(String(128))
    remote_status: Mapped[str | None] = mapped_column(String(40))
    result: Mapped[dict | list | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    retry_errors: Mapped[int] = mapped_column(Integer, default=0)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class ReportRow(Base):
    __tablename__ = "ads_report_rows"
    task_id: Mapped[str] = mapped_column(ForeignKey("ads_tasks.id"), primary_key=True)
    row_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)


class Audit(Base):
    __tablename__ = "ads_audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("ads_users.id"), index=True)
    account_id: Mapped[str | None] = mapped_column(String(36))
    task_id: Mapped[str | None] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, index=True
    )


class LoginAttempt(Base):
    __tablename__ = "ads_login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SchemaVersion(Base):
    __tablename__ = "ads_schema_version"
    version: Mapped[int] = mapped_column(Integer, primary_key=True)

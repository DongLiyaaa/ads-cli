import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from cryptography.fernet import Fernet

SCOPES = {"ads:read", "reports:read", "reports:create", "changes:plan"}


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


@dataclass(frozen=True)
class Actor:
    user_id: str
    kind: str
    scopes: frozenset = frozenset(SCOPES)
    account_ids: tuple = ()
    token_id: str | None = None

    def require(self, scope):
        if scope not in self.scopes:
            raise Problem(403, "令牌没有此操作权限")

    def account_allowed(self, account_id):
        return self.kind == "session" or account_id in self.account_ids


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value):
    if len(value) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def password_matches(value, encoded):
    try:
        _, salt, expected = encoded.split("$")
        actual = hashlib.scrypt(
            value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def csrf_token(session, key):
    return hmac.new(key.encode(), session.encode(), hashlib.sha256).hexdigest()


def encrypt_config(config, key):
    return Fernet(key.encode()).encrypt(json.dumps(config).encode()).decode()


def decrypt_config(value, key):
    return json.loads(Fernet(key.encode()).decrypt(value.encode()))


def redact(value):
    sensitive = {
        "clientsecret",
        "refreshtoken",
        "accesstoken",
        "authorization",
        "password",
        "credentialsciphertext",
        "url",
        "downloadurl",
        "tokenhash",
    }
    if isinstance(value, dict):
        return {
            k: "[REDACTED]"
            if re.sub("[^a-z]", "", k.lower()) in sensitive
            else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        if value.lstrip().startswith(("{", "[")):
            try:
                return json.dumps(redact(json.loads(value)), ensure_ascii=False)
            except (ValueError, RecursionError):
                pass
        value = re.sub(
            r"""(?i)("?(?:client_secret|refresh_token|access_token|password|authorization)"?\s*[:=]\s*)("[^"\n]*"|'[^'\n]*'|[^,\s}]+)""",
            r"\1[REDACTED]",
            value,
        )
        value = re.sub(r'https?://[^\s"<>]+\?[^\s"<>]+', "[signed URL omitted]", value)
        value = re.sub(
            r'(?:Atz[ar]\|[^\s"<>]+|amzn1\.oa2-cs\.[^\s"<>]+|amcp_[A-Za-z0-9_-]+)',
            "[REDACTED]",
            value,
        )
        return value[:40000]
    return value


def bound_hash(owner, account, profile, operation, payload):
    body = {
        "owner": owner,
        "account": account,
        "profile": profile,
        "operation": operation,
        "payload": payload,
    }
    return token_hash(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )

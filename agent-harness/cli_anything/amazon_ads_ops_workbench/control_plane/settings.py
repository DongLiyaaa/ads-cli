from dataclasses import dataclass
import os
from urllib.parse import urlsplit
from cryptography.fernet import Fernet


@dataclass(frozen=True)
class Settings:
    database_url: str
    encryption_key: str
    session_key: str
    admin_username: str = "admin"
    admin_password: str = ""
    setup_token: str = ""
    public_origin: str = "http://127.0.0.1:16666"
    secure_cookies: bool = False
    api_concurrency: int = 3
    frontend_dir: str = "web/dist"
    report_max_bytes: int = 64 * 1024 * 1024

    @classmethod
    def load(cls):
        s = cls(
            database_url=os.environ.get("ADS_DATABASE_URL", ""),
            encryption_key=os.environ.get("ADS_ENCRYPTION_KEY", ""),
            session_key=os.environ.get("ADS_SESSION_KEY", ""),
            admin_username=os.environ.get("ADS_ADMIN_USERNAME", "admin"),
            admin_password=os.environ.get("ADS_ADMIN_PASSWORD", ""),
            setup_token=os.environ.get("ADS_SETUP_TOKEN", ""),
            public_origin=os.environ.get(
                "ADS_PUBLIC_ORIGIN", "http://127.0.0.1:16666"
            ).rstrip("/"),
            secure_cookies=os.environ.get("ADS_SECURE_COOKIES", "false").lower()
            == "true",
            api_concurrency=int(os.environ.get("ADS_API_CONCURRENCY", "3")),
            frontend_dir=os.environ.get("ADS_FRONTEND_DIR", "web/dist"),
        )
        if not s.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("ADS_DATABASE_URL must use postgresql+psycopg://")
        if not s.encryption_key or len(s.session_key) < 32:
            raise ValueError(
                "Generate encryption and session keys using ads-control init-env"
            )
        Fernet(s.encryption_key.encode())
        origin = urlsplit(s.public_origin)
        if (
            origin.scheme not in {"http", "https"}
            or not origin.hostname
            or origin.path
            or origin.query
            or origin.fragment
            or origin.username
        ):
            raise ValueError(
                "ADS_PUBLIC_ORIGIN must be a single HTTP(S) origin without a path"
            )
        if origin.scheme == "http" and origin.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Non-loopback deployments require HTTPS")
        if not 1 <= s.api_concurrency <= 5:
            raise ValueError("API concurrency must be between 1 and 5")
        if s.public_origin.startswith("https://") and not s.secure_cookies:
            raise ValueError("HTTPS deployment requires ADS_SECURE_COOKIES=true")
        return s

    @property
    def loopback(self):
        return urlsplit(self.public_origin).hostname in {"localhost", "127.0.0.1", "::1"}

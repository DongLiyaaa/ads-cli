import argparse
import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from .settings import Settings
from .database import Database
from .service import Service


def init_env():
    path = Path(".env")
    password = secrets.token_urlsafe(32)
    data = {
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "ADS_DB_PASSWORD": password,
        "ADS_DATABASE_URL": f"postgresql+psycopg://ads_app:{password}@postgres:5432/ads_control",
        "ADS_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "ADS_SESSION_KEY": secrets.token_urlsafe(48),
        "ADS_PUBLIC_ORIGIN": "http://127.0.0.1:16666",
        "ADS_SECURE_COOKIES": "false",
        "ADS_API_CONCURRENCY": "3",
        "ADS_FRONTEND_DIR": "/app/web/dist",
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(f"{k}={v}" for k, v in data.items()) + "\n")
    print(
        "Created .env (0600); never commit this file. After startup, open the web "
        "console to create the admin account."
    )


def main():
    parser = argparse.ArgumentParser(description="Amazon Ads MCP control plane")
    parser.add_argument("command", choices=["init-env", "migrate", "serve", "worker"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6666)
    args = parser.parse_args()
    if args.command == "init-env":
        return init_env()
    settings = Settings.load()
    if args.command == "migrate":
        return Database(settings).migrate(settings)
    if args.command == "serve":
        import uvicorn
        from .app import create_app

        uvicorn.run(
            create_app(settings), host=args.host, port=args.port, access_log=False
        )
    else:
        from .worker import Worker

        Worker(Service(Database(settings), settings)).run()


if __name__ == "__main__":
    main()

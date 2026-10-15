from contextlib import contextmanager
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker
from .models import Base, User, SchemaVersion
from .security import password_hash, Problem


class Database:
    def __init__(self, settings):
        self.engine = create_engine(
            settings.database_url,
            pool_size=8,
            max_overflow=2,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.limit = settings.api_concurrency

    def migrate(self, settings):
        with self.engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(6666, 0)"))
            Base.metadata.create_all(conn)
            versions = conn.execute(select(SchemaVersion.version)).scalars().all()
            if versions and versions != [1]:
                raise RuntimeError("Unsupported DB schema version")
            if not versions:
                conn.execute(SchemaVersion.__table__.insert().values(version=1))
        with self.sessions.begin() as s:
            s.execute(text("SELECT pg_advisory_xact_lock(6666, 1)"))
            # Optional env bootstrap; otherwise the first visitor creates the
            # admin on the setup page (Service.setup_admin, same lock).
            if settings.admin_password and not s.scalar(
                select(func.count()).select_from(User)
            ):
                s.add(
                    User(
                        username=settings.admin_username,
                        password_hash=password_hash(settings.admin_password),
                    )
                )

    @contextmanager
    def api_slot(self):
        # Session advisory locks limit API calls across web and worker processes.
        with self.engine.connect() as conn:
            slot = None
            try:
                for number in range(self.limit):
                    if conn.scalar(
                        text("SELECT pg_try_advisory_lock(6667, :slot)"),
                        {"slot": number},
                    ):
                        slot = number
                        break
                if slot is None:
                    raise Problem(503, "API 并发已满，请稍后重试")
                yield
            finally:
                if slot is not None:
                    conn.execute(
                        text("SELECT pg_advisory_unlock(6667, :slot)"), {"slot": slot}
                    )
                conn.commit()

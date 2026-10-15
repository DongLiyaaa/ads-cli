"""First-run admin setup against a NEW database that has no users at all.

ADS_TEST_SETUP_DATABASE=1 python -m unittest \
 cli_anything.amazon_ads_ops_workbench.control_plane.tests.test_setup_postgres -v
"""

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from sqlalchemy import select, func
from ..settings import Settings
from ..database import Database
from ..service import Service
from ..models import User, Audit
from ..security import Problem


class SetupIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("ADS_TEST_SETUP_DATABASE") != "1":
            raise RuntimeError("Explicit empty NEW database test flag required")
        cls.settings = replace(Settings.load(), admin_password="")
        cls.db = Database(cls.settings)
        cls.db.migrate(cls.settings)
        with cls.db.sessions() as s:
            if s.scalar(select(func.count()).select_from(User)):
                raise RuntimeError("Database already has users; use a NEW database")
        cls.service = Service(cls.db, cls.settings)

    def test_first_run_creates_exactly_one_admin(self):
        self.assertTrue(self.service.setup_state()["needs_setup"])

        def attempt(n):
            try:
                return self.service.setup_admin(f"owner{n}", "setup-password-123")
            except Problem as error:
                return error.status

        with ThreadPoolExecutor(5) as pool:
            results = list(pool.map(attempt, range(5)))
        sessions = [r for r in results if isinstance(r, str)]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sorted(r for r in results if r != sessions[0]), [409] * 4)

        actor, username = self.service.authenticate_session(sessions[0])
        self.assertTrue(username.startswith("owner"))
        self.assertFalse(self.service.setup_state()["needs_setup"])
        self.assertTrue(self.service.login(username, "setup-password-123", "test"))

        # Env bootstrap must not add a second account once setup has run.
        self.db.migrate(replace(self.settings, admin_password="bootstrap-pass-123"))
        with self.db.sessions() as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(User)), 1)
            self.assertEqual(
                s.scalar(
                    select(func.count())
                    .select_from(Audit)
                    .where(
                        Audit.owner_id == actor.user_id,
                        Audit.action == "setup.admin_created",
                    )
                ),
                1,
            )

    def test_reset_and_change_password_revoke_sessions(self):
        if self.service.setup_state()["needs_setup"]:
            self.service.setup_admin("owner0", "setup-password-123")
        with self.db.sessions() as s:
            username = s.scalar(select(User.username))
        old = self.service.login(username, "setup-password-123", "test")

        self.service.reset_password(username, "reset-password-456", "", "test")
        with self.assertRaises(Problem) as error:
            self.service.authenticate_session(old)
        self.assertEqual(error.exception.status, 401)
        with self.assertRaises(Problem):
            self.service.login(username, "setup-password-123", "test")
        current = self.service.login(username, "reset-password-456", "test")
        other = self.service.login(username, "reset-password-456", "test")

        actor, _ = self.service.authenticate_session(current)
        self.service.change_password(actor, current, "change-password-789")
        self.service.authenticate_session(current)  # current device stays signed in
        with self.assertRaises(Problem):
            self.service.authenticate_session(other)
        self.assertTrue(self.service.login(username, "change-password-789", "test"))

        # Unknown usernames count towards the reset throttle.
        for _ in range(10):
            with self.assertRaises(Problem) as error:
                self.service.reset_password("nobody", "reset-password-456", "", "ip2")
            self.assertEqual(error.exception.status, 404)
        with self.assertRaises(Problem) as error:
            self.service.reset_password(username, "reset-password-456", "", "ip2")
        self.assertEqual(error.exception.status, 429)


if __name__ == "__main__":
    unittest.main()

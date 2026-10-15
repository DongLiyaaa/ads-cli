"""Run only inside the approved NEW container, before importing real accounts.

ADS_TEST_EMPTY_DATABASE=1 python -m unittest \
 cli_anything.amazon_ads_ops_workbench.control_plane.tests.test_postgres -v
"""

import os
import secrets
import unittest
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch
from sqlalchemy import select, delete, func
from fastapi.testclient import TestClient
from ..settings import Settings
from ..database import Database
from ..service import Service
from ..worker import Worker
from ..models import User, Account, Task, Token, Session, Audit, ReportRow, now
from ..security import Actor, Problem, password_hash
from ..app import create_app


class FakeClient:
    def __init__(self):
        self.submissions = 0
        self.polls = 0
        self.writes = 0
        self.fail_write = False

    def create_report(self, *args):
        self.submissions += 1
        return {"reportId": "report-fixture", "status": "PENDING"}

    def get_report(self, *args):
        self.polls += 1
        return {
            "reportId": "report-fixture",
            "status": "PENDING" if self.polls == 1 else "COMPLETED",
            "url": "https://fixture.s3.amazonaws.com/report?secret=fixture",
        }

    def create_campaign(self, *args):
        self.writes += 1
        if self.fail_write:
            raise RuntimeError("Create campaign failed: connection interrupted")
        return {"campaigns": {"success": [{"campaignId": "12345"}], "error": []}}


class FakeGateway:
    def __init__(self):
        self.client = FakeClient()

    def context(self, env):
        return (
            self.client,
            "fixture-access",
            [],
            {"profileId": 123, "countryCode": "US"},
        )


class PostgresIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("ADS_TEST_EMPTY_DATABASE") != "1":
            raise RuntimeError("Explicit empty NEW database test flag required")
        cls.settings = Settings.load()
        cls.db = Database(cls.settings)
        if "ads_control" not in cls.settings.database_url:
            raise RuntimeError("Unexpected database name")
        with cls.db.sessions() as s:
            if s.scalar(select(func.count()).select_from(Account)) or s.scalar(
                select(func.count()).select_from(Task)
            ):
                raise RuntimeError(
                    "Database is not empty; do not run integration fixtures against user data"
                )

    def setUp(self):
        self.gateway = FakeGateway()
        self.service = Service(self.db, self.settings, self.gateway)
        with self.db.sessions.begin() as s:
            user = User(
                username="integration-" + secrets.token_hex(8),
                password_hash=password_hash("fixture-password-123"),
            )
            s.add(user)
            s.flush()
            self.user_id = user.id
        self.actor = Actor(self.user_id, "session")
        a = self.service.add_account(
            self.actor,
            {
                "label": "integration fixture",
                "region": "NA",
                "marketplace": "US",
                "profile_id": "123",
                "client_id": "fixture-client-id",
                "client_secret": "fixture-client-secret",
                "refresh_token": "fixture-refresh-token",
            },
        )
        self.account_id = a["id"]

    def tearDown(self):
        with self.db.sessions.begin() as s:
            ids = s.scalars(select(Task.id).where(Task.owner_id == self.user_id)).all()
            s.execute(delete(ReportRow).where(ReportRow.task_id.in_(ids)))
            for model in (Audit, Task, Token, Account):
                s.execute(delete(model).where(model.owner_id == self.user_id))
            s.execute(delete(Session).where(Session.user_id == self.user_id))
            s.execute(delete(User).where(User.id == self.user_id))

    def plan(self, key=None):
        return self.service.create_task(
            self.actor,
            self.account_id,
            "campaigns.create",
            {
                "name": "integration-only",
                "budget": 10,
                "targeting_type": "MANUAL",
                "start_date": "2026-10-14",
                "state": "PAUSED",
            },
            key or secrets.token_hex(16),
            "write",
        )

    def due(self, task_id):
        with self.db.sessions.begin() as s:
            s.get(Task, task_id).next_run_at = now() - timedelta(seconds=1)

    def test_owner_token_scope_revoke_and_show_once(self):
        result = self.service.create_token(
            self.actor, "fixture", ["ads:read"], [self.account_id], 1
        )
        actor = self.service.authenticate_token(result["token"])
        self.assertEqual(len(self.service.accounts(actor)), 1)
        self.assertNotIn(result["token"], str(self.service.tokens(self.actor)))
        with self.assertRaises(Problem):
            self.service.task(Actor("other", "session"), self.plan()["id"])
        with self.assertRaises(Problem):
            self.service.create_task(
                actor,
                self.account_id,
                "reports.create-sp-keywords",
                {"start_date": "2026-10-01", "end_date": "2026-10-07"},
                "scope-check-123",
                "report",
            )
        self.service.revoke_token(self.actor, result["id"])
        with self.assertRaises(Problem):
            self.service.authenticate_token(result["token"])

    def test_idempotency_and_concurrent_approval(self):
        p = self.plan("idempotency-test")
        self.assertEqual(self.plan("idempotency-test")["id"], p["id"])

        def approve(_):
            try:
                self.service.approve(self.actor, p["id"], "确认", p["payload_hash"])
                return 200
            except Problem as exc:
                return exc.status

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(approve, [1, 2])), [200, 409])
        worker = Worker(self.service)
        self.assertTrue(worker.run_one())
        self.assertEqual(self.gateway.client.writes, 1)
        self.assertEqual(self.service.task(self.actor, p["id"])["status"], "SUCCEEDED")

    def test_report_survives_new_worker_and_persists_rows(self):
        t = self.service.create_task(
            self.actor,
            self.account_id,
            "reports.create-sp-campaign-placement",
            {
                "start_date": "2026-10-01",
                "end_date": "2026-10-07",
                "time_unit": "DAILY",
            },
            secrets.token_hex(16),
            "report",
        )
        self.assertTrue(Worker(self.service).run_one())
        self.due(t["id"])
        self.assertTrue(Worker(self.service).run_one())
        self.due(t["id"])
        with patch(
            "cli_anything.amazon_ads_ops_workbench.control_plane.worker.download_rows",
            return_value=[{"date": "2026-10-01", "cost": 2.3}],
        ):
            self.assertTrue(Worker(self.service).run_one())
        self.assertEqual(self.gateway.client.submissions, 1)
        task = self.service.task(self.actor, t["id"])
        self.assertEqual(task["status"], "SUCCEEDED")
        self.assertNotIn("secret=fixture", str(task))
        self.assertEqual(
            self.service.result_rows(self.actor, t["id"], 0, 50)["rows"][0]["cost"], 2.3
        )

    def test_uncertain_write_not_replayed(self):
        p = self.plan()
        self.service.approve(self.actor, p["id"], "确认", p["payload_hash"])
        self.gateway.client.fail_write = True
        worker = Worker(self.service)
        worker.run_one()
        self.assertEqual(self.service.task(self.actor, p["id"])["status"], "UNKNOWN")
        self.assertFalse(worker.run_one())
        self.assertEqual(self.gateway.client.writes, 1)

    def test_expired_execution_lease_is_unknown(self):
        p = self.plan()
        self.service.approve(self.actor, p["id"], "确认", p["payload_hash"])
        with self.db.sessions.begin() as s:
            t = s.get(Task, p["id"])
            t.status = "EXECUTING"
            t.lease_owner = "interrupted"
            t.lease_until = now() - timedelta(seconds=1)
        Worker(self.service).recover_expired()
        self.assertEqual(self.service.task(self.actor, p["id"])["status"], "UNKNOWN")

    def test_global_api_concurrency_limit(self):
        with ExitStack() as stack:
            for _ in range(self.db.limit):
                stack.enter_context(self.db.api_slot())
            with self.assertRaises(Problem):
                with self.db.api_slot():
                    pass

    def test_mcp_token_confirms_only_its_own_plan_with_scope(self):
        def token(scopes):
            raw = self.service.create_token(
                self.actor, "fixture", scopes, [self.account_id], 1
            )["token"]
            return self.service.authenticate_token(raw)

        plain = token(["changes:plan"])
        approver = token(["changes:plan", "changes:approve"])
        arguments = {
            "name": "integration-only",
            "budget": 10,
            "targeting_type": "MANUAL",
            "start_date": "2026-10-14",
            "state": "PAUSED",
        }

        def plan(actor):
            return self.service.create_task(
                actor,
                self.account_id,
                "campaigns.create",
                arguments,
                secrets.token_hex(16),
                "write",
            )

        def status(actor, p, text="确认"):
            try:
                self.service.approve(actor, p["id"], text, p["payload_hash"])
                return 200
            except Problem as exc:
                return exc.status

        own = plan(approver)
        self.assertEqual(status(plain, plan(plain)), 403)  # no approve scope
        self.assertEqual(status(approver, self.plan()), 403)  # plan from the web
        self.assertEqual(status(approver, own, "ok"), 400)  # user did not say 确认
        self.assertEqual(status(approver, own), 200)
        self.assertEqual(status(approver, own), 409)  # only once
        self.assertTrue(Worker(self.service).run_one())
        self.assertEqual(self.gateway.client.writes, 1)
        self.assertEqual(self.service.task(self.actor, own["id"])["status"], "SUCCEEDED")
        with self.db.sessions() as s:
            detail = s.scalar(
                select(Audit.detail).where(
                    Audit.task_id == own["id"], Audit.action == "task.approved"
                )
            )
        self.assertEqual((detail["via"], detail["token_id"]), ("mcp", approver.token_id))

    def test_http_login_token_approval_and_revocation(self):
        with self.db.sessions() as s:
            username = s.get(User, self.user_id).username
        with TestClient(
            create_app(self.settings, self.service),
            base_url=self.settings.public_origin,
        ) as client:
            headers = {"Origin": self.settings.public_origin}
            response = client.post(
                "/api/login",
                headers=headers,
                json={"username": username, "password": "fixture-password-123"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            headers["X-CSRF-Token"] = response.json()["csrf_token"]
            generated = client.post(
                "/api/tokens",
                headers=headers,
                json={
                    "name": "fixture",
                    "scopes": ["ads:read"],
                    "account_ids": [self.account_id],
                    "expires_in_days": 1,
                },
            )
            self.assertEqual(generated.status_code, 200, generated.text)
            raw = generated.json()["token"]
            self.assertNotIn(raw, client.get("/api/tokens").text)
            token_id = generated.json()["id"]
            client.post("/api/tokens/" + token_id + "/revoke", headers=headers, json={})
            self.assertEqual(
                client.post(
                    "/mcp/",
                    headers={"Authorization": "Bearer " + raw},
                    json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
                ).status_code,
                401,
            )


if __name__ == "__main__":
    unittest.main()

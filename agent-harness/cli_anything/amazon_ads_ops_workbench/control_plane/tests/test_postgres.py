"""Run only inside the approved NEW container, before importing real accounts.

ADS_TEST_EMPTY_DATABASE=1 python -m unittest \
 cli_anything.amazon_ads_ops_workbench.control_plane.tests.test_postgres -v
"""

import json
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
        self.amc_fail = False

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

    def amc_create_execution(self, token, entity, instance, body):
        self.amc_submitted = (entity, instance, body)
        return {"workflowExecutionId": "exec-fixture", "status": "PENDING"}

    def amc_get_execution(self, token, entity, instance, execution_id):
        self.polls += 1
        if self.amc_fail:
            return {"status": "FAILED", "statusReason": "Syntax error near FROM"}
        return {"status": "RUNNING" if self.polls == 1 else "SUCCEEDED"}

    def amc_download_urls(self, *args):
        return ["https://fixture.s3.amazonaws.com/amc.csv?X-Amz-Signature=secret"]

    ff_campaigns = ()
    unified_throttle = 0

    def query_campaign_ids(self, token, profile_id, ad_product):
        self.campaign_query = (profile_id, ad_product)
        return list(self.ff_campaigns)

    def advertiser_account_id(self, token, profile_id):
        return "amzn1.ads-account.g.fixture"

    def unified_create_report(self, token, body):
        if self.unified_throttle:
            self.unified_throttle -= 1
            raise RuntimeError("Create unified report failed: 429 Too Many Requests")
        self.unified_submitted = body
        return {"reportId": "unified-fixture", "status": "PENDING"}

    def unified_get_report(self, token, report_id):
        self.polls += 1
        report = {"reportId": report_id, "status": "PROCESSING" if self.polls == 1 else "COMPLETED"}
        if report["status"] == "COMPLETED":
            report["completedReportParts"] = [{"url": "https://fixture.s3.amazonaws.com/u.csv?X-Amz-Signature=secret"}]
        return report

    def create_campaign(self, *args):
        self.writes += 1
        if self.fail_write:
            raise RuntimeError("Create campaign failed: connection interrupted")
        return {"campaigns": {"success": [{"campaignId": "12345"}], "error": []}}


class FakeGateway:
    def __init__(self):
        self.client = FakeClient()

    def amc(self, env, client, token, instance_id=None):
        return "ENTITYFIXTURE", {"instanceId": instance_id or "amcfixture"}

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

    def amc_task(self):
        return self.service.create_task(
            self.actor,
            self.account_id,
            "reports.create-amc-query",
            {"template": "ad-product-combo", "start_date": "2026-07-01", "end_date": "2026-09-30"},
            secrets.token_hex(16),
            "report",
        )

    def test_amc_query_submits_polls_and_stores_rows(self):
        task = self.amc_task()
        csv = (
            "ad_product_combo,reached_users,purchasing_users,purchases,product_sales\n"
            ",80,3,4,99.5\nSP+SB,1200,40,41,1001.5\nSP,549634,352,395,11336.98\n"
        )
        worker = Worker(self.service)
        with patch(
            "cli_anything.amazon_ads_ops_workbench.control_plane.worker.download_amc_rows",
            side_effect=lambda urls, limit, relay=None: __import__(
                "cli_anything.amazon_ads_ops_workbench.core.amc", fromlist=["x"]
            ).parse_csv_rows(csv),
        ):
            self.assertTrue(worker.run_one())  # submit
            entity, instance, body = self.gateway.client.amc_submitted
            self.assertEqual((entity, instance), ("ENTITYFIXTURE", "amcfixture"))
            self.assertEqual(body["timeWindowEnd"], "2026-10-01T00:00:00")
            self.assertEqual(self.service.task(self.actor, task["id"])["status"], "WAITING")
            self.due(task["id"])
            self.assertTrue(worker.run_one())  # RUNNING
            self.assertEqual(self.service.task(self.actor, task["id"])["remote_status"], "RUNNING")
            self.due(task["id"])
            self.assertTrue(worker.run_one())  # SUCCEEDED
        detail = self.service.task(self.actor, task["id"])
        self.assertEqual((detail["status"], detail["row_count"]), ("SUCCEEDED", 3))
        rows = self.service.result_rows(self.actor, task["id"], 0, 200)["rows"]
        # Sorted by label; the privacy-filtered row is merged and kept last.
        self.assertEqual([r["ad_product_combo"] for r in rows], ["SP", "SP+SB", "隐私过滤合并（1 行）"])
        self.assertEqual(rows[0]["purchases"], 395)
        self.assertEqual(rows[0]["product_sales"], 11336.98)
        self.assertEqual(rows[2]["purchases"], 4)
        listed = self.service.tasks(self.actor, kind="report", operation="reports.create-amc-query")
        self.assertEqual([t["id"] for t in listed], [task["id"]])
        self.assertEqual(listed[0]["arguments"]["template"], "ad-product-combo")
        privacy = listed[0]["privacy"]
        self.assertEqual((privacy["rows"], privacy["filtered_rows"], privacy["merged"]), (3, 1, True))
        self.assertEqual(privacy["shares"]["purchases"], 0.91)

    def full_funnel_task(self):
        return self.service.create_task(
            self.actor,
            self.account_id,
            "reports.create-full-funnel-campaigns",
            {"start_date": "2026-10-01", "end_date": "2026-10-07", "time_unit": "DAILY"},
            secrets.token_hex(16),
            "report",
        )

    def test_full_funnel_without_campaigns_finishes_empty(self):
        task = self.full_funnel_task()
        self.assertTrue(Worker(self.service).run_one())
        detail = self.service.task(self.actor, task["id"])
        self.assertEqual(
            (detail["status"], detail["row_count"], detail["remote_status"]), ("SUCCEEDED", 0, "NO_CAMPAIGNS")
        )
        self.assertEqual(self.gateway.client.campaign_query[1], "FULL_FUNNEL")
        self.assertFalse(hasattr(self.gateway.client, "unified_submitted"))

    def test_full_funnel_submits_campaign_filter_polls_and_normalizes_rows(self):
        self.gateway.client.ff_campaigns = ("111", "222")
        self.gateway.client.unified_throttle = 1
        task = self.full_funnel_task()
        csv = (
            "date.value,budgetCurrency.value,campaign.id,campaign.name,metric.impressions,metric.totalCost,metric.sales\n"
            "2026-10-01,USD,111,FF one,1200,15.5,40.25\n"
        )
        worker = Worker(self.service)
        with patch(
            "cli_anything.amazon_ads_ops_workbench.control_plane.worker.download_csv_rows",
            side_effect=lambda urls, limit, relay=None, label="": __import__(
                "cli_anything.amazon_ads_ops_workbench.core.amc", fromlist=["x"]
            ).parse_csv_rows(csv),
        ):
            self.assertTrue(worker.run_one())  # throttled: requeued, not failed
            self.assertEqual(self.service.task(self.actor, task["id"])["status"], "QUEUED")
            self.due(task["id"])
            self.assertTrue(worker.run_one())  # submit
            body = self.gateway.client.unified_submitted
            report = body["reports"][0]
            self.assertEqual(report["query"]["filter"]["on"]["values"], ["111", "222"])
            self.assertEqual(report["query"]["fields"][0], "date.value")
            self.assertEqual(body["accessRequestedAccounts"], [{"advertiserAccountId": "amzn1.ads-account.g.fixture"}])
            self.due(task["id"])
            self.assertTrue(worker.run_one())  # PROCESSING
            self.due(task["id"])
            self.assertTrue(worker.run_one())  # COMPLETED
        detail = self.service.task(self.actor, task["id"])
        self.assertEqual((detail["status"], detail["row_count"]), ("SUCCEEDED", 1))
        self.assertNotIn("X-Amz-Signature", json.dumps(detail))
        row = self.service.result_rows(self.actor, task["id"], 0, 200)["rows"][0]
        self.assertEqual(
            (row["date"], row["campaignId"], row["campaignName"], row["impressions"], row["cost"], row["sales"]),
            ("2026-10-01", "111", "FF one", 1200, 15.5, 40.25),
        )

    def test_amc_failure_reports_reason(self):
        task = self.amc_task()
        self.gateway.client.amc_fail = True
        worker = Worker(self.service)
        self.assertTrue(worker.run_one())
        self.due(task["id"])
        self.assertTrue(worker.run_one())
        detail = self.service.task(self.actor, task["id"])
        self.assertEqual(detail["status"], "FAILED")
        self.assertIn("Syntax error near FROM", detail["error"])

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

    def test_token_reveal_revoke_and_delete(self):
        created = self.service.create_token(self.actor, "fixture", ["ads:read"], [self.account_id], 1)
        listed = {t["id"]: t for t in self.service.tokens(self.actor)}
        self.assertTrue(listed[created["id"]]["can_reveal"])
        self.assertEqual(self.service.reveal_token(self.actor, created["id"])["token"], created["token"])
        with self.db.sessions() as s:
            stored = s.get(Token, created["id"])
            self.assertNotIn(created["token"], stored.token_ciphertext)
        token_actor = self.service.authenticate_token(created["token"])
        with self.assertRaises(Problem) as error:
            self.service.reveal_token(token_actor, created["id"])
        self.assertEqual(error.exception.status, 403)

        # Tokens from before this release have no ciphertext.
        legacy = self.service.create_token(self.actor, "legacy", ["ads:read"], [self.account_id], 1)
        with self.db.sessions.begin() as s:
            s.get(Token, legacy["id"]).token_ciphertext = None
        with self.assertRaises(Problem) as error:
            self.service.reveal_token(self.actor, legacy["id"])
        self.assertEqual(error.exception.status, 409)
        rotated = self.service.rotate_token(self.actor, legacy["id"])
        self.assertNotEqual(rotated["token"], legacy["token"])
        self.assertEqual(self.service.reveal_token(self.actor, legacy["id"])["token"], rotated["token"])
        with self.assertRaises(Problem):
            self.service.authenticate_token(legacy["token"])
        self.assertEqual(self.service.authenticate_token(rotated["token"]).token_id, legacy["id"])
        with self.assertRaises(Problem) as error:
            self.service.rotate_token(token_actor, legacy["id"])
        self.assertEqual(error.exception.status, 403)

        self.service.revoke_token(self.actor, created["id"])
        with self.db.sessions() as s:
            self.assertIsNone(s.get(Token, created["id"]).token_ciphertext)
        with self.assertRaises(Problem) as error:
            self.service.reveal_token(self.actor, created["id"])
        self.assertEqual(error.exception.status, 409)
        with self.assertRaises(Problem) as error:
            self.service.rotate_token(self.actor, created["id"])
        self.assertEqual(error.exception.status, 409)

        live = self.service.create_token(self.actor, "live", ["ads:read"], [self.account_id], 1)
        self.service.delete_token(self.actor, live["id"])
        self.assertNotIn(live["id"], {t["id"] for t in self.service.tokens(self.actor)})
        with self.assertRaises(Problem):
            self.service.authenticate_token(live["token"])
        with self.assertRaises(Problem) as error:
            self.service.delete_token(self.actor, live["id"])
        self.assertEqual(error.exception.status, 404)

    def test_permanent_token(self):
        forever = self.service.create_token(self.actor, "forever", ["ads:read"], [self.account_id], None)
        dated = self.service.create_token(self.actor, "dated", ["ads:read"], [self.account_id], 1)
        self.assertTrue(forever["permanent"])
        self.assertFalse(dated["permanent"])
        listed = {t["id"]: t for t in self.service.tokens(self.actor)}
        self.assertTrue(listed[forever["id"]]["permanent"])
        self.assertTrue(listed[forever["id"]]["can_reveal"])
        self.assertFalse(listed[dated["id"]]["permanent"])
        self.assertEqual(self.service.authenticate_token(forever["token"]).token_id, forever["id"])
        rotated = self.service.rotate_token(self.actor, forever["id"])
        self.assertTrue({t["id"]: t for t in self.service.tokens(self.actor)}[forever["id"]]["permanent"])
        self.service.revoke_token(self.actor, forever["id"])
        with self.assertRaises(Problem):
            self.service.authenticate_token(rotated["token"])

    def test_logs_show_token_name(self):
        issued = self.service.create_token(self.actor, "agent-a", ["reports:create"], [self.account_id], 7)
        bot = self.service.authenticate_token(issued["token"])
        task = self.service.create_task(
            bot,
            self.account_id,
            "reports.create-sp-keywords",
            {"start_date": "2026-10-01", "end_date": "2026-10-07"},
            secrets.token_hex(16),
            "report",
        )
        web_task = self.service.create_task(
            self.actor,
            self.account_id,
            "reports.create-sp-keywords",
            {"start_date": "2026-10-01", "end_date": "2026-10-07"},
            secrets.token_hex(16),
            "report",
        )
        self.service.delete_token(self.actor, issued["id"])
        logs = self.service.logs(self.actor, 0, 200)
        by_task = {l["task_id"]: l for l in logs if l["action"] == "task.created"}
        self.assertEqual(by_task[task["id"]]["token_name"], "agent-a")
        self.assertEqual(by_task[task["id"]]["token_prefix"], issued["prefix"])
        self.assertIsNone(by_task[web_task["id"]]["token_name"])
        created = [l for l in logs if l["action"] == "token.created" and l["detail"]["token_id"] == issued["id"]]
        self.assertEqual(created[0]["token_name"], "agent-a")

    def test_rename_account(self):
        renamed = self.service.rename_account(self.actor, self.account_id, "  新店铺名  ")
        self.assertEqual(renamed["label"], "新店铺名")
        with self.assertRaises(Problem):
            self.service.rename_account(self.actor, self.account_id, "   ")
        with self.assertRaises(Problem):
            self.service.rename_account(Actor("other", "session"), self.account_id, "x")

    def test_report_summary_covers_all_rows(self):
        task = self.service.create_task(
            self.actor,
            self.account_id,
            "reports.create-sp-keywords",
            {"start_date": "2026-10-01", "end_date": "2026-10-07"},
            secrets.token_hex(16),
            "report",
        )
        rows = [
            {"campaignName": "A" if i % 3 else "B", "clicks": i, "cost": 0.5, "note": "x" if i == 4 else None}
            for i in range(450)
        ]
        rows.append({"campaignName": None, "clicks": "n/a", "cost": 1})
        with self.db.sessions.begin() as s:
            s.get(Task, task["id"]).status = "SUCCEEDED"
            s.get(Task, task["id"]).row_count = len(rows)
            for i, row in enumerate(rows):
                s.add(ReportRow(task_id=task["id"], row_no=i, data=row))
        result = self.service.result_summary(self.actor, task["id"], "campaignName", ["clicks", "cost"])
        self.assertEqual(result["total"]["rows"], 451)
        self.assertEqual(result["total"]["sums"]["clicks"], sum(range(450)))  # "n/a" ignored
        self.assertEqual(result["total"]["sums"]["cost"], 450 * 0.5 + 1)
        groups = {g["key"]: g for g in result["groups"]}
        self.assertEqual(set(groups), {"A", "B", None})
        self.assertEqual(groups["B"]["rows"], 150)
        self.assertEqual(groups["B"]["sums"]["clicks"], sum(range(0, 450, 3)))
        total_only = self.service.result_summary(self.actor, task["id"], None, ["clicks"])
        self.assertEqual(total_only["groups"], [])
        for bad in (["clicks;drop"], [], ["clicks", "clicks"]):
            with self.assertRaises(Problem) as error:
                self.service.result_summary(self.actor, task["id"], None, bad)
            self.assertEqual(error.exception.status, 400)
        with self.assertRaises(Problem):
            self.service.result_summary(self.actor, task["id"], "x') or 1=1 --", ["clicks"])
        with self.assertRaises(Problem):
            self.service.result_summary(Actor("other", "session"), task["id"], None, ["clicks"])

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
            self.assertFalse(generated.json()["permanent"])
            body = {"name": "forever", "scopes": ["ads:read"], "account_ids": [self.account_id]}
            forever = client.post("/api/tokens", headers=headers, json={**body, "expires_in_days": None})
            self.assertEqual(forever.status_code, 200, forever.text)
            self.assertTrue(forever.json()["permanent"])
            for bad in (0, 366, "never"):
                rejected = client.post("/api/tokens", headers=headers, json={**body, "expires_in_days": bad})
                self.assertEqual(rejected.status_code, 422, bad)
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

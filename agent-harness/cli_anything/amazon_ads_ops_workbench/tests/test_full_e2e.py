import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


def _resolve_cli(name: str):
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    return [
        sys.executable,
        "-m",
        "cli_anything.amazon_ads_ops_workbench.amazon_ads_ops_workbench_cli",
    ]


class CliE2ETests(unittest.TestCase):
    CLI_BASE = _resolve_cli("cli-anything-amazon-ads-ops-workbench")

    BLANK_ENV = {
        "AMAZON_ADS_CLIENT_ID": "",
        "AMAZON_ADS_CLIENT_SECRET": "",
        "AMAZON_ADS_REFRESH_TOKEN": "",
        "AMAZON_ADS_PROFILE_ID": "",
        "AMAZON_ADS_REGION": "NA",
        "AMAZON_ADS_MARKETPLACE": "US",
        "AMAZON_ADS_APPROVAL_DIR": os.path.join(
            tempfile.gettempdir(),
            "amazon_ads_ops_workbench_test_approvals",
        ),
    }

    def _run(self, args, extra_env=None):
        env = os.environ.copy()
        env.setdefault(
            "PYTHONPATH",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        )
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            env=env,
        )

    def _assert_approval_plan(self, result, operation):
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "approval-plan")
        self.assertEqual(payload["meta"]["status"], "awaiting_user_confirmation")
        self.assertEqual(payload["meta"]["operation"], operation)
        self.assertEqual(
            payload["meta"]["confirmationPrompt"],
            "是否执行？执行请回复“确认”，不执行则无需回复！",
        )
        self.assertTrue(payload["meta"]["planId"])
        self.assertIn("payloadHash", payload["data"])
        return payload

    def test_help(self):
        result = self._run(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage", result.stdout)
        self.assertIn("capabilities", result.stdout)

    def test_capabilities_sp_writes_are_machine_readable(self):
        result = self._run(
            [
                "--json",
                "capabilities",
                "--ad-product",
                "SP",
                "--writes-only",
                "--operation",
                "campaigns.edit-budget",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "local")
        self.assertEqual(payload["meta"]["status"], "ok")
        rows = payload["data"]["capabilities"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["operation"], "campaigns.edit-budget")
        self.assertTrue(rows[0]["canExecute"])
        self.assertTrue(rows[0]["approvalRequired"])
        self.assertEqual(rows[0]["executionMode"], "approval-gated")
        self.assertEqual(payload["data"]["summary"]["executableWrites"], 1)

    def test_capabilities_sb_writes_are_machine_readable(self):
        result = self._run(
            [
                "--json",
                "capabilities",
                "--ad-product",
                "SB",
                "--writes-only",
                "--operation",
                "sb-keywords.edit-bid",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "local")
        self.assertEqual(payload["meta"]["status"], "ok")
        self.assertIn("SP, SB, SBV, or SD", payload["meta"]["agentInstruction"])
        rows = payload["data"]["capabilities"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["operation"], "sb-keywords.edit-bid")
        self.assertEqual(rows[0]["adProduct"], "SB")
        self.assertTrue(rows[0]["canExecute"])
        self.assertTrue(rows[0]["approvalRequired"])
        self.assertEqual(rows[0]["executionMode"], "approval-gated")
        self.assertEqual(payload["data"]["summary"]["executableWrites"], 1)

    def test_capabilities_sd_writes_are_machine_readable(self):
        result = self._run(
            [
                "--json",
                "capabilities",
                "--ad-product",
                "SD",
                "--writes-only",
                "--operation",
                "sd-targets.edit-bid",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "local")
        self.assertEqual(payload["meta"]["status"], "ok")
        self.assertIn("SP, SB, SBV, or SD", payload["meta"]["agentInstruction"])
        rows = payload["data"]["capabilities"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["operation"], "sd-targets.edit-bid")
        self.assertEqual(rows[0]["adProduct"], "SD")
        self.assertTrue(rows[0]["canExecute"])
        self.assertTrue(rows[0]["approvalRequired"])

    def test_capabilities_sbv_aliases_sb_non_creative_writes(self):
        result = self._run(
            [
                "--json",
                "capabilities",
                "--ad-product",
                "SBV",
                "--writes-only",
                "--operation",
                "sb-targets.edit-bid",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["aliasOf"], "SB")
        rows = payload["data"]["capabilities"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["operation"], "sb-targets.edit-bid")
        self.assertTrue(rows[0]["approvalRequired"])

    def test_snapshot_json_without_credentials(self):
        result = self._run(
            ["--json", "snapshot"],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

    def test_keywords_json_without_credentials(self):
        result = self._run(
            ["--json", "keywords", "list", "--campaign-id", "123"],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertEqual(payload["data"]["keywords"], [])

    def test_reports_create_sp_keywords_without_credentials(self):
        result = self._run(
            [
                "--json",
                "reports",
                "create-sp-keywords",
                "--start-date",
                "2026-07-01",
                "--end-date",
                "2026-07-07",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

    def test_reports_create_sp_campaign_placement_without_credentials(self):
        result = self._run(
            [
                "--json",
                "reports",
                "create-sp-campaign-placement",
                "--start-date",
                "2026-07-01",
                "--end-date",
                "2026-07-07",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

    def test_reports_create_search_terms_without_credentials(self):
        result = self._run(
            [
                "--json",
                "reports",
                "create-search-terms",
                "--start-date",
                "2026-07-01",
                "--end-date",
                "2026-07-07",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

    def test_reports_download_without_credentials(self):
        result = self._run(
            [
                "--json",
                "reports",
                "download",
                "--report-id",
                "rpt-123",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

    def test_negatives_add_ad_group_without_credentials(self):
        result = self._run(
            [
                "--json",
                "negatives",
                "add-ad-group",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--keyword-text",
                "carplay wireless adapter",
                "--match-type",
                "NEGATIVE_EXACT",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "negatives.add-ad-group")

    def test_keywords_edit_bid_without_credentials(self):
        result = self._run(
            [
                "--json",
                "keywords",
                "edit-bid",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--keyword-id",
                "3",
                "--bid",
                "0.91",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "keywords.edit-bid")

    def test_portfolios_list_without_credentials(self):
        result = self._run(
            ["--json", "portfolios", "list"],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertEqual(payload["data"]["portfolios"], [])

    def test_ad_groups_list_without_credentials(self):
        result = self._run(
            ["--json", "ad-groups", "list", "--campaign-id", "123"],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertEqual(payload["data"]["adGroups"], [])

    def test_campaigns_set_state_without_credentials(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "set-state",
                "--campaign-id",
                "1",
                "--state",
                "PAUSED",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "campaigns.set-state")

    def test_campaigns_edit_budget_without_credentials(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "edit-budget",
                "--campaign-id",
                "1",
                "--budget",
                "5.0",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "campaigns.edit-budget")

    def test_campaigns_set_state_dry_run(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "set-state",
                "--campaign-id",
                "1",
                "--state",
                "PAUSED",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "dry-run")
        self.assertEqual(payload["data"]["payload"]["campaigns"][0]["state"], "PAUSED")

    def test_campaigns_edit_budget_dry_run(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "edit-budget",
                "--campaign-id",
                "1",
                "--budget",
                "7.5",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "dry-run")
        self.assertEqual(payload["data"]["payload"]["campaigns"][0]["budget"]["budget"], 7.5)

    def test_campaigns_edit_bidding_strategy_dry_run(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "edit-bidding-strategy",
                "--campaign-id",
                "1",
                "--strategy",
                "AUTO_FOR_SALES",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "dry-run")
        self.assertEqual(
            payload["data"]["payload"]["campaigns"][0]["dynamicBidding"]["strategy"],
            "AUTO_FOR_SALES",
        )

    def test_campaigns_edit_placement_bids_dry_run(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "edit-placement-bids",
                "--campaign-id",
                "1",
                "--top-of-search",
                "100",
                "--product-pages",
                "25",
                "--rest-of-search",
                "0",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "dry-run")
        self.assertEqual(payload["meta"]["status"], "not_submitted")
        self.assertEqual(
            payload["data"]["payload"]["campaigns"][0]["dynamicBidding"][
                "placementBidding"
            ],
            [
                {"placement": "PLACEMENT_TOP", "percentage": 100},
                {"placement": "PLACEMENT_PRODUCT_PAGE", "percentage": 25},
                {"placement": "PLACEMENT_REST_OF_SEARCH", "percentage": 0},
            ],
        )
        self.assertEqual(
            payload["data"]["placementPolicy"],
            "user_supplied_percentages_only",
        )

    def test_campaigns_edit_placement_bids_without_credentials(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "edit-placement-bids",
                "--campaign-id",
                "1",
                "--top-of-search",
                "50",
            ],
            extra_env=self.BLANK_ENV,
        )
        payload = self._assert_approval_plan(result, "campaigns.edit-placement-bids")
        self.assertEqual(payload["data"]["placementPolicy"], "user_supplied_percentages_only")

    def test_campaigns_edit_placement_bids_requires_user_value(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "edit-placement-bids",
                "--campaign-id",
                "1",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("At least one placement bid adjustment", result.stderr)

    def test_campaigns_create_dry_run(self):
        result = self._run(
            [
                "--json",
                "campaigns",
                "create",
                "--name",
                "T11 Manual",
                "--targeting-type",
                "MANUAL",
                "--budget",
                "10",
                "--start-date",
                "2026-07-22",
                "--strategy",
                "MANUAL",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        campaign = payload["data"]["payload"]["campaigns"][0]
        self.assertEqual(campaign["name"], "T11 Manual")
        self.assertEqual(campaign["targetingType"], "MANUAL")
        self.assertEqual(campaign["dynamicBidding"]["strategy"], "MANUAL")

    def test_portfolios_create_dry_run(self):
        result = self._run(
            [
                "--json",
                "portfolios",
                "create",
                "--name",
                "T11",
                "--budget",
                "100",
                "--currency-code",
                "USD",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        portfolio = payload["data"]["payload"]["portfolios"][0]
        self.assertEqual(portfolio["name"], "T11")
        self.assertEqual(portfolio["budget"]["amount"], 100.0)

    def test_portfolios_set_state_dry_run(self):
        result = self._run(
            [
                "--json",
                "portfolios",
                "set-state",
                "--portfolio-id",
                "p1",
                "--state",
                "ARCHIVED",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["payload"]["portfolios"][0]["state"], "ARCHIVED")

    def test_ad_groups_create_dry_run(self):
        result = self._run(
            [
                "--json",
                "ad-groups",
                "create",
                "--campaign-id",
                "1",
                "--name",
                "Exact Core",
                "--default-bid",
                "0.72",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        ad_group = payload["data"]["payload"]["adGroups"][0]
        self.assertEqual(ad_group["campaignId"], "1")
        self.assertEqual(ad_group["defaultBid"], 0.72)

    def test_ad_groups_set_state_dry_run(self):
        result = self._run(
            [
                "--json",
                "ad-groups",
                "set-state",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--state",
                "PAUSED",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["payload"]["adGroups"][0]["state"], "PAUSED")

    def test_ad_groups_edit_bid_dry_run(self):
        result = self._run(
            [
                "--json",
                "ad-groups",
                "edit-bid",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--default-bid",
                "0.81",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        ad_group = payload["data"]["payload"]["adGroups"][0]
        self.assertEqual(ad_group["defaultBid"], 0.81)
        self.assertNotIn("state", ad_group)

    def test_keywords_add_dry_run(self):
        result = self._run(
            [
                "--json",
                "keywords",
                "add",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--keyword-text",
                "ai recorder",
                "--match-type",
                "EXACT",
                "--bid",
                "0.91",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        keyword = payload["data"]["payload"]["keywords"][0]
        self.assertEqual(keyword["keywordText"], "ai recorder")
        self.assertEqual(keyword["matchType"], "EXACT")

    def test_keywords_edit_bid_dry_run(self):
        result = self._run(
            [
                "--json",
                "keywords",
                "edit-bid",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--keyword-id",
                "3",
                "--bid",
                "0.92",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        keyword = payload["data"]["payload"]["keywords"][0]
        self.assertEqual(keyword["bid"], 0.92)
        self.assertNotIn("state", keyword)

    def test_keywords_set_state_dry_run(self):
        result = self._run(
            [
                "--json",
                "keywords",
                "set-state",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--keyword-id",
                "3",
                "--state",
                "PAUSED",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["payload"]["keywords"][0]["state"], "PAUSED")

    def test_product_ads_list_without_credentials(self):
        result = self._run(
            ["--json", "product-ads", "list", "--campaign-id", "1"],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertEqual(payload["data"]["productAds"], [])

    def test_product_ads_add_dry_run(self):
        result = self._run(
            [
                "--json",
                "product-ads",
                "add",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--sku",
                "SKU-1",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        product_ad = payload["data"]["payload"]["productAds"][0]
        self.assertEqual(product_ad["sku"], "SKU-1")
        self.assertEqual(product_ad["state"], "ENABLED")

    def test_product_ads_set_state_dry_run(self):
        result = self._run(
            [
                "--json",
                "product-ads",
                "set-state",
                "--product-ad-id",
                "9",
                "--state",
                "ARCHIVED",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["payload"]["productAds"][0]["state"], "ARCHIVED")

    def test_targets_list_without_credentials(self):
        result = self._run(
            ["--json", "targets", "list", "--campaign-id", "1"],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertEqual(payload["data"]["targets"], [])

    def test_targets_add_asin_dry_run(self):
        result = self._run(
            [
                "--json",
                "targets",
                "add-asin",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--asin",
                "B000000001",
                "--bid",
                "0.88",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        target = payload["data"]["payload"]["targetingClauses"][0]
        self.assertEqual(target["expression"][0]["type"], "ASIN_SAME_AS")
        self.assertEqual(target["bid"], 0.88)

    def test_targets_add_category_dry_run(self):
        result = self._run(
            [
                "--json",
                "targets",
                "add-category",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--category-id",
                "123456",
                "--bid",
                "0.67",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        target = payload["data"]["payload"]["targetingClauses"][0]
        self.assertEqual(target["expression"][0]["type"], "CATEGORY_SAME_AS")
        self.assertEqual(target["expression"][0]["value"], "123456")

    def test_targets_add_expression_dry_run(self):
        result = self._run(
            [
                "--json",
                "targets",
                "add-expression",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--category-id",
                "123456",
                "--predicate",
                "BRAND_SAME_AS=Brand",
                "--expression-type",
                "AUTO",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        target = payload["data"]["payload"]["targetingClauses"][0]
        expression = target["expression"]
        self.assertEqual(expression[0]["type"], "CATEGORY_SAME_AS")
        self.assertEqual(expression[1]["type"], "BRAND_SAME_AS")
        self.assertEqual(target["expressionType"], "AUTO")

    def test_targets_edit_bid_dry_run(self):
        result = self._run(
            [
                "--json",
                "targets",
                "edit-bid",
                "--target-id",
                "9",
                "--bid",
                "0.79",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        target = payload["data"]["payload"]["targetingClauses"][0]
        self.assertEqual(target["bid"], 0.79)
        self.assertNotIn("state", target)

    def test_targets_set_state_dry_run(self):
        result = self._run(
            [
                "--json",
                "targets",
                "set-state",
                "--target-id",
                "9",
                "--state",
                "PAUSED",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["data"]["payload"]["targetingClauses"][0]["state"],
            "PAUSED",
        )

    def test_keywords_set_state_without_credentials(self):
        result = self._run(
            [
                "--json",
                "keywords",
                "set-state",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--keyword-id",
                "3",
                "--state",
                "PAUSED",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "keywords.set-state")

    def test_negatives_add_campaign_without_credentials(self):
        result = self._run(
            [
                "--json",
                "negatives",
                "add-campaign",
                "--campaign-id",
                "1",
                "--keyword-text",
                "usb c camera",
                "--match-type",
                "NEGATIVE_EXACT",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "negatives.add-campaign")

    def test_negatives_add_ad_group_dry_run(self):
        result = self._run(
            [
                "--json",
                "negatives",
                "add-ad-group",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--keyword-text",
                "carplay wireless adapter",
                "--match-type",
                "NEGATIVE_EXACT",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        negative = payload["data"]["payload"]["negativeKeywords"][0]
        self.assertEqual(negative["keywordText"], "carplay wireless adapter")

    def test_negatives_add_campaign_dry_run(self):
        result = self._run(
            [
                "--json",
                "negatives",
                "add-campaign",
                "--campaign-id",
                "1",
                "--keyword-text",
                "usb c camera",
                "--match-type",
                "NEGATIVE_EXACT",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        negative = payload["data"]["payload"]["campaignNegativeKeywords"][0]
        self.assertEqual(negative["keywordText"], "usb c camera")

    def test_negatives_set_state_dry_run(self):
        result = self._run(
            [
                "--json",
                "negatives",
                "set-state",
                "--negative-keyword-id",
                "1",
                "--scope",
                "adGroup",
                "--state",
                "PAUSED",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["payload"]["negativeKeywords"][0]["state"], "PAUSED")

    def test_negatives_set_state_without_credentials(self):
        result = self._run(
            [
                "--json",
                "negatives",
                "set-state",
                "--negative-keyword-id",
                "1",
                "--scope",
                "adGroup",
                "--state",
                "PAUSED",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "negatives.set-state")

    def test_negative_targets_list_without_credentials(self):
        result = self._run(
            ["--json", "negative-targets", "list", "--campaign-id", "1"],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertEqual(payload["data"]["negativeTargets"], [])

    def test_negative_targets_add_ad_group_asin_dry_run(self):
        result = self._run(
            [
                "--json",
                "negative-targets",
                "add-ad-group",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--asin",
                "B000000001",
                "--expression-type",
                "AUTO",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        negative_target = payload["data"]["payload"]["negativeTargetingClauses"][0]
        self.assertEqual(negative_target["expression"][0]["type"], "ASIN_SAME_AS")
        self.assertEqual(negative_target["adGroupId"], "2")
        self.assertEqual(negative_target["expressionType"], "AUTO")

    def test_negative_targets_add_campaign_category_dry_run(self):
        result = self._run(
            [
                "--json",
                "negative-targets",
                "add-campaign",
                "--campaign-id",
                "1",
                "--category-id",
                "123456",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        negative_target = payload["data"]["payload"]["campaignNegativeTargetingClauses"][0]
        self.assertEqual(negative_target["expression"][0]["type"], "CATEGORY_SAME_AS")
        self.assertNotIn("adGroupId", negative_target)

    def test_negative_targets_set_state_dry_run(self):
        result = self._run(
            [
                "--json",
                "negative-targets",
                "set-state",
                "--negative-target-id",
                "9",
                "--scope",
                "campaign",
                "--state",
                "PAUSED",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        negative_target = payload["data"]["payload"]["campaignNegativeTargetingClauses"][0]
        self.assertEqual(negative_target["targetId"], "9")
        self.assertEqual(negative_target["state"], "PAUSED")

    def test_sp_raw_request_dry_run(self):
        result = self._run(
            [
                "--json",
                "sp-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sp/targets/list",
                "--payload-json",
                '{"maxResults": 10}',
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "dry-run")
        self.assertEqual(payload["data"]["payload"]["path"], "/sp/targets/list")
        self.assertEqual(payload["data"]["payload"]["payload"]["maxResults"], 10)

    def test_sp_raw_request_rejects_non_sp_path(self):
        result = self._run(
            [
                "--json",
                "sp-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sd/campaigns/list",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must start with /sp/", result.stderr)

    def test_sp_raw_request_without_confirm_creates_approval_plan(self):
        result = self._run(
            [
                "--json",
                "sp-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sp/targets/list",
                "--payload-json",
                '{"maxResults": 10}',
            ],
            extra_env=self.BLANK_ENV,
        )
        payload = self._assert_approval_plan(result, "sp-raw.request")
        self.assertEqual(payload["data"]["riskLevel"], "critical")

    def test_sb_campaigns_create_dry_run(self):
        result = self._run(
            [
                "--json",
                "sb-campaigns",
                "create",
                "--name",
                "SB Brand Core",
                "--budget",
                "15",
                "--start-date",
                "2026-07-29",
                "--smart-default",
                "MANUAL",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        campaign = payload["data"]["payload"]["campaigns"][0]
        self.assertEqual(campaign["name"], "SB Brand Core")
        self.assertEqual(campaign["budget"], 15.0)
        self.assertEqual(campaign["budgetType"], "DAILY")
        self.assertNotIn("creative", campaign)

    def test_sb_campaigns_set_state_without_credentials(self):
        result = self._run(
            [
                "--json",
                "sb-campaigns",
                "set-state",
                "--campaign-id",
                "1",
                "--state",
                "PAUSED",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "sb-campaigns.set-state")

    def test_sb_campaigns_archive_dry_run(self):
        result = self._run(
            [
                "--json",
                "sb-campaigns",
                "archive",
                "--campaign-id",
                "1",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["data"]["payload"]["campaignIdFilter"]["include"], ["1"]
        )

    def test_sb_ad_groups_create_dry_run(self):
        result = self._run(
            [
                "--json",
                "sb-ad-groups",
                "create",
                "--campaign-id",
                "1",
                "--name",
                "SB Exact",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        ad_group = payload["data"]["payload"]["adGroups"][0]
        self.assertEqual(ad_group["campaignId"], "1")
        self.assertEqual(ad_group["state"], "PAUSED")
        self.assertNotIn("defaultBid", ad_group)

    def test_sb_ad_groups_edit_name_without_credentials(self):
        result = self._run(
            [
                "--json",
                "sb-ad-groups",
                "edit-name",
                "--ad-group-id",
                "2",
                "--name",
                "SB Phrase",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "sb-ad-groups.edit-name")

    def test_sb_keywords_add_dry_run(self):
        result = self._run(
            [
                "--json",
                "sb-keywords",
                "add",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--keyword-text",
                "ai recorder",
                "--match-type",
                "EXACT",
                "--bid",
                "0.91",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        keyword = payload["data"]["payload"]["keywords"][0]
        self.assertEqual(keyword["matchType"], "exact")
        self.assertEqual(keyword["bid"], 0.91)

    def test_sb_keywords_edit_bid_without_credentials(self):
        result = self._run(
            [
                "--json",
                "sb-keywords",
                "edit-bid",
                "--keyword-id",
                "3",
                "--bid",
                "0.92",
            ],
            extra_env=self.BLANK_ENV,
        )
        self._assert_approval_plan(result, "sb-keywords.edit-bid")

    def test_sb_negatives_add_campaign_dry_run(self):
        result = self._run(
            [
                "--json",
                "sb-negatives",
                "add-campaign",
                "--campaign-id",
                "1",
                "--keyword-text",
                "usb c camera",
                "--match-type",
                "NEGATIVE_EXACT",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        negative = payload["data"]["payload"]["negativeKeywords"][0]
        self.assertEqual(negative["matchType"], "negativeExact")
        self.assertNotIn("adGroupId", negative)

    def test_sb_targets_add_expression_dry_run(self):
        result = self._run(
            [
                "--json",
                "sb-targets",
                "add-expression",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--asin",
                "B000000001",
                "--predicate",
                "asinPriceBetween=10-20",
                "--bid",
                "0.88",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        target = payload["data"]["payload"]["targets"][0]
        self.assertEqual(target["expression"][0]["type"], "asinSameAs")
        self.assertEqual(target["expression"][1]["type"], "asinPriceBetween")
        self.assertEqual(target["bid"], 0.88)

    def test_sb_negative_targets_add_campaign_dry_run(self):
        result = self._run(
            [
                "--json",
                "sb-negative-targets",
                "add-campaign",
                "--campaign-id",
                "1",
                "--asin",
                "B000000001",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        negative_target = payload["data"]["payload"]["negativeTargets"][0]
        self.assertEqual(negative_target["expression"][0]["type"], "asinSameAs")
        self.assertNotIn("adGroupId", negative_target)

    def test_sb_raw_request_dry_run(self):
        result = self._run(
            [
                "--json",
                "sb-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sb/v4/campaigns/list",
                "--payload-json",
                '{"maxResults": 10}',
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "dry-run")
        self.assertEqual(payload["data"]["payload"]["path"], "/sb/v4/campaigns/list")

    def test_sb_raw_rejects_media_path_and_payload(self):
        media_path = self._run(
            [
                "--json",
                "sb-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sb/v4/ads/video",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertNotEqual(media_path.returncode, 0)
        self.assertIn("blocked", media_path.stderr)

        media_payload = self._run(
            [
                "--json",
                "sb-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sb/v4/campaigns",
                "--payload-json",
                '{"creative": {"headline": "x"}}',
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertNotEqual(media_payload.returncode, 0)
        self.assertIn("blocked media/creative key", media_payload.stderr)

    def test_sb_raw_without_confirm_creates_critical_approval_plan(self):
        result = self._run(
            [
                "--json",
                "sb-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sb/v4/campaigns/list",
                "--payload-json",
                '{"maxResults": 10}',
            ],
            extra_env=self.BLANK_ENV,
        )
        payload = self._assert_approval_plan(result, "sb-raw.request")
        self.assertEqual(payload["data"]["riskLevel"], "critical")

    def test_reports_create_sb_targeting_without_credentials(self):
        result = self._run(
            [
                "--json",
                "reports",
                "create-sb-targeting",
                "--start-date",
                "2026-07-01",
                "--end-date",
                "2026-07-07",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertEqual(payload["data"]["requested"]["reportTypeId"], "sbTargeting")

    def test_sd_campaigns_create_dry_run(self):
        result = self._run(
            [
                "--json",
                "sd-campaigns",
                "create",
                "--name",
                "SD Retargeting",
                "--budget",
                "18.5",
                "--start-date",
                "2026-07-29",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        campaign = payload["data"]["payload"]["campaigns"][0]
        self.assertEqual(payload["meta"]["mode"], "dry-run")
        self.assertEqual(campaign["budget"], "18.50")
        self.assertEqual(campaign["startDate"], "20260729")
        self.assertEqual(campaign["state"], "paused")

    def test_sd_campaigns_set_state_without_credentials(self):
        result = self._run(
            [
                "--json",
                "sd-campaigns",
                "set-state",
                "--campaign-id",
                "1",
                "--state",
                "paused",
            ],
            extra_env=self.BLANK_ENV,
        )
        plan = self._assert_approval_plan(result, "sd-campaigns.set-state")
        self.assertEqual(plan["data"]["riskLevel"], "high")

    def test_sd_ad_groups_product_ads_targets_and_locations_dry_run(self):
        ad_group = self._run(
            [
                "--json",
                "sd-ad-groups",
                "create",
                "--campaign-id",
                "1",
                "--name",
                "SD Core",
                "--default-bid",
                "0.72",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(ad_group.returncode, 0, ad_group.stderr)
        ad_group_payload = json.loads(ad_group.stdout)
        self.assertEqual(
            ad_group_payload["data"]["payload"]["adGroups"][0]["defaultBid"],
            0.72,
        )

        product_ad = self._run(
            [
                "--json",
                "sd-product-ads",
                "add",
                "--campaign-id",
                "1",
                "--ad-group-id",
                "2",
                "--sku",
                "SKU-1",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(product_ad.returncode, 0, product_ad.stderr)
        product_ad_payload = json.loads(product_ad.stdout)
        self.assertEqual(product_ad_payload["data"]["payload"]["productAds"][0]["sku"], "SKU-1")

        target = self._run(
            [
                "--json",
                "sd-targets",
                "add-audience",
                "--ad-group-id",
                "2",
                "--audience-id",
                "aud-1",
                "--bid",
                "0.88",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(target.returncode, 0, target.stderr)
        target_payload = json.loads(target.stdout)
        target_row = target_payload["data"]["payload"]["targets"][0]
        self.assertEqual(target_row["expression"][0]["type"], "audience")
        self.assertEqual(target_row["bid"], "0.88")

        location = self._run(
            [
                "--json",
                "sd-locations",
                "add",
                "--ad-group-id",
                "2",
                "--location-id",
                "loc-1",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(location.returncode, 0, location.stderr)
        location_payload = json.loads(location.stdout)
        self.assertEqual(
            location_payload["data"]["payload"]["locations"][0]["expression"][0]["type"],
            "location",
        )

    def test_sd_budget_rules_create_dry_run_and_associate_plan(self):
        create = self._run(
            [
                "--json",
                "sd-budget-rules",
                "create",
                "--name",
                "Prime Day",
                "--rule-type",
                "SCHEDULE",
                "--increase-type",
                "PERCENT",
                "--increase-value",
                "20",
                "--start-date",
                "2026-07-29",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(create.returncode, 0, create.stderr)
        create_payload = json.loads(create.stdout)
        rule = create_payload["data"]["payload"]["budgetRulesDetails"][0]
        self.assertEqual(rule["budgetIncreaseBy"]["value"], 20.0)
        self.assertEqual(rule["duration"]["dateRangeTypeRuleDuration"]["startDate"], "20260729")

        associate = self._run(
            [
                "--json",
                "sd-budget-rules",
                "associate",
                "--campaign-id",
                "1",
                "--rule-id",
                "rule-1",
            ],
            extra_env=self.BLANK_ENV,
        )
        plan = self._assert_approval_plan(associate, "sd-budget-rules.associate")
        self.assertEqual(plan["data"]["changeCount"], 1)

    def test_sd_raw_request_dry_run_and_media_block(self):
        result = self._run(
            [
                "--json",
                "sd-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sd/campaigns",
                "--payload-json",
                '[{"name": "x"}]',
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "dry-run")
        self.assertEqual(payload["data"]["payload"]["path"], "/sd/campaigns")

        blocked = self._run(
            [
                "--json",
                "sd-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sd/creatives",
                "--payload-json",
                "{}",
                "--dry-run",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("blocked", blocked.stderr)

    def test_sd_raw_without_confirm_creates_critical_approval_plan(self):
        result = self._run(
            [
                "--json",
                "sd-raw",
                "request",
                "--method",
                "POST",
                "--path",
                "/sd/campaigns",
                "--payload-json",
                '[{"name": "x"}]',
            ],
            extra_env=self.BLANK_ENV,
        )
        payload = self._assert_approval_plan(result, "sd-raw.request")
        self.assertEqual(payload["data"]["riskLevel"], "critical")

    def test_reports_create_sd_targeting_without_credentials(self):
        result = self._run(
            [
                "--json",
                "reports",
                "create-sd-targeting",
                "--start-date",
                "2026-07-01",
                "--end-date",
                "2026-07-07",
            ],
            extra_env=self.BLANK_ENV,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertEqual(payload["data"]["requested"]["reportTypeId"], "sdTargeting")

    def test_approval_plan_show_list_and_execute_guard(self):
        with tempfile.TemporaryDirectory() as approval_dir:
            env = dict(self.BLANK_ENV)
            env["AMAZON_ADS_APPROVAL_DIR"] = approval_dir
            planned = self._run(
                [
                    "--json",
                    "campaigns",
                    "set-state",
                    "--campaign-id",
                    "1",
                    "--state",
                    "PAUSED",
                ],
                extra_env=env,
            )
            plan_payload = self._assert_approval_plan(planned, "campaigns.set-state")
            plan_id = plan_payload["meta"]["planId"]

            shown = self._run(
                ["--json", "approvals", "show", "--plan-id", plan_id],
                extra_env=env,
            )
            self.assertEqual(shown.returncode, 0, shown.stderr)
            shown_payload = json.loads(shown.stdout)
            self.assertEqual(shown_payload["planId"], plan_id)
            self.assertEqual(shown_payload["payload"]["campaigns"][0]["state"], "PAUSED")

            listed = self._run(
                [
                    "--json",
                    "approvals",
                    "list",
                    "--status",
                    "awaiting_user_confirmation",
                ],
                extra_env=env,
            )
            self.assertEqual(listed.returncode, 0, listed.stderr)
            list_payload = json.loads(listed.stdout)
            self.assertEqual(list_payload["data"]["plans"][0]["planId"], plan_id)

            rejected = self._run(
                [
                    "--json",
                    "approvals",
                    "execute",
                    "--plan-id",
                    plan_id,
                    "--confirm-text",
                    "确定",
                ],
                extra_env=env,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('confirmation must be exactly "确认"', rejected.stderr)

            missing_credentials = self._run(
                [
                    "--json",
                    "approvals",
                    "execute",
                    "--plan-id",
                    plan_id,
                    "--confirm-text",
                    "确认",
                ],
                extra_env=env,
            )
            self.assertEqual(missing_credentials.returncode, 0, missing_credentials.stderr)
            missing_payload = json.loads(missing_credentials.stdout)
            self.assertEqual(missing_payload["meta"]["mode"], "mock")
            self.assertIn("missingCredentials", missing_payload["meta"])
            self.assertEqual(
                missing_payload["data"]["requested"]["planId"],
                plan_id,
            )

    def test_reports_parse_search_terms_local_file(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as fh:
            json.dump(
                [
                    {
                        "date": "2026-07-01",
                        "searchTerm": "ai recorder",
                        "keyword": "ai recorder",
                        "clicks": 2,
                    }
                ],
                fh,
            )
            path = fh.name
        try:
            result = self._run(
                ["--json", "reports", "parse-search-terms", "--input-file", path]
            )
            self.assertEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["meta"]["mode"], "local")
            self.assertEqual(payload["data"]["summary"]["rows"], 1)
        finally:
            os.unlink(path)

    def test_reports_parse_sp_keywords_local_file(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as fh:
            json.dump(
                [
                    {
                        "date": "2026-07-01",
                        "keywordId": 9,
                        "keywordText": "carplay",
                        "topOfSearchImpressionShare": 0.12,
                    }
                ],
                fh,
            )
            path = fh.name
        try:
            result = self._run(
                ["--json", "reports", "parse-sp-keywords", "--input-file", path]
            )
            self.assertEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["meta"]["mode"], "local")
            self.assertEqual(payload["data"]["summary"]["rows"], 1)
        finally:
            os.unlink(path)

    def test_reports_parse_sp_campaign_placement_local_file(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as fh:
            json.dump(
                [
                    {
                        "date": "2026-07-01",
                        "campaignId": 1,
                        "campaignName": "T11 Car Play-词组匹配",
                        "placementClassification": "TOP_OF_SEARCH",
                        "impressions": 12,
                    }
                ],
                fh,
            )
            path = fh.name
        try:
            result = self._run(
                ["--json", "reports", "parse-sp-campaign-placement", "--input-file", path]
            )
            self.assertEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["meta"]["mode"], "local")
            self.assertEqual(payload["data"]["summary"]["rows"], 1)
        finally:
            os.unlink(path)

    def test_reports_parse_sb_report_local_file(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as fh:
            json.dump(
                [
                    {
                        "date": "2026-07-01",
                        "campaignId": 1,
                        "campaignName": "SB Brand Core",
                        "impressions": "10",
                        "cost": "2.50",
                    }
                ],
                fh,
            )
            path = fh.name
        try:
            result = self._run(
                ["--json", "reports", "parse-sb-report", "--input-file", path]
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["meta"]["mode"], "local")
            self.assertEqual(payload["data"]["summary"]["rows"], 1)
            self.assertEqual(payload["data"]["rows"][0]["campaignId"], "1")
        finally:
            os.unlink(path)

    def test_reports_parse_sd_report_local_file(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as fh:
            json.dump(
                [
                    {
                        "date": "2026-07-01",
                        "campaignId": 1,
                        "campaignName": "SD Retargeting",
                        "impressions": "10",
                        "cost": "2.50",
                    }
                ],
                fh,
            )
            path = fh.name
        try:
            result = self._run(
                ["--json", "reports", "parse-sd-report", "--input-file", path]
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["meta"]["mode"], "local")
            self.assertEqual(payload["data"]["summary"]["rows"], 1)
            self.assertEqual(payload["data"]["rows"][0]["campaignId"], "1")
            self.assertEqual(payload["data"]["rows"][0]["cost"], 2.5)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

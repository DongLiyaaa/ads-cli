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

    def test_help(self):
        result = self._run(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage", result.stdout)

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
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

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
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

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
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

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
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

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
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

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
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

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
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["meta"]["mode"], "mock")
        self.assertIn("missingCredentials", payload["meta"])

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


if __name__ == "__main__":
    unittest.main()

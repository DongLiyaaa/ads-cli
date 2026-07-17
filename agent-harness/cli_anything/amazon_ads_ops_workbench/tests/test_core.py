import json
import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(__file__)
HARNESS_ROOT = os.path.abspath(os.path.join(TESTS_DIR, "..", "..", ".."))
if HARNESS_ROOT not in sys.path:
    sys.path.insert(0, HARNESS_ROOT)

from cli_anything.amazon_ads_ops_workbench.core.env import AdsEnvironment, normalize_region
from cli_anything.amazon_ads_ops_workbench.core.client import AmazonAdsClient
from cli_anything.amazon_ads_ops_workbench.core.campaigns import (
    build_campaign_budget_payload,
    build_campaign_state_payload,
)
from cli_anything.amazon_ads_ops_workbench.core.keywords import (
    build_ad_groups_filter,
    build_ad_group_negative_payload,
    build_campaign_negative_payload,
    build_keyword_edit_payload,
    build_keyword_state_payload,
    build_keywords_filter,
    build_negative_list_filter,
    build_negative_state_payload,
    normalize_ad_group_row,
    normalize_keyword_row,
    normalize_negative_row,
    normalize_portfolio_row,
)
from cli_anything.amazon_ads_ops_workbench.core.reports import (
    build_download_target_path,
    build_sp_campaign_placement_report_body,
    build_sp_keywords_report_body,
    build_sp_search_term_report_body,
    load_report_rows,
    normalize_search_term_report_row,
    normalize_sp_campaign_placement_report_row,
    normalize_sp_keyword_report_row,
    summarize_report_rows,
)
from cli_anything.amazon_ads_ops_workbench.core.snapshot import (
    build_missing_credential_snapshot,
    extract_campaign_records,
    find_missing_credentials,
    pick_profile_id,
)


class EnvTests(unittest.TestCase):
    def test_normalize_region_falls_back_to_na(self):
        self.assertEqual(normalize_region("bad"), "NA")

    def test_find_missing_credentials_reports_expected_keys(self):
        env = AdsEnvironment(
            client_id="",
            client_secret="secret",
            refresh_token="",
            profile_id="",
            region="NA",
            marketplace="US",
        )
        self.assertEqual(find_missing_credentials(env), ["CLIENT_ID", "REFRESH_TOKEN"])

    def test_client_build_headers_adds_vendor_accept_for_v3_paths(self):
        env = AdsEnvironment(
            client_id="client",
            client_secret="secret",
            refresh_token="refresh",
            profile_id="123",
            region="NA",
            marketplace="US",
        )
        client = AmazonAdsClient(env)
        headers = client._build_headers("token", accept_path="/sp/campaigns/list")
        self.assertEqual(headers["Accept"], "application/vnd.spcampaign.v3+json")
        self.assertEqual(headers["Authorization"], "Bearer token")

    def test_client_content_media_type_uses_vendor_json(self):
        env = AdsEnvironment(
            client_id="client",
            client_secret="secret",
            refresh_token="refresh",
            profile_id="123",
            region="NA",
            marketplace="US",
        )
        client = AmazonAdsClient(env)
        self.assertEqual(
            client._content_media_type("/sp/campaigns/list"),
            "application/vnd.spcampaign.v3+json",
        )
        self.assertEqual(client._content_media_type("/reporting/reports"), "application/json")


class ProfileResolutionTests(unittest.TestCase):
    def test_pick_profile_id_prefers_direct_marketplace_match(self):
        profiles = [
            {"profileId": 1, "countryCode": "CA"},
            {"profileId": 2, "countryCode": "US"},
        ]
        self.assertEqual(pick_profile_id(profiles, "US"), "2")

    def test_pick_profile_id_falls_back_to_first_profile(self):
        profiles = [{"profileId": 9, "countryCode": "CA"}]
        self.assertEqual(pick_profile_id(profiles, "US"), "9")


class CampaignExtractionTests(unittest.TestCase):
    def test_extract_campaign_records_reads_campaigns_key(self):
        payload = {"campaigns": [{"campaignId": "1", "name": "A"}]}
        self.assertEqual(len(extract_campaign_records(payload)), 1)

    def test_extract_campaign_records_reads_results_key(self):
        payload = {"results": [{"campaignId": "1", "name": "A"}]}
        self.assertEqual(len(extract_campaign_records(payload)), 1)

    def test_extract_campaign_records_reads_items_key(self):
        payload = {"items": [{"campaignId": "1", "name": "A"}]}
        self.assertEqual(len(extract_campaign_records(payload)), 1)


class SnapshotFallbackTests(unittest.TestCase):
    def test_missing_credential_snapshot_has_expected_shape(self):
        env = AdsEnvironment(
            client_id="",
            client_secret="",
            refresh_token="",
            profile_id="",
            region="NA",
            marketplace="US",
        )
        snapshot = build_missing_credential_snapshot(
            env=env,
            marketplace="US",
            missing_credentials=["CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"],
        )
        self.assertEqual(snapshot["meta"]["mode"], "mock")
        self.assertEqual(snapshot["meta"]["status"], "attention")
        self.assertEqual(
            snapshot["meta"]["missingCredentials"],
            ["CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"],
        )


class KeywordNormalizationTests(unittest.TestCase):
    def test_build_keywords_filter_includes_optional_filters(self):
        payload = build_keywords_filter(
            campaign_id="123",
            ad_group_id="456",
            state_filter="ENABLED",
        )
        self.assertEqual(payload["campaignIdFilter"], {"include": ["123"]})
        self.assertEqual(payload["adGroupIdFilter"], {"include": ["456"]})
        self.assertEqual(payload["stateFilter"], {"include": ["ENABLED"]})

    def test_build_negative_list_filter_includes_optional_filters(self):
        payload = build_negative_list_filter(
            campaign_id="123",
            ad_group_id="456",
            state_filter="PAUSED",
        )
        self.assertEqual(payload["campaignIdFilter"], {"include": ["123"]})
        self.assertEqual(payload["adGroupIdFilter"], {"include": ["456"]})
        self.assertEqual(payload["stateFilter"], {"include": ["PAUSED"]})

    def test_build_ad_groups_filter_includes_optional_filters(self):
        payload = build_ad_groups_filter(
            campaign_id="123",
            ad_group_id="456",
            state_filter="PAUSED",
        )
        self.assertEqual(payload["campaignIdFilter"], {"include": ["123"]})
        self.assertEqual(payload["adGroupIdFilter"], {"include": ["456"]})
        self.assertEqual(payload["stateFilter"], {"include": ["PAUSED"]})

    def test_normalize_keyword_row_keeps_bid_and_match_type(self):
        row = normalize_keyword_row(
            {
                "keywordId": 99,
                "keywordText": "wireless carplay adapter",
                "matchType": "PHRASE",
                "bid": 0.82,
                "campaignId": 1,
                "adGroupId": 2,
                "state": "ENABLED",
            }
        )
        self.assertEqual(row["keywordId"], "99")
        self.assertEqual(row["keywordText"], "wireless carplay adapter")
        self.assertEqual(row["matchType"], "PHRASE")
        self.assertEqual(row["bid"], 0.82)

    def test_normalize_negative_row_marks_scope(self):
        row = normalize_negative_row(
            {
                "keywordId": 77,
                "keywordText": "usb c camera",
                "matchType": "NEGATIVE_EXACT",
                "campaignId": 1,
                "adGroupId": 2,
                "state": "ENABLED",
            },
            scope="adGroup",
        )
        self.assertEqual(row["scope"], "adGroup")
        self.assertEqual(row["keywordText"], "usb c camera")

    def test_normalize_ad_group_row_keeps_default_bid(self):
        row = normalize_ad_group_row(
            {
                "adGroupId": 12,
                "campaignId": 34,
                "name": "Exact Core",
                "defaultBid": 0.77,
                "state": "ENABLED",
            }
        )
        self.assertEqual(row["adGroupId"], "12")
        self.assertEqual(row["campaignId"], "34")
        self.assertEqual(row["name"], "Exact Core")
        self.assertEqual(row["defaultBid"], 0.77)

    def test_normalize_portfolio_row_keeps_budget(self):
        row = normalize_portfolio_row(
            {
                "portfolioId": 88,
                "name": "T11",
                "state": "ENABLED",
                "budget": 120.5,
                "inBudget": True,
            }
        )
        self.assertEqual(row["portfolioId"], "88")
        self.assertEqual(row["name"], "T11")
        self.assertEqual(row["budget"], 120.5)
        self.assertTrue(row["inBudget"])

    def test_build_ad_group_negative_payload_uses_expected_fields(self):
        payload = build_ad_group_negative_payload(
            campaign_id="1",
            ad_group_id="2",
            keyword_text="carplay wireless adapter",
            match_type="NEGATIVE_EXACT",
        )
        self.assertEqual(payload["campaignId"], "1")
        self.assertEqual(payload["adGroupId"], "2")
        self.assertEqual(payload["keywordText"], "carplay wireless adapter")
        self.assertEqual(payload["matchType"], "NEGATIVE_EXACT")

    def test_build_campaign_negative_payload_uses_expected_fields(self):
        payload = build_campaign_negative_payload(
            campaign_id="1",
            keyword_text="usb c camera",
            match_type="NEGATIVE_EXACT",
        )
        self.assertEqual(payload["campaignId"], "1")
        self.assertEqual(payload["keywordText"], "usb c camera")
        self.assertEqual(payload["matchType"], "NEGATIVE_EXACT")

    def test_build_keyword_edit_payload_uses_expected_fields(self):
        payload = build_keyword_edit_payload(
            campaign_id="1",
            ad_group_id="2",
            keyword_id="3",
            bid=0.91,
            state="ENABLED",
        )
        self.assertEqual(payload["campaignId"], "1")
        self.assertEqual(payload["adGroupId"], "2")
        self.assertEqual(payload["keywordId"], "3")
        self.assertEqual(payload["bid"], 0.91)
        self.assertEqual(payload["state"], "ENABLED")

    def test_build_keyword_state_payload_uses_expected_fields(self):
        payload = build_keyword_state_payload(
            campaign_id="1",
            ad_group_id="2",
            keyword_id="3",
            state="paused",
        )
        self.assertEqual(payload["campaignId"], "1")
        self.assertEqual(payload["adGroupId"], "2")
        self.assertEqual(payload["keywordId"], "3")
        self.assertEqual(payload["state"], "PAUSED")
        self.assertNotIn("bid", payload)

    def test_build_negative_state_payload_uses_expected_fields(self):
        payload = build_negative_state_payload(
            keyword_id="3",
            state="paused",
        )
        self.assertEqual(payload["keywordId"], "3")
        self.assertEqual(payload["state"], "PAUSED")

    def test_edit_keyword_wraps_keywords_array(self):
        env = AdsEnvironment(
            client_id="client",
            client_secret="secret",
            refresh_token="refresh",
            profile_id="123",
            region="NA",
            marketplace="US",
        )
        client = AmazonAdsClient(env)
        payload = {"campaignId": "1", "adGroupId": "2", "keywordId": "3", "bid": 0.91}
        self.assertEqual(
            client._wrap_keyword_edit_payload(payload),
            {"keywords": [payload]},
        )

    def test_create_negative_keyword_wraps_negative_keywords_array(self):
        env = AdsEnvironment(
            client_id="client",
            client_secret="secret",
            refresh_token="refresh",
            profile_id="123",
            region="NA",
            marketplace="US",
        )
        client = AmazonAdsClient(env)
        payload = {
            "campaignId": "1",
            "adGroupId": "2",
            "keywordText": "x",
            "matchType": "NEGATIVE_EXACT",
        }
        self.assertEqual(
            client._wrap_negative_keyword_payload(payload),
            {"negativeKeywords": [payload]},
        )

    def test_create_campaign_negative_keyword_wraps_array(self):
        env = AdsEnvironment(
            client_id="client",
            client_secret="secret",
            refresh_token="refresh",
            profile_id="123",
            region="NA",
            marketplace="US",
        )
        client = AmazonAdsClient(env)
        payload = {
            "campaignId": "1",
            "keywordText": "x",
            "matchType": "NEGATIVE_EXACT",
        }
        self.assertEqual(
            client._wrap_campaign_negative_keyword_payload(payload),
            {"campaignNegativeKeywords": [payload]},
        )


class CampaignMutationTests(unittest.TestCase):
    def test_build_campaign_state_payload_uses_expected_fields(self):
        payload = build_campaign_state_payload(
            campaign_id="1",
            state="paused",
        )
        self.assertEqual(payload["campaignId"], "1")
        self.assertEqual(payload["state"], "PAUSED")

    def test_build_campaign_budget_payload_uses_expected_fields(self):
        payload = build_campaign_budget_payload(
            campaign_id="1",
            budget=5.0,
        )
        self.assertEqual(payload["campaignId"], "1")
        self.assertEqual(payload["budget"]["budgetType"], "DAILY")
        self.assertEqual(payload["budget"]["budget"], 5.0)

    def test_edit_campaign_wraps_campaigns_array(self):
        env = AdsEnvironment(
            client_id="client",
            client_secret="secret",
            refresh_token="refresh",
            profile_id="123",
            region="NA",
            marketplace="US",
        )
        client = AmazonAdsClient(env)
        payload = {"campaignId": "1", "state": "PAUSED"}
        self.assertEqual(
            client._wrap_campaign_payload(payload),
            {"campaigns": [payload]},
        )


class ReportRequestTests(unittest.TestCase):
    def test_build_sp_keywords_report_body_uses_expected_shape(self):
        payload = build_sp_keywords_report_body(
            start_date="2026-07-01",
            end_date="2026-07-07",
            time_unit="DAILY",
        )
        self.assertEqual(payload["startDate"], "2026-07-01")
        self.assertEqual(payload["endDate"], "2026-07-07")
        self.assertEqual(payload["configuration"]["reportTypeId"], "spKeywords")
        self.assertEqual(payload["configuration"]["groupBy"], ["adGroup"])
        self.assertEqual(payload["configuration"]["timeUnit"], "DAILY")
        self.assertNotIn("campaignId", payload["configuration"]["columns"])

    def test_build_sp_campaign_placement_report_body_uses_expected_shape(self):
        payload = build_sp_campaign_placement_report_body(
            start_date="2026-07-01",
            end_date="2026-07-07",
            time_unit="SUMMARY",
        )
        self.assertEqual(payload["startDate"], "2026-07-01")
        self.assertEqual(payload["endDate"], "2026-07-07")
        self.assertEqual(payload["configuration"]["reportTypeId"], "spCampaigns")
        self.assertEqual(payload["configuration"]["groupBy"], ["campaignPlacement"])
        self.assertEqual(payload["configuration"]["timeUnit"], "SUMMARY")
        self.assertIn("placementClassification", payload["configuration"]["columns"])
        self.assertNotIn("date", payload["configuration"]["columns"])

    def test_build_sp_campaign_placement_daily_report_body_adds_date(self):
        payload = build_sp_campaign_placement_report_body(
            start_date="2026-07-01",
            end_date="2026-07-07",
            time_unit="DAILY",
        )
        self.assertEqual(payload["configuration"]["timeUnit"], "DAILY")
        self.assertEqual(payload["configuration"]["columns"][0], "date")

    def test_build_sp_search_term_report_body_uses_expected_shape(self):
        payload = build_sp_search_term_report_body(
            start_date="2026-07-01",
            end_date="2026-07-07",
            time_unit="SUMMARY",
        )
        self.assertEqual(payload["startDate"], "2026-07-01")
        self.assertEqual(payload["endDate"], "2026-07-07")
        self.assertEqual(payload["configuration"]["reportTypeId"], "spSearchTerm")
        self.assertEqual(payload["configuration"]["groupBy"], ["searchTerm"])
        self.assertEqual(payload["configuration"]["timeUnit"], "SUMMARY")
        self.assertIn("keyword", payload["configuration"]["columns"])
        self.assertNotIn("keywordText", payload["configuration"]["columns"])

    def test_build_download_target_path_uses_report_id_and_extension(self):
        target = build_download_target_path(
            output_dir="/tmp/amz",
            report_id="abc-123",
            report_type="spSearchTerm",
        )
        self.assertTrue(target.endswith("/spSearchTerm-abc-123.json"))

    def test_load_report_rows_reads_json_array(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as fh:
            json.dump([{"date": "2026-07-01", "searchTerm": "carplay"}], fh)
            path = fh.name
        try:
            rows = load_report_rows(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["searchTerm"], "carplay")
        finally:
            os.unlink(path)

    def test_normalize_search_term_report_row_uses_keyword_fallback(self):
        row = normalize_search_term_report_row(
            {
                "date": "2026-07-01",
                "searchTerm": "ai recorder",
                "keywordText": "ai recorder",
                "clicks": 2,
            }
        )
        self.assertEqual(row["keyword"], "ai recorder")
        self.assertEqual(row["clicks"], 2)

    def test_normalize_sp_keyword_report_row_keeps_share(self):
        row = normalize_sp_keyword_report_row(
            {
                "date": "2026-07-01",
                "keywordId": 9,
                "keywordText": "carplay",
                "topOfSearchImpressionShare": 0.12,
            }
        )
        self.assertEqual(row["keywordId"], "9")
        self.assertEqual(row["topOfSearchImpressionShare"], 0.12)

    def test_normalize_sp_campaign_placement_report_row_keeps_placement(self):
        row = normalize_sp_campaign_placement_report_row(
            {
                "date": "2026-07-01",
                "campaignId": 1,
                "campaignName": "T11 Car Play-词组匹配",
                "campaignStatus": "ENABLED",
                "placementClassification": "TOP_OF_SEARCH",
                "campaignBudgetAmount": 15,
                "campaignBudgetType": "DAILY",
                "campaignBudgetCurrencyCode": "USD",
                "impressions": 123,
                "clicks": 7,
                "cost": 5.6,
                "purchases30d": 1,
                "sales30d": 89.99,
                "topOfSearchImpressionShare": 0.17,
            }
        )
        self.assertEqual(row["campaignId"], "1")
        self.assertEqual(row["placementClassification"], "TOP_OF_SEARCH")
        self.assertEqual(row["campaignBudgetAmount"], 15.0)
        self.assertEqual(row["sales30d"], 89.99)

    def test_summarize_report_rows_tracks_date_range(self):
        summary = summarize_report_rows(
            [
                {"date": "2026-07-02", "a": 1},
                {"date": "2026-07-01", "b": 2},
            ]
        )
        self.assertEqual(summary["rows"], 2)
        self.assertEqual(summary["dateStart"], "2026-07-01")
        self.assertEqual(summary["dateEnd"], "2026-07-02")


if __name__ == "__main__":
    unittest.main()

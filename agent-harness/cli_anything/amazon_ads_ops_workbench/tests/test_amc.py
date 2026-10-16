import unittest

from cli_anything.amazon_ads_ops_workbench.core import amc


class NormalizeSqlTests(unittest.TestCase):
    def test_comments_do_not_swallow_the_query(self):
        sql = "SELECT a, -- note\n  SUM(b) AS b /* x */ FROM t\nGROUP BY a;"
        self.assertEqual(amc.normalize_sql(sql), "SELECT a, SUM(b) AS b FROM t GROUP BY a")

    def test_quoted_text_is_preserved(self):
        sql = "SELECT 'a -- not a comment' AS x, 'it''s' AS y, SUM(z) AS z FROM t GROUP BY 1"
        self.assertIn("'a -- not a comment'", amc.normalize_sql(sql))
        self.assertIn("'it''s'", amc.normalize_sql(sql))

    def test_rejects_unsafe_or_empty_input(self):
        for sql in ("", "  -- only a comment", "SELECT 1; DROP TABLE x", "SELECT 'open", "SELECT /* open"):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                amc.normalize_sql(sql)

    def test_semicolon_inside_quotes_is_allowed(self):
        self.assertEqual(
            amc.normalize_sql("SELECT ';' AS s, SUM(x) AS x FROM t GROUP BY s"),
            "SELECT ';' AS s, SUM(x) AS x FROM t GROUP BY s",
        )

    def test_every_template_normalizes_to_one_line(self):
        for key, template in amc.TEMPLATES.items():
            with self.subTest(template=key):
                sql = amc.normalize_sql(template["sql"])
                self.assertNotIn("\n", sql)
                self.assertNotIn("LIMIT", sql.upper().split())
                self.assertTrue(sql.upper().startswith(("SELECT", "WITH")))


class QueryShapeTests(unittest.TestCase):
    def test_resolve_query_requires_exactly_one_source(self):
        with self.assertRaises(ValueError):
            amc.resolve_query(None, None)
        with self.assertRaises(ValueError):
            amc.resolve_query("hour-of-day", "SELECT 1")
        with self.assertRaises(ValueError):
            amc.resolve_query("no-such-template", None)
        sql, template = amc.resolve_query("hour-of-day", None)
        self.assertEqual(template, "hour-of-day")
        self.assertIn("sponsored_ads_traffic", sql)

    def test_execution_window_includes_end_date(self):
        body = amc.build_execution_body("SELECT 1", "2026-09-01", "2026-09-30", "America/Los_Angeles")
        self.assertEqual(body["timeWindowType"], "EXPLICIT")
        self.assertEqual(body["timeWindowStart"], "2026-09-01T00:00:00")
        self.assertEqual(body["timeWindowEnd"], "2026-10-01T00:00:00")
        self.assertEqual(body["timeWindowTimeZone"], "America/Los_Angeles")
        self.assertEqual(body["workflow"], {"sqlQuery": "SELECT 1"})

    def test_window_limits(self):
        amc.check_window("2025-10-01", "2026-09-30")
        for start, end in (("2026-10-02", "2026-10-01"), ("2025-01-01", "2026-09-30"), ("bad", "2026-01-01")):
            with self.subTest(start=start), self.assertRaises(ValueError):
                amc.check_window(start, end)


class ContextTests(unittest.TestCase):
    ACCOUNTS = [
        {
            "alternateIds": [
                {"countryCode": "MX", "entityId": "ENTITYMX", "profileId": 1},
                {"countryCode": "US", "entityId": "ENTITYUS", "profileId": 2},
                {"countryCode": "CA", "entityId": "ENTITYCA"},
            ]
        }
    ]

    def test_entity_prefers_profile_then_country(self):
        self.assertEqual(amc.pick_entity(self.ACCOUNTS, "CA", "2"), "ENTITYUS")
        self.assertEqual(amc.pick_entity(self.ACCOUNTS, "CA", "999"), "ENTITYCA")
        with self.assertRaises(RuntimeError):
            amc.pick_entity(self.ACCOUNTS, "DE", "999")

    def test_instance_selection(self):
        instances = [
            {"instanceId": "amcbusy", "creationStatus": "IN_PROGRESS"},
            {"instanceId": "amcready", "creationStatus": "COMPLETED"},
        ]
        self.assertEqual(amc.pick_instance(instances)["instanceId"], "amcready")
        self.assertEqual(amc.pick_instance(instances, "amcbusy")["instanceId"], "amcbusy")
        with self.assertRaises(RuntimeError):
            amc.pick_instance(instances[:1])
        with self.assertRaises(RuntimeError):
            amc.pick_instance(instances, "amcmissing")


class CsvTests(unittest.TestCase):
    def test_types_and_id_precision(self):
        rows = amc.parse_csv_rows(
            "﻿campaign_id,campaign,impressions,product_sales,share,big\n"
            "123456789012345678,Brand A,42,11336.9800,0.5,123456789012345678901\n"
            ",,,,,\n"
        )
        self.assertEqual(
            rows[0],
            {
                "campaign_id": "123456789012345678",
                "campaign": "Brand A",
                "impressions": 42,
                "product_sales": 11336.98,
                "share": 0.5,
                "big": "123456789012345678901",
            },
        )
        self.assertEqual(set(rows[1].values()), {None})

    def test_leading_zero_labels_stay_strings(self):
        rows = amc.parse_csv_rows("frequency_bucket,postal,zero,ratio\n01,02134,0,0.25\n")
        self.assertEqual(rows[0], {"frequency_bucket": "01", "postal": "02134", "zero": 0, "ratio": 0.25})

    def test_header_only_result_is_empty(self):
        self.assertEqual(amc.parse_csv_rows("a,b\n"), [])


if __name__ == "__main__":
    unittest.main()

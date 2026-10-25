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



class FinalizeRowsTests(unittest.TestCase):
    COLUMNS = [
        {"name": "frequency_bucket", "dataType": "STRING", "columnType": "DIMENSION"},
        # COUNT(DISTINCT ...) comes back as a numeric DIMENSION.
        {"name": "reached_users", "dataType": "LONG", "columnType": "DIMENSION"},
        {"name": "product_sales", "dataType": {"type": "DECIMAL", "precision": 38}, "columnType": "METRIC"},
    ]

    def rows(self):
        return [
            {"frequency_bucket": "21+", "reached_users": 5, "product_sales": 1.5},
            {"frequency_bucket": None, "reached_users": 3, "product_sales": 0.25},
            {"frequency_bucket": "02-03", "reached_users": 9, "product_sales": 2.0},
            {"frequency_bucket": "11-20", "reached_users": 4, "product_sales": None},
            {"frequency_bucket": None, "reached_users": 2, "product_sales": 1.0},
            {"frequency_bucket": "01", "reached_users": 7, "product_sales": 3.0},
        ]

    def test_template_rows_sort_naturally_and_merge_hidden_rows(self):
        rows, privacy = amc.finalize_rows(self.rows(), self.COLUMNS, "frequency-vs-conversion")
        self.assertEqual(
            [r["frequency_bucket"] for r in rows],
            ["01", "02-03", "11-20", "21+", "隐私过滤合并（2 行）"],
        )
        self.assertEqual(rows[-1], {"frequency_bucket": "隐私过滤合并（2 行）", "reached_users": 5, "product_sales": 1.25})
        campaigns = [
            {"campaign": "B", "campaign_id": "2", "clicks": 1},
            {"campaign": None, "campaign_id": None, "clicks": 4},
            {"campaign": "A10", "campaign_id": "1", "clicks": 2},
            {"campaign": "A9", "campaign_id": "3", "clicks": 3},
        ]
        rows, _ = amc.finalize_rows(campaigns, None, "full-conversions-asin")
        self.assertEqual([r["campaign"] for r in rows], ["A9", "A10", "B", "隐私过滤合并（1 行）"])
        self.assertIsNone(rows[-1]["campaign_id"])
        self.assertEqual((privacy["rows"], privacy["filtered_rows"], privacy["merged"]), (6, 2, True))
        self.assertEqual(privacy["shares"], {"reached_users": 16.67, "product_sales": 16.13})

    def test_custom_sql_keeps_hidden_rows(self):
        rows, privacy = amc.finalize_rows(self.rows(), self.COLUMNS)
        self.assertEqual([r["frequency_bucket"] for r in rows][-2:], [None, None])
        self.assertEqual(len(rows), 6)
        self.assertFalse(privacy["merged"])

    def test_template_order_and_numeric_sort_columns(self):
        labels = ["7d+", "1-3d", "0-1h", "6-24h", "1-6h", "3-7d"]
        rows, _ = amc.finalize_rows(
            [{"ad_product_type": "sp", "time_to_purchase": x, "purchases": 1} for x in labels],
            None,
            "time-to-conversion",
        )
        self.assertEqual([r["time_to_purchase"] for r in rows], ["0-1h", "1-6h", "6-24h", "1-3d", "3-7d", "7d+"])
        hours = [{"hour_of_day": h, "ad_product_type": "sp", "clicks": 1} for h in (10, 2, 0)]
        rows, privacy = amc.finalize_rows(hours, None, "hour-of-day")
        self.assertEqual([r["hour_of_day"] for r in rows], [0, 2, 10])
        self.assertNotIn("hour_of_day", privacy["shares"])

    def test_empty_result(self):
        self.assertEqual(amc.finalize_rows([], None, "hour-of-day")[0], [])

    def test_full_templates_are_marked(self):
        full = [t["id"] for t in amc.public_templates() if t["category"] == "full"]
        self.assertEqual(len(full), 4)
        self.assertTrue(all("sort" not in t for t in amc.public_templates()))


if __name__ == "__main__":
    unittest.main()

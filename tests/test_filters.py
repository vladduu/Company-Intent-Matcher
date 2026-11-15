import unittest

from filters import check_filters
from filtered_search import search_with_filters
from query_parser import parse_query


class FilterTests(unittest.TestCase):
    def test_strict_threshold_and_missing(self):
        conditions = [{"field": "employee_count", "operator": ">", "value": 1000}]
        for value, expected in [(999, "fail"), (1000, "fail"), (1001, "pass"),
                                (None, "unknown"), (True, "unknown"), (float("nan"), "unknown")]:
            with self.subTest(value=value):
                self.assertEqual(check_filters({"employee_count": value}, conditions)["status"], expected)

    def test_failure_dominates_unknown(self):
        conditions = parse_query("Public software companies with more than 1,000 employees")["filters"]
        self.assertEqual(check_filters({"is_public": False}, conditions)["status"], "fail")
        self.assertEqual(check_filters({"is_public": True}, conditions)["status"], "unknown")

    def test_country(self):
        conditions = parse_query("Logistic companies in Romania")["filters"]
        self.assertEqual(check_filters({"address": {"country_code": "RO"}}, conditions)["status"], "pass")
        self.assertEqual(check_filters({"address": {"country_code": "de"}}, conditions)["status"], "fail")
        self.assertEqual(check_filters({}, conditions)["status"], "unknown")

    def test_parser(self):
        parsed = parse_query("Public software companies in Romania with more than 1,000 employees.")
        self.assertEqual(parsed["activity"], "software")
        self.assertEqual(len(parsed["filters"]), 3)
        self.assertIn({"field": "employee_count", "operator": ">", "value": 1000}, parsed["filters"])

    def test_comparison_variants(self):
        for phrase, op in [("fewer than", "<"), ("at least", ">="), ("at most", "<="), ("exactly", "==")]:
            condition = parse_query(f"Software companies with {phrase} 200 employees")["filters"][0]
            self.assertEqual(condition["operator"], op)

    def test_public_sector_is_not_public_listing(self):
        for query in ["Public sector software companies", "Software companies serving public organizations"]:
            self.assertEqual(parse_query(query)["filters"], [])

    def test_unsupported_boolean_expressions(self):
        for query in ["Not public companies", "Companies in Romania or Germany", "Companies with between 100 and 200 employees"]:
            parsed = parse_query(query)
            self.assertEqual(parsed["filters"], [])
            self.assertTrue(parsed["warnings"])

    def test_malformed_number_is_not_partially_parsed(self):
        self.assertEqual(parse_query("Software companies with more than 1,00 employees")["filters"], [])

    def test_customer_conditions_are_not_company_filters(self):
        parsed = parse_query("Software companies serving clients in Romania with more than 1000 employees")
        self.assertEqual(parsed["filters"], [])
        self.assertTrue(parsed["warnings"])

    def test_pipeline_keeps_unknown_separate(self):
        companies = [
            {"operational_name": "Fail", "is_public": False, "description": "software"},
            {"operational_name": "Pass", "is_public": True, "employee_count": 2000, "description": "software"},
            {"operational_name": "Unknown", "is_public": True, "description": "software"},
        ]
        result = search_with_filters(companies, "Public software companies with more than 1000 employees", top=1)
        self.assertEqual(result["results"][0]["company"]["operational_name"], "Pass")
        self.assertEqual(result["uncertain_results"][0]["company"]["operational_name"], "Unknown")
        self.assertEqual(result["counts"], {"pass": 1, "unknown": 1, "fail": 1})

    def test_filter_only_query(self):
        result = search_with_filters([{"is_public": True}], "Public companies")
        self.assertEqual(len(result["results"]), 1)


if __name__ == "__main__":
    unittest.main()

import unittest

from filters import check_filters
from query_parser import parse_query, REGIONS


class ExtendedFilterTests(unittest.TestCase):
    def test_revenue_amounts_and_boundaries(self):
        for amount, value in [("$50 million", 50000000), ("USD 1.5 billion", 1500000000),
                              ("$50m", 50000000), ("500 thousand dollars", 500000),
                              ("50,000,000 USD", 50000000), ("$12.50", 12.5)]:
            with self.subTest(amount=amount):
                parsed = parse_query(f"Construction companies in the United States with revenue over {amount}")
                self.assertEqual(parsed["activity"], "construction")
                condition = next(c for c in parsed["filters"] if c["field"] == "revenue")
                self.assertEqual(condition["value"], value)
                self.assertEqual(check_filters({"revenue": value}, [condition])["status"], "fail")
                self.assertEqual(check_filters({"revenue": value+1}, [condition])["status"], "pass")

    def test_currency_and_malformed_amounts_are_not_guessed(self):
        for amount in ["EUR 50 million", "$50 million euros", "50 million GBP", "1,00", "-50 million", "50 million-ish", "1e6"]:
            parsed = parse_query(f"Companies with revenue over {amount}")
            self.assertFalse(any(c["field"] == "revenue" for c in parsed["filters"]), amount)
            self.assertIn("revenue", parsed["activity"])

    def test_combined_year_and_employees(self):
        parsed = parse_query("Clean energy startups founded after 2018 with fewer than 200 employees")
        self.assertEqual(parsed["activity"], "clean energy startups")
        self.assertEqual(len(parsed["filters"]), 2)
        for year, employees, expected in [(2018, 199, "fail"), (2019, 200, "fail"),
                                          (2019, 199, "pass"), (None, 199, "unknown")]:
            self.assertEqual(check_filters({"year_founded": year, "employee_count": employees}, parsed["filters"])["status"], expected)

    def test_year_variants(self):
        for phrase, op in [("after", ">"), ("before", "<"), ("since", ">="), ("in", "==")]:
            parsed = parse_query(f"Software companies established {phrase} 2000 in Europe")
            self.assertEqual(parsed["activity"], "software")
            self.assertIn({"field": "year_founded", "operator": op, "value": 2000}, parsed["filters"])

    def test_regions_and_missing_country(self):
        conditions = parse_query("Renewable energy equipment manufacturers in Scandinavia")["filters"]
        for country, expected in [("NO", "pass"), ("se", "pass"), ("dk", "pass"), ("fi", "fail"), (None, "unknown"), ("", "unknown")]:
            self.assertEqual(check_filters({"address": {"country_code": country}}, conditions)["status"], expected)
        self.assertIn("gb", REGIONS["europe"])
        self.assertIn("ch", REGIONS["europe"])
        self.assertNotIn("us", REGIONS["europe"])

    def test_mixed_conditions_and_conjunctions(self):
        parsed = parse_query("Food and beverage companies in Europe founded before 2010 with revenue at least $2 million and fewer than 200 employees")
        self.assertEqual(parsed["activity"], "food and beverage")
        self.assertEqual(len(parsed["filters"]), 4)
        company = {"address": {"country_code": "fr"}, "year_founded": 2009,
                   "revenue": 2000000, "employee_count": 199}
        self.assertEqual(check_filters(company, parsed["filters"])["status"], "pass")
        company["revenue"] = None
        self.assertEqual(check_filters(company, parsed["filters"])["status"], "unknown")
        company["employee_count"] = 201
        self.assertEqual(check_filters(company, parsed["filters"])["status"], "fail")

    def test_invalid_data_is_unknown(self):
        for field in ("revenue", "year_founded"):
            for value in (None, True, float("nan"), float("inf"), -1, "2000"):
                self.assertEqual(check_filters({field: value}, [{"field": field, "operator": ">", "value": 1900}])["status"], "unknown")
        for year in (0, 2000.5, 10000):
            self.assertEqual(check_filters({"year_founded": year}, [{"field": "year_founded", "operator": ">", "value": 1900}])["status"], "unknown")

    def test_invalid_filter_definitions_rejected(self):
        for condition in [{"field": "revenue", "operator": "in", "value": [5]},
                          {"field": "year_founded", "operator": ">", "value": 2000.5},
                          {"field": "country_code", "operator": "in", "value": "ro"},
                          {"field": "country_code", "operator": "in", "value": []}]:
            with self.assertRaises(ValueError):
                check_filters({}, [condition])

    def test_unsupported_scope_is_preserved(self):
        for query in ["Companies serving clients in Europe with revenue over $50 million",
                      "Companies founded between 2000 and 2010", "Companies in Europe or Asia"]:
            self.assertEqual(parse_query(query)["filters"], [])

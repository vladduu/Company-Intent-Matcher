import unittest

from filtered_search import search_with_filters
from keyword_search import normalize_words, search_companies, tokenize


class WordVariantTests(unittest.TestCase):
    def test_matching_in_both_directions(self):
        for first, second in [
            ("logistic", "logistics"),
            ("battery", "batteries"),
            ("supplier", "suppliers"),
            ("cosmetic", "cosmetics"),
        ]:
            for query, text in [(first, second), (second, first)]:
                with self.subTest(query=query, text=text):
                    result = search_companies(
                        [{"description": text}], query, normalize_variants=True
                    )
                    self.assertEqual(result[0]["score"], 1)

    def test_variants_do_not_double_count(self):
        result = search_companies(
            [{"description": "Logistic LOGISTICS!"}],
            "logistic logistics logistics",
            normalize_variants=True,
        )
        self.assertEqual(result[0]["score"], 1)
        self.assertEqual(result[0]["matched_words"], ["logistics"])

    def test_baseline_is_unchanged(self):
        self.assertEqual(
            search_companies([{"description": "logistics"}], "logistic"), []
        )

    def test_no_blind_suffix_removal_or_substring_matching(self):
        words = tokenize("gas SaaS business analysis glass")
        self.assertEqual(normalize_words(words), words)
        self.assertEqual(
            search_companies(
                [{"description": "intralogistics"}], "logistic", normalize_variants=True
            ),
            [],
        )

    def test_country_filter_still_applies(self):
        companies = [
            {"description": "logistics", "address": {"country_code": "de"}},
            {"description": "logistics", "address": {"country_code": "ro"}},
            {"description": "logistics"},
        ]
        singular = search_with_filters(companies, "Logistic companies in Romania")
        plural = search_with_filters(companies, "Logistics companies in Romania")
        self.assertEqual(singular["results"], plural["results"])
        self.assertEqual(len(singular["results"]), 1)
        self.assertEqual(len(singular["uncertain_results"]), 1)
        self.assertEqual(singular["results"][0]["company"], companies[1])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from qualification import Qualifier, validate
from semantic_search import SemanticSearch, profile_text
from test_semantic_search import FakeEncoder


class QualificationTests(unittest.TestCase):
    def test_evidence_must_exist(self):
        with self.assertRaises(ValueError):
            validate({"verdict": "relevant", "reason": "supplier", "evidence": ["invented"]},
                     {"description": "retailer"})
        with self.assertRaises(ValueError):
            validate({"verdict": "relevant", "reason": "supplier", "evidence": []}, {})

    def test_cache_query_and_profile_invalidation(self):
        calls = []
        def judge(query, company):
            calls.append(query)
            return {"verdict": "relevant", "reason": "offers freight", "evidence": ["freight"]}
        with tempfile.TemporaryDirectory() as directory:
            q = Qualifier("test", directory, judge)
            company = {"description": "freight services"}
            q.judge("logistics", company)
            q.judge("logistics", company)
            self.assertEqual(len(calls), 1)
            q.judge("transport", company)
            q.judge("logistics", dict(company, is_public=True))
            self.assertEqual(len(calls), 3)

    def test_invalid_evidence_never_accepts_and_unknown_filters_stay_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            q = Qualifier("test", directory, lambda *_: {
                "verdict": "relevant", "reason": "guess", "evidence": ["invented"]})
            output = {"results": [{"company": {"description": "retailer"}}],
                      "uncertain_results": [{"company": {"description": "unknown location"}}]}
            result = q.apply(output, "logistics", 10)
            self.assertEqual(result["results"], [])
            self.assertEqual(len(result["uncertain_results"]), 2)

    def test_description_mode_is_separate_and_missing_descriptions_are_skipped(self):
        companies = [{"description": "software", "core_offerings": ["freight"]},
                     {"core_offerings": ["freight"]}]
        self.assertEqual(profile_text(companies[1], "description"), "")
        with tempfile.TemporaryDirectory() as directory:
            full = SemanticSearch(companies, FakeEncoder(), directory)
            description = SemanticSearch(companies, FakeEncoder(), directory, "description")
            self.assertFalse(description.cache_hit)
            self.assertEqual(len(full.search("freight")["results"]), 2)
            self.assertEqual(len(description.search("freight")["results"]), 1)
            self.assertEqual(description.search("freight")["results"][0]["score"], 0)


if __name__ == "__main__":
    unittest.main()

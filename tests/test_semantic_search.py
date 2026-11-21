import tempfile
import unittest
from pathlib import Path

from semantic_search import SemanticSearch


class FakeEncoder:
    identity = {"model": "test-only", "revision": "1"}

    def __init__(self):
        self.calls = []

    def encode(self, texts):
        self.calls.append(texts)
        return [
            (
                [1, 0]
                if any(word in text.lower() for word in ("logistic", "freight"))
                else [0, 1]
            )
            for text in texts
        ]


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.companies = [
            {"description": "freight delivery", "address": {"country_code": "ro"}},
            {"description": "freight forwarding", "address": {"country_code": "de"}},
            {"description": "freight delivery"},
            {"description": "software", "address": {"country_code": "ro"}},
        ]

    def engine(self, companies=None, encoder=None):
        return SemanticSearch(
            self.companies if companies is None else companies,
            encoder=encoder or FakeEncoder(),
            cache_dir=self.temp.name,
        )

    def test_hybrid_preserves_filters_and_unknowns(self):
        output = self.engine().search("Logistic companies in Romania", hybrid=True)
        self.assertEqual(output["counts"], {"pass": 2, "unknown": 1, "fail": 1})
        self.assertEqual(output["results"][0]["company"], self.companies[0])
        self.assertEqual(output["uncertain_results"][0]["company"], self.companies[2])

    def test_cache_reuse_and_invalidation(self):
        self.engine()
        encoder = FakeEncoder()
        engine = self.engine(encoder=encoder)
        self.assertTrue(engine.cache_hit)
        self.assertEqual(encoder.calls, [])
        engine.search("logistics")
        self.assertEqual(len(encoder.calls), 1)
        changed = [dict(self.companies[0], description="changed")]
        self.assertFalse(self.engine(changed).cache_hit)
        revised = FakeEncoder()
        revised.identity = {"model": "test-only", "revision": "2"}
        self.assertFalse(self.engine(encoder=revised).cache_hit)

    def test_corrupt_cache_is_rebuilt(self):
        self.engine()
        for path in Path(self.temp.name).glob("*.json"):
            path.write_text("{bad json", encoding="utf-8")
        self.assertFalse(self.engine().cache_hit)

    def test_empty_dataset_and_missing_text(self):
        self.assertEqual(self.engine([]).search("logistics")["results"], [])
        self.assertEqual(self.engine([{}]).search("logistics")["results"], [])

    def test_filter_only_query_does_not_invent_activity(self):
        output = self.engine([{"is_public": True}]).search(
            "Public companies", hybrid=True
        )
        self.assertEqual(len(output["results"]), 1)

    def test_scores_and_stable_ties(self):
        output = self.engine().search("logistics", top=2)
        self.assertEqual([r["company"] for r in output["results"]], self.companies[:2])
        self.assertEqual(output["results"][0]["score"], 1.0)
        with self.assertRaises(ValueError):
            self.engine().search("logistics", top=0)


if __name__ == "__main__":
    unittest.main()

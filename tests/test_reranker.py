import unittest
from reranker import LocalReranker


class Model:
    def predict(self, pairs, **kwargs):
        return [3 if "offers transport" in text else -2 for query, text in pairs]


class RerankerTests(unittest.TestCase):
    def output(self):
        def item(text):
            return {"company": {"description": text}, "score": 0.5}
        return {"parsed_query": {"activity": "logistics", "warnings": []},
                "results": [item("uses transport"), item("offers transport")],
                "uncertain_results": [item("offers transport, unknown location")],
                "counts": {"pass": 2, "unknown": 1, "fail": 3}}

    def test_reorders_without_promoting_unknowns(self):
        output = LocalReranker(Model()).apply(self.output(), "logistics", 1)
        self.assertEqual(output["results"][0]["company"]["description"], "offers transport")
        self.assertEqual(output["results"][0]["retrieval_score"], 0.5)
        self.assertEqual(output["results"][0]["score_type"], "reranker_logit")
        self.assertEqual(len(output["uncertain_results"]), 1)
        self.assertEqual(output["counts"]["fail"], 3)

    def test_empty_activity_does_not_call_model(self):
        output = self.output()
        output["parsed_query"]["activity"] = ""
        result = LocalReranker(object()).apply(output, "Public companies", 1)
        self.assertEqual(result["results"], output["results"][:1])

    def test_invalid_scores_rejected(self):
        class Broken:
            def predict(self, pairs, **kwargs):
                return [float("nan")] * len(pairs)
        with self.assertRaises(ValueError):
            LocalReranker(Broken()).apply(self.output(), "logistics", 10)

    def test_missing_text_excluded(self):
        output = self.output()
        output["results"] = [{"company": {}, "score": 0}]
        output["uncertain_results"] = []
        self.assertEqual(LocalReranker(object()).apply(output, "logistics", 10)["results"], [])

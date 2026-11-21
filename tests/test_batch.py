import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline import SearchPipeline
from solution import read_queries


class BatchTests(unittest.TestCase):
    def test_invalid_query_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queries.json"
            for payload in [[], {}, [{"id": "a", "text": ""}], [{"id": "a", "text": "x"}, {"id": "a", "text": "y"}]]:
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_queries(path)

    def test_keyword_pipeline_reuses_data_and_reports_timing(self):
        pipeline = SearchPipeline([{"description": "software"}, {"description": "logistics"}], "keyword")
        for query in ["software", "logistics"]:
            result = pipeline.search(query, 1)
            self.assertEqual(result["results"][0]["company"]["description"], query)
            self.assertFalse(result["qualified"])
            self.assertGreaterEqual(result["timings_seconds"]["total"], 0)

    def test_cli_batch_export_and_input_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, queries, output = [root / name for name in ("data.jsonl", "queries.json", "out.json")]
            data.write_text('{"description": "software"}\n', encoding="utf-8")
            queries.write_text('[{"id":"test","text":"software"}]', encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).resolve().parents[1] / "solution.py"), "--queries", str(queries),
                   "--data", str(data), "--method", "keyword", "--output"]
            completed = subprocess.run(cmd + [str(output)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(len(json.loads(output.read_text(encoding="utf-8"))["queries"]), 1)
            before = data.read_bytes()
            self.assertNotEqual(subprocess.run(cmd + [str(data)], capture_output=True).returncode, 0)
            self.assertEqual(data.read_bytes(), before)

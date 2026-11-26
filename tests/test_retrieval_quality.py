import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from scripts import evaluate_published_retrieval as retrieval_cli

from open_ielts_strategy.retrieval_quality import evaluate_retrieval


class FakeEngine:
    def __init__(self):
        self.pack = SimpleNamespace(strategies=[
            {"id": "s1"}, {"id": "s2"}, {"id": "s3"},
        ])
        self.index_identity = {
            "pack_version": "1.2.3", "manifest_sha256": "a" * 64,
            "document_count": 3,
        }
        self.embedding_provider = None

    def search(self, query, *, skill=None, limit=10):
        order = ["s2", "s1", "s3"] if "second" in query else ["s1", "s2", "s3"]
        return [{"strategy_id": item} for item in order[:limit]]


class RetrievalQualityTests(unittest.TestCase):
    def test_reports_macro_recall_precision_mrr_and_ndcg_without_queries(self):
        report = evaluate_retrieval(FakeEngine(), [
            {"id": "case-1", "query": "first query",
             "relevance": {"s1": 3, "s2": 1}},
            {"id": "case-2", "query": "second query",
             "relevance": {"s1": 1, "s2": 3}},
        ], ks=(1, 2))
        self.assertEqual(report["benchmark"], "published-retrieval-relevance")
        self.assertEqual(report["metrics_at_k"]["1"]["recall"], 0.5)
        self.assertEqual(report["metrics_at_k"]["1"]["precision"], 1.0)
        self.assertEqual(report["metrics_at_k"]["1"]["mrr"], 1.0)
        self.assertGreater(report["metrics_at_k"]["2"]["ndcg"], 0.8)
        self.assertFalse(report["query_text_included"])
        self.assertFalse(report["judgments_included"])
        self.assertEqual(len(report["case_suite_sha256"]), 64)

    def test_reports_macro_metrics_and_counts_per_skill_without_query_data(self):
        report = evaluate_retrieval(FakeEngine(), [
            {"id": "writing-1", "query": "first writing query", "skill": "writing",
             "relevance": {"s1": 3}},
            {"id": "writing-2", "query": "second writing query", "skill": "writing",
             "relevance": {"s2": 3}},
            {"id": "general-1", "query": "general query", "skill": "general",
             "relevance": {"s1": 1}},
        ], ks=(1, 2))
        self.assertEqual(report["case_count_by_skill"], {"general": 1, "writing": 2})
        self.assertEqual(report["metrics_by_skill_at_k"]["writing"]["1"]["recall"], 1.0)
        self.assertEqual(report["metrics_by_skill_at_k"]["general"]["1"]["recall"], 1.0)
        self.assertEqual(set(report["metrics_by_skill_at_k"]["writing"]["1"]), {
            "recall", "precision", "mrr", "ndcg",
        })
        serialized = str(report)
        self.assertNotIn("first writing query", serialized)
        self.assertNotIn("second writing query", serialized)
        self.assertNotIn('"relevance"', serialized)

    def test_rejects_unknown_strategy_judgments_and_duplicate_case_ids(self):
        engine = FakeEngine()
        with self.assertRaisesRegex(ValueError, "unknown strategy"):
            evaluate_retrieval(engine, [{"id": "x", "query": "q",
                                         "relevance": {"missing": 2}}])
        case = {"id": "x", "query": "q", "relevance": {"s1": 1}}
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate_retrieval(engine, [case, case])

    def test_rejects_invalid_grades_and_k_values(self):
        with self.assertRaisesRegex(ValueError, "grades"):
            evaluate_retrieval(FakeEngine(), [{"id": "x", "query": "q",
                                                "relevance": {"s1": 4}}])
        with self.assertRaisesRegex(ValueError, "ks"):
            evaluate_retrieval(FakeEngine(), [{"id": "x", "query": "q",
                                                "relevance": {"s1": 1}}], ks=())

    def test_hybrid_mode_is_reported(self):
        engine = FakeEngine()
        engine.embedding_provider = object()
        report = evaluate_retrieval(engine, [{"id": "x", "query": "q",
                                               "relevance": {"s1": 1}}], ks=(1,))
        self.assertEqual(report["retrieval_mode"], "hybrid")


class RetrievalEvaluatorCliSafetyTests(unittest.TestCase):
    def test_reads_valid_utf8_judgments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text('[{"id":"one","query":"original query","relevance":{"s1":3}}]', encoding="utf-8")
            self.assertEqual(retrieval_cli._read_cases_file(path)[0]["id"], "one")

    def test_rejects_judgment_file_over_five_mib(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_bytes(b" " * (retrieval_cli.MAX_CASES_FILE_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "5 MiB"):
                retrieval_cli._read_cases_file(path)

    def test_cli_refuses_to_overwrite_judgment_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            original = b'[]'
            path.write_bytes(original)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = retrieval_cli.main(["--cases-json", str(path), "--output", str(path)])
            self.assertEqual(status, 2)
            self.assertIn("same file", stderr.getvalue())
            self.assertEqual(path.read_bytes(), original)

    def test_cli_refuses_symlink_alias_for_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            alias = Path(directory) / "report.json"
            original = b'[]'
            path.write_bytes(original)
            try:
                alias.symlink_to(path)
            except (NotImplementedError, OSError):
                self.skipTest("symlinks are not available on this platform")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = retrieval_cli.main(["--cases-json", str(path), "--output", str(alias)])
            self.assertEqual(status, 2)
            self.assertIn("same file", stderr.getvalue())
            self.assertEqual(path.read_bytes(), original)

if __name__ == "__main__":
    unittest.main()

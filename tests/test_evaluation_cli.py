import json
import tempfile
import unittest
from pathlib import Path

from scripts.evaluate import load_results


class ExternalResultValidationTests(unittest.TestCase):
    def load_payload(self, payload):
        handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
        try:
            json.dump(payload, handle)
            handle.close()
            return load_results(handle.name)
        finally:
            Path(handle.name).unlink(missing_ok=True)

    def test_accepts_valid_results_and_default_scores(self):
        rows = self.load_payload([
            {"case_id": "passed", "passed": True},
            {"case_id": "failed", "passed": False, "score": 0.25, "notes": "Needs evidence."},
        ])
        self.assertEqual([row.score for row in rows], [1.0, 0.25])
        self.assertEqual([row.passed for row in rows], [True, False])

    def test_rejects_non_object_rows(self):
        with self.assertRaisesRegex(ValueError, "must be an object"):
            self.load_payload(["not-an-object"])

    def test_rejects_empty_or_non_string_case_ids(self):
        for case_id in ("", "   ", 7, None):
            with self.subTest(case_id=case_id):
                with self.assertRaisesRegex(ValueError, "case_id must be a non-empty string"):
                    self.load_payload([{"case_id": case_id, "passed": True}])

    def test_rejects_duplicate_case_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            self.load_payload([
                {"case_id": "same", "passed": True},
                {"case_id": "same", "passed": False},
            ])

    def test_rejects_non_boolean_pass_flags(self):
        for passed in (0, 1, "true", None):
            with self.subTest(passed=passed):
                with self.assertRaisesRegex(ValueError, "passed must be boolean"):
                    self.load_payload([{"case_id": "x", "passed": passed}])

    def test_rejects_non_numeric_scores(self):
        for score in ("0.5", None, True):
            with self.subTest(score=score):
                with self.assertRaisesRegex(ValueError, "score must be a JSON number"):
                    self.load_payload([{"case_id": "x", "passed": True, "score": score}])

    def test_rejects_non_finite_and_out_of_range_scores(self):
        for score in (float("nan"), float("inf"), -0.01, 1.01, 10 ** 1000):
            with self.subTest(score=score):
                with self.assertRaisesRegex(ValueError, "score must be finite and between 0 and 1"):
                    self.load_payload([{"case_id": "x", "passed": True, "score": score}])

    def test_rejects_invalid_notes(self):
        with self.assertRaisesRegex(ValueError, "notes must be a string"):
            self.load_payload([{"case_id": "x", "passed": True, "notes": {"unexpected": True}}])

    def test_rejects_oversized_notes(self):
        with self.assertRaisesRegex(ValueError, "notes exceed"):
            self.load_payload([{"case_id": "x", "passed": True, "notes": "x" * 4097}])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.practice_evaluation import PracticeReviewStore, RUBRIC


def scores(task_relevance):
    return {dimension: (task_relevance if dimension == "task_relevance" else 3)
            for dimension in RUBRIC}


class PracticeReviewCalibrationTests(unittest.TestCase):
    def _report(self, reviewer_ids_and_scores):
        with tempfile.TemporaryDirectory() as tmp:
            with PracticeReviewStore(Path(tmp) / "reviews.sqlite3") as store:
                for item_id, reviewer_id, rating in reviewer_ids_and_scores:
                    if item_id not in getattr(self, "_registered", set()):
                        store.register_output(
                            item_id, pack_version="1.0.0",
                            manifest_sha256="a" * 64, output_sha256=("b" if item_id == "one" else "c") * 64,
                        )
                        self._registered = getattr(self, "_registered", set()) | {item_id}
                    store.submit_review(item_id, reviewer_id, scores(rating))
                return store.calibration_report()

    def test_two_reviewer_perfect_agreement_has_unit_weighted_kappa(self):
        self._registered = set()
        report = self._report([
            ("one", "reviewer-a", 1), ("one", "reviewer-b", 1),
            ("two", "reviewer-a", 2), ("two", "reviewer-b", 2),
        ])
        dimension = report["reviewer_agreement"]["task_relevance"]
        self.assertEqual(dimension["reviewer_pair_count"], 1)
        self.assertEqual(dimension["weighted_kappa_pair_count"], 1)
        self.assertEqual(dimension["weighted_kappa"], 1.0)

    def test_multi_rater_result_is_invariant_to_reviewer_identifier_order(self):
        observations = [
            ("one", "alpha", 1), ("one", "bravo", 2), ("one", "charlie", 5),
            ("two", "alpha", 2), ("two", "bravo", 3), ("two", "charlie", 4),
        ]
        self._registered = set()
        first = self._report(observations)["reviewer_agreement"]["task_relevance"]
        renamed = [(item, {"alpha": "zulu", "bravo": "yankee", "charlie": "xray"}[reviewer], rating)
                   for item, reviewer, rating in observations]
        self._registered = set()
        second = self._report(renamed)["reviewer_agreement"]["task_relevance"]
        self.assertEqual(first["reviewer_pair_count"], 3)
        self.assertEqual(first["weighted_kappa_pair_count"], 3)
        self.assertEqual(first["weighted_kappa"], second["weighted_kappa"])
        self.assertEqual(first["exact_agreement"], second["exact_agreement"])


if __name__ == "__main__":
    unittest.main()

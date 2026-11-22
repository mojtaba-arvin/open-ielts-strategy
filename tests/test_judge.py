import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from open_ielts_strategy.judge import judge, DIMENSIONS
from scripts.judge_calibrate import collect_human_ratings, select_calibration_items


def judge_response(rationale=None):
    payload = {
        "scores": {dimension: 6 for dimension in DIMENSIONS},
        "overall": 6,
        "rationale": rationale if rationale is not None else {
            dimension: f"Evidence for {dimension}" for dimension in DIMENSIONS
        },
    }
    content = json.dumps(payload)
    return json.dumps({"choices": [{"message": {"content": content}}]}).encode()


class JudgeTests(unittest.TestCase):
    @patch("open_ielts_strategy.judge.urllib.request.urlopen")
    def test_structured_scores_and_dimension_rationales(self, urlopen):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return judge_response()

        urlopen.return_value = Response()
        with patch.dict(os.environ, {"JUDGE_API_KEY": "test", "JUDGE_MODEL": "fixture-model"}):
            result = judge("synthetic essay", "Task 2", {})
        self.assertEqual(set(result["scores"]), set(DIMENSIONS))
        self.assertEqual(set(result["rationale"]), set(DIMENSIONS))

    def test_live_judging_requires_explicit_model(self):
        with patch.dict(os.environ, {"JUDGE_API_KEY": "test"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "JUDGE_MODEL"):
                judge("essay", "Task 2", {})

    @patch("open_ielts_strategy.judge.urllib.request.urlopen")
    def test_rejects_incomplete_dimension_rationale(self, urlopen):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return judge_response({})

        urlopen.return_value = Response()
        with patch.dict(os.environ, {"JUDGE_API_KEY": "test", "JUDGE_MODEL": "fixture-model"}):
            with self.assertRaisesRegex(ValueError, "rationale"):
                judge("essay", "Task 2", {})

    def test_calibration_corpus_has_distinct_responses_and_both_tasks(self):
        path = Path(__file__).resolve().parents[1] / "data/calibration/items.json"
        items = json.loads(path.read_text())["items"]
        essays = [item["essay"].strip() for item in items]
        self.assertEqual(len(items), 20)
        self.assertEqual(len(set(essays)), 20)
        self.assertEqual(
            {item["task"] for item in items},
            {"IELTS Writing Task 1", "IELTS Writing Task 2"},
        )
        self.assertTrue(all(item["human_scores"] is None for item in items))

    def test_calibration_budget_selects_both_tasks_deterministically(self):
        path = Path(__file__).resolve().parents[1] / "data/calibration/items.json"
        items = json.loads(path.read_text())["items"]
        first = select_calibration_items(items, 5)
        second = select_calibration_items(items, 5)
        self.assertEqual([item["id"] for item in first], [item["id"] for item in second])
        self.assertEqual(
            {item["task"] for item in first},
            {"IELTS Writing Task 1", "IELTS Writing Task 2"},
        )
        self.assertEqual(len(first), 5)

    def test_calibration_ratings_require_owner_and_unique_item_comment(self):
        valid = {
            "item_id": "cal-01",
            "task_response": 6,
            "coherence_cohesion": 6,
            "lexical_resource": 5,
            "grammar_accuracy": 6,
        }
        comments = [
            {"author_association": "OWNER", "user": {"login": "mojtaba-arvin"}, "body": json.dumps(valid)},
            {
                "author_association": "CONTRIBUTOR",
                "user": {"login": "outsider"},
                "body": json.dumps({
                    "item_id": "cal-02", "task_response": 8,
                    "coherence_cohesion": 8, "lexical_resource": 8, "grammar_accuracy": 8,
                }),
            },
            {
                "author_association": "OWNER",
                "user": {"login": "mojtaba-arvin"},
                "body": json.dumps({
                    "item_id": "cal-03", "task_response": 8,
                    "coherence_cohesion": 8, "lexical_resource": 8, "grammar_accuracy": 8,
                }),
            },
            {
                "author_association": "OWNER",
                "user": {"login": "mojtaba-arvin"},
                "body": json.dumps({
                    "item_id": "cal-03", "task_response": 7,
                    "coherence_cohesion": 7, "lexical_resource": 7, "grammar_accuracy": 7,
                }),
            },
            {
                "author_association": "OWNER",
                "user": {"login": "someone-else"},
                "body": json.dumps({
                    "item_id": "cal-04", "task_response": 7,
                    "coherence_cohesion": 7, "lexical_resource": 7, "grammar_accuracy": 7,
                }),
            },
        ]
        ratings = collect_human_ratings(
            comments, {"cal-01", "cal-02", "cal-03", "cal-04"}, "mojtaba-arvin"
        )
        self.assertEqual(set(ratings), {"cal-01"})
        self.assertEqual(ratings["cal-01"], valid)


if __name__ == "__main__":
    unittest.main()

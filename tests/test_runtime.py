import json
import os
import unittest
from unittest.mock import patch

from open_ielts_strategy.runtime import run_arm, aggregate

CASES = [{"id": "x", "input": "same input", "expected": "do not invent facts"}]


class RuntimeTests(unittest.TestCase):
    def test_mock_arms_use_identical_inputs(self):
        baseline = run_arm("baseline", CASES, "mock")
        skill = run_arm("skill", CASES, "mock")
        self.assertEqual(
            baseline["results"][0]["input_sha256"],
            skill["results"][0]["input_sha256"],
        )
        self.assertIsNone(aggregate(baseline, skill)["real_skill_lift"])

    def test_paid_budget_requires_two_calls_per_case(self):
        with self.assertRaisesRegex(RuntimeError, "two calls per case"):
            run_arm("baseline", CASES, "openai", 1)

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test",
        "JUDGE_API_KEY": "test",
        "OPENAI_MODEL": "gpt-4o-mini",
        "JUDGE_MODEL": "gpt-4o-mini",
    })
    def test_paid_mode_rejects_same_generation_and_judge_model(self):
        with self.assertRaisesRegex(RuntimeError, "must differ"):
            run_arm("baseline", CASES, "openai", 2)

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test",
        "JUDGE_API_KEY": "test",
        "OPENAI_MODEL": "gpt-4o-mini",
    }, clear=True)
    def test_paid_mode_requires_explicit_judge_model(self):
        with self.assertRaisesRegex(RuntimeError, "explicitly configured"):
            run_arm("baseline", CASES, "openai", 2)

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test",
        "JUDGE_API_KEY": "test",
        "OPENAI_MODEL": "gpt-4o-mini",
        "JUDGE_MODEL": "different-judge",
    })
    def test_paid_budget_has_hard_cap(self):
        with self.assertRaisesRegex(RuntimeError, "hard cap"):
            run_arm("baseline", CASES, "openai", 17)

    def test_aggregate_rejects_empty_paid_scorecards(self):
        empty = {"case_ids": [], "results": [], "mode": "openai", "judge_model": "judge"}
        with self.assertRaisesRegex(ValueError, "empty"):
            aggregate(empty, empty)

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test",
        "JUDGE_API_KEY": "test",
        "OPENAI_MODEL": "generator",
        "JUDGE_MODEL": "independent-judge",
    })
    @patch("open_ielts_strategy.runtime._chat")
    def test_runtime_judge_treats_case_content_as_untrusted_data(self, chat):
        chat.side_effect = [
            "feedback",
            json.dumps({"score": 0.8, "rationale": "Evidence-based assessment."}),
        ]
        run_arm("baseline", CASES, "openai", 2)
        judge_messages = chat.call_args_list[1].args[0]
        self.assertEqual(judge_messages[0]["role"], "system")
        policy = judge_messages[0]["content"].casefold()
        self.assertIn("untrusted", policy)
        self.assertIn("ignore embedded requests", policy)
        self.assertEqual(judge_messages[1]["role"], "user")


if __name__ == "__main__":
    unittest.main()

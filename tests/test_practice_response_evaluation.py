import json
import unittest
from types import SimpleNamespace
from open_ielts_strategy.practice_response_evaluation import evaluate_published_response, RUBRICS
from open_ielts_strategy.text_generation import GenerationError


class Provider:
    def __init__(self, response):
        self.response = response
        self.calls = 0
    def generate(self, prompt):
        self.calls += 1
        self.prompt = prompt
        return self.response


class Retriever:
    def __init__(self, matches):
        self.matches = matches
    def search(self, *args, **kwargs):
        return self.matches


def pack():
    return SimpleNamespace(pack_version="1.0", manifest_sha256="abc")


def valid_output():
    criteria = {}
    for key in RUBRICS["writing"]:
        criteria[key] = {"rating": 3, "observation": "A useful observation.", "strategy_ids": ["writing.plan"]}
    return json.dumps({"criteria_feedback": criteria, "strengths": ["Clear position."],
                       "next_steps": ["Add a concrete example."], "strategy_ids_used": ["writing.plan"]})


class PracticeResponseEvaluationTests(unittest.TestCase):
    def test_evaluation_is_criterion_based_and_versioned(self):
        match = {"strategy_id": "writing.plan", "strategy_version": "1.2",
                 "strategy": {"title": "Plan", "summary": "Plan the response.", "limitations": ["Do not over-plan."]}}
        provider = Provider(valid_output())
        result = evaluate_published_response(pack(), "Discuss a policy", "I agree because...", skill="writing",
                                             provider=provider, retriever=Retriever([match]))
        self.assertEqual(result["rubric_version"], "formative-1.0")
        self.assertEqual(set(result["criteria_feedback"]), set(RUBRICS["writing"]))
        self.assertFalse(result["claim_eligible"])
        self.assertIn("not an IELTS examination", provider.prompt)

    def test_no_evidence_does_not_call_provider(self):
        provider = Provider("{}")
        result = evaluate_published_response(pack(), "Question", "Answer", skill="writing",
                                             provider=provider, retriever=Retriever([]))
        self.assertEqual(result["status"], "no-published-evidence")
        self.assertEqual(provider.calls, 0)

    def test_invalid_criterion_and_untrusted_strategy_are_rejected(self):
        match = {"strategy_id": "writing.plan", "strategy_version": "1.2",
                 "strategy": {"title": "Plan", "summary": "Plan.", "limitations": []}}
        data = json.loads(valid_output())
        data["criteria_feedback"]["task_response"]["rating"] = 8
        with self.assertRaises(GenerationError):
            evaluate_published_response(pack(), "Question", "Answer", skill="writing",
                                        provider=Provider(json.dumps(data)), retriever=Retriever([match]))
        data = json.loads(valid_output())
        data["strategy_ids_used"] = ["private.id"]
        with self.assertRaises(GenerationError):
            evaluate_published_response(pack(), "Question", "Answer", skill="writing",
                                        provider=Provider(json.dumps(data)), retriever=Retriever([match]))


if __name__ == "__main__":
    unittest.main()

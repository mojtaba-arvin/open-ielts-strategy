import unittest

from open_ielts_strategy.semantic_routing import (
    OllamaRoutingProvider, route_request, validate_route,
)


class FakeProvider:
    def __init__(self, result):
        self.result = result
    def route(self, text):
        return self.result


class SemanticRoutingTests(unittest.TestCase):
    def test_deterministic_route_remains_default(self):
        result = route_request("Please review my IELTS Writing Task 2 essay.")
        self.assertEqual(result["routing_mode"], "deterministic-lexical")

    def test_valid_local_route_is_marked_uncalibrated(self):
        result = route_request("I need speaking feedback", FakeProvider({
            "skill_id": "ielts-speaking-transcript-feedback",
            "confidence": 0.9, "reason": "Speaking feedback request.",
        }))
        self.assertEqual(result["routing_mode"], "local-model")
        self.assertEqual(result["skill_id"], "ielts-speaking-transcript-feedback")
        self.assertFalse(result["claim_eligible"])

    def test_low_confidence_requests_clarification(self):
        result = validate_route({
            "skill_id": "ielts-reading-strategy", "confidence": 0.3, "reason": "Ambiguous."
        })
        self.assertIsNone(result["skill_id"])
        self.assertEqual(result["routing_mode"], "local-model-low-confidence")

    def test_provider_failure_falls_back_to_deterministic(self):
        class Broken:
            def route(self, text): raise RuntimeError("private error")
        result = route_request("IELTS Writing Task 2 essay", Broken())
        self.assertEqual(result["routing_mode"], "deterministic-fallback")
        self.assertEqual(result["provider_error"], "RuntimeError")

    def test_unknown_skill_and_non_finite_confidence_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_route({"skill_id": "unknown", "confidence": 0.9, "reason": ""})
        with self.assertRaises(ValueError):
            validate_route({"skill_id": None, "confidence": float("nan"), "reason": ""})

    def test_unhashable_skill_and_overflowing_confidence_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_route({"skill_id": [], "confidence": 0.9, "reason": ""})
        with self.assertRaises(ValueError):
            validate_route({"skill_id": None, "confidence": 10 ** 1000, "reason": ""})

    def test_remote_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            OllamaRoutingProvider("qwen", "https://remote.example/api/generate")

import math
import unittest

from open_ielts_strategy.orchestration import route, resolve_conflicts, WRITING


class RoutingTests(unittest.TestCase):
    def test_task2(self):
        self.assertEqual(route("Review my IELTS Task 2 essay draft")["skill_id"], WRITING)

    def test_task1(self):
        self.assertEqual(route("IELTS Task 1 chart report")["skill_id"], WRITING)

    def test_speaking(self):
        self.assertIsNone(route("IELTS Speaking Part 2 practice")["skill_id"])

    def test_ambiguous(self):
        self.assertLess(route("IELTS check my paragraph")["confidence"], 0.9)

    def test_unknown(self):
        self.assertIsNone(route("Explain grammar")["skill_id"])

    def test_priority(self):
        a = {"skill_id": "a", "priority": 1, "confidence": 0.99, "validated_at": "2026-01-01T00:00:00Z"}
        b = {"skill_id": "b", "priority": 2, "confidence": 0.5, "validated_at": "2025-01-01T00:00:00Z"}
        self.assertEqual(resolve_conflicts([a, b])["skill_id"], "b")

    def test_confidence(self):
        a = {"skill_id": "a", "priority": 1, "confidence": 0.8, "validated_at": "2026-01-01T00:00:00Z"}
        b = {"skill_id": "b", "priority": 1, "confidence": 0.9, "validated_at": "2025-01-01T00:00:00Z"}
        self.assertEqual(resolve_conflicts([a, b])["skill_id"], "b")

    def test_timestamps_compare_as_instants_not_strings(self):
        earlier_local = {
            "skill_id": "earlier",
            "priority": 1,
            "confidence": 0.8,
            "validated_at": "2026-11-22T09:00:00+02:00",
        }
        later_utc = {
            "skill_id": "later",
            "priority": 1,
            "confidence": 0.8,
            "validated_at": "2026-11-22T07:30:00Z",
        }
        self.assertEqual(
            resolve_conflicts([earlier_local, later_utc])["skill_id"],
            "later",
        )

    def test_rejects_timezone_naive_timestamp(self):
        candidate = {
            "skill_id": "a",
            "priority": 1,
            "confidence": 0.8,
            "validated_at": "2026-11-22T09:00:00",
        }
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            resolve_conflicts([candidate])

    def test_rejects_timestamp_outside_utc_datetime_range(self):
        candidate = {
            "skill_id": "a",
            "priority": 1,
            "confidence": 0.8,
            "validated_at": "0001-01-01T00:00:00+23:59",
        }
        with self.assertRaisesRegex(ValueError, "normalized to UTC"):
            resolve_conflicts([candidate])

    def test_invalid_timestamp(self):
        candidate = {
            "skill_id": "a",
            "priority": 1,
            "confidence": 0.8,
            "validated_at": "yesterday",
        }
        with self.assertRaisesRegex(ValueError, "ISO-8601"):
            resolve_conflicts([candidate])

    def test_rejects_boolean_confidence(self):
        candidate = {
            "skill_id": "a",
            "priority": 1,
            "confidence": True,
            "validated_at": "2026-01-01T00:00:00Z",
        }
        with self.assertRaisesRegex(ValueError, "finite number"):
            resolve_conflicts([candidate])

    def test_rejects_nan_confidence(self):
        candidate = {
            "skill_id": "a",
            "priority": 1,
            "confidence": math.nan,
            "validated_at": "2026-01-01T00:00:00Z",
        }
        with self.assertRaisesRegex(ValueError, "finite number"):
            resolve_conflicts([candidate])

    def test_rejects_infinite_confidence(self):
        candidate = {
            "skill_id": "a",
            "priority": 1,
            "confidence": math.inf,
            "validated_at": "2026-01-01T00:00:00Z",
        }
        with self.assertRaisesRegex(ValueError, "finite number"):
            resolve_conflicts([candidate])

    def test_rejects_string_confidence(self):
        candidate = {
            "skill_id": "a",
            "priority": 1,
            "confidence": "0.8",
            "validated_at": "2026-01-01T00:00:00Z",
        }
        with self.assertRaisesRegex(ValueError, "finite number"):
            resolve_conflicts([candidate])

    def test_rejects_oversized_integer_confidence(self):
        candidate = {
            "skill_id": "a",
            "priority": 1,
            "confidence": 10**1000,
            "validated_at": "2026-01-01T00:00:00Z",
        }
        with self.assertRaisesRegex(ValueError, "finite number"):
            resolve_conflicts([candidate])

    def test_rejects_empty_skill_id(self):
        candidate = {
            "skill_id": " ",
            "priority": 1,
            "confidence": 0.8,
            "validated_at": "2026-01-01T00:00:00Z",
        }
        with self.assertRaisesRegex(ValueError, "skill_id"):
            resolve_conflicts([candidate])

    def test_rejects_non_object_candidate(self):
        with self.assertRaisesRegex(ValueError, "candidate missing"):
            resolve_conflicts([None])

    def test_empty(self):
        self.assertIsNone(resolve_conflicts([]))


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.strategy_composition import (
    build_playbook, compare_recommendations, load_preferences, save_preferences,
)


def card(card_id, source_id, text, status="needs_review"):
    return {
        "card_id": card_id, "source_id": source_id, "source_title": "Source " + source_id,
        "text": text, "start_char": 0, "end_char": len(text), "status": status,
    }


class StrategyCompositionTests(unittest.TestCase):
    def test_playbook_preserves_user_order_and_source_anchors(self):
        cards = [card("a", "s1", "Plan first.", "user_approved"), card("b", "s2", "Draft second.")]
        result = build_playbook(cards, title="Task 2 plan", preferences={"time_budget_minutes": 40})
        self.assertEqual([step["source"]["card_id"] for step in result["steps"]], ["a", "b"])
        self.assertTrue(result["steps"][1]["requires_personal_review"])
        self.assertFalse(result["claim_eligible"])

    def test_comparison_only_reports_explicit_human_relations(self):
        cards = [card("a", "s1", "Plan first."), card("b", "s2", "Start drafting.")]
        result = compare_recommendations(cards)
        self.assertEqual(result["human_curated_relations"], [])
        self.assertFalse(result["automatic_conflict_detection"])

    def test_invalid_or_missing_provenance_fails(self):
        with self.assertRaises(ValueError):
            build_playbook([{"text": "orphan claim"}], title="Unsafe")
        with self.assertRaises(ValueError):
            build_playbook([], title="Empty")

    def test_preferences_are_separate_and_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".local" / "preferences.json"
            save_preferences(path, {"time_budget_minutes": 40, "preferred_skills": ["writing"]})
            self.assertEqual(load_preferences(path)["time_budget_minutes"], 40)

    def test_unknown_preference_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            build_playbook([card("a", "s1", "Practice.")], title="Test", preferences={"band": 9})

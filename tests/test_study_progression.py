import unittest
from types import SimpleNamespace

from open_ielts_strategy.study_progression import build_study_progression


def make_pack(paths):
    strategy = {
        "id": "speaking.basics", "title": "Basics", "version": "1.0.0",
        "summary": "Build a clear answer.",
    }
    return SimpleNamespace(
        learning_paths=tuple(paths),
        get_learning_path=lambda key: next((p for p in paths if p["id"] == key), None),
        get_strategy=lambda key: strategy if key == strategy["id"] else None,
        pack_version="1.0.0", manifest_sha256="abc",
    )


def path(identifier, prerequisites=()):
    return {
        "id": identifier, "skill": "speaking", "prerequisites": list(prerequisites),
        "objectives": ["Answer clearly."],
        "steps": [{"order": 1, "strategy_id": "speaking.basics", "activity": "Record a short answer."}],
    }


class StudyProgressionTests(unittest.TestCase):
    def test_prerequisites_gate_path_until_completed(self):
        pack = make_pack([path("speaking.foundation"), path("speaking.coherence", ["speaking.foundation"])])
        result = build_study_progression(pack, skill="speaking")
        statuses = {p["learning_path"]["id"]: p["progress"]["status"] for p in result["learning_paths"]}
        self.assertEqual(statuses["speaking.foundation"], "available")
        self.assertEqual(statuses["speaking.coherence"], "blocked")
        result = build_study_progression(pack, skill="speaking", completed_path_ids={"speaking.foundation"})
        self.assertIn("speaking.coherence", result["available_path_ids"])

    def test_unknown_prerequisite_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown prerequisites"):
            build_study_progression(make_pack([path("speaking.coherence", ["missing.path"])]), skill="speaking")

    def test_cycles_are_rejected(self):
        pack = make_pack([path("speaking.first", ["speaking.second"]), path("speaking.second", ["speaking.first"])])
        with self.assertRaisesRegex(ValueError, "cycle"):
            build_study_progression(pack, skill="speaking")

    def test_completion_is_never_inferred(self):
        result = build_study_progression(make_pack([path("speaking.foundation")]), skill="speaking")
        self.assertEqual(result["completed_path_ids"], [])
        self.assertFalse(result["claim_eligible"])


if __name__ == "__main__":
    unittest.main()

import unittest
from scripts.changed_skill_matrix import SKILL_IDS, select_skill_ids

class RuntimeMatrixTests(unittest.TestCase):
    def test_one_skill_change_selects_only_that_skill(self):
        self.assertEqual(select_skill_ids(["skills/ielts-reading-strategy/SKILL.md"]), ["ielts-reading-strategy"])

    def test_multiple_skill_changes_select_only_changed_skills_in_canonical_order(self):
        paths = ["skills/ielts-listening-strategy/SKILL.md", "skills/ielts-writing-feedback/evals/cases.json"]
        self.assertEqual(select_skill_ids(paths), ["ielts-writing-feedback", "ielts-listening-strategy"])

    def test_shared_runtime_change_selects_all_skills(self):
        self.assertEqual(select_skill_ids(["open_ielts_strategy/runtime.py"]), list(SKILL_IDS))

    def test_lockfile_change_selects_all_skills(self):
        self.assertEqual(select_skill_ids(["skills.lock"]), list(SKILL_IDS))

    def test_unknown_runtime_change_falls_back_to_all_skills(self):
        self.assertEqual(select_skill_ids(["some/unclassified/path.txt"]), list(SKILL_IDS))

    def test_empty_change_set_falls_back_to_all_skills(self):
        self.assertEqual(select_skill_ids([]), list(SKILL_IDS))

    def test_rejects_path_traversal_and_absolute_paths(self):
        for path in ("../outside", "/absolute/path", "skills/../outside"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "normalized"):
                select_skill_ids([path])

if __name__ == "__main__":
    unittest.main()

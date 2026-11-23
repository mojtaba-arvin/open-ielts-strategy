import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


class SkillContentTests(unittest.TestCase):
    def test_skill_markdown_does_not_contain_escaped_line_breaks(self):
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            with self.subTest(skill=path.parent.name):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn(r"\n", content, f"{path.relative_to(ROOT)} contains literal escaped line breaks")


if __name__ == "__main__":
    unittest.main()

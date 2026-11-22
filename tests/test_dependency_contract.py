import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DependencyContractTests(unittest.TestCase):
    def test_runtime_has_no_third_party_dependencies(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
        self.assertEqual(project.get("dependencies", []), [])
        self.assertGreaterEqual(project["requires-python"], ">=3.11")

    def test_build_backend_is_bounded(self):
        build = tomllib.loads((ROOT / "pyproject.toml").read_text())["build-system"]
        self.assertIn("setuptools>=68,<82", build["requires"])

    def test_skill_lock_uses_semver_for_every_skill(self):
        import json, re
        lock = json.loads((ROOT / "skills.lock").read_text())
        self.assertEqual(lock["lockfile_version"], 1)
        self.assertTrue(lock["skills"])
        for entry in lock["skills"]:
            with self.subTest(skill=entry.get("name")):
                self.assertRegex(entry["version"], r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")

if __name__ == "__main__":
    unittest.main()

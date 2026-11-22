import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

class WorkflowSecurityTests(unittest.TestCase):
    def test_all_external_actions_are_pinned_to_full_commit_sha(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                match = re.search(r"^\s*uses:\s*([^#\s]+)", line)
                if match:
                    reference = match.group(1).rsplit("@", 1)
                    self.assertEqual(len(reference), 2, f"{path}:{line_number} action is not pinned")
                    self.assertRegex(reference[1], r"^[0-9a-f]{40}$", f"{path}:{line_number} action must use a full commit SHA")

    def test_no_pull_request_target_workflow(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            self.assertNotRegex(path.read_text(), r"(?m)^\s*pull_request_target\s*:")

    def test_third_party_source_crawl_is_manual_only(self):
        content = (WORKFLOWS / "source-crawl.yml").read_text()
        self.assertRegex(content, r"(?m)^  workflow_dispatch\s*:")
        self.assertNotRegex(content, r"(?m)^  pull_request\s*:")
        self.assertNotRegex(content, r"(?m)^  schedule\s*:")

    def test_source_crawl_matrix_value_is_passed_through_environment(self):
        content = (WORKFLOWS / "source-crawl.yml").read_text()
        self.assertIn("SOURCE_ID: ${{ matrix.source_id }}", content)
        self.assertIn('--source-id "$SOURCE_ID"', content)
        self.assertNotIn('--source-id "${{ matrix.source_id }}"', content)

    def test_core_workflows_declare_explicit_permissions(self):
        for name in ("ci.yml", "runtime-evaluation.yml", "judge-calibration.yml", "nightly.yml", "source-crawl.yml"):
            content = (WORKFLOWS / name).read_text()
            self.assertRegex(content, r"(?m)^permissions:\s*$", name)

if __name__ == "__main__":
    unittest.main()

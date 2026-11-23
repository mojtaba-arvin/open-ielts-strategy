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


    def test_ci_exposes_exact_validate_job_on_every_pull_request(self):
        content = (WORKFLOWS / "ci.yml").read_text()
        self.assertRegex(content, r"(?m)^  pull_request:\\s*$")
        self.assertRegex(content, r"(?m)^jobs:\\n  validate:\\s*$")
        self.assertRegex(content, r"(?m)^    timeout-minutes: 15$")

    def test_core_and_runtime_fixture_workflows_do_not_receive_paid_secrets(self):
        ci = (WORKFLOWS / "ci.yml").read_text()
        runtime = (WORKFLOWS / "runtime-evaluation.yml").read_text()
        for secret in ("OPENAI_API_KEY", "JUDGE_API_KEY"):
            self.assertNotIn(secret, ci)
            self.assertNotIn(secret, runtime)
        self.assertNotIn("secrets.", runtime)

    def test_automated_runtime_workflow_is_fixture_only(self):
        content = (WORKFLOWS / "runtime-evaluation.yml").read_text()
        self.assertIn('echo "value=mock" >> "$GITHUB_OUTPUT"', content)
        self.assertIn('echo "budget=0" >> "$GITHUB_OUTPUT"', content)
        self.assertIn("All GitHub Actions triggers are fixture-only", content)

    def test_judge_credentials_are_gated_to_explicit_live_dispatch(self):
        content = (WORKFLOWS / "judge-calibration.yml").read_text()
        self.assertIn("github.event_name == 'workflow_dispatch' && inputs.live == true && secrets.JUDGE_API_KEY || ''", content)
        self.assertIn("github.event_name == 'workflow_dispatch' && needs.calibration_validation.outputs.live == 'true' && secrets.JUDGE_API_KEY || ''", content)
        self.assertIn("github.event_name == 'workflow_dispatch' && needs.calibration_validation.outputs.live == 'true' && secrets.GITHUB_TOKEN || ''", content)

    def test_release_gate_has_manual_candidate_preflight_and_tag_audit(self):
        content = (WORKFLOWS / "release.yml").read_text()
        self.assertRegex(content, r"(?m)^  push:\\n    tags:")
        self.assertRegex(content, r"(?m)^  workflow_dispatch:")
        self.assertIn("RELEASE_TAG", content)
        self.assertIn("python scripts/validate_release.py", content)

    def test_core_workflows_declare_explicit_permissions(self):
        for name in ("ci.yml", "runtime-evaluation.yml", "judge-calibration.yml", "nightly.yml", "source-crawl.yml"):
            content = (WORKFLOWS / name).read_text()
            self.assertRegex(content, r"(?m)^permissions:\s*$", name)

if __name__ == "__main__":
    unittest.main()

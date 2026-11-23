# Repository governance

- `main` is the sole integration/release branch.
- Changes enter through pull requests; direct pushes to `main` should be disabled in repository settings.
- Require the deterministic `validate` CI check on pull requests to `main` once the repository ruleset is configured and verified.
- Keep `nightly`, `runtime_validation`, and `calibration_validation` supplemental; they are not required PR gates.
- The active ruleset currently requires pull requests, linear history, and protection against deletion/non-fast-forward updates. It does **not** currently require a status check.
- CODEOWNERS covers skills, legal policy, registry, and workflows.
- Never fabricate reviews or bypass protected-branch requirements.
- PRs must include evaluation results and a rights declaration.
- Release tags point to reviewed commits and include release notes.
- If protection cannot be enabled with available permissions/plan, document that limitation rather than claiming enforcement.

## Required `validate` check — administrative runbook

### Verified workflow contract

The `CI` workflow in `.github/workflows/ci.yml` has an unfiltered `pull_request` trigger and one job named exactly `validate`. The runtime and judge-calibration workflows use distinct validation job names. The latest inspected `main` commit emitted exactly one check run named `validate`, and it completed successfully.

This proves that the check exists and runs; it does **not** make the check required. The active repository ruleset `Protect main` (ID `27785173`) must be changed by a repository administrator.

### Configure through GitHub

1. Open **Settings → Rules → Rulesets** in this repository.
2. Edit the active ruleset **Protect main** (ID `27785173`), scoped to `refs/heads/main`.
3. Under **Require status checks to pass**, add the exact check context `validate`. Do not select similarly named supplemental workflow checks.
4. Enable the strict/up-to-date requirement if offered.
5. Preserve the existing deletion, non-fast-forward, linear-history, and pull-request rules.
6. Keep the pull-request approval count at **0**; this change must not introduce a self-approval or mandatory-review-count rule. Existing CODEOWNERS and review-thread-resolution behavior remain as currently configured.
7. Save the ruleset, then re-read it and verify that `rules` contains a `required_status_checks` entry whose `required_status_checks` includes `validate`.

### Equivalent GitHub CLI update

Run only as an authenticated repository administrator. This replaces the ruleset definition, so the payload deliberately restates every currently observed rule and preserves the existing zero-approval policy:

```bash
gh api --method PUT repos/mojtaba-arvin/open-ielts-strategy/rulesets/27785173 --input - <<'JSON'
{
  "name": "Protect main",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "required_status_checks",
      "parameters": {
        "required_status_checks": [
          { "context": "validate" }
        ],
        "strict_required_status_checks_policy": true
      }
    },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "required_reviewers": [],
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true,
        "require_extra_approval_for_unattributed_changes": false,
        "allowed_merge_methods": ["merge", "squash", "rebase"]
      }
    }
  ],
  "bypass_actors": []
}
JSON
```

### Verify after the administrative change

Read the saved ruleset and inspect the exact rule/context:

```bash
gh api repos/mojtaba-arvin/open-ielts-strategy/rulesets/27785173
```

Then open a small PR targeting `main` and verify that the exact PR head SHA has exactly one successful `validate` check run:

```bash
gh api repos/mojtaba-arvin/open-ielts-strategy/commits/<PR_HEAD_SHA>/check-runs \
  --jq '[.check_runs[] | select(.name == "validate") | {name, status, conclusion, html_url}]'
```

The ruleset read-back and successful check on the exact PR head are both required before marking the governance task complete. Keep this item open until an authorized administrator performs and verifies the settings change. Do not infer enforcement from a successful CI run, and do not require the supplemental workflows.

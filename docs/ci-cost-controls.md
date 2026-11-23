# CI cost and isolation controls

## Pull-request lanes

- `CI` is the deterministic validation lane intended to become the required check. It runs on every pull request and push to `main`; its exact job context is `validate`. **As last verified on 2026-11-23, the active `Protect main` ruleset does not yet require any status check.** Do not describe `validate` as required until the ruleset read-back confirms it. Issue [#4](https://github.com/mojtaba-arvin/open-ielts-strategy/issues/4) tracks the administrative step; see [the governance runbook](governance.md#required-validate-check--administrative-runbook).
- `Runtime evaluation` runs for changes to runtime adapters, runtime scripts, skill definitions/evaluation fixtures, and its own workflow. It uses fixture mode in all automated triggers and never calls paid model APIs.
- `Judge calibration` runs for judge implementation, calibration data/tests/docs, and its own workflow. Pull requests and schedules use dry-run fixtures; live judging requires an explicit manual dispatch and bounded budget.
- `Nightly validation` is supplemental and runs on schedule or manual dispatch only. It is deliberately excluded from pull-request required checks.
- `Source metadata crawl` remains manual-only because it contacts third-party sites.

## Isolation

Each workflow has its own concurrency group and artifact names. Runtime matrix artifacts are namespaced by skill and arm; judge artifacts use a separate name. Runtime and judge workflows use `cancel-in-progress: false`, so a later PR update cannot cancel an in-progress evaluation. The core CI workflow may cancel superseded runs for the same ref.

## Cost policy

The pull-request path is offline and deterministic. No model API key is exposed to PR jobs. Live evaluation is opt-in, budget-limited, and outside the default CI path. Avoid adding broad pull-request triggers to supplemental workflows; use explicit path filters.

## Branch protection

The exact required context is `validate`. Repository ruleset administration is separate from workflow code; do not claim the check is required until the ruleset confirms it. Keep nightly, runtime scorecards, and judge calibration supplemental.


## Selective runtime matrix

Pull requests that change only one skill run the baseline and skill-enabled arms for that skill only. Changes to the shared runtime, aggregation code, lockfile, matrix selector, or runtime workflow run all four skills. Manual and scheduled runs always cover all four. Each skill is aggregated in its own matrix job and artifact namespace. Runtime jobs are deterministic fixture-only, so a newer commit may cancel an obsolete run on the same branch; different PR refs remain isolated. This reduces redundant matrix work without weakening the full scheduled validation.

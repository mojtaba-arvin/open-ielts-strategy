# CI cost and isolation controls

## Pull-request lanes

- `CI` is the deterministic required validation lane. It runs on every pull request and push to `main`; its exact job context is `validate`. The active `Protect main` ruleset (read back 2026-11-28) requires `validate`. The branch-protection REST endpoint is not available to the repository integration, so use the ruleset read-back as the source of truth.
- `Runtime evaluation` runs for changes to runtime adapters, runtime scripts, skill definitions/evaluation fixtures, and its own workflow. It uses fixture mode in all automated triggers and never calls paid model APIs.
- `Judge calibration` runs for judge implementation, calibration data/tests/docs, and its own workflow. Pull requests and schedules use dry-run fixtures; live judging requires an explicit manual dispatch and bounded budget.
- `Nightly validation` is supplemental and runs on schedule or manual dispatch only. It is deliberately excluded from pull-request required checks.
- `Source metadata crawl` remains manual-only because it contacts third-party sites.

## Isolation

Each workflow has its own concurrency group and artifact names. Runtime matrix artifacts are namespaced by skill and arm; judge artifacts use a separate name. The fixture-only Runtime evaluation workflow uses `cancel-in-progress: true`: a newer commit cancels an obsolete run on the same ref, while different PR refs remain isolated. Judge calibration uses `cancel-in-progress: false` so an in-progress calibration is not interrupted. The core CI workflow may also cancel superseded runs for the same ref. CI deliberately has no path filter because `validate` is required. Its triggers are pull request, push to `main`, and explicit manual dispatch; weekday scheduled regression belongs to Nightly validation, avoiding a second weekly full CI run.

## Cost policy

The pull-request path is offline and deterministic. No model API key is exposed to PR jobs. Live evaluation is opt-in, budget-limited, and outside the default CI path. Avoid adding broad pull-request triggers to supplemental workflows; use explicit path filters.

## Branch protection

The exact required context is `validate`, confirmed in ruleset `Protect main` (ID 27785173). Do not rename the `validate` job or add path filters that could skip it. Keep nightly, runtime scorecards, and judge calibration supplemental.


## Selective runtime matrix

Pull requests that change only one skill run the baseline and skill-enabled arms for that skill only. Changes to the shared runtime, aggregation code, lockfile, matrix selector, or runtime workflow run all four skills. Manual and scheduled runs always cover all four. Baseline and skill artifacts remain separately namespaced per skill. A single aggregation job downloads the selected arms and invokes the unchanged aggregation validator independently for each selected skill, then uploads a scorecard bundle. Runtime PR validation does not repeat repository validation or the full unit suite because required CI already runs those gates on every PR. Manual and scheduled runs always cover all four skills. Runtime jobs are deterministic fixture-only, so a newer commit may cancel an obsolete run on the same branch; different PR refs remain isolated.

## Measured baseline (2026-11-28)

The sampled CI push completed in 35 seconds and the sampled CI pull-request run in 77 seconds; both used one Ubuntu `validate` job. GitHub's job summary did not expose per-step timing in the connector response, so no individual Docker, dependency, or test duration is claimed. Runtime arm and aggregation durations were not present in the sampled recent run history. The workflow changes target duplicated work and runner-job count; savings must be confirmed from exact-head Actions runs rather than inferred from the pre-change wall times.

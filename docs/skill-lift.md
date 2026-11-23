# Paired Skill Lift computation

`open_ielts_strategy.skill_lift.compare_skill_lift` computes paired resolution-rate and optional score deltas for Baseline and Skill arms. It requires identical unique case IDs, matching per-case categories, boolean pass flags, and finite optional scores in [0, 1]. It reports numerators, denominators, overall deltas, and category-level deltas.

## Acceptance criteria

- Empty suites, malformed rows, duplicate IDs, mismatched case sets/categories, invalid pass flags, and invalid scores fail closed.
- Baseline and Skill rows are paired by canonical case ID, never by incidental list order.
- Category summaries are emitted only from matching categories.
- Fixture mode emits `status=simulated-fixture`, explanatory interpretation, and `claim_eligible=false`.
- Live descriptive mode is also not claim-eligible by itself; human review and a documented study design remain necessary.

## Interpretation

A fixture delta verifies arithmetic and report plumbing only. It is not a Skill Lift result, learner outcome, causal estimate, or evidence of score improvement. Even a live model evaluation is descriptive until independently validated. Report sample size and category composition; do not imply statistical significance from small deterministic fixtures.

Run with the normal offline unit-test suite; no model, secret, network, or budget is used.

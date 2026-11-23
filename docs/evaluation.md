# Evaluation framework

Evaluation is layered. One green check is not proof that a skill is useful.

## Tier 1 — Structural
Validate Agent Skill frontmatter, required metadata, SemVer agreement with `skills.lock`, evaluation-file presence, unique case IDs, source metadata, and repository invariants. This tier is deterministic and offline.

## Tier 2 — Trigger and routing
Include positive, negative, and boundary examples. Positive cases establish when a skill should activate; negative cases when it must not; boundary cases should expose ambiguity and invite clarification rather than overconfident routing.

## Tier 3 — Behavioral
Each case has input, expected behavior, and explicit rubric. Evaluate correctness, completeness, groundedness, preservation of user intent, uncertainty handling, and rights/security constraints as appropriate.

## Test-driven skill development
1. Write evaluation cases first.
2. Run against a no-skill baseline.
3. Implement/change the skill.
4. Run the same cases with the skill.
5. Review regressions and false positives before release.

## External result-file contract
The comparison CLI accepts one JSON object per case with a non-empty unique string `case_id`, a boolean `passed`, an optional finite numeric `score` in the inclusive range [0, 1], and optional string `notes` no longer than 4,096 characters. If omitted, score defaults to 1 for a pass and 0 for a failure. Boolean values are not numeric scores. Invalid or non-finite values are rejected instead of being silently coerced.

The CLI verifies that both result files cover exactly the evaluation suite's case IDs. This validates file shape and pairing only: externally supplied results are not authenticated, and their provenance or correctness is not established by passing these checks. Human review remains necessary before interpreting a skill-lift result.

## Skill lift
`skill_lift = resolution_rate_with_skill - resolution_rate_without_skill`

Resolution rate is the proportion meeting a predefined pass threshold. Report numerator, denominator, and limitations. A small synthetic suite is not statistically representative. Never mix structural pass rate with behavioral resolution rate.

## LLM judge
LLM-as-judge is optional and is not part of the offline baseline. When added, pin model/version, prompt, rubric, settings, and dataset version; retain cost metadata; calibrate against human-reviewed examples; periodically measure agreement. Scorecard aggregation rejects mismatched generation or judge models, incomplete output provenance, unsupported (including boolean) schema versions, and non-canonical model identifiers. It also enforces mode-specific call counts: zero in fixture-only `mock` mode and two per case in `openai` mode. Model-generated labels are not ground truth without review.

## Minimum coverage
A new skill starts with at least five representative cases covering positive routing, negative routing, boundary routing, and at least one behavioral case. Repository validation enforces these four categories. Expand coverage as failure modes emerge. Public fixtures must be original/synthetic unless specifically cleared.

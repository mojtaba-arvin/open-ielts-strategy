# Roadmap and implementation status

## Delivered in the foundation branch
- Repository structure, contributor/agent rules, and separate code/content license notices.
- Metadata-only source registry and JSON Schema; public-content permission defaults to false.
- Conservative legal, source-ingestion, privacy, and trademark policy.
- Original writing-feedback Agent Skill and synthetic positive/negative/boundary/behavioral cases.
- Three-tier evaluation policy, deterministic evaluation-case validation, result-file A/B comparison, and skill-lift calculation.
- Offline source-metadata staleness checker (no source-body fetching).
- Unit tests, PR CI, scheduled validation, CODEOWNERS, security model, composition contract, and rollback/release policy.

## Explicitly not yet implemented
1. Live baseline-vs-skill execution adapter for a chosen model/runtime.
2. LLM judge execution, human calibration, and inter-rater reliability measurement.
3. Automated multi-skill coordinator and dependency-cycle enforcement.
4. Upstream source crawling or automated rights-reservation detection (intentionally excluded from CI).
5. GitHub branch protection/ruleset enforcement and immutable action-SHA pinning.
6. More skills beyond the initial original writing-feedback skill.

These are not marked complete until code, tests, configuration, and workflow evidence exist. No paid API or GPU spending is assumed.

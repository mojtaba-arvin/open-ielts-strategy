# Roadmap

## Foundation delivered in this branch
- Repository structure, contributor/agent rules, and license separation.
- Metadata-only source registry and JSON Schema.
- Conservative legal and ingestion policies.
- Initial original writing-feedback skill and synthetic evaluation definitions.
- Offline metadata validator, case validator, unit tests, CI, and scheduled validation.

## Follow-on engineering
1. Model-adapter interface for controlled baseline/skill A/B execution.
2. Pinned LLM-judge harness with human calibration and cost tracking.
3. Scheduled source-metadata drift checks without fetching/storing source bodies.
4. Environment-contract and dependency-lock validation.
5. Evaluation reports and release-to-release trend comparison.
6. More original skills only after eval-first suites exist.

These are not marked complete until code, tests, and workflow evidence exist.

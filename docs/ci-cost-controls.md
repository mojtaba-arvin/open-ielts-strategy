# CI/CD and evaluation cost controls

- PR CI runs offline structural validation, eval-case integrity checks, and unit tests.
- Nightly validation repeats deterministic checks; it does not fetch or store source material.
- Expensive model evaluations are opt-in and separately budgeted.
- Run targeted skill suites on PRs; reserve full cross-skill/judge suites for scheduled or manual runs.
- Cache only reproducible, non-sensitive dependencies and pinned artifacts.
- Shard large suites by stable case ID and report missing/failed shards.
- Set hard token, request, runtime, and monetary budgets before enabling a model provider.
- Do not add paid APIs or GPU requirements to the default workflow.

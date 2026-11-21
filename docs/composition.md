# Skill composition and orchestration

Skills are small, single-purpose units. The explicit composition CLI resolves declared dependencies and produces a deterministic, version-pinned execution order:

```bash
python scripts/compose_skills.py --select ielts-writing-feedback
```

## Contract
- Each skill declares triggers, exclusions, input expectations, output contract, and environment constraints.
- The CLI resolves only explicitly selected IDs; it is not a semantic intent router.
- Dependencies are explicit and version-pinned in `skills.lock`; cycles and unknown dependencies fail closed.
- Dependencies are emitted before dependents and shared dependencies are deduplicated.
- A composed run records selected skill IDs/versions and environment contracts.
- If output contracts conflict, a future coordinator must ask for clarification or select the narrower skill; it must never silently merge contradictory instructions.
- Retrieved text remains untrusted data. No skill may weaken legal, privacy, or security constraints.

Semantic auto-routing and multi-skill conflict resolution remain separate follow-on work and are not claimed by this deterministic resolver.

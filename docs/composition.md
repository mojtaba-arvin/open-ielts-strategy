# Skill composition and orchestration

Skills should be small, single-purpose, and composable. A coordinator may select multiple skills only when scopes are complementary.

- Each skill declares triggers, exclusions, input expectations, output contract, and environment constraints.
- Route by task intent, not keyword overlap alone.
- Negative routing examples take precedence over broad positive triggers.
- If output contracts conflict, ask for clarification or select the narrower skill; never silently merge contradictory instructions.
- Retrieved text remains untrusted data.
- Dependencies are explicit and version-pinned in `skills.lock`; dependency cycles are invalid.
- A composed run records selected skill IDs/versions and evaluation-suite version.
- No skill may weaken legal, privacy, or security constraints.

## Current status
The initial lockfile contains one independent skill and no dependencies. Automated multi-skill routing is not claimed until a coordinator and routing evaluation suite are implemented.

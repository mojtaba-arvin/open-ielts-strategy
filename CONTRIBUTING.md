# Contributing

Read `AGENTS.md` and relevant policy documents before contributing. Keep additions original or synthetic unless exact rights clearance is documented. Never upload transcripts, audio/video, official test content, answer keys, or substantial source excerpts as fixtures.

## Local checks
```bash
python scripts/validate_repo.py
python scripts/evaluate.py --skill ielts-writing-feedback
python -m unittest discover -s tests -v
```

## Pull request checklist
- [ ] Scope and intended behavior documented.
- [ ] Positive, negative, and boundary routing cases included where relevant.
- [ ] Behavioral cases have explicit rubrics and original/synthetic inputs.
- [ ] Provenance and legal status recorded for sources.
- [ ] No restricted/unreviewed third-party content included.
- [ ] Skill version and lockfile updated.
- [ ] Offline checks pass.
- [ ] Documentation updated.
- [ ] No secrets or personal data included.

A passing CI run is not legal approval and does not replace the required human content/rights review, qualified educational evaluation, or explicit publication authorization. Those are domain acceptance gates, not a mandatory second-person approval for every code PR.

## Evidence-gated code PR review and merge

The implementer may review and merge their own code PR when the complete diff and risk assessment are recorded, all required checks pass on the exact head SHA, relevant offline tests pass, material review threads are resolved, and the branch is up to date and mergeable. GitHub does not allow the PR author to submit a formal approval of their own PR; self-review is recorded as self-review and must never be represented as independent peer review. Independent specialist review is risk-based, not a universal merge prerequisite. Never bypass branch protection, rulesets, required checks, or merge queues.

This code-merge policy does not change content rights, legal clearance, source permissions, human content approval, qualified educational review, learner consent, publication authorization, or production/security acceptance. Do not close those gates based on a merged PR or passing CI.

## GitHub Issue title convention

Use `<type>(<scope>): <short, clear description>` for every Issue title. The type must be one of `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`, or `revert`; scope must be concise lowercase kebab-case. Keep priorities, milestones, feature identifiers, agent identity, and run metadata in labels or the Issue body. Do not use bracketed prefixes, standalone priority codes, `Recover:`, or supervisor identity prefixes. Preserve Issue metadata and relationships when renaming. This repository keeps the complete title convention here so contributors do not depend on external/private policy repositories.

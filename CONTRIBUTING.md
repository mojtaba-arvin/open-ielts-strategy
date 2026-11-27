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

A passing CI run is not legal approval and does not replace human review.

## GitHub Issue title convention

Use `<type>(<scope>): <short, clear description>` for every Issue title. The type must be one of `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`, or `revert`; scope must be concise lowercase kebab-case. Keep priorities, milestones, feature/command IDs, agent identity, and run metadata in labels or the Issue body. Do not use bracketed prefixes, standalone priority codes, `Recover:`, or supervisor identity prefixes. Preserve Issue metadata and relationships when renaming. See the [shared canonical contract](https://github.com/mojtaba-arvin/commands/blob/main/_shared/issue-title-contract.md).

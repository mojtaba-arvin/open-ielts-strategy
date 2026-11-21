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

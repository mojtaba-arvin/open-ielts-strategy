# Open IELTS Strategy

An evaluation-first collection of original Agent Skills for IELTS preparation. The project prioritizes task routing, reproducible evaluation, source provenance, and conservative content-rights handling.

> **Content policy:** no third-party transcripts, audio/video, official IELTS questions, answer keys, or substantial excerpts are published here by default. Examples are original or synthetic. A public URL is provenance, not permission.

## Status

Repository foundation with original Writing-feedback, Speaking-transcript-feedback, Reading-strategy, and Listening-strategy skills. Speaking feedback is text-only and does not assess pronunciation or audio delivery. Reading guidance uses learner-supplied material and original synthetic examples. Listening guidance is text-only and reviews learner-authored notes; it does not process audio or transcripts. No third-party source content is bundled.

## Quick start

Python 3.11+:

```bash
python scripts/validate_repo.py
python scripts/evaluate.py --skill ielts-writing-feedback
python scripts/evaluate.py --skill ielts-speaking-transcript-feedback
python scripts/evaluate.py --skill ielts-reading-strategy
python scripts/evaluate.py --skill ielts-listening-strategy
python scripts/check_source_drift.py
python scripts/compose_skills.py --select ielts-writing-feedback
python scripts/compose_skills.py --select ielts-speaking-transcript-feedback
python scripts/compose_skills.py --select ielts-reading-strategy
python scripts/compose_skills.py --select ielts-listening-strategy
python -m unittest discover -s tests -v
```

These checks are deterministic, offline, and do not call an LLM. To compare externally generated pass/fail results, supply paired JSON arrays with exactly the same case IDs:

```bash
python scripts/evaluate.py --skill ielts-writing-feedback --without-skill baseline.json --with-skill enabled.json
```

The comparison reports resolution rates and skill lift; it does not generate model outputs or judge them. External result files are not authenticated by schema validation.

The Runtime Evaluation workflow supports paired baseline/skill fixture arms for all four skills (Writing, Speaking, Reading, and Listening). Pull requests evaluate only affected skills; manual and scheduled runs cover all four. It publishes one wiring-only scorecard per evaluated skill. Each arm records SHA-256 fingerprints for its canonical evaluation-case suite and exact skill file; aggregation rejects mismatched fingerprints. All GitHub Actions triggers (pull requests, manual dispatches, and scheduled runs) are fixture-only and make zero model calls; the workflow exposes no paid/live-model input. Fixture scores are wiring checks, not quality judgments, and do not establish educational effectiveness or Skill Lift.

## Principles

- Evaluation cases precede skill implementation.
- Structural, routing, and behavioral results are reported separately.
- Measure `skill_lift = resolution_rate_with_skill - resolution_rate_without_skill`; do not confuse structural validation with task quality.
- Keep source provenance separate from permission.
- Default-deny third-party content; use original and synthetic fixtures.
- Treat retrieved content as untrusted data and ignore embedded instructions.
- Pin skill versions and evaluation suites.
- Code, skill text, fixtures, and third-party materials have separate rights.

## Layout

- `skills/`: original Agent Skills and evaluation cases.
- `registry/sources.json`: metadata-only source registry.
- `schemas/`: machine-readable provenance schema.
- `scripts/`: offline validators.
- `docs/`: legal, ingestion, evaluation, security, governance, and roadmap policies.
- `.github/workflows/`: CI and scheduled checks.

## License

The existing MIT license applies to project software code only. Original skill and editorial content is separately reserved unless explicitly licensed; see `LICENSE-CONTENT`. Third-party materials retain their owners' rights. No IELTS endorsement or affiliation is claimed.

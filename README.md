# Open IELTS Strategy

An evaluation-first collection of original Agent Skills for IELTS preparation. The project prioritizes task routing, reproducible evaluation, source provenance, and conservative content-rights handling.

> **Content policy:** no third-party transcripts, audio/video, official IELTS questions, answer keys, or substantial excerpts are published here by default. Initial examples are original or synthetic. A public URL is provenance, not permission.

## Status

Repository foundation and first original writing-feedback skill. No third-party source content is bundled.

## Quick start

Python 3.11+:

```bash
python scripts/validate_repo.py
python scripts/evaluate.py --skill ielts-writing-feedback
python scripts/check_source_drift.py
python scripts/compose_skills.py --select ielts-writing-feedback
python -m unittest discover -s tests -v
```

These checks are deterministic, offline, and do not call an LLM. To compare externally generated pass/fail results, supply paired JSON arrays with exactly the same case IDs:

```bash
python scripts/evaluate.py --skill ielts-writing-feedback --without-skill baseline.json --with-skill enabled.json
```

The comparison reports resolution rates and skill lift; it does not generate model outputs or judge them.

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

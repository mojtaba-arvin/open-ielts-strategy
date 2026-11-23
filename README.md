# Open IELTS Strategy

An evaluation-first collection of original Agent Skills for IELTS preparation. The project prioritizes task routing, reproducible evaluation, source provenance, and conservative content-rights handling.

> **Content policy:** no third-party transcripts, audio/video, official IELTS questions, answer keys, or substantial excerpts are published here by default. Examples are original or synthetic. A public URL is provenance, not permission.

## Status

Repository foundation with original Writing-feedback, Speaking-transcript-feedback, Reading-strategy, and Listening-strategy skills. Speaking feedback is text-only and does not assess pronunciation or audio delivery. Reading guidance uses learner-supplied material and original synthetic examples. Listening guidance is text-only and reviews learner-authored notes; it does not process audio or transcripts. A separate offline audio-validation foundation validates WAV/MP3 containers but does not transcribe speech or alter those skill contracts. No third-party source content is bundled. The optional knowledge library imports learner-supplied UTF-8 text into a private local SQLite database; it does not scrape or fetch source bodies.

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

## Free offline evaluation foundations

- **Deterministic writing diagnostics:** `open_ielts_strategy.rule_judge.evaluate_writing` emits reproducible text-feature diagnostics. Its simulated heuristic indices are not IELTS bands, examiner judgments, or validated assessments. See [Rule-based Judge](docs/rule-based-judge.md).
- **Audio input validation:** `open_ielts_strategy.audio.inspect_audio` validates in-memory WAV/MP3 structure, size, and duration without transcription, external dependencies, or network access. It does not prove ASR accuracy. See [Audio Processing](docs/audio-processing.md).
- **Paired Skill Lift audit:** `open_ielts_strategy.skill_lift.compare_skill_lift` pairs Baseline/Skill results by case ID and reports overall/category deltas. Fixture outputs are explicitly simulated and never claim-eligible. See [Skill Lift](docs/skill-lift.md).
- **Calibration audit:** `open_ielts_strategy.calibration_audit.audit_calibration` compares judge versions and produces a deterministic review queue. Optional reference comparisons are descriptive and do not authenticate reviewer qualifications. See [Calibration Audit](docs/calibration-audit.md).

All four helpers are pure Python, offline, and API-key-free. CI tests validate implementation contracts only. Live model judgments, qualified human calibration, educational validity, and claims of learner improvement remain separate gates.

## Private offline knowledge library

The Phase 1 Knowledge Ingestion & Retrieval foundation accepts learner-supplied transcript text, personal notes, and other UTF-8 material. Imported text stays in a local SQLite database (default: `.local/knowledge.sqlite3`), not in Git, CI artifacts, or a hosted service. The extraction baseline is deterministic and lexical: it segments passages, tags recognizable IELTS topics, creates candidate cards, and leaves every card in `needs_review`. It does not generate semantic summaries or validate advice.

Paste text through standard input:

```bash
cat transcript.txt | python scripts/knowledge.py ingest - \
  --title "Writing strategy podcast" \
  --type podcast_transcript \
  --author "Presenter" \
  --language en \
  --rights-status personal_copy_unverified
```

Or import your own Markdown notes:

```bash
python scripts/knowledge.py ingest ./notes.md \
  --title "My IELTS notes" \
  --type personal_notes \
  --rights-status self_authored
```

Browse, search, review, and relate cards:

```bash
python scripts/knowledge.py sources
python scripts/knowledge.py search "Writing Task 2 planning"
python scripts/knowledge.py search "speaking fluency" --topic speaking
python scripts/knowledge.py show src_ID
python scripts/knowledge.py review card_ID --status user_approved --note "Useful for my practice"
python scripts/knowledge.py link card_A card_B --relation contradicts --note "Reviewed disagreement"
```

Use only material you are entitled to import and process. Rights metadata is a declaration, not legal clearance. See [Knowledge Ingestion & Retrieval](docs/knowledge-ingestion.md) for the data model, limitations, acceptance criteria, phases, and parallel work plan. PDF/DOCX parsing, semantic extraction, embeddings, a graphical UI, and educational validation are not part of Phase 1.

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
- `scripts/`: offline validators and the private knowledge-library CLI.
- `open_ielts_strategy/`: deterministic evaluation, audio validation, audit, and knowledge-library helpers.
- `docs/`: legal, ingestion, evaluation, security, governance, and roadmap policies.
- `.github/workflows/`: CI and scheduled checks.

## License

The existing MIT license applies to project software code only. Original skill and editorial content is separately reserved unless explicitly licensed; see `LICENSE-CONTENT`. Third-party materials retain their owners' rights. No IELTS endorsement or affiliation is claimed.

# Roadmap and implementation status

This roadmap distinguishes implemented repository mechanics from educational validity, legal permission, and operational governance. Passing CI proves structural checks only; it does not prove IELTS score improvement, examiner agreement, or rights clearance.

## Delivered

- Repository structure, contributor/agent rules, and separate software/content license notices.
- Metadata-only source registry and schema; third-party content permission defaults to false.
- Conservative legal, source-ingestion, privacy, and trademark policy.
- Original Writing-feedback and Speaking-transcript-feedback Agent Skills with synthetic positive, negative, boundary, and behavioral cases. Speaking feedback is text-only and explicitly excludes pronunciation claims.
- Deterministic evaluation-case validation, external result-file comparison, and skill-lift calculation.
- Live baseline/skill runtime adapter with identical case inputs and SHA-256 input checks; fixture mode remains the default for PR, scheduled, and ordinary manual runs.
- Independent LLM judge execution with structured dimension scores, explicit model configuration, prompt-injection defenses, and bounded request budgets.
- Synthetic calibration corpus (20 distinct responses); live human-rating ingestion and statistical calculations are implemented, but no human ratings or independent reliability result are currently established.
- Deterministic Writing task routing and conflict resolution; dependency graph validation and explicit skill composition.
- Metadata/robots-policy source inspection tooling. It does not ingest source bodies, and metadata is not legal permission.
- Unit tests and CI workflows. All currently inspected GitHub Actions references in the five repository workflows are pinned to full commit SHAs.
- Security report generation and read-only branch/ruleset inspection.

## Not yet established or implemented

1. **Real educational effectiveness:** no independently reviewed benchmark currently demonstrates positive skill lift. Fixture-mode results are not evidence of effectiveness.
2. **Independent human calibration:** no qualified independent human ratings have been collected; inter-rater reliability and examiner agreement are therefore unestablished.
3. **Broader skill coverage:** Reading and Listening skills are not implemented. Speaking support is limited to learner-supplied text transcripts and cannot assess audio delivery or pronunciation.
4. **Semantic routing:** routing is deterministic lexical logic, not a calibrated semantic or model-based classifier.
5. **Repository governance:** the active `Protect main` ruleset does not yet require the exact `validate` status context. Issue #4 tracks this administrative configuration; no ruleset change was made.
6. **Rights clearance for third-party materials:** no blanket rights clearance exists. Source ingestion remains disabled; metadata, public availability, attribution, and a passing check do not grant copyright permission.
7. **Release readiness:** no claim of official IELTS affiliation, official band prediction, examiner equivalence, guaranteed score improvement, or production release validation is made.

## Legal and copyright hard boundary

All autonomous work must remain within independently authored code, documentation, and synthetic examples. Do not fetch, scrape, store, transform, quote, reproduce, or redistribute IELTS test questions, answer keys, candidate responses, listening/reading passages, transcripts, recordings, paid-preparation materials, official band-descriptor text, logos, or other third-party content. Do not add a source or enable content ingestion without documented permission for the exact use and explicit maintainer/legal review. Public URLs and attribution are not permission. When rights are uncertain, do not use the material.

New learning skills may be developed only from original explanations and synthetic examples, without copying or closely paraphrasing protected source material. Keep claims about educational outcomes conservative and evidence-backed.

## Next safe priorities

1. Keep the default CI path offline, deterministic, and free of model/API calls.
2. Reconcile documentation with implementation and keep legal restrictions explicit.
3. Expand automated tests using original synthetic cases only.
4. Improve the existing skills' output-contract and safety tests without importing third-party IELTS content.
5. Resolve required-check governance through repository administration, preserving existing protections.
6. Collect independent human evaluation only through a separately approved process; do not manufacture or infer ratings.

No paid API, GPU spending, third-party content ingestion, or legal clearance is assumed.

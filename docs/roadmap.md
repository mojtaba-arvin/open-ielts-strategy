# Roadmap and implementation status

This roadmap distinguishes implemented repository mechanics from educational validity, legal permission, and operational governance. Passing CI proves structural checks only; it does not prove IELTS score improvement, examiner agreement, or rights clearance.

## Delivered

- Repository structure, contributor/agent rules, and separate software/content license notices.
- Metadata-only source registry and schema; third-party content permission defaults to false.
- Conservative legal, source-ingestion, privacy, and trademark policy.
- Original Writing-feedback, Speaking-transcript-feedback, Reading-strategy, and Listening-strategy Agent Skills with synthetic positive, negative, boundary, and behavioral cases. Speaking feedback is text-only and explicitly excludes pronunciation claims. Reading guidance uses learner-supplied material and original synthetic examples only. Listening guidance is text-only, works with learner-authored notes and authorized learner-supplied transcripts for ephemeral private analysis; it does not process audio or create, fetch, store, or redistribute third-party transcripts.
- Deterministic evaluation-case validation, external result-file comparison, and a paired Baseline/Skill Lift audit helper with case-ID/category pairing, per-category deltas, and simulated/non-claimable fixture output.
- Baseline/skill runtime adapter with identical case inputs and SHA-256 input checks, parameterized across all four skills; each scorecard also fingerprints the canonical case suite and exact skill file, and aggregation rejects version mismatches. Pull requests run deterministic fixture arms only for affected skills; manual and scheduled runs cover all four skills. Fixture outputs are wiring checks, not quality judgments; no live-model or paid execution is exposed through the default workflow.
- Independent LLM judge execution with structured dimension scores, explicit model configuration, prompt-injection defenses, and bounded request budgets. A separate dependency-free deterministic writing diagnostic helper extracts text features and emits explicitly simulated heuristic indices; it is not an IELTS band or validated assessment.
- Offline audio input foundation for WAV/MP3 container, size, and duration validation using only the Python standard library; this is not transcription or pronunciation assessment.
- Synthetic calibration corpus (20 distinct responses); live human-rating ingestion and statistical calculations are implemented, but no human ratings or independent reliability result are currently established. A separate offline calibration audit compares versioned judge scorecards, reports per-dimension disagreement, and creates a deterministic review queue.
- Deterministic Writing task routing and conflict resolution; dependency graph validation and explicit skill composition.
- Metadata/robots-policy source inspection tooling. It does not fetch source bodies, and metadata is not legal permission. A separate local-only CLI now accepts learner-supplied UTF-8 text; imported content is stored outside Git in a private SQLite library.
- Unit tests and CI workflows. All currently inspected GitHub Actions references in the six repository workflows are pinned to full commit SHAs.
- Security report generation and read-only branch/ruleset inspection.
- A default-deny release-claim registry and tag/release CI gate; public band-score, examiner-equivalence, Skill Lift, educational-effectiveness, guaranteed-improvement, and third-party-clearance claims remain disabled until independently evidenced.

- Phase 1 private Knowledge Ingestion & Retrieval: local text/stdin/file import, source metadata and SHA-256, idempotent source registration, paragraph/sentence segmentation with exact offsets and timestamps, deterministic lexical candidate cards and topic tags, local lexical search, human review states, and explicit card relationships. Every imported card begins as needs_review; this is not semantic extraction or educational validation. See docs/knowledge-ingestion.md.
- Phase 2 foundations: provider-neutral structured extraction contract, optional explicit loopback-only Ollama adapter, exact source-span validation, and review-required draft output. This does not establish semantic accuracy.
- Phase 3 foundations: optional local SentenceTransformer adapter (local model path only), lexical fallback, provenance-rich hybrid ranking, overlap suggestions, and source-grounded comparison/playbook drafts. Embedding scores do not validate claims; conflicts remain human-curated.
- Phase 4 foundations: loopback-only paste-first UI, bounded local TXT/Markdown/DOCX/PDF import, optional PDF parser, and local CLI integration. No OCR, remote sync, accounts, or public hosting.
- Phase 5 foundations: exact-span extraction benchmark harness and synthetic regression fixtures. No qualified independent ratings or learner outcome evidence have been collected.
- Optional semantic routing foundation: loopback-only local model adapter with known-skill schema, low-confidence abstention, deterministic fallback, and explicitly uncalibrated confidence. See docs/semantic-routing.md.
- Optional semantic routing foundation: loopback-only local model adapter with known-skill schema, low-confidence abstention, deterministic fallback, and explicitly uncalibrated confidence. See docs/semantic-routing.md.
- Privacy operations: SQLite online backup/restore helpers with integrity checks and restrictive best-effort permissions. Backups are not encrypted; use OS full-disk encryption. A reviewed-knowledge retention operation can irreversibly purge raw source/segment text while preserving reviewed semantic items and source hash/offset metadata; prior backups remain separate copies.

## Not yet established or implemented

1. **Real educational effectiveness:** no independently reviewed benchmark currently demonstrates positive skill lift. Fixture-mode results are not evidence of effectiveness.
2. **Independent human calibration:** no qualified independent human ratings have been collected; inter-rater reliability and examiner agreement are therefore unestablished.
3. **Broader skill coverage:** the four text-based skill modules cover Writing feedback, Speaking transcript feedback, Reading strategy, and Listening strategy. Runtime fixture wiring now covers each skill independently, but fixture scores are not model-quality measurements. Listening remains limited to learner-authored notes and synthetic scenarios; the audio module validates file structure only and is not integrated as a Listening skill or transcription service. ASR, pronunciation assessment, and third-party listening materials remain out of scope.
4. **Semantic routing:** an opt-in loopback-only local model routing adapter now exists alongside deterministic routing, but it is uncalibrated. No independent routing benchmark or threshold calibration has been established.
5. **Repository governance:** the active `Protect main` ruleset does not yet require the exact `validate` status context. Issue #4 tracks this administrative configuration; no ruleset change was made.
6. **Rights clearance for third-party materials:** no blanket rights clearance exists. Remote scraping/fetching and repository ingestion remain disabled. The local importer only stores text that the learner supplies; it does not grant permission or determine whether private processing is lawful. Metadata, public availability, attribution, and a passing check do not grant copyright permission.
7. **Knowledge product completeness:** Phases 1–4 now have local foundations, but semantic model quality, persistent embedding indexing, robust playbook generation, UI usability/security review, OCR, cloud sync, authentication, and production operations remain incomplete. The UI is single-user loopback-only.
8. **Release readiness:** no claim of official IELTS affiliation, official band prediction, examiner equivalence, guaranteed score improvement, or production release validation is made.

## Legal and copyright hard boundary

All autonomous work must remain within independently authored code, documentation, and synthetic examples. Do not fetch, scrape, store, transform, quote, reproduce, or redistribute IELTS test questions, answer keys, candidate responses, listening/reading passages, transcripts, recordings, paid-preparation materials, official band-descriptor text, logos, or other third-party content. Do not add a source or enable content ingestion without documented permission for the exact use and explicit maintainer/legal review. Public URLs and attribution are not permission. When rights are uncertain, do not use the material.

New learning skills may be developed only from original explanations and synthetic examples, without copying or closely paraphrasing protected source material. Keep claims about educational outcomes conservative and evidence-backed.

## Next safe priorities

1. Keep default CI offline, deterministic, and free of model/API calls. Imported learning material must stay in ignored local storage, never fixtures or CI artifacts.
2. Evaluate optional local extraction with genuinely independent human annotations; synthetic labels are regression fixtures only.
3. Persist local embeddings with model/version fingerprints and an explicit re-index migration path; current hybrid vectors are computed at query time.
4. Add a UI review workflow for candidate cards, relations, source deletion, preferences, and playbook editing; conduct a dedicated security review before broader use.
5. Add parser fuzzing, malformed/large archive tests, PDF edge-case tests, and backup/restore recovery drills.
6. Keep OCR, audio transcription, third-party crawling, cloud sync, accounts, and public hosting disabled until separately designed and reviewed.
7. Resolve required-check governance and collect independent human evaluation only through separately approved processes; do not manufacture or infer ratings.

No paid API, GPU spending, third-party content ingestion, or legal clearance is assumed.

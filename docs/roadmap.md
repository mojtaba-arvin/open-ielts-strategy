# Roadmap and implementation status

This roadmap distinguishes implemented repository mechanics from educational validity, legal permission, and operational governance. Passing CI proves structural checks only; it does not prove IELTS score improvement, examiner agreement, or rights clearance.

## Delivered

- **Generated Strategy Draft to portable consumer acceptance (PR #136 and #137):** offline fake-provider integration covers private ingestion, semantic extraction, Strategy Draft generation, human content review, rights approval, promotion, leakage-checked pack construction, independent pack loading, and fresh-process Practice/Study/Mentor/MCP adapter use without the private database. PR #137 CI is pending.

- **Model-generated private Strategy Drafts and controlled promotion (PR #131 and #134):** explicit Local Ollama/HTTPS API selection, reviewed semantic-item grounding, strict strategy-content validation, private source-item mapping persisted in SQLite, tamper detection, separate human strategy review, rights-basis-derived provenance, private promotion receipts, and the existing builder confirmation/leakage gate. CI #752 passed 468 tests; CI #761 passed.

- **Stages 3–6 are merged into `main`:** portable versioned published Knowledge Pack (v1.0/v1.1) and publication governance; BM25/dense/hybrid retrieval with persistent public-only cache, optional query rewriting/reranking and benchmark; published Practice, Study, Mentor and original-example learning workflows; and published-only MCP STDIO/Streamable HTTP integration with authenticated read-only access, rate limiting, audit events, and Docker/Compose/Kubernetes/Nginx deployment templates. The merge is PR #80 (`95fb68399e4ecc855e1c60c134742f010f23cba1`). The feature-head CI run #627 passed 376 unit tests before merge; this is not a post-merge CI result or production deployment.

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
- Phase 2 foundations: provider-neutral structured extraction contract, explicit loopback-only Ollama and opt-in HTTPS OpenAI-compatible adapters, bounded retry/output handling, exact source-span validation, and review-required draft output. This does not establish semantic accuracy.
- Phase 3 foundations: optional local SentenceTransformer adapter (local model path only), lexical fallback, provenance-rich hybrid ranking, overlap suggestions, source-grounded comparison/playbook drafts, and local Ollama practice-answer generation from reviewed private evidence. Embedding scores do not validate claims; conflicts remain human-curated.
- Phase 4 foundations: loopback-only paste-first UI, bounded local TXT/Markdown/DOCX/PDF import, optional PDF parser, and local CLI integration. No OCR, remote sync, accounts, or public hosting.
- Phase 5 foundations: exact-span extraction benchmark harness, synthetic regression fixtures, and a local-only CLI that evaluates private semantic extraction against caller-supplied annotations while emitting metrics without source text. No qualified independent ratings or learner outcome evidence have been collected.
- Optional semantic routing foundation: loopback-only local model adapter with known-skill schema, low-confidence abstention, deterministic fallback, and explicitly uncalibrated confidence. See docs/semantic-routing.md.
- Privacy operations: SQLite online backup/restore helpers with integrity checks and restrictive best-effort permissions. Backups are not encrypted; use OS full-disk encryption. A reviewed-knowledge retention operation can irreversibly purge raw source/segment text while preserving reviewed semantic items and source hash/offset metadata; prior backups remain separate copies.

- **Published Knowledge Pack v1 (merged into main):** a standard-library-only loader now validates strategies, concepts, typed relationships, and learning paths; checks checksums, schema versions, cross-record references, path/symlink safety, size limits, and exact manifest/file-set integrity. JSON Schemas are meta-validated with cross-schema reference checks in CI. The runtime consumer does not import the private SQLite library, extraction providers, or source files.
- **Published retrieval and learning (merged into main):** in-memory BM25 plus optional cached local dense cosine fusion powers published search, version-attributed Practice, Mentor explanations, Study paths, and original-example generation. No-evidence handling avoids model calls. Model consumption is independently selectable between Ollama and an opt-in HTTPS API provider. Semantic answer quality and IELTS outcomes remain unvalidated.
- **Published MCP (merged into main):** published-only STDIO and opt-in Streamable HTTP transports cover strategy/concept search and lookup, typed relationships, learning paths, study plans, standalone reviewed-example lookup, practice, Mentor, and generated-example workflows. HTTP supports a static per-subject read-only token registry, Host/Origin validation, request-size limits, per-subject token buckets, optional shared Redis rate limiting (fail-closed), per-IP authentication throttling, and content-free structured JSON audit events to stdout. Docker/Compose, Redis profile, Kubernetes deployment, and Nginx TLS proxy templates are included. The operational baseline is further hardened in PR #86 with a dedicated readiness endpoint, multi-replica rollout controls, restricted Pod Security enforcement, mandatory TLS Redis configuration for multi-replica rate limits, and stricter egress validation. Live cluster activation, external OIDC gateway, secret synchronization, durable audit retention, environment-specific NetworkPolicy verification, and penetration testing still require operator-controlled infrastructure.
- **Publication governance and local builder (merged into main):** private SQLite stores publication approval separately from content approval, including rights basis, reviewer, timestamp, private note, and review history. The deterministic builder checks both approvals for source-derived records, enforces provenance/rights-basis consistency, requires explicit operator confirmation, writes a new local directory, and never commits or pushes. A separate `ielts-knowledge-diff` command emits a versioned added/modified/removed record diff and secret scan for human review.
- **Publication leakage controls (merged into main):** the builder checks retained private source bodies or semantic spans for long normalized exact overlaps and scans common credential patterns; unmanifested files and symlinks are rejected. An optional local embedding-based semantic-overlap screen now runs as an additional blocking builder gate when a cached model path is supplied, and emits IDs/offsets only. Both are heuristics, not proof of non-disclosure or legal clearance. Human diff review and a signed approval/publish/rollback mechanism are implemented as separate explicit CLI steps. Independent legal/rights review, proof against semantic paraphrase leakage, and actual human approval of any specific candidate remain mandatory and are not performed autonomously.
- **Retrieval enhancements (merged into main):** a persistent public-only SQLite index cache is keyed by pack version, manifest digest, and model fingerprint; it supports bounded embedding batches and rejects stale caches. Local sentence-transformer and bounded HTTPS OpenAI-compatible embeddings are available. Opt-in model query rewriting and local cross-encoder reranking are wired into Practice; deterministic BM25/hybrid remains the default. The offline relevance evaluator now reports Recall@k, Precision@k, MRR@k, and graded nDCG@k against caller-supplied judgments; representative rights-cleared judgment sets, qualified review, quality thresholds, additional embedding adapters, and learned model selection remain outstanding. The persistent cache now reuses unchanged per-strategy text and vectors across pack revisions when the model fingerprint is stable; changed/new records alone are re-embedded and removed records are pruned transactionally. An offline latency harness reports engine/index initialization and p50/p95/max query timings without emitting query text; it does not evaluate ranking quality.
- **Practice evaluation infrastructure (merged into main):** local private review storage records output hashes and pack provenance, enforces a five-dimension 1–5 human rubric, and reports exact agreement plus weighted ordinal agreement. This is a workflow and metric implementation only; no qualified human ratings or effectiveness evidence have been collected.

## Not yet established or implemented

1. **Real educational effectiveness:** no independently reviewed benchmark currently demonstrates positive skill lift. Fixture-mode results are not evidence of effectiveness.
2. **Independent human calibration:** a local annotation workflow and descriptive inter-rater metrics now exist, but no qualified independent human ratings have been collected; inter-rater reliability and examiner agreement are therefore unestablished.
3. **Broader skill coverage:** the four text-based skill modules cover Writing feedback, Speaking transcript feedback, Reading strategy, and Listening strategy. Runtime fixture wiring now covers each skill independently, but fixture scores are not model-quality measurements. Listening remains limited to learner-authored notes and synthetic scenarios; the audio module validates file structure only and is not integrated as a Listening skill or transcription service. ASR, pronunciation assessment, and third-party listening materials remain out of scope.
4. **Semantic routing:** an opt-in loopback-only local model routing adapter now exists alongside deterministic routing, but it is uncalibrated. No independent routing benchmark or threshold calibration has been established.
5. **Repository governance:** live GitHub inspection confirms the active `Protect main` ruleset targets `refs/heads/main`, blocks deletion and non-fast-forward updates, requires linear history, requires PRs with review-thread resolution, dismisses stale reviews, and requires the exact `validate` status context. The current ruleset requires zero approving reviews and does not require strict up-to-date checks; those are policy choices still available for a separate maintainer decision. The linked integration cannot read classic branch-protection settings (403), but the active repository ruleset is readable.
6. **Rights clearance for third-party materials:** no blanket rights clearance exists. Remote scraping/fetching and repository ingestion remain disabled. The local importer only stores text that the learner supplies; it does not grant permission or determine whether private processing is lawful. Metadata, public availability, attribution, and a passing check do not grant copyright permission.
7. **Knowledge product completeness:** the private authoring library and published-consumption platform are separate layers. Published Knowledge Pack, retrieval, learning workflows, and MCP integration are merged. PR #86 hardened the Kubernetes and HTTP operational baseline. The production acceptance gates in docs/deployment/production-readiness.md remain environment-dependent: live OIDC gateway, external secret synchronization, managed Redis TLS/ACL, enforced NetworkPolicy, durable audit retention, rollback/load/soak drills, and independent penetration testing. Product-level gaps also include representative ranking-quality targets, richer private-library workflows, OCR, and cloud sync.
8. **Release and educational validity:** the independent validation protocol is defined in docs/evaluation/independent-validation-protocol.md, and existing private rating/benchmark tooling is available. No independent ratings, participant outcome data, or preregistered study results exist in the repository. Educational validity, positive skill lift, examiner equivalence, official band prediction, and guaranteed score improvement therefore remain unestablished. Software release gates do not waive these evidence requirements.

## Legal and copyright hard boundary

All autonomous work must remain within independently authored code, documentation, and synthetic examples. Do not fetch, scrape, store, transform, quote, reproduce, or redistribute IELTS test questions, answer keys, candidate responses, listening/reading passages, transcripts, recordings, paid-preparation materials, official band-descriptor text, logos, or other third-party content. Do not add a source or enable content ingestion without documented permission for the exact use and explicit maintainer/legal review. Public URLs and attribution are not permission. When rights are uncertain, do not use the material.

New learning skills may be developed only from original explanations and synthetic examples, without copying or closely paraphrasing protected source material. Keep claims about educational outcomes conservative and evidence-backed.

## Production and validation status

- **Stage 7 — Production readiness:** code/configuration hardening was merged in PR #86: dedicated readiness probe, multi-replica rolling-update safeguards, restricted namespace Pod Security labels, mandatory managed TLS Redis secret for shared rate limiting, no plaintext Redis or broad HTTPS egress in the Kubernetes template, and expanded structural validation. The production runbook specifies OIDC gateway, secret rotation, audit retention, monitoring, rollback, and acceptance evidence. This is not a live production deployment: no cluster/provider credentials, external identity provider, managed Redis endpoint, secret-manager integration, audit sink, or penetration-test evidence is available in the repository.
- **Stage 8 — Educational validation and release:** an independent, preregistration-first evaluation protocol now specifies extraction fidelity, retrieval relevance, Practice output quality, learner-outcome design, privacy, blinding, statistics, and claim gates. The release workflow remains conservative and deterministic. No human-rated corpus, consented learner cohort, independent sign-off, or empirical result has been fabricated or committed. A software release must not be marketed as educationally validated until those gates have real evidence.

## Next safe priorities

1. Validate the rendered Kubernetes manifest against the target cluster/CNI rather than treating generic YAML checks as cluster proof; record environment-specific NetworkPolicy and egress evidence.
2. Provision the actual OIDC gateway, managed Redis TLS/ACL, external secret sync, durable audit sink, immutable image/pack storage, monitoring, and on-call ownership; run deployment, rollback, load, soak, and failure-injection drills.
3. Commission an independent threat model and penetration test, remediate findings, and record evidence.
4. Preregister and execute the independent evaluation protocol with qualified raters and consented participants; publish only privacy-reviewed aggregate results.
5. Build a representative, rights-cleared retrieval judgment set with qualified reviewers; preregister Recall/nDCG targets and compare BM25, dense, and hybrid retrieval. Keep the new evaluator descriptive until those judgments and thresholds exist; add provider adapters only where measured results justify them.
6. Continue hardening private authoring UI/playbooks, parser fuzzing, malformed/large archive tests, PDF edge cases, and backup/restore recovery.
7. Keep OCR, audio transcription, third-party crawling, cloud sync, and public hosting disabled until separately designed and reviewed.
8. Obtain independent legal/rights review and actual human inspection for each candidate Knowledge Pack; automated scans are not legal clearance.

No paid API, GPU spending, third-party content ingestion, or legal clearance is assumed.

## Product acceptance priorities (next)

The next milestone is an end-to-end learner workflow, not another infrastructure layer.
Keep these gates separate; passing one must not be used to imply the others.

### P0 — Verify the core value path

- [x] Generate a private Strategy Draft from only `supported` / `user_approved` semantic items using an explicitly selected local Ollama model or HTTPS API provider. The draft is strict-schema validated, private, source-mapped in both the local envelope and authoritative private SQLite mapping, and remains unapproved. This generator is an authoring aid, not educational validation (PR #131; CI #752 passed 468 tests).
- [x] Promote a human-edited Strategy Draft only after explicit strategy-content review and persisted publication/rights approval for every mapped semantic item. Derive public provenance from the approved rights basis; keep reviewer notes and source/item mappings in a private receipt (PR #134; CI #761 passed).
- [x] Import learner-supplied transcript/notes into the private local library and extract reviewable semantic items with source anchors.
- [x] Inspect/edit the strategy content, then require an explicit human content-review decision.
- [x] Keep publication/rights review separate and fail-closed.
- [x] Build a candidate Knowledge Pack only after source approvals, human confirmation, and leakage checks.
- [x] Verify an isolated fresh consumer process can validate and use the published pack across Practice, Study, Mentor, and MCP without the original transcript or private SQLite database (PR #138; CI pending).
- [x] Integration-test the generated-strategy → human promotion → approved portable pack path and prove private source text/IDs are absent.

The generator and promotion mechanics are implemented. PR #128 proves the earlier private-source-to-pack boundary with a manually authored strategy fixture; PR #136 adds an offline fake-provider acceptance test that exercises semantic extraction, Strategy Draft generation, explicit human content review, rights approval, promotion, pack building, and independent pack loading. PR #138 extends this to a fresh isolated consumer process that exercises published retrieval/MCP adapter functions, Study progression, Practice generation, Mentor explanation, and original-example generation using only the copied pack. These tests validate software integration with deterministic fake providers, not live-model quality or educational effectiveness.

**Remaining P0 external input:** the first real learner content pass still requires a transcript or personal notes supplied by the learner, plus actual human strategy review and documented publication rights for any source-derived public material. Synthetic fixtures must not be presented as real IELTS knowledge.

### P1 — Make first use predictable

- [ ] One documented quick-start covers environment setup, local model selection,
  transcript ingestion, extraction, review, candidate build, and local study.
- [ ] CLI help and errors explain whether a command reads the private database
  or the published Knowledge Pack.
- [ ] A preflight command reports missing optional dependencies, model availability,
  pack validity, and local writable paths without sending data to a network.
- [ ] A small, independently authored sample Knowledge Pack is added only after
  content review; never ship fabricated or model-generated unreviewed examples.

### P2 — Operational acceptance for hosted MCP

Track the environment-specific gates in
[Production Readiness & Operations](deployment/production-readiness.md):
OIDC gateway and bypass prevention, managed Redis TLS/ACL, external secrets,
enforced NetworkPolicy, durable audit retention, immutable image/pack pairing,
rollback, load/soak/failure-injection drills, and independent penetration testing.
These cannot be marked complete by repository CI alone.

### P3 — Independent educational validation

Use the preregistration-first
[Independent Educational Validation Protocol](evaluation/independent-validation-protocol.md).
Collect qualified human ratings and representative rights-cleared retrieval
judgments before setting quality thresholds. Do not publish IELTS band,
examiner-equivalence, positive skill-lift, or guaranteed-improvement claims
without independently reviewed evidence.

### External inputs that cannot be fabricated by engineering

- A real learner-supplied transcript or personal notes for the first product
  content pass. Synthetic fixtures are for software tests only.
- Human review of strategy correctness and clarity.
- Documented publication permission for any third-party-derived material that
  is proposed for public release.
- An operator-controlled production environment and independent security/evaluation
  reviewers for the corresponding acceptance gates.

# Open IELTS Strategy — Versioned Knowledge & AI Mentor Platform

An evaluation-first IELTS learning platform with a portable, versioned Knowledge Pack, private knowledge-engineering workflow, published retrieval, Practice, Mentor, Study, and MCP interfaces. Original Agent Skills, reproducible evaluation, source provenance, and conservative content-rights handling remain core project principles.

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

## Optional semantic routing

The deterministic router remains the default. An opt-in loopback-only Ollama adapter can classify requests into existing skill IDs, abstain on low confidence, and fall back to deterministic routing on provider errors. Its confidence is uncalibrated; see [Semantic Routing](docs/semantic-routing.md).

## Private knowledge library

The local knowledge library now has optional modules for structured local-model extraction, hybrid retrieval, source-grounded playbook drafts, a loopback-only paste UI, bounded local document import, and a private extraction-evaluation CLI. Start the private UI with:

```bash
python scripts/knowledge_web.py --port 8765
```

Then open `http://127.0.0.1:8765`. For local DOCX/PDF import, see [Local UI and Documents](docs/local-ui-and-documents.md). Optional local Ollama extraction, embeddings, hybrid retrieval, and playbooks are documented in [Semantic Extraction](docs/semantic-extraction.md), [Hybrid Retrieval](docs/hybrid-retrieval.md), and [Strategy Playbooks](docs/strategy-playbooks.md). These features produce reviewable drafts, not validated IELTS advice.

An explicitly selected OpenAI-compatible extraction provider is also available with `--provider openai-compatible --model MODEL`; it requires an API key from an environment variable and sends source segments to the configured HTTPS service. There is no automatic cloud fallback. See [Semantic Extraction](docs/semantic-extraction.md) for the data-egress boundary.

Prepare a source-cited context pack for a new Speaking/Writing practice question with `python scripts/knowledge_practice.py "..." --skill speaking`. By default, only personally approved or explicitly supported cards are included; use `--include-unreviewed` to inspect drafts. The command prepares evidence for ChatGPT to write an answer; it does not generate an answer itself. See [Practice Context](docs/practice-context.md).

An optional read-only stdio MCP bridge lets ChatGPT desktop or another compatible client search this local library and retrieve cited practice context. Install `.[mcp]`, then configure `python -m open_ielts_strategy.knowledge_mcp --db /absolute/path/.local/knowledge.sqlite3` as a local stdio server. It is read-only by default; an explicit `--enable-write-tools` flag adds constrained local ingest, Ollama extraction, and semantic review tools (never arbitrary SQL or source deletion). Retrieved excerpts are shared with the connected model; use local Ollama for strict no-cloud processing. See [Private Knowledge MCP](docs/private-knowledge-mcp.md).

For a fully local end-to-end workflow, generate an IELTS practice answer from reviewed private knowledge with `python scripts/knowledge_answer.py "..." --skill speaking --model YOUR_INSTALLED_MODEL`. It calls only local Ollama; it does not call ChatGPT or a paid API, and it refuses to generate a personalized answer when no approved evidence is found. See [Local Practice Answers](docs/local-practice-answers.md).

Backup and restore helpers are available in `open_ielts_strategy.knowledge_backup`; backups are unencrypted and must be stored privately with full-disk encryption.

## Free offline evaluation foundations

- **Deterministic writing diagnostics:** `open_ielts_strategy.rule_judge.evaluate_writing` emits reproducible text-feature diagnostics. Its simulated heuristic indices are not IELTS bands, examiner judgments, or validated assessments. See [Rule-based Judge](docs/rule-based-judge.md).
- **Audio input validation:** `open_ielts_strategy.audio.inspect_audio` validates in-memory WAV/MP3 structure, size, and duration without transcription, external dependencies, or network access. It does not prove ASR accuracy. See [Audio Processing](docs/audio-processing.md).
- **Paired Skill Lift audit:** `open_ielts_strategy.skill_lift.compare_skill_lift` pairs Baseline/Skill results by case ID and reports overall/category deltas. Fixture outputs are explicitly simulated and never claim-eligible. See [Skill Lift](docs/skill-lift.md).
- **Calibration audit:** `open_ielts_strategy.calibration_audit.audit_calibration` compares judge versions and produces a deterministic review queue. Optional reference comparisons are descriptive and do not authenticate reviewer qualifications. See [Calibration Audit](docs/calibration-audit.md).

All four helpers are pure Python, offline, and API-key-free. CI tests validate implementation contracts only. Live model judgments, qualified human calibration, educational validity, and claims of learner improvement remain separate gates. The preregistration-first [Independent Educational Validation Protocol](docs/evaluation/independent-validation-protocol.md) defines how extraction fidelity, retrieval relevance, Practice quality, and learner outcomes must be independently assessed.

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

After semantic extraction and review, if you do not want the original transcript retained locally, you can irreversibly purge its raw body while keeping reviewed semantic items searchable:

```bash
python scripts/knowledge.py purge-source-text src_ID --confirm
```

This requires all extracted items to be reviewed. The source hash and offsets remain, but exact source-span re-verification is no longer possible; old backups may still contain the original.

Browse, search, review, and relate cards:

```bash
python scripts/knowledge.py sources
python scripts/knowledge.py search "Writing Task 2 planning"
python scripts/knowledge.py search "speaking fluency" --topic speaking
python scripts/knowledge.py show src_ID
python scripts/knowledge.py review card_ID --status user_approved --note "Useful for my practice"
python scripts/knowledge.py link card_A card_B --relation contradicts --note "Reviewed disagreement"
python scripts/knowledge.py relations --source-id src_ID
python scripts/knowledge.py delete-source src_ID --confirm
```

Use only material you are entitled to import and process. Rights metadata is a declaration, not legal clearance. See [Knowledge Ingestion & Retrieval](docs/knowledge-ingestion.md) for the data model, limitations, acceptance criteria, phases, and parallel work plan. PDF/DOCX parsing, semantic extraction, embeddings, a graphical UI, and educational validation are not part of Phase 1.

## Published Knowledge Pack (v1 foundation)

The repository now includes a dependency-free reader for versioned published Knowledge Packs. A cloned checkout can load approved strategies, concepts, typed relationships, learning paths, and (in manifest schema v1.1) separately reviewed examples, then perform BM25 retrieval without opening the private SQLite library or contacting a model/API provider. Optional cached local sentence-transformer or HTTPS OpenAI-compatible embeddings enable dense/hybrid retrieval; remote calls are explicit and require an environment-backed API key.

The pack contract uses `knowledge/manifest.json`, typed JSON records, and SHA-256 file checksums. Manifest schema v1.0 supports strategies/concepts/relationships/learning paths; v1.1 adds standalone `examples/<skill>/` records with explicit strategy references and separate review/provenance gates. Content approval and publication approval are separate mandatory states. Published provenance excludes private source/extraction IDs, source bodies, transcript text, and private review notes. See [Published Knowledge Pack v1](docs/knowledge/published-knowledge-pack-v1.md) and [ADR-001](docs/architecture/adr-001-published-knowledge-pack.md).

A published-only stdio MCP adapter is available as `ielts-published-knowledge-mcp --pack ./knowledge`. An opt-in Streamable HTTP transport is available via `python -m pip install '.[http-mcp]'` and `ielts-published-knowledge-mcp-http`; it supports static per-subject read-only token registries, Host/optional Origin checks, per-subject rate limits, content-free structured audit events, and optional shared Redis rate limiting via `.[redis-rate-limit]`. It is packaged with a non-root container and localhost-only Compose deployment. Published MCP supports local or explicitly configured HTTPS OpenAI-compatible embeddings. See [HTTP MCP deployment](docs/deployment/published-mcp-http.md) and the [Production Readiness & Operations Runbook](docs/deployment/production-readiness.md). The Kubernetes baseline now includes a dedicated readiness probe and multi-replica/TLS-Redis hardening; a live OIDC gateway, external secret synchronization, durable audit retention, cluster-specific policy validation, and independent penetration testing remain operator acceptance gates. Static tokens are not OIDC, and stdout audit is not durable retention.

The portable-consumption and local publication foundations are implemented. An optional local embedding-based semantic-overlap screen is now a blocking Knowledge Pack build gate when enabled; it supplements exact overlap/secret checks but remains a heuristic, not legal clearance. A persistent public-only index cache is versioned by pack manifest and model fingerprint and is wired into the Practice CLI. Optional local sentence-transformer and HTTPS OpenAI-compatible embedding providers are supported. Opt-in `--query-rewriting` and local `--reranker-model-path` options extend retrieval without changing the deterministic default. Human Practice review and reviewer-agreement reporting are available locally; no human ratings or educational outcomes are claimed. The signed release CLI now supports short-lived human diff/rights attestations, expected-head-protected push to a non-default branch, and revert-based rollback. Distributed HTTP rate limiting, per-user authorization, audit retention, independent legal review, and actual human evaluation remain separate gates.

A local pack builder (`ielts-knowledge-publish`) verifies the private content/publication approvals for source-derived records, checks rights-basis consistency and exact source/secret overlap, optionally adds local semantic-overlap screening with `--semantic-embedding-model-path`, requires explicit human confirmation, and writes a deterministic pack. Git operations are intentionally delegated to the separate signed release command. See the [publishing guide](docs/knowledge/published-knowledge-pack-v1.md).

The `ielts-practice` command can generate an evidence-attributed practice answer from the published pack with either a local Ollama model or an explicitly selected OpenAI-compatible API provider. It refuses to fabricate strategy attribution and makes no model call when no relevant published evidence is found; see [Published Knowledge Pack v1](docs/knowledge/published-knowledge-pack-v1.md).

Knowledge Pack JSON Schemas are meta-validated and cross-reference checked in CI with the optional `schema-validation` extra; the runtime loader itself remains standard-library-only. The optional `ielts-practice-eval` CLI stores private human rubric reviews locally and reports descriptive inter-rater agreement; see [Practice human review](docs/evaluation/practice-human-review.md).

`ielts-knowledge-diff` produces a deterministic, review-only diff between two verified Knowledge Pack revisions; it never commits or pushes. The separate `ielts-knowledge-release` command adds a short-lived HMAC-protected human approval, explicit push confirmation to a non-default release branch, expected-head protection, and a revert-based rollback command. It never merges a PR or bypasses branch protection; see [Knowledge Pack release authorization](docs/release/knowledge-pack-release.md). `open_ielts_strategy.published_index.PublishedIndexStore` caches published record text/vectors in a separate disposable SQLite index. Across pack revisions it retains unchanged per-strategy vectors when the model fingerprint is stable, re-embeds only changed/new records, and prunes removed records. `EnhancedPublishedRetrievalEngine` supports explicit model-assisted query rewriting and local cross-encoder reranking; both are opt-in and bounded. `semantic_publication_scan` provides the local embedding-based source-overlap gate. `ielts-knowledge-benchmark` reports offline retrieval initialization, p50/p95 latency, and throughput without emitting query text or retrieved content.

The `ielts-learning` CLI provides deterministic Study paths plus model-backed Mentor explanations and original-example generation from published strategies. Published MCP exposes Study and standalone published-example lookup by default, and model-backed Mentor/generated-example tools only when a provider and model are explicitly configured.

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

See the [release and public API contract](docs/release.md) for package versioning, supported CLI entry points, license packaging, and release preflight.

## License

The existing MIT license applies to project software code only. Original skill and editorial content is separately reserved unless explicitly licensed; see `LICENSE-CONTENT`. Third-party materials retain their owners' rights. No IELTS endorsement or affiliation is claimed.

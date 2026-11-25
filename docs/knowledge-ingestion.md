# IELTS Knowledge Ingestion & Retrieval

## Purpose

Turn learner-supplied IELTS learning material into a private, source-linked, searchable knowledge base. Inputs may be podcast/video transcripts, personal notes, articles, lecture notes, or book excerpts. A source may discuss any IELTS-related subject; the system must not require the learner to pre-classify every passage.

The product has three layers:

1. **Knowledge acquisition:** import and preserve a source with provenance.
2. **Knowledge management:** segment it, create reviewable candidate cards, tag topics, and maintain explicit human-reviewed relationships and statuses.
3. **Knowledge application:** search passages and use cited source anchors to compare, explain, and assemble study playbooks.

## Goals

- Accept UTF-8 text by paste/stdin or local TXT/Markdown/PDF/DOCX files; PDF support is optional and local.
- Preserve the exact original input locally and calculate a SHA-256 fingerprint.
- Record source type, title, author/speaker, optional HTTPS URL, publication date, language, learner notes, and an explicit rights-status declaration.
- Split text at paragraph and sentence boundaries while retaining exact character offsets and optional transcript timestamps.
- Create one reviewable candidate card per segment; attach deterministic topic tags and a transparent lexical classification.
- Support local lexical search with source title, segment ordinal, character offsets, and timestamp/paragraph locator in every result.
- Let the learner review cards and manually record relationships such as supports, contradicts, duplicates, and supersedes.
- Run without network access, paid APIs, secrets, or non-standard Python dependencies.
- Keep imported material out of Git and public CI artifacts by default.

## Boundaries of the private authoring foundation

- The private authoring library does not automatically publish content. Published Knowledge Pack construction and consumption are separate workflows documented in [Published Knowledge Pack v1](knowledge/published-knowledge-pack-v1.md).
- Optional Ollama and explicitly selected HTTPS OpenAI-compatible extraction/embedding providers exist; they require explicit configuration and must not be treated as a default or silent cloud fallback. Remote embedding credentials are environment-backed and requests are bounded.
- No automatic fact checking, educational validation, or authoritative IELTS strategy classification. Optional semantic extraction produces drafts only.
- No automatic assertion that two cards contradict each other. Similarity is not contradiction.
- No audio transcription, ASR, diarization, OCR, or video downloading. PDF/DOCX parsing is local and text-only; scanned-PDF OCR is unsupported.
- No public dataset or content redistribution.
- No claim that a recommendation improves an IELTS band score.

The first implementation intentionally exposes deterministic lexical extraction as a transparent baseline. It labels passages; it does not understand or endorse them. A later local-model adapter may produce richer summaries and candidate claims, but its outputs must remain drafts with source offsets and human review.

## User workflow

### 1. Add a source

The current entry point is the local CLI. Paste a transcript into standard input or provide a UTF-8 text/Markdown file:

    cat transcript.txt | ielts library ingest - --title "Writing strategy podcast" --type podcast_transcript --author "Presenter" --language en --rights-status personal_copy_unverified

Or:

    ielts library ingest ./notes.md --title "My IELTS notes" --type personal_notes --rights-status self_authored

Supported source types: podcast_transcript, video_transcript, personal_notes, book_excerpt, article, lecture_notes, web_article, and other.

Rights values are declarations, not legal findings: self_authored, permission_confirmed, public_domain, personal_copy_unverified, or unknown. The default is unknown. A rights value never grants permission to publish or redistribute the material.

### 2. What the importer does

1. Validates text and metadata; rejects empty/NUL-containing or over-limit input.
2. Preserves the submitted body without rewriting it and calculates SHA-256.
3. Detects an exact repeat from the same URL and returns the existing source ID instead of creating duplicate records.
4. Splits paragraphs into manageable passages, preferring sentence boundaries for long paragraphs.
5. Records exact character offsets; transcript timestamps at the beginning of a segment are kept as locators.
6. Creates a candidate card for each segment. A small, versioned lexical ruleset labels it as claim, recommendation, question, example, or note, and assigns zero or more topic tags. Unmatched passages are tagged unclassified.
7. Sets every new card to needs_review. No claim is marked correct or supported automatically.

### 3. Review and curate

Inspect a source and its segment/card links:

    ielts library sources
    ielts library show src_ID

Search the local library:

    ielts library search "Writing Task 2 planning"
    ielts library search "speaking fluency" --topic speaking
    ielts library search "time management" --status needs_review

Review an individual card:

    ielts library review card_ID --status user_approved --note "Useful as a personal practice preference."

Record a reviewed relationship:

    ielts library link card_A card_B --relation contradicts --note "The recommendations differ in the planning time they propose."
    ielts library relations --source-id src_ID
    ielts library delete-source src_ID --confirm

A user-approved card means accepted for personal use, not scientifically verified. supported must be used only when the reviewer can record the supporting basis. conflicting records an explicitly reviewed disagreement; the system does not infer contradiction from similar words.

### Purge the original transcript but keep reviewed strategies

After semantic extraction, review every extracted item. If you no longer want the raw transcript retained locally, run:

    ielts library purge-source-text src_ID --confirm

This irreversible operation requires every semantic item to have left `needs_review`. It clears the source body, raw segment text, and generated segment summaries, deletes lexical cards that contain whole passages, and keeps reviewed semantic items, their source IDs/offsets, metadata, and the original SHA-256 fingerprint. It then runs SQLite VACUUM to reduce recoverable remnants in the database file. Semantic items remain searchable. Since the original body is gone, exact text-to-source re-verification is no longer possible; the retained hash and offsets are provenance metadata, not a recoverable copy. Backups made before purging may still contain the transcript and must be handled separately. VACUUM cannot guarantee erasure from SSD wear-leveling, filesystem snapshots, sync history, or other backups.

## Separate publication approval

Semantic item review and publication permission are separate decisions. A content reviewer may mark a candidate `user_approved` or `supported` for learning use; that does not make it publishable. Publication approval is stored in a separate private SQLite table with a reviewer, timestamp, rights-basis declaration, and private note.

```bash
ielts library review-semantic sitem_ID --status user_approved --note "Content reviewed for personal learning"
ielts library review-publication sitem_ID --status approved \
  --reviewer "maintainer" --rights-basis self_authored \
  --note "Authorship and publication permission checked"
```

Publication approval is fail-closed: the semantic item must already have content approval and an explicit rights basis of `self_authored`, `permission_confirmed`, `public_domain`, or `independently_authored`. The source's import-time rights declaration alone is not sufficient. Private review notes and local source identifiers are not exported to a Knowledge Pack. The helper `assert_items_publishable` verifies both gates before a future pack builder can consume source-derived items.

## Outputs

- **Source record:** immutable imported body, SHA-256, metadata, rights declaration, source ID, capture timestamp.
- **Segments:** exact text, ordinal, character offsets, and paragraph/timestamp locator.
- **Candidate cards:** title derived from the first sentence, type, topic tags, extraction-method version, reason for review, and status.
- **Search results:** matching excerpt, card/source IDs, title, author/source URL when supplied, rights declaration, topic tags, and exact segment anchor.
- **Human curation:** review status/note and explicit card-to-card relations. Relations can be listed globally or by source. Deleting a source cascades to its segments, cards, and links involving those cards.

The current first-sentence title is a display label, not an AI summary. Search is lexical, not semantic. The CLI emits JSON so that a future UI or assistant can consume the records without changing the storage contract.

## Data and trust model

### Local storage

The default database is .local/knowledge.sqlite3. The importer creates a private local directory (0700 where supported) and database file (0600 where supported). .local/ and SQLite files are ignored by Git. The body is stored only in this local database; it is not uploaded by the library or added to fixtures. Backups must be treated as private copies too.

Do not point the database at a synchronized/shared folder unless that storage is appropriate for the material. The permissions are best-effort filesystem controls, not encryption at rest. SQLite secure_delete is enabled, but it cannot guarantee removal from filesystem snapshots, SSD wear-leveling areas, backups, or synchronized copies. Use full-disk encryption and secure backups for sensitive material.

### Untrusted content

Imported text is data, never instructions. The importer does not execute shell commands, links, macros, or source-embedded prompts. Any future LLM stage must isolate the source as untrusted quoted data, expose no secrets/tools, constrain output to a schema, and verify each generated claim against exact source spans.

### Copyright and permissions

A URL, attribution, public availability, personal-use intent, or content hash is not permission. The local tool does not determine legal entitlement. Keep third-party excerpts private and only import/process material where the intended use is lawful and permitted. Do not commit transcripts, book passages, restricted material, private permission evidence, or imported learner data. Do not publish source text, card excerpts, derived datasets, or exports without specific rights review and approval.

### Provenance integrity

Each card links to a segment; each segment links to a source. Search results expose source ID and exact character offsets. A future UI should render a stable quote/locator and never remove the provenance trail when cards are edited or combined.

## Data model

- sources: source identity, metadata, body, rights declaration, content hash, captured timestamp.
- segments: source-linked text ranges and locators.
- knowledge_cards: derived candidate type, title, topics, review status and extraction method.
- card_relations: explicitly curated relations between cards.

IDs are opaque. Re-importing the same content from the same source URL is idempotent. A changed source creates a new source record; the foundation does not overwrite old source bodies.

## Review states

| State | Meaning |
|---|---|
| needs_review | Newly imported; no human assessment yet |
| supported | Reviewer recorded an external supporting basis |
| conflicting | Reviewer identified a conflict with another card |
| user_approved | Learner accepts it for their own practice |
| superseded | A reviewed newer recommendation replaces this one |
| rejected | Reviewer rejected it for the intended use |

These states are not a single quality score. Personal preference, source fidelity, evidence quality, and educational validity are different dimensions.

## Acceptance criteria

The foundation is accepted only when all of these hold:

1. Empty, NUL-containing, oversized, malformed, or invalid-metadata input fails closed.
2. Identical input and source URL returns the same source ID; identical text from distinct URLs can remain distinct sources.
3. Original body and SHA-256 are retained, with no normalization that changes source text.
4. Every segment's text equals the exact source substring at its stored offsets.
5. Transcript timestamps and paragraph/segment locators survive ingestion.
6. Every card links to exactly one source segment and starts in needs_review.
7. Classification is deterministic, versioned, and explicitly lexical; no generated band score or validation label is emitted.
8. Search results include source ID, segment ID/card ID, and exact source offsets.
9. Review transitions reject unknown states/IDs; relationships reject self-links, invalid types, missing cards, and duplicates.
10. A close/reopen cycle preserves the source and curation data.
11. The default path makes no network calls and uses only the Python standard library.
12. The default database is ignored by Git and stored with restrictive local permissions where supported.
13. Unit tests cover malformed input, offsets, duplicate behavior, extraction categories, search, provenance, review, relations, and persistence.

## Delivery roadmap

### Phase 1 — private offline foundation (implemented in this change)

- SQLite schema and source metadata contract.
- Text/stdin/file ingestion; content hashing and idempotency.
- Paragraph/sentence segmentation with source offsets and timestamps.
- Deterministic candidate extraction and topic tags.
- Local lexical search and source-linked results.
- Human review states, explicit relationships, relationship browsing, and confirmed source deletion with cascading derived-data cleanup.
- CLI, unit tests, private storage defaults, and operating documentation.

### Phase 2 — richer local extraction (implemented foundation)

- Optional local-model adapter behind a provider-neutral interface.
- Structured outputs: recommendation, procedure, claim, rationale, example, exception, warning, and open question.
- Sentence-level citations, model/prompt/version provenance, confidence as an uncalibrated triage signal, and per-field review.
- Golden fixtures authored independently; measure extraction precision/recall with human annotations.
- Never treat model confidence or repeated claims as truth.

### Phase 3 — retrieval and strategy composition (implemented foundation; advanced published retrieval is in the separate Knowledge Pack layer)

- Local embedding/index adapter with a lexical fallback.
- Hybrid ranking, filters by IELTS skill/task/source/status, and duplicate/overlap suggestions.
- Evidence-linked answers, comparison views, and playbook drafts.
- Explicit contradiction review; never infer contradicts from semantic similarity alone.
- Personal constraints/preferences stored separately from source claims.

### Phase 4 — user experience and richer files (implemented foundation)

- Paste form and local library UI.
- TXT/Markdown first; PDF/DOCX parsing only via vetted local parsers with size/page limits and fixture-based tests.
- Export curated cards without source passages by default.
- Audio remains a separate future capability; file validation is not transcription.
- Encryption-at-rest and backup/restore guidance for private libraries.

### Phase 5 — educational validation (infrastructure exists; independent evidence remains outstanding)

- Independent reviewers annotate source fidelity, classification, and extraction quality.
- Evaluate against curated human-reviewed examples; keep inter-rater agreement separate from correctness.
- Study learner outcomes independently before any skill-lift or band-improvement claims.

## Parallel work groups

These workstreams can be developed concurrently once the interfaces in this document are treated as contracts:

| Group | Scope | Main dependency |
|---|---|---|
| A — source and segment engine | SQLite migrations, source metadata, hash/idempotency, offsets, local privacy | None |
| B — extraction and taxonomy | structured candidate types, topic taxonomy, source-span mapping, deterministic baselines | Segment contract from A |
| C — retrieval and relations | lexical/hybrid indexing, filters, provenance-rich results, overlap suggestions | A data contract; B tags are optional |
| D — CLI and user experience | paste/file import, library browsing, review, compare, export | A–C stable APIs |
| E — security and rights | privacy review, prompt-injection tests, content lifecycle, permission controls | Cross-cutting; can review A–D concurrently |
| F — evaluation and documentation | synthetic fixtures, annotated extraction benchmark, acceptance reports, docs | Contract can be tested alongside A–D |

Recommended execution: start A and B in parallel against shared schemas; C can implement against A's published record shape; E and F review continuously; integrate D after the APIs stabilize. Run independent CI checks while the other groups continue, then run full CI on the integrated branch.

## Current completion boundary

The private authoring library has implemented local ingestion, optional structured extraction, hybrid retrieval, source-grounded playbook foundations, a loopback-only UI, bounded local document parsing, and private extraction-evaluation infrastructure. These capabilities are still a single-user local authoring system, not a hosted multi-user service. The separately published Knowledge Pack, enhanced retrieval, Practice/Study/Mentor learning runtime, and published-only MCP integration are implemented on `main`; see [Published Knowledge Pack v1](knowledge/published-knowledge-pack-v1.md) and [roadmap](roadmap.md). Educational effectiveness, qualified independent ratings, legal rights clearance for specific content, ASR/OCR, cloud sync, federated identity, and production operations are not implied by those implementations.


## Optional advanced local workflows

- Structured extraction: see [Semantic Extraction](semantic-extraction.md). It is opt-in, loopback-only, exact-span validated, and always needs human review.
- Hybrid search: see [Hybrid Retrieval](hybrid-retrieval.md). It falls back to lexical retrieval and uses only pre-installed local model weights when configured.
- Comparison and playbook drafts: see [Strategy Playbooks](strategy-playbooks.md). Every step preserves source offsets and selection order; no conflicting advice is silently reconciled.
- Paste-first UI and local documents: see [Local UI and Documents](local-ui-and-documents.md). The UI is loopback-only; parser limits apply.
- Extraction evaluation: see [Knowledge Evaluation](knowledge-evaluation.md). Synthetic tests measure code behavior, not educational validity.


## Model-generated private Strategy Drafts

After semantic extraction, inspect items with:

```sh
ielts library --db .local/knowledge.sqlite3 semantic-items <SOURCE_ID>
ielts library --db .local/knowledge.sqlite3 review-semantic <ITEM_ID> --status user_approved
```

Generate a draft only after reviewing the semantic items:

```sh
ielts knowledge-draft --db .local/knowledge.sqlite3 \
  --source-id <SOURCE_ID> \
  --strategy-id speaking.direct-answer \
  --skill speaking \
  --provider ollama --model <LOCAL_OLLAMA_MODEL>
```

For a remote provider, explicitly select `--provider openai-compatible`; the API
key is read from `OPENAI_API_KEY` (or the environment variable named by
`--api-key-env`). Remote generation sends the reviewed semantic-item text to
the selected HTTPS endpoint. Do not use it for material that must remain local.

The generated file is written under `.local/strategy-drafts/` with restrictive
best-effort permissions. It contains a private source/item mapping and a
`needs_human_review` state. The model receives reviewed item content without
private database identifiers. Draft generation does not change either review
state, does not infer publication rights, and cannot build or publish a pack.
A human must inspect and edit the strategy, then complete the independent
content and publication review workflow before any publication build.

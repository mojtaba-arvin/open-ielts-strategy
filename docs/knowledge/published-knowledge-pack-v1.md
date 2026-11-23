# Published Knowledge Pack v1

The private SQLite library remains an authoring workspace. Published knowledge is a separate, portable artifact in Git. A consumer must be able to clone the repository and load this pack without the owner's database, transcript files, extraction history, Ollama, or API credentials.

## Canonical layout

```text
knowledge/
  manifest.json
  strategies/
    speaking/
    writing/
    reading/
    listening/
  concepts/
  relationships/
  learning-paths/
schemas/
  strategy.schema.json
  concept.schema.json
  relationship.schema.json
  learning-path.schema.json
```

The v1 loader accepts strategy, concept, typed relationship, and learning-path JSON records. Every record is listed in the manifest; unlisted files and symlinks are rejected. The canonical manifest uses JSON to keep the consumer dependency-free and checksum inputs deterministic.

## Manifest

Each file entry is relative to the pack root and includes its SHA-256 digest:

```json
{
  "format": "open-ielts-knowledge-pack",
  "schema_version": "1.0",
  "pack_version": "0.1.0",
  "files": [
    {
      "path": "strategies/speaking/answer-development.json",
      "sha256": "<64 lowercase hexadecimal characters>"
    }
  ]
}
```

The manifest is an integrity index, not a signature. Consumers must trust the Git revision or another authenticated distribution channel that supplied it.

## Strategy record

A strategy has stable identity, a strategy-level semantic version, applicability, reasoning, limitations, examples, typed relationships, public provenance, and two independent approvals. The loader rejects unknown/missing fields, unsupported schema versions, invalid relationships, checksum mismatches, path traversal, symlink entries, private provenance fields, and any record without both approvals.

Published provenance must not include private `source_id`, `extraction_id`, source text, transcript text, local paths, or private review notes. A source hash or offset is not a substitute for publication permission and is not part of the public contract.

## Consume locally

```python
from open_ielts_strategy.knowledge_pack import load_knowledge_pack

pack = load_knowledge_pack("knowledge")
strategy = pack.get_strategy("speaking.answer-development")
matches = pack.search_strategies("describe a memorable journey", skill="speaking")
```

No private database, network, extraction provider, embedding model, or LLM is imported by the loader API. Its convenience search is deterministic lexical matching; the separate PublishedRetrievalEngine adds BM25 and optional dense cosine fusion without requiring the private SQLite library.

Before writing the staged pack, the builder scans all serialized published records against retained private source bodies (or retained semantic source spans when the body was purged) and checks common credential patterns. It blocks detected long exact overlaps and secret-like values. This is a heuristic leak detector, not a proof of non-disclosure, a semantic paraphrase detector, or legal clearance; the maintainer must still inspect the diff and confirm rights.

## Local pack build and publication gate

After authoring strategy JSON drafts in private local storage, build a pack with explicit maintainer confirmation:

```bash
ielts-knowledge-publish \
  --strategy .local/drafts/speaking.answer-development.json \
  --destination ./knowledge \
  --version 1.0.0 \
  --confirm-human-review
```

For source-derived records, map each record to its private semantic item IDs with repeated `--source-item RECORD_ID=SITEM_ID` arguments. The command checks content approval, separate publication approval, and a matching rights basis in the private SQLite database. Private IDs, reviewer notes, and source text are not included in the generated pack. The builder writes a new directory only, verifies the staged pack, and refuses to overwrite an existing destination. It does not create a Git commit or push. Review the resulting file diff separately, then use the distinct signed release workflow in [Knowledge Pack release authorization](../release/knowledge-pack-release.md) if you explicitly intend to publish.

The `--confirm-human-review` flag is an explicit operator attestation, not an automated legal determination. Rights metadata and model-generated content are never treated as self-approving. For an additional local semantic-overlap gate during the build, install `.[local-embeddings]` and pass `--semantic-embedding-model-path /path/to/cached/model`. The builder then compares candidate records with retained private source text/spans and blocks above-threshold embedding matches. It reports source IDs and offsets only. This is a heuristic similarity screen, not a guarantee against paraphrase leakage or legal clearance.

Retrieval defaults to in-memory BM25 and works without an embedding model. For local dense/hybrid retrieval, install `.[local-embeddings]` and pass an existing on-disk sentence-transformer directory with `--embedding-model-path /path/to/cached/model` to either `ielts-practice` or `ielts-published-knowledge-mcp`. The adapter uses `local_files_only=True`; it will not download model weights. The default hybrid fusion is BM25 plus cosine similarity. `PublishedIndexStore` can persist public-only document text/vectors in a separate SQLite cache; its identity includes the pack manifest digest and embedding-model fingerprint, and stale identities must be rebuilt. The Practice CLI can use that cache for repeat runs: `EnhancedPublishedRetrievalEngine` accepts optional query-rewriter and reranker adapters, but neither is enabled unless explicitly injected.

```bash
ielts-practice "How can I structure a direct answer?" --pack ./knowledge \
  --provider ollama --model qwen3:8b \
  --embedding-model-path /path/to/cached/model \
  --index-db .local/published-index.sqlite \
  --embedding-model-fingerprint sentence-transformers/model-name@revision
```

For opt-in model-assisted query expansion and local cross-encoder reranking, add `--query-rewriting` and/or `--reranker-model-path /path/to/cached/cross-encoder`. Query rewriting uses the explicitly selected Practice generation provider and requires a valid JSON array response; it does not silently fall back. If the provider is an API service, the learner query is sent to that service. The cross-encoder loads only from the supplied local model directory. Both are optional; the deterministic baseline remains BM25/hybrid retrieval.
 Use a stable fingerprint that identifies the exact local model revision; changing either the pack manifest or model fingerprint triggers a rebuild. The index contains only published strategy text and vectors, never private source or learner data. Remote embedding providers and production benchmark calibration remain future work.

## Study, Mentor, and Example workflows

Use the curated learning paths without a model, or explicitly select a model for teaching and original example generation:

```bash
ielts-learning study --pack ./knowledge --skill speaking
ielts-learning mentor --pack ./knowledge --strategy-id speaking.answer-development \
  --provider ollama --model qwen3:8b
ielts-learning example --pack ./knowledge --strategy-id speaking.answer-development \
  --task "Describe a useful skill" --provider ollama --model qwen3:8b
```

The Mentor and Example commands consume only the published pack. Example generation checks for long exact overlap with existing examples; this does not prove semantic originality. The published MCP server exposes `get_learning_path` and `create_study_plan` without a model. Configure `--provider` and `--model` on the MCP command to expose `explain_strategy` and `generate_strategy_example` tools as well.

The builder also accepts repeated `--concept`, `--relationship`, and `--learning-path` draft files. All record types are validated, cross-references are checked, and source-derived records can be mapped to private review items with `--source-item RECORD_ID=SITEM_ID`. All records are included in the same manifest and checksummed build.

## Review the publication diff

Compare the current public pack with a newly built candidate before any Git operation:

```bash
ielts-knowledge-diff --current ./knowledge --candidate ./.local/candidate-knowledge
```

The command verifies both packs, emits deterministic added/modified/removed record diffs with exact pack versions and manifest digests, and blocks candidate content containing common secret-like values. It is review output only: it does not create a commit, push, or release. A separate human review is mandatory. The diff scanner cannot compare against private source bodies; that check occurs during the local pack build. After approval, `ielts-knowledge-release` can create a short-lived signed approval, commit/push only the pack to a release branch with expected-head protection, and create a revert commit for rollback. It does not merge PRs. The standalone `python -m open_ielts_strategy.semantic_publication_scan` command remains available for pre-build diagnostics; the same scanner can now be enabled as a blocking optional gate directly in `ielts-knowledge-publish` with `--semantic-embedding-model-path`. Both report source IDs and offsets, never matched text. They are heuristic signals, not proof of semantic non-disclosure or legal clearance.

## Published Knowledge MCP (stdio)

Install the optional MCP dependency and run the published-only adapter against a checked-out pack:

```bash
python -m pip install '.[mcp]'
ielts-published-knowledge-mcp --pack ./knowledge
```

The server exposes `search_strategies`, `get_strategy`, `get_related_strategies`, `get_concept`, `get_learning_path`, and `create_study_plan`. When a provider and model are explicitly configured, it also exposes `answer_ielts_question`, `explain_strategy`, and `generate_strategy_example`. It loads and verifies the pack at startup and returns the pack version and manifest digest with results. It does not import the private SQLite store or expose private ingestion/review tools. Restart the server after changing the checked-out pack. The stdio adapter remains the simplest local integration. An opt-in authenticated Streamable HTTP deployment is available with `python -m pip install '.[http-mcp]'` and `ielts-published-knowledge-mcp-http`. It requires `IELTS_MCP_BEARER_TOKEN` (32+ characters), validates Host and optional Origin, applies an in-memory per-IP token bucket, and is packaged in `Dockerfile.published-mcp` plus `compose.published-mcp.yml`. See [HTTP MCP deployment](../deployment/published-mcp-http.md). The Compose configuration binds to host loopback only. Public deployment still requires a TLS reverse proxy, restricted direct network access, distributed rate limiting, per-user identity/authorization, and a security review.

## Contract validation

The repository validates every JSON Schema against the Draft 2020-12 meta-schema and resolves cross-schema references in CI:

```bash
python -m pip install '.[schema-validation]'
python scripts/validate_knowledge_schemas.py
```

The runtime pack loader remains standard-library-only; `jsonschema` is a development/validation extra, not a consumer dependency.

## Practice against published knowledge

A portable practice answer can be generated from the published pack without opening the private SQLite library:

```bash
ielts-practice "How can I give a direct answer?" --pack ./knowledge \
  --skill speaking --provider ollama --model qwen3:8b
```

Choose `--provider openai-compatible` and configure the API key environment variable to use a remote model. This sends the retrieved public pack context and learner question to that service. The CLI does not silently switch providers. If retrieval finds no evidence, it returns without making a model call. Generated attribution IDs are checked against the retrieved strategy IDs, and every result carries the exact pack version and manifest digest.

## Governance boundary

Loading validates structure and integrity. It does not grant rights, certify IELTS advice, or authorize publication. The publication workflow must independently enforce human content approval, rights approval, private-data leakage checks, deterministic build validation, diff review, and explicit maintainer authorization before commit/push.

## Practice review and calibration

Generated outputs can be registered and reviewed locally with `ielts-practice-eval --db .local/practice-reviews.sqlite`. Use `register`, `review`, and `report` subcommands; the rubric covers task relevance, evidence grounding, clarity, actionability, and factual safety. The report gives descriptive reviewer agreement only. See [Practice human review](../evaluation/practice-human-review.md). No human ratings, examiner equivalence, band calibration, or educational outcomes are implied.

## Offline retrieval latency benchmark

Run an aggregate, local-only latency benchmark against the current published pack:

```bash
ielts-knowledge-benchmark --pack ./knowledge --iterations 10 --warmup 3
```

For repeatable hybrid runs, supply a JSON array of queries, an already-cached local embedding model or the optional HTTPS OpenAI-compatible provider, and optionally the persistent public index cache:

```bash
ielts-knowledge-benchmark --pack ./knowledge \
  --queries-json ./.local/retrieval-queries.json \
  --embedding-model-path /path/to/cached/model \
  --index-db .local/published-index.sqlite \
  --model-fingerprint sentence-transformers/model-name@revision \
  --iterations 20 --warmup 5 --output ./.local/retrieval-benchmark.json
```

The report includes pack/model identity, engine/index initialization time, mean/p50/p95/max search latency, and throughput. It never includes query text or retrieved content. This measures runtime performance only; it does not measure ranking relevance, educational quality, or learner outcomes. Use a representative, rights-cleared local query set and compare results across the same machine/model configuration.

## Standalone reviewed examples (manifest schema 1.1)

An example is a separately versioned, reviewed record linked to exactly one strategy. Its contract is in `schemas/example.schema.json`; the record includes `strategy_id`, `skill`, the task, example content, strategy application, learning note, public provenance, two approval states, and its own record version. The builder checks that the referenced strategy exists and that the skill matches.

Pass one or more reviewed example JSON drafts with `ielts-knowledge-publish --example ./drafts/example.json`. Retrieve a published example by ID with `ielts-learning get-example --pack ./knowledge --example-id speaking.example.direct-answer-01` or the published MCP `get_example` tool. Supplying at least one example produces a manifest with `schema_version: "1.1"`; packs without standalone examples remain schema 1.0. Source-derived examples must pass the same private rights/publication approval mapping as other records. Unreviewed model output is not automatically accepted or published. The diff and release workflow includes standalone example additions, changes, and removals, and published MCP exposes `get_example`.

The alternative remote configuration uses `--embedding-provider openai-compatible --embedding-model-name text-embedding-3-small --embedding-api-key-env OPENAI_API_KEY` and, when using the persistent cache, a matching stable `--model-fingerprint`. The remote provider requires HTTPS, reads its credential only from the environment, disables redirects, bounds input/response sizes, and uses bounded retries. It sends the published pack text and search queries to the configured provider; choose this only when that data transfer is acceptable.

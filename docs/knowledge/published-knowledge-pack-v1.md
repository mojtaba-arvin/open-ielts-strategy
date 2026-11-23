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
schemas/
  strategy.schema.json
```

The v1 loader currently accepts a pack directory with `manifest.json` and strategy JSON files. The canonical manifest uses JSON to keep the consumer dependency-free and checksum inputs deterministic.

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

No private database, network, extraction provider, embedding model, or LLM is imported by this API. Search is deterministic lexical matching in v1; hybrid retrieval and answer generation are separate layers.

Before writing the staged pack, the builder scans serialized strategy records against retained private source bodies (or retained semantic source spans when the body was purged) and checks common credential patterns. It blocks detected long exact overlaps and secret-like values. This is a heuristic leak detector, not a proof of non-disclosure, a semantic paraphrase detector, or legal clearance; the maintainer must still inspect the diff and confirm rights.

## Local pack build and publication gate

After authoring strategy JSON drafts in private local storage, build a pack with explicit maintainer confirmation:

```bash
ielts-knowledge-publish \
  --strategy .local/drafts/speaking.answer-development.json \
  --destination ./knowledge \
  --version 1.0.0 \
  --confirm-human-review
```

For source-derived records, map each record to its private semantic item IDs with repeated `--source-item RECORD_ID=SITEM_ID` arguments. The command checks content approval, separate publication approval, and a matching rights basis in the private SQLite database. Private IDs, reviewer notes, and source text are not included in the generated pack. The builder writes a new directory only, verifies the staged pack, and refuses to overwrite an existing destination. It does not create a Git commit or push; review the resulting file diff separately.

The `--confirm-human-review` flag is an explicit operator attestation, not an automated legal determination. Rights metadata and model-generated content are never treated as self-approving.

Retrieval defaults to in-memory BM25 and works without an embedding model. For local dense/hybrid retrieval, install `.[local-embeddings]` and pass an existing on-disk sentence-transformer directory with `--embedding-model-path /path/to/cached/model` to either `ielts-practice` or `ielts-published-knowledge-mcp`. The adapter uses `local_files_only=True`; it will not download model weights. The current hybrid fusion is BM25 plus cosine similarity; learned reranking and incremental persistent indexes remain future work.

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

The builder also accepts repeated `--concept`, `--relationship`, and `--learning-path` draft files. All record types are validated, cross-references are checked, and source-derived records can be mapped to private review items with `--source-item RECORD_ID=SITEM_ID`. Concepts and learning paths are included in the same manifest and checksummed build.

## Published Knowledge MCP (stdio)

Install the optional MCP dependency and run the published-only adapter against a checked-out pack:

```bash
python -m pip install '.[mcp]'
ielts-published-knowledge-mcp --pack ./knowledge
```

The server exposes `search_strategies`, `get_strategy`, `get_related_strategies`, `get_concept`, `get_learning_path`, and `create_study_plan`. When a provider and model are explicitly configured, it also exposes `answer_ielts_question`, `explain_strategy`, and `generate_strategy_example`. It loads and verifies the pack at startup and returns the pack version and manifest digest with results. It does not import the private SQLite store or expose private ingestion/review tools. Restart the server after changing the checked-out pack. This v1 adapter supports stdio; authenticated Streamable HTTP remains a separate deployment task.

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

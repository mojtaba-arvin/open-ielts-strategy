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

## Published Knowledge MCP (stdio)

Install the optional MCP dependency and run the published-only adapter against a checked-out pack:

```bash
python -m pip install '.[mcp]'
ielts-published-knowledge-mcp --pack ./knowledge
```

The server exposes only `search_strategies`, `get_strategy`, and `get_related_strategies`. It loads and verifies the pack at startup and returns the pack version and manifest digest with results. It does not import the private SQLite store, expose private ingestion/review tools, or contact a model. Restart the server after changing the checked-out pack. This v1 adapter supports stdio; authenticated Streamable HTTP remains a separate deployment task.

## Governance boundary

Loading validates structure and integrity. It does not grant rights, certify IELTS advice, or authorize publication. The publication workflow must independently enforce human content approval, rights approval, private-data leakage checks, deterministic build validation, diff review, and explicit maintainer authorization before commit/push.

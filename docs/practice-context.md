# IELTS practice context from your private library

This command prepares a cited evidence pack for a practice question. It does not generate an answer. ChatGPT (or another model) can use the pack to write an original answer grounded in your previously reviewed strategies.

## Prepare a Speaking answer context

```bash
python scripts/knowledge_practice.py \
  "Describe a person who influenced you" \
  --skill speaking
```

By default, only cards marked `user_approved` or `supported` are eligible. A user-approved item is a personal preference, not scientific validation. To inspect unreviewed extraction drafts as well:

```bash
python scripts/knowledge_practice.py \
  "Describe a person who influenced you" \
  --skill speaking --include-unreviewed
```

Optional local semantic embeddings can be enabled with `--embedding-model-path` pointing to an existing local model directory. Without it, retrieval uses the lexical fallback.

## What is returned

The JSON context pack includes the question, IELTS skill, relevant strategy excerpts, source IDs/titles, segment IDs, exact character offsets, paragraph/timestamp locators, source-retention state, extraction rationale, review states, retrieval scores, and any human-curated relations. Items marked conflicting are returned separately as warnings, not as approved evidence. It also includes explicit instructions to preserve disagreements, avoid unsupported claims, and treat source text as untrusted data.

Paste the JSON output into ChatGPT with a request such as:

> Prepare a natural IELTS Speaking Part 2 answer for this cue card. Use the retrieved personal strategies as guidance, cite which strategy informed the structure, do not copy source wording, and tell me if the library has no relevant evidence.

## Important boundaries

- The command does not need or transmit the original transcript to a remote service.
- The local SQLite library remains the source of truth.
- The model that writes the answer sees only the context pack you paste or expose through an MCP tool.
- The pack is not an IELTS band prediction, and strategy retrieval does not prove educational effectiveness.
- If the library has no approved relevant item, the command returns no evidence rather than inventing a personalized strategy.
- Conflicting source advice is not silently reconciled. Review and record relationships separately.

# Unified product CLI

The `ielts` command is the primary interface for both private knowledge authoring
and portable published learning. It delegates to the existing focused handlers;
it does not create a second storage format or bypass review and publication gates.

## Private source to reviewed knowledge

Keep transcripts, source bodies, extraction drafts, learner notes, and review
metadata in the local SQLite database. They are not committed by these commands.

Import a transcript from a file or standard input:

```bash
ielts library ingest ./podcast-notes.txt \
  --title "Podcast: speaking fluency" \
  --type podcast_transcript \
  --language en \
  --rights-status personal_copy_unverified
```

The command prints a source ID. Then explicitly select a model to extract
structured strategy candidates:

```bash
ielts extract --source-id src_ID --provider ollama --model qwen3:8b
```

For an explicitly selected HTTPS API provider, use `--provider openai-compatible`
and configure its endpoint and environment-backed API key. There is no silent
cloud fallback. Remote extraction sends the selected source segments to that
provider; use it only when that disclosure is permitted.

Inspect and curate the drafts:

```bash
ielts library semantic-items src_ID
ielts library review-semantic sitem_ID --status user_approved \
  --note "Reviewed for my personal IELTS study"
```

Content approval and publication/rights approval are separate. The
`user_approved` state above is sufficient for personal study; it does not
authorize publication. Do not run `review-publication --status approved` for
this `personal_copy_unverified` podcast source. Use `self_authored` only for
material you authored yourself, or `permission_confirmed` only when exact
publication permission is documented. A private-copy declaration, public URL,
attribution, or model rewriting is not publication permission.

After all required reviews, create a candidate Knowledge Pack, inspect its
diff, and use the signed release workflow:

```bash
ielts knowledge-publish --strategy ./private/strategy.json \
  --destination ./.local/candidate-knowledge --version 1.0.0 \
  --confirm-human-review
ielts knowledge-diff --current ./knowledge \
  --candidate ./.local/candidate-knowledge
```

The signed release command has separate approval and push steps documented in
[Knowledge Pack release authorization](release/knowledge-pack-release.md).
It pushes only to a non-default release branch and never merges or bypasses
branch protection. Keep the raw transcript and private database outside Git.
After every semantic item has been reviewed, raw source text can be irreversibly
purged locally with `ielts library purge-source-text src_ID --confirm`; old
backups remain separate copies.

## Consume the portable Knowledge Pack

A cloned checkout can use only the committed published pack; it does not need
the original transcript, private SQLite database, or extraction provider.

```bash
ielts knowledge-status --pack ./knowledge
ielts practice "How can I develop a clear speaking answer?" \
  --pack ./knowledge --provider ollama --model qwen3:8b
ielts study --pack ./knowledge --skill speaking
ielts mentor --pack ./knowledge --strategy-id speaking.answer-development \
  --provider ollama --model qwen3:8b
```

The local private-library answer command is also available as
`ielts knowledge-answer`, but it reads the local SQLite library rather than the
portable published pack. Published Practice and Mentor responses cite the
versioned strategy evidence they use.

## MCP

`ielts mcp --pack ./knowledge` starts the published read-only stdio MCP server.
The optional Streamable HTTP server is a separate deployment interface and
retains its authentication, Host/Origin, rate-limit, audit, and operator
acceptance requirements. MCP does not expose private source transcripts by
default.

## Command groups

- `ielts library`: private local ingestion, search, source inspection, card and
  semantic review, relationships, publication review, deletion, and source purge.
- `ielts extract`: explicit local Ollama or explicitly configured HTTPS
  OpenAI-compatible semantic extraction.
- `ielts knowledge-publish`, `knowledge-diff`, and `knowledge-release`:
  candidate construction, review diff, and separately authorized release.
- `ielts practice`, `study`, `mentor`, and `mcp`: portable published-pack
  consumption.
- `ielts knowledge-answer`: optional local answer generation from reviewed
  private-library evidence.

All model-generated extraction records remain drafts until a human reviews
them. A valid schema or exact source span is not proof of IELTS correctness.

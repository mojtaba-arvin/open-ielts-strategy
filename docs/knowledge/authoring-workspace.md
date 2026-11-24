# Knowledge Pack authoring workspace

The repository intentionally does not ship a default approved IELTS content
pack. Use the unified CLI to initialize a private authoring workspace:

```bash
ielts knowledge-init --workspace .local/knowledge-authoring
```

The destination must not already exist. The command creates:

- `README.md` with the human review and publication workflow
- `.gitignore` entries for local databases, approvals, and private source files
- `drafts/strategy.template.json` with the required strategy record structure

On POSIX systems the workspace directory is created with owner-only access
(`0700`) and files with owner read/write access (`0600`). The command refuses
to overwrite an existing path and removes a partially created workspace if
initialization fails.

## Why the template is deliberately invalid

The template contains explicit placeholders, a non-selected provenance basis,
and `content_status=draft` / `publication_status=pending`. It is not a published
record and cannot pass the Knowledge Pack publication validator. This is
intentional: the tool must not manufacture provenance or mark content approved.

For every record, an authorized reviewer must:

1. Replace all placeholders with original, evidence-based, learner-appropriate
   content.
2. Choose a truthful provenance basis. A public URL is evidence of origin, not
   permission to reproduce the material.
3. Complete content review and publication/rights review separately.
4. For source-derived records, map the public record ID to private reviewed
   semantic item IDs through repeated `--source-item RECORD_ID=SITEM_ID`
   arguments. Private IDs and source text must not enter the public record.
5. Build a candidate pack into a new directory, validate it, inspect the
   complete diff, and obtain the separate release approval before publishing.

Example candidate build (after the reviews are genuinely complete):

```bash
ielts knowledge-publish \
  --strategy .local/knowledge-authoring/drafts/strategy.json \
  --destination .local/candidate-knowledge \
  --version 1.0.0 \
  --confirm-human-review
```

The flag is an explicit maintainer attestation, not a legal determination.
Source-derived records additionally require the private SQLite approval gate.
See [Published Knowledge Pack v1](published-knowledge-pack-v1.md) and
[Knowledge Pack release authorization](../release/knowledge-pack-release.md).

## Capability adapter status

Run `ielts adapter-status` to inspect installed entry points for document
ingestion, knowledge extraction, audio transcription, hybrid retrieval, and
response evaluation. Discovery does not import provider code, make network
requests, or choose a provider. See [Adapter availability](adapter-availability.md).

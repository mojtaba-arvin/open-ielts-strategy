# ADR-001: Published Knowledge Pack is the portable source of truth

- Status: Accepted for the v1 foundation
- Date: 2026-11-23

## Context

The existing SQLite library is a private knowledge-engineering workspace. It stores learner-supplied source bodies, extraction drafts, review notes, and operational state. Those records must not become a runtime dependency of a cloned/public installation.

## Decision

1. Private SQLite remains the source of truth for private ingestion, extraction, provenance verification, and human review.
2. A versioned Knowledge Pack committed to Git is the source of truth for published knowledge.
3. Consumers load only a pack from a local filesystem checkout. The v1 loader has no database, network, model, or extraction dependency.
4. Pack records carry content approval and publication approval as separate mandatory states.
5. Published provenance is intentionally sanitized: it may describe the basis and public references, but may not expose private source IDs, extraction IDs, source bodies, review notes, or private paths.
6. JSON is the canonical v1 serialization for the manifest and records. It is deterministic, natively supported by Python's standard library, and avoids making YAML a runtime dependency. Human-authored YAML may be added later as an authoring format, but must normalize to the same canonical JSON bytes before hashing.
7. The manifest contains a SHA-256 checksum for every published strategy file. A checksum proves integrity relative to the manifest, not authorship, educational correctness, or legal permission.

## Consequences

- Fresh environments can consume published knowledge without a private database or Ollama.
- A pack can be reviewed and diffed in Git at the strategy-file level.
- Schema compatibility and semantic quality remain separate checks.
- A valid pack is not automatically safe to publish: the future publication command must still enforce rights review, leak detection, and explicit human approval before writing Git changes.
- The initial loader supports strategy JSON files only. Concepts, relationships, examples, and learning paths are added through compatible schema revisions and loader extensions rather than implicit acceptance.

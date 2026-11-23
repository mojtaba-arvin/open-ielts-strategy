# Calibration diff and audit pipeline

`open_ielts_strategy.calibration_audit.audit_calibration` compares two or more versioned judge scorecards offline. Each scorecard carries a canonical judge version, a SHA-256 rubric fingerprint, unique item IDs, and four integer dimension scores in [1, 9].

## Audit behavior

- Pairwise comparisons use intersecting item IDs and report exact agreement, mean absolute difference, maximum difference, and changed item IDs per dimension.
- Any per-item dimension difference meeting the configurable threshold (default 2 points) is added to a deterministic review queue.
- Optional human-reference comparison requires explicit reviewer, timestamp, method, and dimension labels. The tool reports provenance as supplied; it does not authenticate qualifications or reviewer identity.
- Missing overlap, duplicate IDs, invalid scores, malformed provenance, and duplicate judge-version/rubric combinations fail closed.

## Acceptance and interpretation

The audit is deterministic, offline, and has no API dependency. A fixture-only report is marked `simulated-audit`. Agreement is not accuracy; disagreement only identifies review candidates. A human reference is useful only when collected under a documented process by qualified reviewers. No synthetic fixture or self-reported provenance can establish examiner equivalence, model validity, or educational benefit.

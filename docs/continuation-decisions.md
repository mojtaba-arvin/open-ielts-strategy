# Continuation decisions and acceptance boundaries

This file records durable product decisions so future contributors and sessions do not
re-open settled questions or infer completion from repository mechanics.

## Product priority

Prioritize operational predictability, safe first use, recoverability, and evidence-backed
acceptance over adding another feature layer. Prefer changes that can be verified in CI
without private learner data, external services, paid model calls, or fabricated evidence.

## Data and trust boundaries

- `library`, `extract`, `knowledge-draft`, `knowledge-promote`, and
  `knowledge-answer` operate on the private local authoring database.
- `practice`, `practice-evaluate`, `study`, `mentor`, `mentor-chat`, and `mcp`
  consume the published Knowledge Pack. Optional `--session-db` flags persist
  learner attempts locally; they are not a dependency for pack consumption.
- `knowledge-publish`, `knowledge-diff`, and `knowledge-release` bridge
  authoring and publication only through separate, explicit human review and release gates.
- `preflight` must preserve the author/consumer separation. Consumer readiness must
  not depend on a private database; author readiness must not require an already-published pack.
- Never print API secrets, private transcripts, learner prompts, reviewer notes, or private IDs
  into public artifacts, CI logs, or published records.

## Non-negotiable evidence gates

- Do not invent IELTS educational content, source permissions, reviewer identities,
  approvals, human ratings, participant outcomes, or production evidence.
- Synthetic fixtures are software wiring tests only; they are not IELTS quality evidence.
- No IELTS band prediction, examiner equivalence, positive skill lift, or effectiveness
  claim without the independent validation protocol and qualified evidence.
- A deployment template, local preflight, passing CI, or a security unit test is not
  a live production deployment or operational acceptance.
- Third-party content may be processed or published only with documented rights for
  the exact use. Public availability, attribution, or a personal-copy declaration is
  not permission.

## External acceptance gates (tracked in issue #109)

1. **First real Knowledge Pack:** learner/maintainer supplies original or rights-cleared
   source material; a human reviews strategy correctness and clarity; publication rights
   are independently established; candidate diff and leakage checks are reviewed; signed
   release evidence is recorded.
2. **Independent educational validation:** qualified independent raters, representative
   rights-cleared cases, preregistered evaluation, blinded ratings, agreement analysis,
   and privacy-reviewed outcome evidence.
3. **Production operations:** operator-owned OIDC gateway and bypass prevention, external
   secret sync, managed Redis TLS/ACL, cluster-enforced NetworkPolicy/egress checks,
   durable audit retention, immutable image/pack pairing, rollback/load/soak/failure
   drills, independent penetration testing, and on-call ownership.

These are genuine external dependencies, not missing GitHub permission. Continue all
independent code, documentation, test, and CI work while they are pending.

## CI and branch hygiene

- Run focused tests locally/through the repository's test workflow while iterating; run
  the full required CI once a coherent PR is ready for review.
- Do not merge until required status checks pass and the reviewed head SHA is unchanged.
- Delete a feature branch only after its PR is merged or intentionally abandoned and
  no follow-up depends on it. Never delete a branch merely to tidy the branch list.
- Keep main protected; do not weaken rulesets or bypass review/status requirements.

## Private authoring UI trust copy

- The local authoring UI must say that rights status is self-reported metadata, not legal clearance. Public release still requires documented permission for the exact processing and redistribution use plus a separate human publication review.
- Private card/semantic review statuses are curation workflow states only; they are not educational validation or publication approval.
- Never make a UI label or checkbox imply that the system has independently verified ownership, copyright permission, or educational correctness.

## CLI error context

When a command returns a non-zero status or its argument parser exits with an error,
the unified CLI must append the command's data-scope boundary to stderr. Successful
commands and `--help` output must remain unchanged. Keep this scope map aligned with
`docs/product-cli.md` and the individual command handlers.

## Loopback authoring UI Host validation

- The private authoring UI must bind only to `127.0.0.1`; do not expose it through a LAN bind, tunnel, reverse proxy, or public host.
- Validate the complete HTTP Host authority. Accept only the exact loopback hostnames `127.0.0.1` and `localhost`, optionally followed by a valid TCP port. Reject malformed/empty/out-of-range ports, userinfo, paths, query/fragment components, and all other hostnames.
- Do not use prefix checks or split-on-colon parsing for Host validation; malformed authorities can otherwise pass a naive loopback check.
- Host validation is not authentication and does not make this single-user UI safe for network exposure. Keep CSRF and same-origin checks in place.

## Kubernetes validation boundary

- `scripts/validate_kubernetes_manifest.py` is a static template regression check, not
  proof that a rendered deployment is accepted or enforced by a live cluster/CNI.
- Keep it fail-closed for host namespaces, hostPath mounts, seccomp, resource bounds,
  service/ingress wiring, and narrow ingress/egress policy. Add regression tests for
  every security invariant that can be checked without cluster access.
- `scripts/validate_rendered_kubernetes_manifest.py` validates a rendered artifact
  against a local operator-owned profile: namespace, ingress namespace, hostname,
  OIDC auth URL, Redis TLS CIDRs, and immutable image digest. Its profile must remain
  non-secret and outside Git; its JSON contract is in
  `schemas/kubernetes-cluster-profile.schema.json`.
- The rendered validator is an artifact consistency check only. It does not contact
  Kubernetes, prove admission policy behavior, verify CNI enforcement, validate
  certificate issuance, test OIDC bypass resistance, or establish operational acceptance.
  Those remain operator-owned deployment and evidence gates.
- Validate operator profile namespace values as Kubernetes DNS labels, the service hostname as a lowercase DNS subdomain, and OIDC URLs without credentials/query/fragment or malformed ports.
- Redis egress profiles must be private unicast ranges and no broader than IPv4 /16 or IPv6 /32. This is a conservative profile guard, not proof that the cluster routes or enforces those ranges.
- Keep regression cases in `tests/test_rendered_kubernetes_profile.py`; the regular unit-test discovery job executes them. The validator must continue to avoid reading secret values or contacting the cluster.

## Document import resource bounds

- TXT/Markdown reads stop at one character beyond `MAX_EXTRACTED_CHARS`; file SHA-256 uses `hashlib.file_digest` rather than a second whole-file allocation.
- PDF extraction must guard `Tj`, `TJ`, single-quote, and double-quote text operands through `visitor_operand_before`, then guard decoded output with `visitor_text`. Use a private `BaseException` sentinel so pypdf's broad nested-XObject `except Exception` cannot swallow the abort. Keep tests proving an oversized text operator aborts before page extraction completes and later pages are not touched. This does not bound pypdf's earlier decompression of the content stream itself.
- DOCX remains a local ZIP/XML parser with entry-count, uncompressed-size, and extracted-character bounds. Do not add generic archive extraction, OCR, remote fetching, or third-party ingestion as part of parser hardening.
- These bounds are resource controls, not an independent parser security audit.

## Backup and restore boundary

- `open_ielts_strategy.knowledge_backup` uses SQLite's online backup API and checks
  database integrity; tests must cover committed WAL data as well as ordinary files.
- Backups contain private source text and review data, are **not encrypted**, and must
  stay on encrypted, access-controlled storage outside Git. Never claim a backup is
  secure merely because its file mode is restrictive.
- Restore only to a new destination. Inspect the restored library before an explicit
  operator switches the active database. Integrity checks are necessary, not sufficient
  proof of a successful application-level recovery.
- The recovery runbook documents a manual local procedure. Scheduling, off-site copies,
  retention, ransomware protection, and measured RPO/RTO remain unimplemented.

## Next product work

1. Continue private-library recovery, parser robustness, malformed/large archive tests,
   PDF edge cases, and usability work.
2. Improve retrieval evaluation ergonomics for caller-supplied, rights-cleared judgments,
   while keeping quality thresholds unset until independent reviewers establish them.
3. Continue CI coverage and operator-facing examples for rendered Kubernetes profile
   validation.
4. Reassess OCR, ASR, cloud sync, crawling, and public hosting only through separate
   threat, rights, privacy, and product decisions; they are not implicit roadmap commitments.


## Retrieval evaluator input safety

- The published-retrieval judgment CLI must read at most 5 MiB plus one detection byte from its caller-supplied JSON file; reject larger files before decoding or parsing. This is a CLI transport/resource bound, separate from the evaluator's existing 10,000-case and per-field validation.
- Reject an output path whose resolved path equals the judgment input, including symlink aliases, before loading the Knowledge Pack or writing any report. Never risk destroying the caller's private judgments.
- The relevance map is already bounded by the selected pack's finite strategy ID set: every key must be a known strategy ID and dictionary keys are unique. Do not add an arbitrary independent judgment-count cap unless a measured pack-size or memory risk justifies one.
- Keep judgment files and learner/reviewer data outside Git. These safeguards do not create representative judgments, quality thresholds, or IELTS educational evidence.

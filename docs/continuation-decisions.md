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

## CLI error context

When a command returns a non-zero status or its argument parser exits with an error,
the unified CLI must append the command's data-scope boundary to stderr. Successful
commands and `--help` output must remain unchanged. Keep this scope map aligned with
`docs/product-cli.md` and the individual command handlers.

## Next product work after CLI scope/help

1. Add safe operational acceptance tooling that validates rendered deployment artifacts
   against an operator-supplied cluster profile without pretending to validate a live cluster.
2. Improve retrieval evaluation ergonomics for caller-supplied, rights-cleared judgments,
   while keeping quality thresholds unset until independent reviewers establish them.
3. Continue private-library recovery, backup/restore, parser robustness, and usability work.
4. Reassess OCR, ASR, cloud sync, crawling, and public hosting only through separate threat,
   rights, privacy, and product decisions; they are not implicit roadmap commitments.

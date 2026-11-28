# Evidence-gated code PR review and merge

The implementer may self-review and merge their own code PR when the exact-head evidence is complete. Self-review is not independent peer review, and no reviewer identity or approval may be fabricated.

## Merge prerequisites

- Intended base and merge-base freshness are recorded.
- The complete diff, dependency changes, workflow permissions, security/privacy impact, and content-rights impact are reviewed.
- Repository validation, offline unit tests, skill/evaluation validation, and all required CI checks pass on the exact PR head SHA.
- Any relevant positive, negative, and boundary tests are included.
- Material review threads are resolved or explicitly documented as accepted limitations.
- The branch is mergeable under the actual GitHub rules.

The implementer may author the review record and merge when these conditions pass. Independent specialist review may be requested for high-risk code changes but is not a universal approval gate. GitHub does not permit the PR author to submit a formal APPROVE review. Never bypass branch protection, rulesets, required checks, or merge queues.

## Domain gates that remain mandatory

This policy changes only code-PR review and merge. It does not waive:
- documented rights/permission for source-derived content;
- qualified human content review and explicit publication authorization;
- legal clearance for the exact redistribution/use;
- learner consent and privacy obligations;
- independent educational validation and human outcome studies before effectiveness/Skill Lift claims;
- external security, deployment, or production acceptance.

A green CI run or merged PR is not evidence that these domain gates passed. Keep the claim registry default-deny and preserve all official-content, answer-key, transcript, licensed-material, personal-data, and paid-model restrictions.

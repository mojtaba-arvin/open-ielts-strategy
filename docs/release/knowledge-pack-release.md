# Knowledge Pack release authorization

The local pack builder deliberately stops before Git operations. This separate command implements a two-step maintainer-controlled release and rollback path.

## 1. Review and approve

First inspect the full diff yourself:

```bash
ielts-knowledge-diff --current ./knowledge --candidate ./.local/candidate-knowledge
```

Set a local approval HMAC key once in a secret manager or private shell environment (never commit it):

```bash
export IELTS_PUBLICATION_APPROVAL_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Create a short-lived approval only after checking the diff and rights basis:

```bash
ielts-knowledge-release approve \
  --current ./knowledge \
  --candidate ./.local/candidate-knowledge \
  --approval-file .local/knowledge-release-approval.json \
  --reviewer maintainer-id \
  --confirm-diff \
  --confirm-rights
```

The approval file is HMAC-protected, written with owner-only permissions, bound to the current and candidate manifest digests plus canonical diff digest, and expires after 24 hours. It contains no source text. A changed candidate or current pack invalidates the approval.

## 2. Publish to a release branch

The worktree must be clean, the checked-out branch must match the selected non-default release branch, and HEAD must match the explicitly reviewed SHA:

```bash
git rev-parse HEAD
ielts-knowledge-release publish \
  --repo . \
  --candidate ./.local/candidate-knowledge \
  --target knowledge \
  --approval-file .local/knowledge-release-approval.json \
  --branch release/knowledge-pack-1.1.0 \
  --expected-head <full-40-character-head-sha> \
  --confirm-publish
```

The command validates the candidate again, stages only the configured Knowledge Pack directory, creates a local commit, and pushes with an expected-remote-head lease. It refuses to push directly to `main` or `master`; open a normal reviewed pull request from the release branch. If the push fails after the local commit, the commit and matching worktree are intentionally preserved so the operator can inspect and retry; the tool does not silently discard the commit.

## 3. Roll back a published pack commit

Rollback creates a new revert commit; it never rewrites history:

```bash
git rev-parse HEAD
ielts-knowledge-release rollback \
  --repo . \
  --commit <published-commit-sha> \
  --branch release/knowledge-pack-1.1.0 \
  --expected-head <current-full-head-sha> \
  --target knowledge \
  --confirm-rollback
```

Only single-parent commits whose changed paths are entirely inside the configured Knowledge Pack directory are eligible. Rollback also uses an expected-head lease. Resolve conflicts manually; no force push or automatic history rewrite is performed.

## Security boundaries

- The approval HMAC key is a local maintainer secret; it is not an identity provider or a digital signature verifiable by third parties.
- The reviewer and confirmation flags are explicit operator attestations, not automated legal clearance.
- The candidate must already have passed the local builder's private approval and leakage checks.
- The release command does not merge a pull request or bypass branch protection.
- Git push requires a configured remote and credentials; no credentials are stored by the project.
- Protect the approval file and private candidate directory. Keep both out of Git.

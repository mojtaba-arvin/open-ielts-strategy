# Commit identity and attribution policy

For maintainer-directed AI-assisted implementation, use Git author `Mojtaba Arvin <m.arvin@live.com>` only when GitHub attributes that exact author email to the `mojtaba-arvin` account. The repository's current PR commit metadata confirms that association; the check does not expose or require account email settings. Do not use model, assistant, AI-agent, Copilot, Claude, Cursor, Codex, Gemini, generic agent, or bot identities as the author. Do not add bot/AI `Co-authored-by` trailers.

Include `<!-- maintainer-directed-ai-work -->` in the PR body for owner-authorized AI-assisted work. This machine-readable marker requires at least one maintainer-authored commit and validates every commit attributed to `mojtaba-arvin` against the exact maintainer name/email; other human contributor identities remain unchanged. Disclose AI assistance in the PR description; the marker does not claim the maintainer personally typed every line.

Preserve every real human contributor's original author name/email. Never relabel another person as the maintainer and never rewrite historical commits.

Genuine GitHub Actions/Dependabot commits are exceptional, not a general bot allowance. They require the explicit `allow-automation-commits` PR label and matching GitHub Bot author **and committer** accounts with the canonical noreply addresses below. The author and committer must be the same approved automation identity. This rejects a bot author paired with a human committer and rejects unknown bot identities. The exception does not cover agent-written implementation. Bot co-author trailers remain prohibited. A `web-flow` committer is distinct from the commit author and does not change author attribution.

| Automation account | Required author and committer email |
| --- | --- |
| `github-actions[bot]` | `41898282+github-actions[bot]@users.noreply.github.com` |
| `dependabot[bot]` | `49699333+dependabot[bot]@users.noreply.github.com` |

Convenience defaults (not enforcement):

```sh
git config --global user.name "Mojtaba Arvin"
git config --global user.email "m.arvin@live.com"
```

`scripts/check_commit_identity.py` checks all PR commits, rejects bot/agent authors and bot co-author trailers, validates the separate committer identity, requires the narrowly allowlisted automation author/committer/email combination plus explicit label, and enforces the maintainer identity when the marker is present. It also compares the live PR head with the workflow event's exact head SHA and fails closed if the PR moved during validation.

The `Commit identity` workflow uses no GitHub token, no secrets, and no write permissions; it checks out the public PR head and reads public commit metadata without authentication. This follows this repository's prohibition on `pull_request_target` workflows. Configure this check as required in branch protection/rulesets where governance permits; a workflow alone does not block merges.

Git metadata and GitHub account association are evidence of attribution, not proof of who physically typed code or a cryptographic attestation that a bot workflow generated a commit. The explicit label is an additional maintainer-controlled gate, not proof by itself. Review automation provenance when applying it. The validator cannot detect every disguised agent identity. Disclose AI assistance transparently.

Never amend, rebase, or cherry-pick a contributor's work under the maintainer identity. Preserve the contributor's original author fields and add a separate maintainer-authored commit for AI-assisted changes.

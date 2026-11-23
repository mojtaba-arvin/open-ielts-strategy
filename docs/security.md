# Security and prompt-injection threat model

## Assets
Repository write access, private permission evidence, credentials, learner data, evaluation integrity, provenance records, and release artifacts.

## Threats
Prompt injection embedded in source/user text; malicious links or scripts; secret exfiltration through prompts/logs/artifacts; poisoned evaluation cases; unauthorized publication of copyrighted or personal material; dependency/workflow compromise.

## Controls
- Treat retrieved, source, and learner text as data, never trusted instructions.
- Keep secrets out of prompts, fixtures, public logs, and CI artifacts.
- Use least-privilege GitHub Actions permissions; pin third-party actions to reviewed immutable SHAs before production hardening.
- Never execute code or shell commands supplied by source content.
- Do not fetch arbitrary URLs in CI.
- Keep private rights evidence outside Git.
- Require human review for rights status, skill behavior, and release.
- Use synthetic fixtures and sanitise learner data.
- Review dependency and workflow changes.

## Incident response
For suspected rights/privacy incidents, stop publication, preserve minimal incident metadata, restrict affected artifacts, notify maintainers, and seek legal guidance. For credential exposure, revoke/rotate immediately and inspect logs/artifacts.


## Workflow input and injection boundaries

All third-party actions are pinned to full commit SHAs. Workflows must declare explicit least-privilege permissions and must not use `pull_request_target` to execute untrusted pull-request code. Third-party source crawling remains manual-only. Values originating from a matrix, dispatch input, issue, or repository metadata must be passed through step environment variables and quoted as shell variables; do not interpolate untrusted values directly into a `run:` script. Regression tests enforce these invariants for the current workflow set.


## Local knowledge library

The knowledge importer stores learner-supplied text only in an ignored local SQLite database. It makes no network requests and never executes commands, links, markup, macros, or instructions found in source text. The database and source text must not be uploaded to CI artifacts, issues, logs, or public fixtures. File permissions are best-effort and are not encryption; use disk encryption and private backups.

Any future LLM extraction or retrieval stage must keep source text in a data-only context, deny source-controlled tool execution and secret access, require schema-constrained output, and attach every generated item to a verifiable source span. Generated recommendations remain untrusted drafts until human review.

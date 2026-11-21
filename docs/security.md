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

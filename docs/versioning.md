# Versioning and drift management

Skills use Semantic Versioning independently of the repository package:
- Patch: wording/examples without intentional routing or behavior changes.
- Minor: backward-compatible capability addition.
- Major: breaking trigger, output-contract, or behavior change.

Every released skill version is recorded in `skills.lock`. Evaluation cases are versioned with the skill and reviewed for leakage. Source updates do not silently rewrite skills: provenance, rights, and behavioral drift are checked separately.

## Drift signals
Track source last-verified timestamps, skill/eval changes, failing cases, routing changes, and environment-contract changes. A stale source record moves to `under_review` or `expired`; it must not silently remain cleared.

## Rollback
Keep the last known-good skill version and evaluation suite. Revert skill and lockfile together. If rights status changes, stop using affected content and remove it from future releases; investigate repository history and distribution obligations with counsel.


## Python dependency contract

The runtime package intentionally has no third-party runtime dependencies. The project supports Python 3.11 and later. The PEP 517 build backend is setuptools constrained to the supported major-version window (`>=68,<82`) so a future incompatible major release cannot silently alter the build. CI installs the package with `--no-deps` to verify packaging without adding runtime packages. GitHub Actions are pinned to full commit SHAs, and Agent Skill versions remain explicit SemVer entries in `skills.lock`.

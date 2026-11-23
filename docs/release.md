# Release gate and public claims

The release workflow supports a manual pre-publication run against a candidate SemVer tag and also runs automatically when a version tag is pushed. Run it manually against the candidate tag, wait for every check to pass, and only then publish the GitHub release. The tag-push run is a second audit after the tag exists; it cannot prevent someone from creating a tag. The release preflight now requires the candidate tag to match both `project.version` in `pyproject.toml` and `open_ielts_strategy.__version__`, validates every declared console-script target, and verifies that the software license, separate content notice, and NOTICE are included in package metadata.

The claim registry is default-deny. Official IELTS band prediction, examiner equivalence, positive Skill Lift, educational effectiveness, guaranteed score improvement, and blanket third-party content clearance are explicitly not established and cannot be stated as public project claims. A future claim may be enabled only after independent evidence is recorded with a reviewer, method, scope, sample count, timezone-aware review timestamp, and evidence references. The validator checks the completeness of that evidence record; it does not independently verify the evidence or establish legal/educational validity.

A passing release workflow proves the repository's declared gates passed. It does not prove IELTS score accuracy, learner improvement, examiner equivalence, or copyright clearance beyond the exact permission metadata recorded.


## Public package API boundary

The current stable Python-level package contract is intentionally limited to `open_ielts_strategy.__version__`. The supported developer-facing entry points are the console commands declared in `pyproject.toml` and the documented MCP transports. Internal module functions and classes are currently importable but are not yet promised as a semver-stable Python SDK. The release preflight checks that every declared console command resolves to a real module and callable. A separately versioned Python API should be declared only with dedicated public API documentation and compatibility tests; do not infer stability from an import path alone.

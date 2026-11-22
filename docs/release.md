# Release gate and public claims

The release workflow supports a manual pre-publication run against a candidate SemVer tag and also runs automatically when a version tag is pushed. Run it manually against the candidate tag, wait for every check to pass, and only then publish the GitHub release. The tag-push run is a second audit after the tag exists; it cannot prevent someone from creating a tag.

The claim registry is default-deny. Official IELTS band prediction, examiner equivalence, positive Skill Lift, educational effectiveness, guaranteed score improvement, and blanket third-party content clearance are explicitly not established and cannot be stated as public project claims. A future claim may be enabled only after independent evidence is recorded with a reviewer, method, scope, sample count, timezone-aware review timestamp, and evidence references. The validator checks the completeness of that evidence record; it does not independently verify the evidence or establish legal/educational validity.

A passing release workflow proves the repository's declared gates passed. It does not prove IELTS score accuracy, learner improvement, examiner equivalence, or copyright clearance beyond the exact permission metadata recorded.

# Optional LLM judge protocol

Default repository checks do not call a model. The judge is a separate, opt-in execution layer.

## Implemented mechanics

- Live runtime evaluation pairs baseline and skill outputs by case ID and verifies identical input hashes.
- The judge scores explicit rubric dimensions and validates a structured response schema with evidence rationales.
- Generation and judging require separately configured credentials and an explicitly configured judge model distinct from the generation model.
- Live request budgets are bounded; fixture mode is the default for pull requests, schedules, and ordinary manual runs.
- Judge prompts explicitly treat supplied task content, cases, rubrics, essays, and feedback as untrusted data. Prompt-injection regression tests cover the judge path.
- Synthetic calibration data contains 20 distinct original responses across Writing Task 1 and Task 2. Human scores are null until actual trusted ratings are supplied.
- Calibration tooling accepts ratings only from an explicitly selected trusted GitHub account with an eligible repository association, rejects ambiguous duplicate ratings, and reports undefined statistical cases honestly.

## What these mechanics do not establish

- Fixture-mode output is not a model evaluation and cannot establish Skill Lift.
- A live model-judge score is not ground truth, an official IELTS band, an examiner score, or evidence of examiner equivalence.
- No independent human calibration result exists until qualified independent ratings are actually collected.
- A synthetic corpus is a software test fixture, not a representative sample of IELTS candidates or official test material.
- Passing schema, security, and unit tests establishes implementation behavior only, not educational validity.

## Safe operation

Keep live runs opt-in and budget-bounded. Do not send third-party IELTS questions, official test material, candidate answers belonging to others, copyrighted passages, recordings, transcripts, paid-preparation content, or confidential learner data to a model. Use only independently authored synthetic inputs or learner-provided material for which the user has authority to request processing. Do not add source content to the repository. Never claim legal clearance, official band prediction, guaranteed score improvement, or examiner equivalence from judge output.

For any release-blocking educational conclusion, require qualified human review and independently documented evidence. Human calibration remains a separate gate, not something synthetic fixtures can replace.


## Judge-to-judge disagreement

The optional pure-Python helper `open_ielts_strategy.judge_analysis.analyze_judge_disagreement` compares two or more independently produced judge scorecards. It intersects item IDs, reports exact agreement, mean absolute score difference, and maximum difference separately for each rubric dimension and model pair, and rejects malformed/duplicate records. It does not call a model, infer which judge is correct, or treat agreement as accuracy. Use it only with scorecards produced under documented model and prompt versions; it is descriptive analysis, not human calibration.


## Deterministic non-LLM diagnostic judge

The separate `open_ielts_strategy.rule_judge.evaluate_writing` helper uses only local text features and fixed thresholds. It is not a substitute for this optional model-judge protocol: its simulated heuristic indices are not IELTS bands, examiner judgments, or validated rubric scores. See [Rule-based Judge](rule-based-judge.md).

## Offline calibration audit

`open_ielts_strategy.calibration_audit.audit_calibration` compares versioned scorecards without model calls. It provides descriptive disagreement metrics and a review queue. It cannot establish judge accuracy, examiner equivalence, or educational validity. See [Calibration Audit](calibration-audit.md).

# Optional LLM judge protocol

Default repository checks do not call a model. A judge is a separate reproducible layer.

- Pin provider, model identifier/version, prompt hash, rubric version, decoding settings, and dataset revision.
- Pair baseline and skill outputs by case ID; blind/randomize presentation where practical.
- Score explicit rubric dimensions, not vague overall impressions.
- Calibrate against human-reviewed gold examples before using scores for release decisions.
- Track agreement, disagreement, false positives/negatives, tokens, latency, and estimated cost.
- Keep judge inputs free of secrets and restricted source material.
- Require human review for borderline and release-blocking results.
- Never describe judge scores as official IELTS bands or ground truth.

Current status: rubric-bearing synthetic cases and comparison of externally generated result files exist. No LLM provider adapter, judge execution, or calibration is implemented yet.

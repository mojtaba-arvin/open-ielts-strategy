# Human calibration protocol

The repository includes 20 original synthetic calibration responses. They are fixtures, not human ratings or examiner exemplars. Maintainers submit one issue comment per rated item containing a JSON object with item_id and four integer ratings from 1 to 9. Example:

{"item_id":"cal-01","task_response":6,"coherence_cohesion":6,"lexical_resource":5,"grammar_accuracy":6}

Only comments with valid IDs and all four scores are consumed. The workflow requires explicit live-run dispatch and a bounded item-call budget. The judge uses JUDGE_API_KEY and JUDGE_MODEL independently from the agent model. Spearman correlation is reported only with at least three matched human ratings; a deterministic bootstrap 95% interval is emitted at n >= 10. Small samples are descriptive, not validation of examiner equivalence.

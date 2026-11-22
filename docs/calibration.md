# Human calibration protocol

The repository includes 20 original synthetic calibration responses. They are fixtures, not human ratings or examiner exemplars.

Submit one issue comment per rated item on the dedicated calibration issue or pull request. Each comment must contain a JSON object with an item ID and four integer ratings from 1 to 9:

{"item_id":"cal-01","task_response":6,"coherence_cohesion":6,"lexical_resource":5,"grammar_accuracy":6}

For a live run, dispatch the **Judge calibration** workflow with the exact issue or pull-request number containing the ratings, the repository owner as the trusted rater, and an item-call budget from 1 to 20. The workflow reads comments only from that one issue or pull request. The script accepts ratings only when both the GitHub author association is `OWNER` and the comment author's login matches the repository owner. Comments from other accounts, malformed scores, unknown item IDs, and duplicate valid ratings for an item are excluded; duplicate ratings make that item ambiguous and therefore unusable.

The workflow requires explicit live-run dispatch and a bounded item-call budget. The judge uses JUDGE_API_KEY and JUDGE_MODEL independently from the agent model. Spearman correlation is reported only with at least three matched human ratings; a deterministic bootstrap 95% interval is emitted at n >= 10. Small samples are descriptive, not validation of examiner equivalence.

# Human calibration protocol

The repository includes 20 original synthetic calibration responses. They are fixtures, not human ratings or examiner exemplars.

Submit one issue comment per rated item on the dedicated calibration issue or pull request. Each comment must contain a JSON object with an item ID and four integer ratings from 1 to 9:

{"item_id":"cal-01","task_response":6,"coherence_cohesion":6,"lexical_resource":5,"grammar_accuracy":6}

For a live run, dispatch the **Judge calibration** workflow with the exact issue or pull-request number containing the ratings, the exact GitHub login of the explicitly trusted human rater, and an item-call budget from 1 to 20. The workflow reads comments only from that one issue or pull request. The live dispatch requires the exact GitHub login of a trusted human rater. The script accepts ratings only when the comment author's login matches that configured account and the GitHub author association is `OWNER`, `MEMBER`, or `COLLABORATOR`. For independent calibration, configure a qualified reviewer/collaborator other than the repository owner; do not treat self-ratings as independent examiner agreement. Comments from other accounts, malformed scores, unknown item IDs, and duplicate valid ratings for an item are excluded; duplicate ratings make that item ambiguous and therefore unusable.

The live sample is selected deterministically by round-robin task stratification, so a budget of at least two includes both Task 1 and Task 2 when both groups are available; the previous corpus-order bias is removed. A budget of one cannot represent both task types.

The workflow requires explicit live-run dispatch and a bounded item-call budget. The judge uses JUDGE_API_KEY and JUDGE_MODEL independently from the agent model. Spearman correlation is reported only with at least three matched human ratings and non-constant score vectors; zero-variance vectors are reported as undefined rather than being mislabeled as zero correlation. A deterministic bootstrap 95% interval is emitted at n >= 10 only when at least 800 of 1,000 resamples yield a defined estimate. Small samples are descriptive, not validation of examiner equivalence.


## Multiple independent raters

For inter-rater analysis, pass a comma-separated allowlist of exact GitHub logins through the workflow's trusted-rater input (for example, `examiner-a,examiner-b`). Every account must be explicitly trusted and have an accepted repository author association. Ratings remain partitioned by account; they are never pooled into one pseudo-rater. The report computes pairwise quadratic weighted Cohen kappa on items rated by both accounts, separately for each rubric dimension. It reports the number of paired items and leaves the statistic undefined when the expected weighted disagreement is zero. The mean across available pairs is descriptive and is not a fully crossed multi-rater reliability model.

When more than one trusted rater is supplied, judge-to-human Spearman correlation is intentionally not collapsed across raters. Inter-rater agreement and judge agreement answer different questions and remain separate. The existing bootstrap interval for judge-to-human Spearman is only computed in the single-rater mode with at least ten paired ratings and enough valid resamples.

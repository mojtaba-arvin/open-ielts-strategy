# Semantic routing and conflict resolution

## MVP router
Offline lexical routing uses IELTS task vocabulary and learner-draft signals. Task 1/Task 2 plus a draft selects ielts-writing-feedback. An IELTS draft without a clear task selects it at lower confidence and the skill should clarify. Speaking, Listening, and Reading never select the Writing skill. Unknown intent returns no skill. This is deterministic lexical routing, not an embedding or LLM classifier.

## Conflict resolution
Candidates require skill_id, integer priority, confidence in [0,1], and ISO-8601 validated_at. Winner order: (1) higher priority; (2) higher confidence; (3) more recent validation timestamp; (4) lexicographically smaller skill ID. Missing metadata or invalid confidence fails closed. Incompatible output contracts are not silently merged; the selected skill contract is authoritative and conflicts are surfaced for maintainer review.

## Limitations
Only one Writing skill exists. Confidence is a rule score, not a calibrated probability. Add semantic models only after a labeled routing benchmark exists.

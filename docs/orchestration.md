# Semantic routing and conflict resolution

## MVP router
Offline lexical routing uses IELTS task vocabulary and learner-draft signals. Task 1/Task 2 plus a draft selects ielts-writing-feedback. An IELTS draft without a clear task selects it at lower confidence and the skill should clarify. Speaking, Listening, and Reading never select the Writing skill. Unknown intent returns no skill. This is deterministic lexical routing, not an embedding or LLM classifier.

## Conflict resolution
Candidates require a non-empty string skill_id, an exact integer priority (booleans are not integers here), a finite JSON number confidence in [0,1] (booleans and numeric strings are rejected), and a non-empty timezone-aware ISO-8601 validated_at that can be normalized within Python’s UTC datetime range. Timestamp ordering compares instants in UTC. Winner order: (1) higher priority; (2) higher confidence; (3) more recent validation timestamp; (4) lexicographically smaller skill ID. Missing or malformed metadata fails closed. Incompatible output contracts are not silently merged; the selected skill contract is authoritative and conflicts are surfaced for maintainer review.

## Limitations
Only one Writing skill exists. Confidence is a rule score, not a calibrated probability. Add semantic models only after a labeled routing benchmark exists.

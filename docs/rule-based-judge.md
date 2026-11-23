# Deterministic writing diagnostics

`open_ielts_strategy.rule_judge.evaluate_writing` is an offline, deterministic diagnostic helper. It extracts observable text features (word, paragraph and sentence counts, lexical variety, sentence-length variation, transition markers, and simple punctuation-format signals) and maps them to bounded heuristic indices for the four familiar writing dimensions.

## Contract and acceptance

- Same text and task produce byte-for-byte equivalent JSON-compatible values.
- No network, model, credential, external corpus, or optional dependency is used.
- Empty/non-text inputs are rejected; scores are integers in [1, 9].
- Output status is `simulated-heuristic`; the overall value is named `overall_heuristic_index`.
- Evidence contains measurable features and output includes explicit limitations.

## Non-claims

This is not an IELTS band score, official assessment, examiner simulation, or validated rubric implementation. Text-only heuristics cannot reliably assess task fulfillment, reasoning quality, semantic coherence, grammar correctness, or spoken performance. Do not use the values for learner placement, progress claims, or release claims. Human review and independent validation are separate requirements.

Run offline tests with `python -m unittest tests.test_rule_judge` or the repository-wide unittest discovery command.

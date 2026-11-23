# Learner State and Practice Evaluation

This guide documents the local learner workflow built on top of a published Knowledge Pack. All state is local by default; there is no hosted learner account service in this package.

## Study progress

Study can remain stateless, with completion IDs supplied on each invocation. For durable local progress, opt in to a SQLite database and a stable learner scope:

```bash
ielts study --pack ./knowledge --skill speaking \
  --state-db .local/learner-state.sqlite --learner-id local-profile
```

Mark a path complete explicitly, then recalculate prerequisite availability:

```bash
ielts study --pack ./knowledge --skill speaking \
  --state-db .local/learner-state.sqlite --learner-id local-profile \
  --complete-path speaking.foundations
```

The command rejects unknown path IDs. Completions are keyed by learner ID and Knowledge Pack version, so progress for a new pack version is a distinct scope. Completion means only that the learner marked the path complete; it does not imply mastery, proficiency, or an inferred outcome.

## Mentor conversations

Use the same database with a stable learner ID to continue a bounded conversation for a published strategy:

```bash
ielts mentor-chat --pack ./knowledge \
  --strategy-id speaking.answer-development \
  --message "How can I add a relevant example?" \
  --provider ollama --model qwen3:8b \
  --state-db .local/learner-state.sqlite --learner-id local-profile
```

History is isolated by learner ID, Knowledge Pack version, and strategy ID. The most recent bounded turns are loaded before generation and the new learner/mentor pair is stored only after a successful response. The CLI does not combine caller-supplied `--history-json` with persisted state. Without `--state-db`, Mentor remains stateless and accepts caller-supplied history.

## Practice response evaluation

Generating a model-written example answer and evaluating a learner's own answer are separate workflows. Submit the exact task and learner response:

```bash
ielts practice-evaluate --pack ./knowledge --skill writing \
  --question "Some people believe public transport should be free. Discuss both views." \
  --answer "Your own response goes here." \
  --provider ollama --model qwen3:8b \
  --session-db .local/practice.sqlite
```

The evaluator retrieves published strategies before making a model call. If no relevant evidence is found, it returns `no-published-evidence` and does not call the provider. Successful feedback contains criterion-level observations, strengths, next steps, rubric version, Knowledge Pack version and digest, and strategy attribution. Structured output is validated before being returned or stored.

The criterion ratings are descriptive 1–5 formative indicators, not IELTS bands, examiner judgments, or calibrated scores. Speaking feedback is text-only and does not assess pronunciation, accent, pace, or audio delivery. Reading/listening feedback does not assert correctness without an approved answer key. No overall band or total score is generated.

When `--session-db` is supplied, the learner response and structured assessment are persisted in the existing Practice SQLite schema. The database file is restricted to owner read/write permissions on POSIX systems. Treat the database as private learner data and protect backups accordingly.

## Privacy and lifecycle

- `--state-db` and `--session-db` are opt-in; no network synchronization is implemented.
- Use a stable, non-sensitive local learner identifier; it is a local partition key, not an authenticated identity.
- Keep SQLite databases and backups out of Git and shared CI artifacts.
- Study completion is a learner-declared event, not a mastery signal.
- LLM-generated formative feedback is not independent educational validation.

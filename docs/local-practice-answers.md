# Fully local IELTS practice answers

The private library can optionally generate a practice answer using a local Ollama model. This is separate from the context-pack command and does not use ChatGPT, the OpenAI API, or any remote endpoint.

## Example

Make sure Ollama is running and the model is already installed. Check exact model names with `ollama list`, then run:

```bash
python scripts/knowledge_answer.py \
  "Describe a person who has influenced your life" \
  --skill speaking \
  --model YOUR_INSTALLED_MODEL
```

The installed console command is also available after `pip install -e .`:

```bash
ielts-knowledge-answer "Describe a person who has influenced your life" --skill speaking --model YOUR_INSTALLED_MODEL
```

By default, only `user_approved` and `supported` items are used. If no eligible evidence is retrieved, the command does not call the model and returns `no-approved-evidence`. Use `--include-unreviewed` only when you explicitly want draft material included.

## Data flow

1. Search the private SQLite library for relevant reviewed semantic items.
2. Build a bounded context pack with exact source IDs, offsets, review states, conflicts, and source-retention state.
3. Send only that context pack and the question to the local Ollama process on loopback.
4. Return the generated answer plus its evidence context.

The original transcript is not sent to the model after raw-source purge; only retained extracted items are used. The model output is not a validated IELTS band or examiner judgment. Keep source excerpts as untrusted data and review the result before using it.

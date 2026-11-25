# Optional local semantic extraction

The baseline lexical extractor remains the default. This optional module defines a provider-neutral contract and an explicit Ollama adapter for a model already installed on the same machine. It makes no request unless a caller constructs the adapter and invokes it.

## CLI

```bash
ielts extract --source-id src_ID --model qwen3:8b
```

This explicitly invokes the local Ollama service at `127.0.0.1:11434`. The model must already be installed. A remote endpoint is rejected. The command persists draft items and prints their IDs and provenance metadata.

## Safety and data contract

- The adapter accepts only plain HTTP loopback endpoints; remote hosts are rejected.
- The source is marked as untrusted data in the prompt. It cannot authorize tools, shell commands, network access, or policy changes.
- Output is schema-checked, bounded, and each item must match the exact original source substring at its Python character offsets.
- Supported draft types: recommendation, procedure, claim, rationale, example, exception, warning, open_question.
- Every accepted item is `needs_review`; schema/span validation does not validate factual or educational correctness.
- The persistence pipeline stores provider/model/prompt versions and maps segment-local offsets back to exact absolute offsets in the original source. Semantic items are separate from the original lexical cards.
- The model may hallucinate offsets; failed span checks reject the item.

## Explicit remote API provider

The extraction CLI also supports an OpenAI-compatible Chat Completions endpoint. Remote processing is opt-in and sends the selected private source segment to that provider; use it only when the source may lawfully be disclosed to that service.

```bash
export OPENAI_API_KEY="..."
ielts extract --source-id src_ID \
  --provider openai-compatible --model YOUR_API_MODEL
```

The adapter requires HTTPS, reads the credential only from the named environment variable, bounds source and response sizes, uses structured JSON output, retries only bounded transient failures, and runs the same exact source-span validation as the local adapter. It does not print or persist the API key. Override the endpoint with `--endpoint` only for a trusted HTTPS-compatible service. Configure another secret variable with `--api-key-env`.

The default remains local Ollama. There is no implicit provider fallback: a selected provider failure is reported rather than silently sending private text to a different service.

## Python API

```python
from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.semantic_extraction import OllamaLocalProvider
from open_ielts_strategy.knowledge_pipeline import extract_source, list_semantic_items

with KnowledgeStore() as store:
    provider = OllamaLocalProvider(model="qwen3:8b")
    source_id = "src_..."  # an already imported local source
    extract_source(store, source_id, provider, provider_name="ollama",
                   model_name="qwen3:8b", prompt_version="extract-v1")
    items = list_semantic_items(store, source_id)
```

List and review the extracted items without exposing the original transcript in Git:

```bash
ielts library semantic-items src_ID
ielts library review-semantic sitem_ID --status user_approved --note "Useful for my speaking practice"
```

Review states and reviewer notes are stored separately from the model's extraction rationale. They are personal curation, not a validation of IELTS correctness. The local Ollama service must already be running. This adapter does not download models or install dependencies. No remote endpoint, paid API, or secret is supported.

## Acceptance boundary

Tests verify schema rejection, exact span fidelity, output bounds, and loopback-only endpoint policy. They do not measure semantic extraction quality. Human-annotated precision/recall must be evaluated separately before using the extractor as anything beyond a draft generator.

# Optional local semantic extraction

The baseline lexical extractor remains the default. This optional module defines a provider-neutral contract and an explicit Ollama adapter for a model already installed on the same machine. It makes no request unless a caller constructs the adapter and invokes it.

## Safety and data contract

- The adapter accepts only plain HTTP loopback endpoints; remote hosts are rejected.
- The source is marked as untrusted data in the prompt. It cannot authorize tools, shell commands, network access, or policy changes.
- Output is schema-checked, bounded, and each item must match the exact original source substring at its Python character offsets.
- Supported draft types: recommendation, procedure, claim, rationale, example, exception, warning, open_question.
- Every accepted item is `needs_review`; schema/span validation does not validate factual or educational correctness.
- Model, prompt, and extraction-method provenance must be recorded by any persistence integration. Do not overwrite the original lexical cards.
- The model may hallucinate offsets; failed span checks reject the item.

## Example

```python
from open_ielts_strategy.semantic_extraction import OllamaLocalProvider

provider = OllamaLocalProvider(model="qwen3:8b")
draft = provider.extract("For IELTS Writing Task 2, plan before drafting.")
```

The local Ollama service must already be running. This adapter does not download models or install dependencies. No remote endpoint, paid API, or secret is supported.

## Acceptance boundary

Tests verify schema rejection, exact span fidelity, output bounds, and loopback-only endpoint policy. They do not measure semantic extraction quality. Human-annotated precision/recall must be evaluated separately before using the extractor as anything beyond a draft generator.

# Offline hybrid retrieval

The existing SQLite lexical search remains the no-dependency fallback. This module can optionally rerank all local cards using a caller-supplied embedding provider. `LocalSentenceTransformer` loads a model directory already present on disk and requests local-only loading; it does not download weights.

## Usage

```python
from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.hybrid_retrieval import hybrid_search, LocalSentenceTransformer

with KnowledgeStore() as store:
    results = hybrid_search(store, "essay planning", limit=10)
    # Optional, after installing sentence-transformers and placing model weights locally:
    provider = LocalSentenceTransformer("/models/all-MiniLM-L6-v2")
    results = hybrid_search(store, "essay planning", provider=provider)
```

Results include lexical and semantic components, retrieval mode, card status, source ID, exact offsets, and locator. The provider must be local and already provisioned. Embedding similarity is a retrieval signal, not truth or quality.

` suggest_overlaps` reports possible lexical overlap for human review. It does not create relationships or infer contradiction. A similar pair can agree, disagree, or merely share vocabulary.

## Security and limitations

- No remote model names or model downloads are accepted by the local loader.
- The no-provider path remains fully standard-library and offline.
- The current implementation computes vectors at query time; a persistent embedding cache/index and model-version migration remain future optimization work.
- Human-reviewed provenance is retained in every result.

# Published retrieval relevance evaluation

The latency benchmark measures speed, not ranking quality. This offline evaluator
adds Recall@k, Precision@k, MRR@k, and graded nDCG@k against caller-supplied
strategy relevance judgments. It does not ship or invent an IELTS benchmark
corpus, and it makes no educational-validity or score-improvement claim.

## Judgment file

Create a UTF-8 JSON array outside the repository when queries or judgments are
sensitive:

```json
[
  {
    "id": "writing-planning-001",
    "query": "How should I plan a response before drafting?",
    "skill": "writing",
    "relevance": {
      "writing.task-planning": 3,
      "writing.coherence": 1
    }
  }
]
```

Each relevance grade is an integer from 1 (partially relevant) to 3 (highly
relevant). Unlisted strategies are treated as non-relevant. Every judged
strategy ID must exist in the selected Knowledge Pack. Case IDs must be unique.
Use original, synthetic, or otherwise rights-cleared queries and judgments;
do not add official IELTS questions, candidate responses, paid-preparation
content, or third-party passages.

## Run

```bash
python scripts/evaluate_published_retrieval.py \
  --pack ./knowledge \
  --cases-json ./private/retrieval-cases.json \
  --k 1 3 5 10 \
  --output ./private/retrieval-report.json
```

For optional dense/hybrid retrieval, pass an already-cached local model path:

```bash
python scripts/evaluate_published_retrieval.py \
  --pack ./knowledge \
  --cases-json ./private/retrieval-cases.json \
  --embedding-model-path /models/all-MiniLM-L6-v2
```

The report records pack version and manifest digest, retrieval mode, case count,
a canonical case-suite SHA-256 fingerprint, overall macro-averaged metrics,
and per-skill/task macro metrics and case counts. It omits query text and
relevance judgments. Cases without a skill are grouped as `unspecified`.
Keep the input judgment file private when it contains sensitive learner data.
The evaluator rejects duplicate case IDs, unknown strategy IDs, malformed
grades, and unbounded inputs.

## Interpretation

- Recall@k: fraction of judged-relevant strategies retrieved in the top k.
- Precision@k: fraction of the top k results judged relevant.
- MRR@k: reciprocal rank of the first relevant result, or zero if absent.
- nDCG@k: graded ranking quality normalized by the ideal ordering.

Per-skill values are descriptive breakdowns of the caller's supplied cases;
they do not correct sampling imbalance or establish representative coverage.
Reviewers must define the skill/task taxonomy and held-out split before tuning.
These metrics are only as representative and reliable as the query set and
reviewers that created them. They do not measure IELTS band scores, examiner
agreement, learner outcomes, or educational effectiveness. For external claims,
use the independent protocol and qualified blinded reviewers.

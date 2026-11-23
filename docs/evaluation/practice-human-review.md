# Human review protocol for generated Practice outputs

Generated Practice answers are educational drafts, not IELTS scores or examiner decisions. Evaluate them before making claims about answer quality or learner outcomes.

## Rubric

Each reviewer scores each dimension independently from 1 (unacceptable) to 5 (strong):

1. **Task relevance** — addresses the exact learner task.
2. **Evidence grounding** — claims are supported by the published strategy IDs and pack revision.
3. **Clarity** — explanation is coherent and understandable.
4. **Actionability** — suggested practice is specific and usable.
5. **Factual safety** — avoids invented IELTS rules, score claims, and guarantees.

Reviewers must be qualified for the review scope, use the same rubric version, and assess outputs independently before discussing disagreements. Preserve the output hash, Knowledge Pack version, and manifest digest so a rating cannot silently drift to a different answer or knowledge revision.

## Local workflow

```bash
ielts-practice-eval --db .local/practice-reviews.sqlite register \
  --item-id sample-001 --pack-version 1.0.0 \
  --manifest-sha256 <manifest-sha256> --output-sha256 <answer-sha256>

ielts-practice-eval --db .local/practice-reviews.sqlite review \
  --item-id sample-001 --reviewer-id reviewer-a \
  --scores-json '{"task_relevance":4,"evidence_grounding":5,"clarity":4,"actionability":4,"factual_safety":5}'

ielts-practice-eval --db .local/practice-reviews.sqlite report
```

Keep the database local and private. Do not commit learner prompts, candidate answers, reviewer identities, or rationales. The report calculates descriptive exact agreement and quadratic weighted Cohen-style kappa for paired ordinal ratings. Small samples and uneven score distributions make these statistics unstable; publish counts and uncertainty alongside any later analysis.

## Interpretation

This workflow establishes an annotation and calibration mechanism only. It does not automatically establish examiner equivalence, official IELTS band calibration, construct validity, positive skill lift, or generalization. Those require a pre-registered protocol, representative consented data, qualified independent raters, adequate sample sizes, inter-rater reliability analysis, and a separately reviewed outcome study.

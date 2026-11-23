# Knowledge extraction evaluation and governance

## What can be measured now

The benchmark helper compares candidate extractions against caller-supplied annotations using exact kind + text + source-offset matches. It reports precision, recall, and F1. This is a source-fidelity/classification metric only; it does not measure whether advice is true, useful, IELTS-aligned, or improves learner outcomes.

The repository fixture file contains original synthetic examples with author-created labels for regression testing. They are not qualified examiner ratings, independent human annotations, or evidence of educational effectiveness.

## Independent annotation protocol

Before reporting a human-reviewed benchmark:

1. Recruit at least two independent reviewers with documented relevant expertise.
2. Provide a written annotation manual for boundaries and the eight extraction categories.
3. Have reviewers annotate independently without seeing model output or each other's labels.
4. Preserve source IDs, text hashes, exact character offsets, rubric version, reviewer pseudonyms, and review timestamps in a private audit record.
5. Calculate per-category precision/recall/F1 against adjudicated annotations, plus inter-rater agreement separately.
6. Report sample size, confidence intervals, disagreements, exclusions, and known selection bias.
7. Do not publish source text or private reviewer identity/evidence without explicit rights and privacy approval.

A local CLI can evaluate stored semantic items against a private JSON annotation file without printing source text:

```bash
python scripts/evaluate_knowledge_extraction.py \
  --source-id src_ID \
  --annotations ~/PrivateIELTS/annotations/source-01.json \
  --model-name qwen3:8b \
  --prompt-version knowledge-extract-v1
```

The command selects the latest matching extraction per segment, emits only counts, hashes, model/prompt identifiers, and exact-match metrics, and refuses to evaluate after the raw source body has been purged. Keep annotation JSON outside Git. No reviewer credentials are authenticated by this code. No human ratings are present in the repository. Until the protocol is completed, use only synthetic regression metrics and do not make educational or score-improvement claims.

## Security and privacy review

- Source text remains in the local library; never place it in fixtures, logs, CI artifacts, issues, or public PRs.
- Local-model calls require explicit opt-in and a loopback endpoint; the default CI path does not invoke a model.
- Treat source content as prompt-injection-capable untrusted data.
- Verify exact source spans, bound output, reject unknown schema fields, and retain needs_review.
- Use local-only embedding model paths; never auto-download model weights.
- Keep learner preferences separate from source-derived claims.
- Local UI binds only to loopback; do not expose it through tunnels or a LAN interface.
- Document parsers have size/page/archive limits; OCR and macro execution are unsupported.

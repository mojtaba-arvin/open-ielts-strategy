# Independent educational validation protocol

## Purpose and claim boundary

This protocol is for evaluating whether the platform's Practice, extraction, retrieval, and teaching workflows are useful and safe. It is not an IELTS examination, does not confer examiner status, and cannot support official IELTS band predictions or score-improvement guarantees. Repository fixtures and automated judge scores are engineering regression signals, not independent educational evidence.

No participant data, ratings, outcomes, or study results are included in this repository. This document defines the protocol to be approved and executed by independent reviewers before any educational-effectiveness claim is considered.

## Governance before data collection

Before recruiting or evaluating participants, publish a dated preregistration containing:
- the exact research question, hypotheses, primary and secondary outcomes;
- target population, eligibility/exclusion criteria, recruitment and consent process;
- intervention and comparator definitions, task forms, timing, exposure, and permitted assistance;
- randomization/allocation procedure and concealment;
- primary analysis, missing-data handling, multiplicity control, subgroup policy, and stopping rules;
- sample-size/power calculation using a justified minimum practically important effect, expected variance, alpha, power, attrition, and clustering/repeated-measures assumptions;
- rater qualifications, training, blinding, adjudication, conflict-of-interest declarations, and rubric version;
- privacy, retention, withdrawal, access controls, and ethics/legal approvals.

Do not choose a sample size after inspecting outcome results. If no defensible effect-size assumption exists, run a separately labelled feasibility/pilot study and do not describe it as a powered effectiveness study.

## Workstream A — content and extraction fidelity

1. Assemble a rights-cleared, consented corpus of learner-provided or independently authored material. Never add official IELTS questions, answer keys, copyrighted candidate responses, transcripts, or paid-preparation content without documented rights for the exact use.
2. Have two qualified annotators independently label source-span correctness, claim fidelity, taxonomy, omissions, unsupported additions, and harmful/conflicting advice.
3. Blind annotators to model/provider identity and one another's labels. Randomize item order.
4. Preserve item IDs, source/segment hashes, extractor version, prompt version, model/provider revision, and annotation rubric version. Keep source text and personal data in an access-controlled private system; publish only aggregated, disclosure-reviewed results.
5. Report per-label precision/recall/F1 where applicable, span exactness/overlap, unsupported-claim rate, omission rate, severity-weighted error rate, confidence intervals, and inter-rater agreement separately. Adjudicate disagreements only after independent ratings are locked.

## Workstream B — retrieval quality

1. Create a rights-cleared query set with independently judged relevant and non-relevant published records, skill/task filters, and difficult negative queries.
2. Split development and held-out test queries before tuning. Prevent near-duplicate or source-leaking queries across splits.
3. Compare deterministic BM25, hybrid retrieval, query rewriting, and reranking on the same query/pack/model revisions.
4. Report Recall@k, Precision@k, MRR, nDCG@k, no-evidence abstention quality, latency p50/p95, initialization cost, and memory/resource use. Report confidence intervals and per-skill/task breakdowns.
5. Do not tune thresholds or select the winning model on the held-out set. Store query and judgement data privately; publish aggregate metrics and hashes only.

## Workstream C — Practice output quality

1. Freeze the Knowledge Pack manifest digest, model/provider revision, generation settings, prompt version, and retrieval configuration before collecting outputs.
2. Use consented learner prompts or original synthetic prompts that do not reproduce protected test content. Stratify by skill, task, proficiency range, and safety risk.
3. Compare the platform against a predeclared baseline under matched inputs and equivalent assistance/time budgets. Randomize output order and blind reviewers to condition.
4. Use the versioned five-dimension rubric: task relevance, evidence grounding, clarity, actionability, and factual safety. Reviewers score independently; do not average away a critical safety failure.
5. Report dimension distributions, severe error rates, missing/abstention rates, exact and weighted ordinal agreement, uncertainty intervals, and subgroup results. Keep human judgement, automated judge output, and learner preference as separate outcomes.

## Workstream D — learner outcome study

A learner outcome study is distinct from answer-quality annotation. Use a controlled, ethically reviewed design with baseline and follow-up tasks, parallel task forms, a comparator, blinded qualified raters, and predeclared outcome scoring. Track adherence and attrition. Analyze by intention-to-treat where appropriate, report effect sizes and uncertainty, and disclose limitations and adverse events. Do not infer causal improvement from satisfaction surveys, completion rates, a single before/after example, or a model-generated band estimate.

## Data and reproducibility contract

Each private evaluation record should bind:
- opaque item and participant IDs (no direct identifiers in the analysis dataset);
- consent/ethics reference and permitted-use scope;
- prompt/task hash, output hash, Knowledge Pack version and manifest digest;
- model/provider/prompt/retrieval configuration fingerprints;
- annotator ID pseudonym, qualification scope, rubric version, timestamp, and independent score vector;
- randomization arm, task form, and predeclared exclusion/missingness reason.

Keep identifiable consent records separate from ratings. Restrict access, encrypt storage and backups, define deletion/withdrawal handling, and do not commit raw prompts, outputs, or ratings to Git or CI artifacts.

## Release and claim gates

- Software release may ship deterministic functionality and clearly labelled experimental features, but must not imply educational effectiveness.
- Any public claim about extraction accuracy, retrieval relevance, human agreement, examiner equivalence, band prediction, or learner improvement requires a separately reviewed evidence package with protocol, sample counts, uncertainty, limitations, and independent sign-off.
- Examiner equivalence and official band prediction are prohibited unless a qualified independent study specifically validates the relevant construct and applicable permissions are established. This project makes no official IELTS affiliation claim.
- A passing CI run, synthetic benchmark, LLM-as-judge result, or maintainer self-rating cannot satisfy independent validation.

## Result report template

Publish only after independent review and privacy/legal disclosure checks:
- protocol ID/version and preregistration timestamp;
- recruitment flow and sample counts per stage/arm;
- participant/task characteristics in non-identifying aggregates;
- model, prompt, retrieval, and pack fingerprints;
- primary/secondary outcomes with uncertainty intervals;
- inter-rater agreement and adjudication policy;
- safety/error analysis, missing data, exclusions, adverse events;
- deviations from preregistration, limitations, conflicts of interest;
- independent reviewer names/credentials only with explicit consent, otherwise role-level attribution;
- explicit statement of which claims are and are not supported.

Until a real independent study is completed, the correct status is “validation protocol and tooling available; empirical educational validity not established.”

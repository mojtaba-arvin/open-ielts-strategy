# Issue #109 — external acceptance evidence package

**Status:** evidence plan only; all three acceptance gates remain blocked pending external evidence.  
**Tracking issue:** https://github.com/mojtaba-arvin/open-ielts-strategy/issues/109  
**Scope:** documentation and evidence organization. This document does not grant content rights, approve educational content, validate IELTS outcomes, or attest to a live deployment.

## Decision and claim boundary

The repository can provide deterministic schemas, validators, private review workflows, deployment templates, and test harnesses. Those are engineering controls, not evidence that an external gate has passed.

Keep these gates independent:

1. **Content rights and publication:** original/rights-cleared educational content, complete provenance, independent content review, separate publication approval, candidate-pack validation and signed release.
2. **Independent educational evaluation:** qualified independent reviewers, blinded ratings, reviewer-agreement analysis, and tests preregistered before outcomes are observed.
3. **Production operations:** operator-controlled identity, secrets, audit, network, Redis, security testing, and target-cluster acceptance.

No gate inherits approval from another. A valid pack does not establish educational quality; educational ratings do not establish legal rights; CI or deployment templates do not establish production operation.

Until evidence is independently verified, retain these statuses:

- No publishable Knowledge Pack is represented as rights-cleared or educationally approved.
- No IELTS effectiveness, positive skill-lift, band-improvement, examiner-equivalence, examiner-calibration, or official score-prediction claim.
- No live production deployment, OIDC integration, durable audit retention, target-cluster network acceptance, or penetration-test completion claim.

## Repository contract and existing evidence

Read and apply these sources before any candidate is prepared:

- `AGENTS.md` — prohibits unlicensed IELTS/test/course material, requires original/synthetic material or exact-use permission, and forbids fabricated approval.
- `LICENSE-CONTENT` — project-authored editorial and learning content is not covered by the root MIT software license; third-party rights remain with their owners.
- `docs/knowledge/published-knowledge-pack-v1.md` and `docs/architecture/adr-001-published-knowledge-pack.md` — manifest, record schemas, checksums, sanitized public provenance, dual approvals, leakage checks, candidate diff and signed release workflow.
- `docs/evaluation/independent-validation-protocol.md` — preregistration, extraction/retrieval/Practice/learner-outcome workstreams, blinding, statistics, privacy, and claim gates.
- `docs/evaluation/practice-human-review.md` — versioned five-dimension Practice rubric and local private rating workflow.
- `docs/deployment/production-readiness.md` and `docs/deployment/published-mcp-http.md` — production topology, operator configuration, deployment sequence, security and acceptance tests.
- `docs/release/knowledge-pack-release.md` — explicit signed pack authorization and rollback.

Existing implementation is evidence of tooling only: Knowledge Pack schema/build/diff/release controls, private rights/review metadata, exact/secret and optional semantic-overlap screens, a local reviewer-rating store and descriptive agreement report, retrieval evaluation tools, and hardened deployment templates. None of these creates an external approval or a measured outcome. The current repository roadmap records no independently reviewed human-rated corpus, consented learner cohort, preregistered results, or live target-cluster acceptance.

## Gate 1 — original content, provenance, independent review, publication

### Required evidence bundle

Store restricted rights documents and source copies outside Git. The public evidence record may contain only a disclosure-reviewed reference or opaque evidence ID; never commit contracts, private correspondence, restricted source text, personal learner data, or reviewer-private notes.

For every proposed record, the owner must assemble:

1. **Content identity:** stable record ID, record type, skill, record version, authored date, author/rights-holder identity in the private record, and a cryptographic digest of the reviewed draft.
2. **Origin and provenance:** whether wholly original, synthetic, or source-derived; authoring method; source reference and source version/date where applicable; transformation/derivation description; exact source-to-record mapping in the private store; and source/draft hashes. Do not publish private source IDs, extraction IDs, local paths, source text, transcript text, or private review notes.
3. **Rights basis:** rights holder; exact permission or license; permitted acts (copy, adapt, process, publish, redistribute, commercial/non-commercial use as relevant); territory, term, attribution conditions, restrictions, and evidence reference; reviewer and decision timestamp. A URL, attribution, public availability, learner possession, or self-reported rights field is not permission.
4. **Independent content review:** reviewer identity and qualifications in the private evidence record; conflict-of-interest declaration; rubric/version; reviewed record digest; independent factual/educational correctness, clarity, scope, limitations, and safety findings; issue disposition; decision and timestamp. Reviewer must not be the author of the record.
5. **Separate publication approval:** a distinct authorized approver; exact candidate record digest; rights evidence reference; permitted publication scope; decision and timestamp. Content approval is not publication approval.
6. **Pack-level checks:** candidate manifest and pack version; schema and cross-record validation; exact-overlap/secret scan results; optional semantic-overlap scan configuration/results where used; complete versioned diff; independent diff review; signed release authorization and resulting Git revision/artifact digest.

### Required workflow

- Author original strategy/concept/relationship/learning-path/example material. Synthetic examples must be labelled as synthetic and must not be presented as authentic IELTS items or learner outcomes.
- If any source-derived material is proposed, obtain written permission for the exact processing and redistribution use before importing or transforming it. If permission is absent, unclear, expired, or narrower than the proposed use, exclude the material.
- Keep source text, rights evidence, source mappings, and reviewer notes in the private authoring system. Public provenance must be sanitized and sufficient to describe the basis without disclosing restricted material.
- Obtain independent content review and record the real decision. Resolve review findings and re-review the exact changed digest.
- Obtain publication approval as a separate decision.
- Build a new candidate pack with the documented publisher command; run all schema, manifest, checksum, cross-reference, path/symlink, exact-overlap, and secret checks. Run the optional local semantic-overlap screen when a suitable cached local model is available; record that it is heuristic only.
- Inspect the complete `ielts-knowledge-diff` output against the current pack. Obtain signed release approval only for the exact reviewed candidate and current-head digests. Publish through the protected PR/release process; retain rollback reference.
- Do not publish the template, empty evidence records, generated drafts, or unreviewed model output as learning content.

### Gate 1 pass condition

Every shipped record has a traceable and appropriate rights basis, complete private provenance, independent content approval, separate publication approval, and a matching digest in the verified candidate. The complete candidate passes pack validation and leakage screens, receives independent human diff review, and is released through the signed workflow. Any missing or ambiguous record blocks the entire candidate from publication.

## Gate 2 — independent educational evaluation

### Governance and preregistration (before data collection)

An independent study lead must approve and timestamp a public or otherwise immutable preregistration containing:

- research question, hypotheses, primary and secondary outcomes, estimands, and claim scope;
- target population, eligibility/exclusion criteria, recruitment, consent, compensation (if any), and withdrawal process;
- intervention, comparator, task forms, timing, exposure, permitted assistance, randomization and allocation concealment;
- sample-size/power calculation based on a justified minimum practically important effect, variance, alpha, power, attrition, and clustering/repeated-measures assumptions;
- analysis plan, missing-data handling, multiplicity correction, subgroup policy, exclusions, stopping rules, and sensitivity analyses;
- reviewer qualification requirements, training, conflict declarations, blinding, adjudication, rubric version, and a predeclared reviewer-agreement method/acceptance criterion;
- privacy, security, retention, access, ethics/legal approval, adverse-event handling, and publication/disclosure plan.

Do not choose sample size, thresholds, or analysis after inspecting results. If no defensible effect-size assumption exists, label the work a feasibility/pilot study; do not describe it as powered effectiveness evidence.

### Independent rating design

- Recruit at least two qualified independent raters for the relevant construct; record their qualification scope and conflicts privately.
- Freeze the exact Knowledge Pack manifest digest, output hashes, model/provider and revision, prompt, retrieval configuration, generation settings, task form, and rubric version before rating.
- Remove condition/provider identifiers, randomize item order, and blind each rater to condition and other raters' scores.
- Collect independent ratings before discussion. Lock the raw score vectors before adjudication; preserve adjudication as a separate record.
- Use the existing five-dimension Practice rubric: task relevance, evidence grounding, clarity, actionability, and factual safety (1–5). Do not average away a critical safety failure.
- Keep rater identity and private rationales separate from public outputs. Do not commit raw prompts, learner answers, ratings, or participant data to Git or CI artifacts.

### Preregistered test workstreams

1. **Extraction fidelity:** rights-cleared/consented or independently authored cases; two independent annotators; source-span correctness, claim fidelity, taxonomy, omissions, unsupported additions, and harmful/conflicting advice. Report per-label precision/recall/F1 where applicable, span exactness/overlap, unsupported-claim and omission rates, severity-weighted errors, confidence intervals, and agreement.
2. **Retrieval relevance:** independently judged relevant/non-relevant rights-cleared queries; pre-separated development and held-out test sets; prevent near-duplicate/source leakage; compare BM25, hybrid, query rewriting, and reranking on identical frozen inputs. Report Recall@k, Precision@k, MRR, nDCG@k, no-evidence abstention, uncertainty intervals, per-skill/task results, latency and resource metrics. Never tune on the held-out set.
3. **Practice output quality:** stratified rights-cleared or original synthetic prompts; matched baseline and assistance/time budgets; randomized output order; blinded ratings using the frozen rubric. Report score distributions, severe error rates, missing/abstention, exact and weighted ordinal agreement, uncertainty intervals, and subgroup results. Keep human judgement, automated judge output, and learner preference separate.
4. **Learner outcomes (only if separately approved):** ethically reviewed controlled design, baseline/follow-up parallel task forms, comparator, blinded qualified raters, adherence/attrition, predeclared scoring and intention-to-treat analysis where appropriate, effect sizes, uncertainty, limitations, and adverse events. Satisfaction, completion, one before/after example, or model-generated band estimates are not causal evidence.

### Agreement and claim handling

Predeclare the agreement statistic(s), confidence interval method, handling of missing/uneven ordinal ratings, minimum acceptable reliability, and adjudication procedure before collection. Report sample counts and uncertainty; do not invent a threshold or treat a small/imbalanced sample as stable. The local tool's exact agreement and quadratic weighted Cohen-style kappa are descriptive outputs, not proof of calibration.

Do not claim positive skill lift, IELTS band improvement, examiner equivalence, official band prediction, or guaranteed score improvement unless the exact claim is supported by a sufficiently powered, preregistered, independently reviewed design specifically measuring that construct and applicable rights/permissions are established. Examiner equivalence and official band prediction remain prohibited absent such specific validation and permissions.

### Gate 2 pass condition

A dated preregistration predates data collection; reviewers meet predeclared qualification and independence criteria; ratings are blinded and independently locked; agreement meets the predeclared criterion with uncertainty reported; each preregistered analysis is reproducible from privacy-protected data; deviations and limitations are disclosed; and an independent study lead signs off on the narrow claims actually supported. No result may be generalized beyond the tested population, task, pack, and configuration.

## Gate 3 — target production operations and security acceptance

### Operator evidence bundle

The target-environment operator must provide attributable, timestamped evidence for each item below. Redact secrets and sensitive infrastructure details before sharing; do not place credential values in GitHub.

| Control | Required target evidence |
|---|---|
| OIDC gateway | Issuer/audience/expiry validation, required MFA policy where applicable, authorized subject/scope mapping, access logs, and negative tests proving unauthenticated/unauthorized requests fail. |
| Bypass prevention | Network and ingress tests proving the gateway cannot be bypassed through Service, NodePort, LoadBalancer, pod IP, alternate ingress, or direct application port. Application Service remains ClusterIP. |
| Secret synchronization | External secret manager source, workload identity/least-privilege mapping, synchronization status, rotation and revocation test, and proof that no secret values enter manifests, Git, logs, or CI artifacts. |
| Durable audit | Central stdout event export, append-only/tamper-evident retention configuration, access controls, retention/expiry policy, integrity verification, delivery-gap alert, and a demonstrated restore/query of retained metadata. No prompts, tokens, retrieved content, or model responses in audit. |
| Network policy | Actual cluster CNI enforcement evidence; rendered policy review; ingress restricted to trusted gateway/controller; egress restricted to cluster DNS and exact managed Redis TLS destinations/ports; positive and negative connectivity tests. Replace documentation-only CIDRs. |
| TLS Redis | Managed Redis endpoint using `rediss://`, certificate verification, dedicated ACL identity with least privilege, secret rotation, multi-replica rate-limit test, and outage/fail-closed test. No plaintext Redis. |
| Immutable deployment pair | Image digest, source commit, Knowledge Pack version/manifest digest, deployment change ID, read-only pack mount, and proof the deployed pair matches approved artifacts. |
| Operational drills | Readiness/rollout evidence; backup/restore and prior image+pack rollback; load, soak, and failure-injection results against preregistered service objectives; monitoring/alert delivery and on-call ownership. |
| Independent security | Independent threat model and penetration-test scope, tester identity/independence, dated report reference, finding severity/disposition, retest evidence, and no unresolved critical/high findings. Keep exploit details private. |
| Operational governance | Named accountable operator/on-call rota, incident response, data retention/deletion policy, escalation path, exception register, and signed target-environment acceptance. |

### Required negative/positive tests

At minimum, test OIDC enforcement and bypass attempts; token scope and revocation; Host/Origin rejection; request-size limits; cross-replica rate limiting; Redis certificate failure and outage fail-closed behavior; NetworkPolicy deny paths and allowed DNS/Redis paths; audit delivery interruption and alerting; readiness and rollout failure; secret rotation; immutable digest mismatch rejection; rollback to a prior approved image/pack pair; and load/soak/failure behavior under the preregistered objectives.

The operator must validate the rendered manifests against the real cluster admission policy and CNI. Generic YAML validation, local Compose, CI, or a template review is not target-cluster acceptance.

### Gate 3 pass condition

All environment-specific evidence is attributable to the named target cluster and deployment revision; OIDC cannot be bypassed; secret synchronization/rotation, durable audit, enforced network policy, TLS Redis/ACL, rollback and operational drills pass; an independent penetration test has no unresolved critical/high findings; and the accountable operator signs acceptance with any residual risks explicitly documented.

## Owner-only action list

These actions require the repository owner/maintainer or the named external accountable party. They are intentionally not delegated to automated repository changes.

### Content rights and publication — repository owner / content rights holder

- [ ] Decide whether the first candidate will be wholly original/synthetic. Prefer this path; exclude all official IELTS tests, answer keys, transcripts, licensed course content, scraped text, and paid-preparation materials.
- [ ] If any third-party source is proposed, obtain and privately retain written permission from the actual rights holder covering the exact ingestion, processing, adaptation, public redistribution, and intended commercial/non-commercial use. Verify term, territory, attribution and restrictions; otherwise reject the source.
- [ ] Identify the actual author and rights holder for each record; complete private source-to-record provenance and digest mapping.
- [ ] Commission a reviewer who did not author the material; verify educational subject-matter qualifications and conflicts; obtain a signed, digest-bound content decision.
- [ ] Make a separate publication-approval decision after reviewing rights evidence and the exact candidate diff.
- [ ] Run the documented pack build, validation, leakage scans, versioned diff and signed release process; publish only the exact approved candidate and preserve rollback evidence.

### Independent educational evaluation — repository owner / independent study lead

- [ ] Recruit and contract qualified independent reviewers/annotators; verify credentials, scope, independence, conflicts, consent and privacy obligations.
- [ ] Appoint an independent study lead/statistician to finalize and timestamp the preregistration, sample-size rationale, hypotheses, outcomes, analysis, blinding, agreement statistic and acceptance threshold before collection.
- [ ] Obtain applicable ethics/privacy/legal approval and consent; create a representative, rights-cleared case/query set and freeze all pack/model/prompt/configuration fingerprints.
- [ ] Run extraction, retrieval and Practice studies as separate workstreams; collect blinded independent ratings; lock score vectors before adjudication.
- [ ] Publish only privacy-reviewed aggregate reports with uncertainty, deviations, limitations, actual reviewer sign-off and narrowly supported claims. Keep effectiveness, band, and examiner claims disabled unless specifically validated.

### Target infrastructure — named production operator / security owner

- [ ] Name the target cluster, accountable operator, on-call owner, SLOs, data-retention policy and incident escalation path.
- [ ] Provision OIDC gateway and prove issuer/audience/MFA/scope enforcement plus all bypass-denial paths.
- [ ] Configure external secret synchronization using least-privilege workload identity; test rotation/revocation without exposing values.
- [ ] Configure durable tamper-evident audit export, retention, access controls, integrity checks and delivery-gap alerts.
- [ ] Apply cluster/CNI-specific NetworkPolicy; replace all example CIDRs/hostnames; prove restricted ingress and DNS/Redis-only egress.
- [ ] Provision managed TLS Redis with certificate verification and dedicated ACL; test multi-replica limiting, rotation and fail-closed outage.
- [ ] Deploy immutable image and approved pack digest pair; run readiness, rollback, restore, load, soak and failure-injection drills.
- [ ] Commission independent threat modelling and penetration testing; remediate and retest all critical/high findings.
- [ ] Attach redacted evidence and sign target-cluster acceptance. Until then, do not call the service production-ready or deployed.

## Evidence record and change control

For each evidence item, retain: gate ID; evidence ID; control/test; accountable party; reviewer; target artifact/revision/digest; date/time (UTC); method/tool version; result; exceptions; redacted evidence location; approval signature/identity; and expiry/retest date. Keep raw restricted evidence in the owner's approved private system. Public references must be stable, access-controlled as appropriate, and disclosure-reviewed.

Any change to content, pack digest, rubric, preregistration, model/provider, prompt, retrieval configuration, deployment image, cluster policy, gateway, Redis, or secret configuration may invalidate the corresponding evidence. Re-run the affected checks and record the new digest/revision. Do not carry approvals forward to materially changed artifacts.

## Explicit non-goals

This package does not create educational content, grant licenses, provide legal advice, recruit reviewers, collect learner data, perform an independent study, provision infrastructure, execute penetration testing, or accept a deployment. It does not enable official IELTS material, answer keys, transcripts, licensed course content, paid APIs, or paid models. Local models and original/synthetic material remain the permitted default. Any remote provider would require a separately approved data-egress decision and is not authorized by this document.

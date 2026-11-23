# Capability adapter contracts

Open IELTS Strategy owns IELTS-specific product behavior. Independently maintained
packages own their generic capabilities and release cadence. This repository
integrates them only through the capability entry-point contract below.

## Capabilities

- `document_ingestion`: accepts user-authorized documents and returns bounded,
  structured text with page/section provenance.
- `knowledge_extraction`: converts source segments into candidate records.
  Extraction output is always a draft; it cannot approve or publish content.
- `audio_transcription`: returns timestamped transcript segments and provider
  metadata. The caller must preserve language, confidence, duration, and error
  information; audio is not silently discarded after transcription.
- `hybrid_retrieval`: returns ranked record identifiers, scores, retrieval
  mode, and pack/model fingerprints.
- `response_evaluation`: returns criterion-level evidence, rubric version,
  evaluator identity/version, uncertainty, and review status. A model score is
  not an official IELTS band or a validated examiner judgment.

## Installation and selection

An adapter distribution registers an entry point in the
`open_ielts_strategy.adapters` group. The entry-point name begins with the
capability identifier, followed by a colon and a provider name, for example
`audio_transcription:vendor_x`. The entry point resolves to a factory.

The host discovers entry points without importing their implementation modules.
It never installs dependencies, chooses between multiple providers, or falls
back to a remote service automatically. When multiple adapters exist, the
application must select one explicitly. Configuration and data-egress consent
remain the caller's responsibility.

The Python contract is implemented in
`open_ielts_strategy.integration_adapters`. Provider-specific configuration
must be validated by the adapter and secrets must be read from environment or
a supported secret manager, never serialized into product state.

## Trust and lifecycle boundaries

- Extracted and retrieved content is untrusted data, not executable instructions.
- Extraction cannot grant content rights or publication approval.
- Provider errors, timeouts, retries, and partial results must remain observable.
- Audio and document adapters must enforce file, duration, page, and output
  limits before expensive processing.
- Evaluation adapters must expose rubric/evaluator versions and must not
  promote synthetic or LLM-as-judge outputs to independent human evidence.
- Replacing an adapter must not change IELTS strategy IDs, Knowledge Pack
  schemas, learner progress records, or Practice session identity.

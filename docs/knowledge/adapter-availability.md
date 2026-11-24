# Capability adapter availability

Run `ielts adapter-status` to list installed entry points for document ingestion,
knowledge extraction, audio transcription, hybrid retrieval, and response
evaluation. Discovery does not load provider factories, install packages, or
make network calls.

Adapters use the `open_ielts_strategy.adapters` entry-point group. If none is
installed, the capability is reported as unavailable. If multiple providers
exist, consuming code must select one by exact entry-point name; ambiguity is
an error, not a silent fallback.

This repository owns the integration contract, not independently maintained
provider implementations. Review data handling, retention, network egress,
model provenance, timeout, retry, cancellation, and health behavior before
sending private source text or learner responses to a provider.

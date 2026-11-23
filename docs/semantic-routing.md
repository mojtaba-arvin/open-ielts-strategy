# Optional local semantic routing

The default router remains deterministic and offline. This optional adapter can call an already-running Ollama service on loopback to classify a request into one of the four existing skill IDs or return null.

## Contract

- No model is called unless a provider is explicitly supplied.
- Only plain HTTP loopback endpoints are accepted; remote model services are rejected.
- Input and output sizes are bounded; the output schema permits only known skill IDs, finite confidence in [0,1], and a short reason.
- A low-confidence result returns no skill so the caller can ask for clarification.
- Provider errors fall back to the deterministic router and are identified in metadata.
- Model confidence is uncalibrated. The module makes no accuracy or educational-quality claim.
- CI tests use fake providers only; they never contact Ollama.

This is an optional routing foundation, not a calibrated semantic classifier. It must not replace deterministic routing in production until independently annotated routing benchmarks and threshold calibration exist.

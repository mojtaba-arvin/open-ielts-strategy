# First-use quick start

This guide gets a local authoring workspace ready and explains how to verify a
published pack in a separate consumer checkout. It does not create approved
IELTS content or require a hosted service.

## 1. Install the project

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows, activate the environment with `.venv\\Scripts\\activate`.

## 2. Check the local authoring environment

For local model use, install and start Ollama separately, then pull a model you
intend to use. The following example uses Qwen3 8B:

```bash
ollama pull qwen3:8b
ielts preflight --mode author --provider ollama --model qwen3:8b
```

Preflight checks Python, the private database's writable location, optional
integration dependencies, and the explicitly selected model. It does not
create the database, download models, or send learner content. The Ollama
check makes only a local loopback GET to list installed model names.

For an explicitly selected OpenAI-compatible API provider, set the API key in
your shell and check its presence without printing its value:

```bash
export OPENAI_API_KEY="..."
ielts preflight --mode author --provider openai-compatible --model YOUR_MODEL
```

Remote extraction sends the selected private source segments to the configured
HTTPS provider. Use it only when that disclosure is permitted. There is no
automatic cloud fallback.

## 3. Import your own notes or a transcript

Use only material you are entitled to process. The database and imported text
remain local under `.local/`, which is excluded from Git.

```bash
ielts library ingest ./my-ielts-notes.txt \
  --title "My IELTS notes" \
  --type personal_notes \
  --language en \
  --rights-status self_authored
```

For a third-party transcript that you may keep for personal study but do not
have permission to publish, use `personal_copy_unverified`. That status is
not publication permission and must not be promoted into a public Knowledge
Pack.

The command prints a source ID. Use it in the next steps:

```bash
ielts extract --source-id src_ID --provider ollama --model qwen3:8b
ielts library semantic-items src_ID
```

Extraction creates review-required semantic drafts. Inspect them and record
your own review; model output and exact source spans are not proof of IELTS
correctness.

## 4. Build a private Strategy Draft

After reviewing the semantic items, generate a private Strategy Draft from
reviewed evidence:

```bash
ielts knowledge-draft \
  --source-id src_ID \
  --strategy-id speaking.answer-development \
  --skill speaking \
  --provider ollama \
  --model qwen3:8b
```

The result remains private and requires human editing/review. Follow the full
[Unified product CLI guide](product-cli.md) for semantic-item review,
strategy promotion, publication/rights approval, candidate-pack construction,
diff inspection, and the separately authorized release flow. Do not skip or
combine those gates.

## 5. Consume a published Knowledge Pack

A consumer needs only the repository's published `knowledge/` directory; it
does not need the author's private SQLite database, transcripts, or extraction
provider. Check the pack before using Practice, Study, Mentor, or MCP:

```bash
ielts preflight --mode consume --pack ./knowledge
ielts knowledge-status --pack ./knowledge
ielts study --pack ./knowledge --skill speaking
```

A missing or invalid pack is a blocker for pack-backed consumption, not a
reason to create placeholder IELTS content. This repository intentionally
does not fabricate a default approved Knowledge Pack.

## Data and trust boundaries

- Private transcripts, notes, SQLite data, draft files, and reviewer notes stay
  outside Git. Back up the private workspace securely.
- Content approval and publication/rights approval are independent decisions.
- Public URLs, attribution, personal-copy status, and model rewriting do not
  grant publication rights.
- Knowledge Pack loading and CI validate software contracts, not IELTS advice,
  band scores, examiner equivalence, or learner improvement.
- Hosted MCP is a separate operational milestone. Follow the
  [production runbook](deployment/production-readiness.md); a passing local
  preflight is not production acceptance.

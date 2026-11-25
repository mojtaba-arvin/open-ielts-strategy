# Local library UI and document import

## Local paste-first UI

Run:

```bash
python scripts/knowledge_web.py --port 8765
```

Open `http://127.0.0.1:8765`. The server refuses non-loopback bind addresses, parses the complete Host authority (only `localhost` or `127.0.0.1`, with an optional valid port), rejects malformed ports/userinfo/paths, and checks same-origin POSTs. It uses a per-process CSRF token, limits POST bodies/field counts, escapes all rendered user text, and sends restrictive security headers. The UI lists sources, opens source-linked passages, allows human review-state updates for both lexical cards and semantic extraction items, displays extraction rationale separately from reviewer notes, and supports source deletion only after typing DELETE. It has no login system and is intended for a single-user local workstation only. Review statuses are personal curation, not educational validation. Stop it when not in use; do not expose it through a tunnel, reverse proxy, LAN bind, or public host.

The UI stores source text in the same private SQLite database and does not upload it. Logs must not contain request bodies.

## TXT, Markdown, DOCX, and PDF

`import_document(path)` supports local UTF-8 TXT/Markdown and bounded DOCX/PDF extraction. DOCX parsing uses the Python standard library, streams the document XML, discards completed paragraph elements, and stops as soon as the 5-million-character output limit is exceeded. It rejects macro-bearing packages, normalizes malformed, encrypted, or unsupported ZIP-entry failures into `DocumentImportError`, and bounds ZIP entry count and uncompressed size. PDF parsing requires optional `pypdf`; encrypted files and files over 300 pages are rejected. PDF text-showing operands (`Tj`, `TJ`, `'`, and `\"`) are checked before pypdf decodes and aggregates them; a text-fragment visitor also checks decoded output. An internal abort signal escapes pypdf's nested-XObject exception handler. This limits text processing, but pypdf may still materialize a decompressed content stream before visiting its operators. All formats are bounded by 20 MiB input and 5 million extracted characters. TXT/Markdown reads stop one character beyond the output budget, and SHA-256 fingerprints are computed incrementally rather than loading the original file into memory again. The CLI records filename, format, and file SHA-256 in source notes; the database stores extracted text, not a binary archive of the original document. Keep the original file separately if exact binary preservation is required. Scanned PDFs need OCR, which is not implemented.

The document importer tests include malformed DOCX mutation cases, normalized PDF parser failures, output-limit checks (including abort before oversized text operands are decoded), and a regression check that file hashing does not use whole-file reads. These are deterministic robustness tests, not a substitute for independent parser security review.

Example:

```python
from open_ielts_strategy.document_import import import_document
from open_ielts_strategy.knowledge_store import KnowledgeStore

document = import_document("./my-notes.docx")
with KnowledgeStore() as store:
    source = store.ingest_text(document["text"], title="My notes", source_type="personal_notes")
```

PDF support can be installed separately with `pip install '.[documents]'`. This project does not download parsers or document content automatically. Do not import material unless its intended processing is permitted.

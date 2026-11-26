"""Bounded local TXT/Markdown/PDF/DOCX text extraction."""
from __future__ import annotations

import hashlib
import lzma
import re
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_DOCX_UNCOMPRESSED = 80 * 1024 * 1024
MAX_DOCX_ENTRIES = 2000
MAX_PDF_PAGES = 300
MAX_PDF_DECODED_STREAM_BYTES = 20 * 1024 * 1024
MAX_PDF_DECODED_WORK_BYTES = 40 * 1024 * 1024
MAX_EXTRACTED_CHARS = 5_000_000
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class DocumentImportError(ValueError):
    pass


class _PDFTextBudgetExceeded(BaseException):
    """Internal abort signal that survives pypdf's broad XObject exception handler."""


def import_document(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.is_file():
        raise DocumentImportError("input must be a regular local file")
    size = file_path.stat().st_size
    if size <= 0 or size > MAX_FILE_BYTES:
        raise DocumentImportError("file must be between 1 byte and 20 MiB")
    suffix = file_path.suffix.casefold()
    if suffix in {".txt", ".md"}:
        try:
            # Read only one character beyond the output budget. Hashing below
            # is streamed separately, so a valid large input is never loaded
            # into memory a second time just to fingerprint it.
            with file_path.open("r", encoding="utf-8", newline="") as handle:
                text = handle.read(MAX_EXTRACTED_CHARS + 1)
        except UnicodeError as exc:
            raise DocumentImportError("text files must be valid UTF-8") from exc
    elif suffix == ".docx":
        text = _read_docx(file_path)
    elif suffix == ".pdf":
        text = _read_pdf(file_path)
    else:
        raise DocumentImportError("supported formats are TXT, Markdown, PDF, and DOCX")
    if not text.strip() or len(text) > MAX_EXTRACTED_CHARS:
        raise DocumentImportError("extracted text is empty or exceeds the 5-million-character limit")
    with file_path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {
        "text": text, "filename": file_path.name, "format": suffix[1:],
        "characters": len(text), "file_sha256": digest,
    }


def _read_docx(path: Path) -> str:
    paragraphs = []
    extracted_chars = 0
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_DOCX_ENTRIES or sum(x.file_size for x in infos) > MAX_DOCX_UNCOMPRESSED:
                raise DocumentImportError("DOCX archive exceeds safe expansion limits")
            names = {x.filename for x in infos}
            if len(names) != len(infos):
                raise DocumentImportError("DOCX archive contains duplicate entries")
            if "word/document.xml" not in names or any(name.casefold().endswith("vbaproject.bin") for name in names):
                raise DocumentImportError("invalid or macro-bearing DOCX is not accepted")

            # Stream the XML and discard completed paragraphs so the full XML
            # tree is never retained in memory. Stop as soon as the text budget
            # is exceeded, before parsing the remainder of the document.
            with archive.open("word/document.xml") as document:
                stack = []
                for event, element in ElementTree.iterparse(document, events=("start", "end")):
                    if event == "start":
                        stack.append(element)
                        continue
                    if element.tag == f"{{{WORD_NS}}}p":
                        value = "".join(node.text or "" for node in element.iter(f"{{{WORD_NS}}}t"))
                        if value:
                            extracted_chars += len(value) + (2 if paragraphs else 0)
                            if extracted_chars > MAX_EXTRACTED_CHARS:
                                raise DocumentImportError(
                                    "extracted DOCX text exceeds the 5-million-character limit"
                                )
                            paragraphs.append(value)
                        element.clear()
                        if len(stack) > 1:
                            stack[-2].remove(element)
                    stack.pop()
    except DocumentImportError:
        raise
    except ElementTree.ParseError as exc:
        raise DocumentImportError("malformed DOCX XML") from exc
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError, NotImplementedError,
            EOFError, zlib.error, lzma.LZMAError) as exc:
        raise DocumentImportError("invalid or unreadable DOCX container") from exc
    return "\n\n".join(paragraphs)


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader, apply_configuration
    except ImportError as exc:
        raise DocumentImportError("PDF support requires the optional pypdf dependency") from exc
    try:
        with apply_configuration(
            maximum_declared_stream_length=MAX_PDF_DECODED_STREAM_BYTES,
            array_based_stream_maximum_output_length=MAX_PDF_DECODED_STREAM_BYTES,
            jbig2_maximum_output_length=MAX_PDF_DECODED_STREAM_BYTES,
            lzw_maximum_output_length=MAX_PDF_DECODED_STREAM_BYTES,
            run_length_maximum_output_length=MAX_PDF_DECODED_STREAM_BYTES,
            zlib_maximum_output_length=MAX_PDF_DECODED_STREAM_BYTES,
            brotli_maximum_output_length=MAX_PDF_DECODED_STREAM_BYTES,
            image_maximum_buffer_size=MAX_PDF_DECODED_STREAM_BYTES,
            stream_decoding_work_maximum_length=MAX_PDF_DECODED_WORK_BYTES,
        ):
            return _extract_pdf_text(PdfReader, path)
    except DocumentImportError:
        raise
    except Exception as exc:
        raise DocumentImportError("PDF parsing failed") from exc


def _extract_pdf_text(PdfReader, path: Path) -> str:
    reader = PdfReader(str(path), strict=True)
    if reader.is_encrypted:
        raise DocumentImportError("encrypted PDFs are not accepted")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise DocumentImportError("PDF exceeds the 300-page limit")
    pages = []
    extracted_chars = 0
    for page in reader.pages:
        remaining_chars = MAX_EXTRACTED_CHARS - extracted_chars
        observed_operand_chars = 0
        observed_output_chars = 0

        def text_operand_size(value):
            if isinstance(value, (str, bytes, bytearray)):
                return len(value)
            if isinstance(value, (list, tuple)):
                return sum(text_operand_size(item) for item in value)
            return 0

        def guard_operator(operator, operands, *_):
            nonlocal observed_operand_chars
            if operator in (b"Tj", b"'"):
                text_operands = operands[:1]
            elif operator == b'"':
                text_operands = operands[-1:]
            elif operator == b"TJ":
                text_operands = operands[:1]
            else:
                return
            observed_operand_chars += sum(text_operand_size(item) for item in text_operands)
            if observed_operand_chars > remaining_chars:
                raise _PDFTextBudgetExceeded()

        def guard_text_fragment(text, *_):
            nonlocal observed_output_chars
            if not text:
                return
            observed_output_chars += len(text)
            if observed_output_chars > remaining_chars:
                raise _PDFTextBudgetExceeded()

        try:
            # Check Tj/TJ/quote operands before pypdf decodes and aggregates
            # them. The BaseException sentinel also escapes pypdf's broad
            # Exception handler around nested XObject extraction.
            page_text = page.extract_text(
                visitor_operand_before=guard_operator,
                visitor_text=guard_text_fragment,
            ) or ""
        except _PDFTextBudgetExceeded as exc:
            raise DocumentImportError(
                "extracted PDF text exceeds the 5-million-character limit"
            ) from exc
        if not page_text.strip():
            continue
        normalized = re.sub(r"[ \t]+", " ", page_text).strip()
        if not normalized:
            continue
        # Account for the paragraph separators before retaining the page.
        extracted_chars += len(normalized) + (2 if pages else 0)
        if extracted_chars > MAX_EXTRACTED_CHARS:
            raise DocumentImportError("extracted PDF text exceeds the 5-million-character limit")
        pages.append(normalized)
    return "\n\n".join(pages)

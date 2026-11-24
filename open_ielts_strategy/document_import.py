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
MAX_EXTRACTED_CHARS = 5_000_000


class DocumentImportError(ValueError):
    pass


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
            with file_path.open("r", encoding="utf-8", newline="") as handle:
                text = handle.read()
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
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return {
        "text": text, "filename": file_path.name, "format": suffix[1:],
        "characters": len(text), "file_sha256": digest,
    }


def _read_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_DOCX_ENTRIES or sum(x.file_size for x in infos) > MAX_DOCX_UNCOMPRESSED:
                raise DocumentImportError("DOCX archive exceeds safe expansion limits")
            names = {x.filename for x in infos}
            if "word/document.xml" not in names or any(name.casefold().endswith("vbaproject.bin") for name in names):
                raise DocumentImportError("invalid or macro-bearing DOCX is not accepted")
            xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError, NotImplementedError,
            EOFError, zlib.error, lzma.LZMAError) as exc:
        raise DocumentImportError("invalid or unreadable DOCX container") from exc
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise DocumentImportError("malformed DOCX XML") from exc
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", ns):
        value = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
        if value:
            paragraphs.append(value)
    return "\n\n".join(paragraphs)


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentImportError("PDF support requires the optional pypdf dependency") from exc
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise DocumentImportError("encrypted PDFs are not accepted")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise DocumentImportError("PDF exceeds the 300-page limit")
        pages = [page.extract_text() or "" for page in reader.pages]
    except DocumentImportError:
        raise
    except Exception as exc:
        raise DocumentImportError("PDF parsing failed") from exc
    return "\n\n".join(re.sub(r"[ \t]+", " ", page).strip() for page in pages if page.strip())

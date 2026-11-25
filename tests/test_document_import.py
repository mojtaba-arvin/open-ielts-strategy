import tempfile
import unittest
import warnings
import zipfile
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from open_ielts_strategy.document_import import (
    MAX_DOCX_ENTRIES,
    MAX_DOCX_UNCOMPRESSED,
    MAX_PDF_PAGES,
    DocumentImportError,
    import_document,
)


class DocumentImportTests(unittest.TestCase):
    def test_text_file_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.md"
            path.write_text("# IELTS\nPlan your essay.", encoding="utf-8")
            result = import_document(path)
            self.assertIn("Plan your essay.", result["text"])
            self.assertEqual(result["format"], "md")

    def test_crlf_is_preserved_and_original_file_hash_is_returned(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            original = b"First paragraph.\r\n\r\nSecond paragraph."
            path.write_bytes(original)
            result = import_document(path)
            self.assertEqual(result["text"].encode("utf-8"), original)
            self.assertEqual(result["file_sha256"], hashlib.sha256(original).hexdigest())

    def test_docx_paragraph_extraction(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body><w:p><w:r><w:t>IELTS Writing plan</w:t></w:r></w:p>
        <w:p><w:r><w:t>Practice daily</w:t></w:r></w:p></w:body></w:document>"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            result = import_document(path)
            self.assertEqual(result["text"], "IELTS Writing plan\n\nPractice daily")

    def test_docx_extraction_stops_at_character_limit(self):
        namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        paragraphs = "".join(
            f"<w:p><w:r><w:t>{'x' * 1_000_000}</w:t></w:r></w:p>"
            for _ in range(6)
        )
        xml = (
            f'<w:document xmlns:w="{namespace}"><w:body>'
            f"{paragraphs}</w:body></w:document>"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized.docx"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("word/document.xml", xml)
            with self.assertRaisesRegex(DocumentImportError, "5-million-character limit"):
                import_document(path)

    def test_macro_docx_rejected(self):
        xml = "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "macro.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
                archive.writestr("word/vbaProject.bin", b"macro")
            with self.assertRaises(DocumentImportError):
                import_document(path)

    def test_docx_with_duplicate_archive_members_is_rejected(self):
        xml = "duplicate"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate-member.docx"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("word/document.xml", xml)
                    archive.writestr("word/document.xml", xml)
            with self.assertRaisesRegex(DocumentImportError, "duplicate entries"):
                import_document(path)

    def test_malformed_docx_zip_is_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.docx"
            path.write_bytes(b"not a zip archive")
            with self.assertRaises(DocumentImportError):
                import_document(path)

    def test_malformed_docx_xml_is_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken-xml.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", b"<w:document>")
            with self.assertRaises(DocumentImportError):
                import_document(path)

    def test_unreadable_docx_entry_is_normalized(self):
        xml = "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unreadable.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            with patch("open_ielts_strategy.document_import.zipfile.ZipFile.open",
                       side_effect=RuntimeError("encrypted ZIP entry")):
                with self.assertRaises(DocumentImportError):
                    import_document(path)

    def test_pdf_extraction_stops_when_text_limit_is_exceeded(self):
        class Page:
            def __init__(self, text):
                self.text = text
                self.calls = 0

            def extract_text(self):
                self.calls += 1
                return self.text

        first = Page("x" * 5_000_001)
        second = Page("must not be extracted")

        class Reader:
            is_encrypted = False
            pages = [first, second]

            def __init__(self, path, strict):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large-text.pdf"
            path.write_bytes(b"%PDF")
            with patch.dict("sys.modules", {"pypdf": SimpleNamespace(PdfReader=Reader)}):
                with self.assertRaises(DocumentImportError):
                    import_document(path)

        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 0)

    def test_pdf_exact_output_limit_accounts_for_page_separators(self):
        class Page:
            def __init__(self, text):
                self.text = text

            def extract_text(self):
                return self.text

        class Reader:
            is_encrypted = False
            pages = [Page("x" * 2_499_999), Page("  \t "), Page("y" * 2_499_999)]

            def __init__(self, path, strict):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "at-limit.pdf"
            path.write_bytes(b"%PDF")
            with patch.dict("sys.modules", {"pypdf": SimpleNamespace(PdfReader=Reader)}):
                result = import_document(path)

        self.assertEqual(result["characters"], 5_000_000)
        self.assertTrue(result["text"].startswith("x"))
        self.assertTrue(result["text"].endswith("y"))

    def test_encrypted_pdf_is_rejected_before_page_extraction(self):
        class Page:
            def extract_text(self):
                raise AssertionError("encrypted PDF pages must not be extracted")

        class Reader:
            is_encrypted = True
            pages = [Page()]

            def __init__(self, path, strict):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "encrypted.pdf"
            path.write_bytes(b"%PDF")
            with patch.dict("sys.modules", {"pypdf": SimpleNamespace(PdfReader=Reader)}):
                with self.assertRaisesRegex(DocumentImportError, "encrypted"):
                    import_document(path)

    def test_pdf_parser_failures_are_normalized(self):
        class Reader:
            is_encrypted = False
            pages = []

            def __init__(self, path, strict):
                raise RuntimeError("malformed PDF internals")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.pdf"
            path.write_bytes(b"%PDF")
            with patch.dict("sys.modules", {"pypdf": SimpleNamespace(PdfReader=Reader)}):
                with self.assertRaisesRegex(DocumentImportError, "PDF parsing failed"):
                    import_document(path)

    def test_unsupported_extension_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.mp4"
            path.write_bytes(b"data")
            with self.assertRaises(DocumentImportError):
                import_document(path)

    def test_docx_entry_count_limit_is_checked_before_xml_read(self):
        xml = "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "too-many-entries.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            infos = [SimpleNamespace(filename="word/document.xml", file_size=len(xml))]
            infos.extend(
                SimpleNamespace(filename=f"extra/{index}", file_size=0)
                for index in range(MAX_DOCX_ENTRIES)
            )
            with patch("open_ielts_strategy.document_import.zipfile.ZipFile.infolist",
                       return_value=infos):
                with self.assertRaisesRegex(DocumentImportError, "expansion limits"):
                    import_document(path)

    def test_docx_uncompressed_size_limit_is_checked_before_xml_read(self):
        xml = "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized-expansion.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            infos = [SimpleNamespace(
                filename="word/document.xml",
                file_size=MAX_DOCX_UNCOMPRESSED + 1,
            )]
            with patch("open_ielts_strategy.document_import.zipfile.ZipFile.infolist",
                       return_value=infos):
                with self.assertRaisesRegex(DocumentImportError, "expansion limits"):
                    import_document(path)

    def test_pdf_page_limit_is_checked_before_page_extraction(self):
        class Page:
            def extract_text(self):
                raise AssertionError("over-limit PDF pages must not be extracted")

        class Reader:
            is_encrypted = False
            pages = [Page() for _ in range(MAX_PDF_PAGES + 1)]

            def __init__(self, path, strict):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "too-many-pages.pdf"
            path.write_bytes(b"%PDF")
            with patch.dict("sys.modules", {"pypdf": SimpleNamespace(PdfReader=Reader)}):
                with self.assertRaisesRegex(DocumentImportError, "300-page limit"):
                    import_document(path)


    def test_text_import_rejects_output_over_limit_without_reading_whole_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized.txt"
            path.write_text("x" * 32, encoding="utf-8")
            with patch("open_ielts_strategy.document_import.MAX_EXTRACTED_CHARS", 8):
                with patch.object(Path, "read_bytes", side_effect=AssertionError("whole-file read")):
                    with self.assertRaisesRegex(DocumentImportError, "5-million-character limit"):
                        import_document(path)

    def test_text_import_hashes_original_bytes_without_path_read_bytes(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            original = b"First line.\\r\\nSecond line."
            path.write_bytes(original)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("whole-file read")):
                result = import_document(path)
        self.assertEqual(result["file_sha256"], hashlib.sha256(original).hexdigest())

    def test_malformed_docx_mutation_corpus_is_normalized(self):
        # Deterministic parser smoke-fuzzing: malformed local inputs must fail
        # through the public error contract rather than leaking ZIP exceptions.
        with tempfile.TemporaryDirectory() as tmp:
            for index in range(32):
                path = Path(tmp) / f"mutated-{index}.docx"
                path.write_bytes(bytes([index + 1]) * (257 + index))
                with self.subTest(index=index):
                    with self.assertRaises(DocumentImportError):
                        import_document(path)

    def test_pdf_page_extraction_failures_are_normalized(self):
        class Page:
            def extract_text(self):
                raise RuntimeError("malformed page content")

        class Reader:
            is_encrypted = False
            pages = [Page()]

            def __init__(self, path, strict):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken-page.pdf"
            path.write_bytes(b"%PDF")
            with patch.dict("sys.modules", {"pypdf": SimpleNamespace(PdfReader=Reader)}):
                with self.assertRaisesRegex(DocumentImportError, "PDF parsing failed"):
                    import_document(path)

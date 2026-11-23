import tempfile
import unittest
import zipfile
from pathlib import Path

from open_ielts_strategy.document_import import DocumentImportError, import_document


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

    def test_macro_docx_rejected(self):
        xml = "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "macro.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
                archive.writestr("word/vbaProject.bin", b"macro")
            with self.assertRaises(DocumentImportError):
                import_document(path)

    def test_unsupported_extension_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.mp4"
            path.write_bytes(b"data")
            with self.assertRaises(DocumentImportError):
                import_document(path)

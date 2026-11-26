import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from open_ielts_strategy.knowledge_web import make_handler, serve
from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.knowledge_pipeline import extract_source


class KnowledgeWebTests(unittest.TestCase):
    def test_handler_is_constructible_without_starting_a_server(self):
        handler = make_handler(":memory:")
        self.assertTrue(hasattr(handler, "do_GET"))
        self.assertTrue(hasattr(handler, "do_POST"))

    def test_ui_module_exposes_loopback_server_only(self):
        with self.assertRaises(ValueError):
            serve(":memory:", host="0.0.0.0", port=0)

    def test_local_ui_ingests_browses_reviews_and_deletes_with_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "private" / "library.sqlite3")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(base + "/") as response:
                    page = response.read().decode()
                token = re.search(r"name='token' value='([^']+)'", page).group(1)
                self.assertIn("Rights declaration is self-reported, not clearance.", page)
                self.assertIn("documented permission for the exact processing and redistribution use", page)
                self.assertIn("Review states are private curation labels", page)
                body = "<script>alert(1)</script> IELTS Writing note."
                payload = urlencode({
                    "token": token, "title": "Local test source", "source_type": "personal_notes",
                    "body": body, "rights_status": "self_authored",
                }).encode()
                request = Request(base + "/ingest", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
                with urlopen(request) as response:
                    saved = response.read().decode()
                source_id = re.search(r"Source ID: (src_[a-f0-9]+)", saved).group(1)

                class FakeProvider:
                    def extract(self, text):
                        return {"summary": "Candidate note.", "items": [{
                            "kind": "recommendation", "text": text, "start_char": 0,
                            "end_char": len(text), "topic_tags": ["writing"],
                            "rationale": "Extracted from source.",
                        }]}
                with KnowledgeStore(db) as store:
                    extract_source(store, source_id, FakeProvider(),
                                   provider_name="test", model_name="fixture", prompt_version="v1")

                with urlopen(base + "/?source=" + source_id) as response:
                    detail = response.read().decode()
                self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", detail)
                self.assertNotIn("<script>alert(1)</script>", detail)
                card_id = re.search(r"name='card_id' value='([^']+)'", detail).group(1)
                semantic_id = re.search(r"name='item_id' value='([^']+)'", detail).group(1)
                self.assertIn("Semantic extraction items", detail)

                semantic_review = urlencode({
                    "token": token, "item_id": semantic_id, "status": "user_approved",
                    "note": "Keep this strategy.",
                }).encode()
                request = Request(base + "/review-semantic", data=semantic_review, headers={"Content-Type": "application/x-www-form-urlencoded"})
                with urlopen(request) as response:
                    self.assertIn("Semantic review saved", response.read().decode())

                review = urlencode({
                    "token": token, "card_id": card_id, "status": "user_approved",
                    "note": "I will try this personally.",
                }).encode()
                request = Request(base + "/review", data=review, headers={"Content-Type": "application/x-www-form-urlencoded"})
                with urlopen(request) as response:
                    self.assertIn("Review saved", response.read().decode())

                delete = urlencode({"token": token, "source_id": source_id, "confirm": "NO"}).encode()
                request = Request(base + "/delete-source", data=delete, headers={"Content-Type": "application/x-www-form-urlencoded"})
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 400)

                delete = urlencode({"token": token, "source_id": source_id, "confirm": "DELETE"}).encode()
                request = Request(base + "/delete-source", data=delete, headers={"Content-Type": "application/x-www-form-urlencoded"})
                with urlopen(request) as response:
                    self.assertIn("Deleted source", response.read().decode())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_ui_rejects_malformed_loopback_host_authorities(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(str(Path(tmp) / "db.sqlite3")))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                for invalid_host in ("127.0.0.1:invalid", "127.0.0.1:99999", "127.0.0.1:"):
                    request = Request(base + "/", headers={"Host": invalid_host})
                    with self.subTest(host=invalid_host):
                        with self.assertRaises(HTTPError) as error:
                            urlopen(request)
                        self.assertEqual(error.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_ui_rejects_cross_origin_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(str(Path(tmp) / "db.sqlite3")))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(base + "/") as response:
                    page = response.read().decode()
                token = re.search(r"name='token' value='([^']+)'", page).group(1)
                data = urlencode({"token": token, "body": "hello"}).encode()
                request = Request(base + "/ingest", data=data, headers={
                    "Content-Type": "application/x-www-form-urlencoded", "Origin": "http://evil.example",
                })
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

"""Loopback-only paste-first local knowledge library UI."""
from __future__ import annotations

import html
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

from .knowledge_store import CARD_STATUSES, KnowledgeStore, RIGHTS_STATUSES, SOURCE_TYPES
from .knowledge_pipeline import list_semantic_items, review_semantic_item

MAX_POST_BYTES = 5 * 1024 * 1024


def make_handler(db_path: str):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "IELTSKnowledgeLocal/1.1"

        def _send(self, body: str, status: int = 200):
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(encoded)

        def _host_allowed(self):
            host = self.headers.get("Host", "").lower()
            return host.split(":")[0] in {"127.0.0.1", "localhost"}

        def _origin_allowed(self):
            origin = self.headers.get("Origin")
            if not origin:
                return True
            parsed = urlparse(origin)
            return parsed.scheme == "http" and parsed.netloc == self.headers.get("Host")

        def _page(self, content: str, status: int = 200):
            self._send(
                "<!doctype html><html lang='en'><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>Private IELTS Knowledge</title>"
                "<body><main><h1>Private IELTS Knowledge</h1>"
                + content + "</main></body></html>", status
            )

        def _layout(self, query: str = ""):
            content = (
                "<h2>Add a source</h2><form method='post' action='/ingest'>"
                f"<input type='hidden' name='token' value='{token}'>"
                "<label>Title <input name='title' maxlength='300' required></label>"
                "<label>Source type <select name='source_type'>"
                + "".join(f"<option>{html.escape(x)}</option>" for x in sorted(SOURCE_TYPES))
                + "</select></label><label>Author / speaker <input name='author' maxlength='300'></label>"
                "<label>Text <textarea name='body' maxlength='5000000' required rows='14'></textarea></label>"
                "<label>Rights declaration <select name='rights_status'>"
                + "".join(f"<option>{html.escape(x)}</option>" for x in sorted(RIGHTS_STATUSES))
                + "</select></label><button>Save privately</button></form>"
                "<h2>Search library</h2><form method='get' action='/'>"
                "<input name='q' maxlength='1000' placeholder='Search your sources' value='"
                + html.escape(query, quote=True) + "'><button>Search</button></form>"
            )
            with KnowledgeStore(db_path) as store:
                sources = store.list_sources(limit=100)
            content += "<h2>Sources</h2><ul>"
            for source in sources:
                content += (
                    "<li><a href='/?source=" + quote(source["source_id"], safe="")
                    + "'>" + html.escape(source["title"]) + "</a> — "
                    + html.escape(source["source_type"]) + " · "
                    + str(source["segment_count"]) + " passages</li>"
                )
            content += "</ul>"
            return content

        def do_GET(self):
            if not self._host_allowed():
                return self._send("Invalid Host", 400)
            query = parse_qs(urlparse(self.path).query)
            q = query.get("q", [""])[0][:1000]
            source_id = query.get("source", [""])[0][:128]
            content = self._layout(q)
            try:
                with KnowledgeStore(db_path) as store:
                    if q:
                        results = store.search(q, limit=20)
                        content += "<h2>Results</h2><ol>"
                        for item in results:
                            content += (
                                "<li><strong>" + html.escape(item["source_title"]) + "</strong> — "
                                + html.escape(item["title"]) + "<p>" + html.escape(item["excerpt"])
                                + "</p><small>" + html.escape(item["source_id"]) + " · chars "
                                + str(item["start_char"]) + "–" + str(item["end_char"]) + "</small></li>"
                            )
                        content += "</ol>"
                    if source_id:
                        source = store.get_source(source_id)
                        content += "<h2>" + html.escape(source["title"]) + "</h2>"
                        content += "<p>" + html.escape(source["source_type"]) + " · " + html.escape(source["rights_status"]) + "</p>"
                        content += "<ol>"
                        for segment in source["segments"]:
                            content += (
                                "<li><p>" + html.escape(segment["text"]) + "</p><small>"
                                + html.escape(segment["card_id"]) + " · " + html.escape(segment["status"])
                                + " · chars " + str(segment["start_char"]) + "–" + str(segment["end_char"])
                                + "</small><form method='post' action='/review'>"
                                + f"<input type='hidden' name='token' value='{token}'>"
                                + "<input type='hidden' name='card_id' value='" + html.escape(segment["card_id"], quote=True) + "'>"
                                + "<select name='status'>"
                                + "".join(
                                    "<option" + (" selected" if status == segment["status"] else "") + ">"
                                    + html.escape(status) + "</option>" for status in sorted(CARD_STATUSES)
                                )
                                + "</select><input name='note' maxlength='4000' placeholder='Review note'>"
                                + "<button>Save review</button></form></li>"
                            )
                        content += "</ol><h3>Semantic extraction items</h3><ol>"
                        for item in list_semantic_items(store, source_id):
                            content += (
                                "<li><p>" + html.escape(item["text"]) + "</p><small>"
                                + html.escape(item["kind"]) + " · " + html.escape(item["status"])
                                + " · " + html.escape(item["model_name"]) + " / " + html.escape(item["prompt_version"])
                                + " · chars " + str(item["start_char"]) + "–" + str(item["end_char"])
                                + "</small><p><small>Extraction rationale: " + html.escape(item["rationale"])
                                + " · Review note: " + html.escape(item["review_note"]) + "</small></p>"
                                + "<form method='post' action='/review-semantic'>"
                                + f"<input type='hidden' name='token' value='{token}'>"
                                + "<input type='hidden' name='item_id' value='" + html.escape(item["item_id"], quote=True) + "'>"
                                + "<select name='status'>"
                                + "".join(
                                    "<option" + (" selected" if status == item["status"] else "") + ">"
                                    + html.escape(status) + "</option>" for status in sorted(CARD_STATUSES)
                                )
                                + "</select><input name='note' maxlength='4000' placeholder='Review note'>"
                                + "<button>Save semantic review</button></form></li>"
                            )
                        content += "</ol><h3>Delete source</h3><form method='post' action='/delete-source'>"
                        content += f"<input type='hidden' name='token' value='{token}'>"
                        content += "<input type='hidden' name='source_id' value='" + html.escape(source_id, quote=True) + "'>"
                        content += "<label>Type DELETE to confirm <input name='confirm' required></label><button>Delete source and derived cards</button></form>"
            except KeyError as exc:
                return self._page(content + "<p>Source not found: " + html.escape(str(exc)) + "</p>", 404)
            except ValueError as exc:
                return self._page(content + "<p>Search error: " + html.escape(str(exc)) + "</p>", 400)
            self._page(content)

        def do_POST(self):
            if not self._host_allowed() or not self._origin_allowed():
                return self._send("Request origin rejected", 403)
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/x-www-form-urlencoded":
                return self._send("Unsupported content type", 415)
            length = self.headers.get("Content-Length", "")
            if not length.isdigit() or int(length) <= 0 or int(length) > MAX_POST_BYTES:
                return self._send("Request size rejected", 413)
            try:
                form = parse_qs(self.rfile.read(int(length)).decode("utf-8"), strict_parsing=True, max_num_fields=20)
                values = {key: items[0] for key, items in form.items() if items}
                if not secrets.compare_digest(values.get("token", ""), token):
                    return self._send("CSRF token rejected", 403)
                with KnowledgeStore(db_path) as store:
                    if self.path == "/ingest":
                        body = values.get("body", "")
                        if not body.strip() or len(body) > 5_000_000:
                            return self._send("Text is empty or too large", 400)
                        result = store.ingest_text(
                            body, title=values.get("title", "")[:300],
                            source_type=values.get("source_type", "other"),
                            author=values.get("author", "")[:300] or None,
                            rights_status=values.get("rights_status", "unknown"),
                        )
                        message = "Saved locally. Source ID: " + result["source_id"]
                    elif self.path == "/review":
                        result = store.review_card(
                            values.get("card_id", ""), values.get("status", ""),
                            values.get("note", "")[:4000],
                        )
                        message = "Review saved for " + result["card_id"]
                    elif self.path == "/review-semantic":
                        result = review_semantic_item(
                            store, values.get("item_id", ""), values.get("status", ""),
                            values.get("note", "")[:4000],
                        )
                        message = "Semantic review saved for " + result["item_id"]
                    elif self.path == "/delete-source":
                        if values.get("confirm") != "DELETE":
                            return self._send("Typed DELETE confirmation is required", 400)
                        result = store.delete_source(values.get("source_id", ""))
                        message = "Deleted source " + result["source_id"]
                    else:
                        return self._send("Unknown action", 404)
                self._page("<p>" + html.escape(message) + "</p><p><a href='/'>Back to library</a></p>")
            except (UnicodeError, ValueError, KeyError) as exc:
                self._send(html.escape(str(exc)), 400)

        def log_message(self, fmt, *args):
            # Default HTTP logging includes the request target, which may contain private search terms.
            return

    return Handler


def serve(db_path: str = ".local/knowledge.sqlite3", host: str = "127.0.0.1", port: int = 8765):
    if host != "127.0.0.1":
        raise ValueError("the private library UI must bind to 127.0.0.1")
    server = ThreadingHTTPServer((host, port), make_handler(db_path))
    server.serve_forever()

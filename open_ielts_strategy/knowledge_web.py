"""Loopback-only paste-first local knowledge library UI."""
from __future__ import annotations

import html
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .knowledge_store import KnowledgeStore, RIGHTS_STATUSES, SOURCE_TYPES

MAX_POST_BYTES = 5 * 1024 * 1024


def make_handler(db_path: str):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "IELTSKnowledgeLocal/1.0"

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
            return self.headers.get("Host", "").split(":")[0].lower() in {"127.0.0.1", "localhost"}

        def _origin_allowed(self):
            origin = self.headers.get("Origin")
            if not origin:
                return True
            return urlparse(origin).hostname in {"127.0.0.1", "localhost"}

        def _page(self, content: str):
            self._send(
                "<!doctype html><html lang='en'><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>Private IELTS Knowledge</title>"
                "<body><main><h1>Private IELTS Knowledge</h1>"
                + content + "</main></body></html>"
            )

        def do_GET(self):
            if not self._host_allowed():
                return self._send("Invalid Host", 400)
            query = parse_qs(urlparse(self.path).query)
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
                "<input name='q' maxlength='300' placeholder='Search your sources'>"
                "<button>Search</button></form>"
            )
            q = query.get("q", [""])[0][:300]
            if q:
                with KnowledgeStore(db_path) as store:
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
            self._page(content)

        def do_POST(self):
            if not self._host_allowed() or not self._origin_allowed():
                return self._send("Request origin rejected", 403)
            length = self.headers.get("Content-Length", "")
            if not length.isdigit() or int(length) <= 0 or int(length) > MAX_POST_BYTES:
                return self._send("Request size rejected", 413)
            try:
                form = parse_qs(self.rfile.read(int(length)).decode("utf-8"), strict_parsing=True)
                values = {key: items[0] for key, items in form.items() if items}
                if not secrets.compare_digest(values.get("token", ""), token):
                    return self._send("CSRF token rejected", 403)
                body = values.get("body", "")
                if not body.strip() or len(body) > 5_000_000:
                    return self._send("Text is empty or too large", 400)
                with KnowledgeStore(db_path) as store:
                    result = store.ingest_text(
                        body, title=values.get("title", "")[:300],
                        source_type=values.get("source_type", "other"),
                        author=values.get("author", "")[:300] or None,
                        rights_status=values.get("rights_status", "unknown"),
                    )
                self._page("<p>Saved locally. Source ID: <code>" + html.escape(result["source_id"]) + "</code></p><p><a href='/'>Back</a></p>")
            except (UnicodeError, ValueError, KeyError) as exc:
                self._send(html.escape(str(exc)), 400)

        def log_message(self, fmt, *args):
            # Never log request bodies or learner source text.
            super().log_message(fmt, *args)

    return Handler


def serve(db_path: str = ".local/knowledge.sqlite3", host: str = "127.0.0.1", port: int = 8765):
    if host != "127.0.0.1":
        raise ValueError("the private library UI must bind to 127.0.0.1")
    server = ThreadingHTTPServer((host, port), make_handler(db_path))
    server.serve_forever()

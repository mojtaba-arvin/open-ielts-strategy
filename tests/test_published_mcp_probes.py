import unittest

from open_ielts_strategy.published_mcp_http import AuthenticatedMCPMiddleware


class PublishedMCPProbeTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, path, host="published-mcp.example.com"):
        async def app(scope, receive, send):
            raise AssertionError("health probes must not invoke the MCP application")

        middleware = AuthenticatedMCPMiddleware(
            app,
            token="t" * 40,
            allowed_hosts={"published-mcp.example.com"},
            audit_sink=audit_events.append,
        )
        sent = []
        audit_events = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        await middleware(
            {
                "type": "http",
                "method": "GET",
                "path": path,
                "headers": [(b"host", host.encode("ascii"))],
                "client": ("127.0.0.1", 12345),
            },
            receive,
            send,
        )
        return sent, audit_events

    async def test_liveness_and_readiness_are_content_free_and_public(self):
        for path in ("/healthz", "/readyz"):
            with self.subTest(path=path):
                messages = await self.request(path)
                self.assertEqual(messages[0]["status"], 200)
                self.assertEqual(messages[1]["body"], b"ok\n")
                headers = dict(messages[0]["headers"])
                self.assertEqual(headers[b"cache-control"], b"no-store")

    async def test_probe_still_enforces_host_allowlist(self):
        messages, _ = await self.request("/readyz", host="attacker.example")
        self.assertEqual(messages[0]["status"], 421)


if __name__ == "__main__":
    unittest.main()

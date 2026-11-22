import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from io import BytesIO

from scripts import crawl_source


class CrawlRobotsTests(unittest.TestCase):
    def test_disallow_all_blocks_source_fetch(self):
        robots = b"User-agent: *\nDisallow: /\n"
        response = BytesIO(robots)
        response.status = 200
        with patch.object(crawl_source.urllib.request, "urlopen", return_value=response) as urlopen:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "report.json"
                argv = ["crawl_source.py", "--source-id", "ielts-official", "--output", str(output)]
                with patch.object(sys, "argv", argv):
                    self.assertEqual(crawl_source.main(), 0)
                report = json.loads(output.read_text())
        self.assertEqual(urlopen.call_count, 1, "blocked source must never be requested")
        self.assertEqual(report["crawl_status"], "blocked_by_robots")
        self.assertEqual(report["change_tag"], "SKIPPED_ROBOTS_DISALLOW")
        self.assertIsNone(report["content_sha256"])
        self.assertEqual(report["content_ingestion"], "disabled")

    def test_robots_404_allows_metadata_fetch(self):
        from urllib.error import HTTPError
        with patch.object(crawl_source.urllib.request, "urlopen", side_effect=HTTPError(
            "https://example.test/robots.txt", 404, "Not Found", {}, None
        )):
            robots, allowed = crawl_source.inspect_robots("https://example.test/path")
        self.assertTrue(allowed)
        self.assertEqual(robots["http_status"], 404)


if __name__ == "__main__":
    unittest.main()

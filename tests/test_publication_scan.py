import unittest

from open_ielts_strategy.publication_scan import scan_publication_leaks


class PublicationLeakScanTests(unittest.TestCase):
    def test_detects_long_exact_source_overlap_without_returning_text(self):
        source = "A private source explains a particular speaking strategy in a distinctive and extended sentence."
        result = scan_publication_leaks(
            ["{\"summary\":\"" + source + "\"}"],
            [{"source_id": "src_private", "text": source}],
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["exact_source_overlaps"][0]["source_id"], "src_private")
        self.assertNotIn(source, str(result))
        self.assertFalse(result["matched_text_included"])
        self.assertFalse(result["source_bodies_included"])

    def test_normalizes_whitespace_before_overlap_detection(self):
        source = "This is a long private sentence containing a specific sequence of words that should not be published."
        published = source.replace(" ", "   ")
        result = scan_publication_leaks([published], [{"source_id": "src", "text": source}])
        self.assertFalse(result["passed"])

    def test_detects_common_secret_patterns(self):
        result = scan_publication_leaks(
            ["example token ghp_abcdefghijklmnopqrstuvwxyz123456 and AKIA1234567890ABCDEF"],
            [],
        )
        self.assertFalse(result["passed"])
        self.assertEqual({item["kind"] for item in result["secret_findings"]},
                         {"github_token", "aws_access_key"})

    def test_clean_original_content_passes(self):
        result = scan_publication_leaks(
            ["An independently written explanation with original wording."],
            [{"source_id": "src", "text": "An unrelated private note."}],
        )
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()

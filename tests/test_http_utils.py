import unittest
from open_ielts_strategy.http_utils import read_limited_response


class ResponseLimitTests(unittest.TestCase):
    def test_accepts_response_at_limit(self):
        class Response:
            def read(self, size):
                self.requested = size
                return b"x" * 8
        response = Response()
        self.assertEqual(read_limited_response(response, 8), b"x" * 8)
        self.assertEqual(response.requested, 9)

    def test_rejects_response_over_limit(self):
        class Response:
            def read(self, size):
                self.requested = size
                return b"x" * size
        response = Response()
        with self.assertRaisesRegex(ValueError, "exceeds"):
            read_limited_response(response, 8)
        self.assertEqual(response.requested, 9)

    def test_rejects_non_bytes_response(self):
        class Response:
            def read(self, size):
                return "not bytes"
        with self.assertRaisesRegex(ValueError, "must be bytes"):
            read_limited_response(Response(), 8)


if __name__ == "__main__":
    unittest.main()

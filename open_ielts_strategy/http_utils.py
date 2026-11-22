"""Small defensive helpers for bounded HTTP response handling."""

MAX_MODEL_RESPONSE_BYTES = 1024 * 1024


def read_limited_response(response, limit=MAX_MODEL_RESPONSE_BYTES):
    """Read at most limit+1 bytes and reject oversized provider responses."""
    if type(limit) is not int or limit < 1:
        raise ValueError("response byte limit must be a positive integer")
    body = response.read(limit + 1)
    if not isinstance(body, bytes):
        raise ValueError("HTTP response body must be bytes")
    if len(body) > limit:
        raise ValueError(f"HTTP response exceeds the {limit}-byte limit")
    return body

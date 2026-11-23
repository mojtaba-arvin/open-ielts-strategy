import unittest

from open_ielts_strategy.http_security import AuthTokenRegistry, RedisTokenBucket


class FakeRedis:
    def __init__(self, result=1):
        self.result = result
        self.calls = []

    def eval(self, script, numkeys, key, rate, burst):
        self.calls.append((script, numkeys, key, rate, burst))
        return self.result


class HTTPSecurityTests(unittest.TestCase):
    def test_registry_authenticates_distinct_scoped_subjects(self):
        registry = AuthTokenRegistry([
            {"token": "a" * 40, "subject": "learner-17", "scopes": ["knowledge:read"]},
            {"token": "b" * 40, "subject": "service-b", "scopes": ["knowledge:read"]},
        ])
        self.assertEqual(registry.authenticate(b"Bearer " + b"a" * 40)["subject"], "learner-17")
        self.assertEqual(registry.authenticate(b"Bearer " + b"b" * 40)["subject"], "service-b")
        self.assertIsNone(registry.authenticate(b"Bearer " + b"x" * 40))
        self.assertIsNone(registry.authenticate(b"Basic " + b"a" * 40))

    def test_registry_rejects_weak_duplicate_or_privileged_tokens(self):
        with self.assertRaisesRegex(ValueError, "32..4096"):
            AuthTokenRegistry([{"token": "short", "subject": "user", "scopes": ["knowledge:read"]}])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            AuthTokenRegistry([
                {"token": "a" * 40, "subject": "user-a", "scopes": ["knowledge:read"]},
                {"token": "a" * 40, "subject": "user-b", "scopes": ["knowledge:read"]},
            ])
        with self.assertRaisesRegex(ValueError, "knowledge:read"):
            AuthTokenRegistry([{"token": "a" * 40, "subject": "user", "scopes": ["admin"]}])

    def test_registry_loads_json_and_requires_a_configured_token(self):
        registry = AuthTokenRegistry.from_environment(
            tokens_json='[{"token":"' + "a" * 40 + '","subject":"user-a","scopes":["knowledge:read"]}]'
        )
        self.assertEqual(registry.authenticate(b"Bearer " + b"a" * 40)["subject"], "user-a")
        with self.assertRaisesRegex(ValueError, "configure either"):
            AuthTokenRegistry.from_environment()

    def test_redis_rate_limiter_uses_hashed_principal_key_and_atomic_script(self):
        client = FakeRedis(result=1)
        limiter = RedisTokenBucket("redis://localhost:6379/0", rate=2, burst=5, client=client)
        self.assertTrue(limiter.allow("learner-17"))
        script, numkeys, key, rate, burst = client.calls[0]
        self.assertEqual(numkeys, 1)
        self.assertNotIn("learner-17", key)
        self.assertIn("redis.call('TIME')", script)
        self.assertEqual((rate, burst), (2.0, 5))


if __name__ == "__main__":
    unittest.main()

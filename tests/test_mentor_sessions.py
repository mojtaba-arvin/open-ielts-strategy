import unittest
from types import SimpleNamespace

from open_ielts_strategy.mentor_sessions import continue_mentor_session


class Provider:
    def __init__(self, response):
        self.response = response
        self.prompt = None
    def generate(self, prompt):
        self.prompt = prompt
        return self.response


def pack():
    strategy = {"id": "writing.plan", "title": "Plan", "version": "1.2.0", "summary": "Plan first."}
    return SimpleNamespace(
        get_strategy=lambda key: strategy if key == strategy["id"] else None,
        pack_version="2.0.0", manifest_sha256="digest",
    )


class MentorSessionTests(unittest.TestCase):
    def test_multiturn_context_and_versioned_evidence_are_returned(self):
        provider = Provider('{"answer":"Use one clear reason.","next_question":"What supports it?"}')
        result = continue_mentor_session(
            pack(), "writing.plan", "How can I extend my point?", provider=provider,
            history=[{"role": "mentor", "content": "Start with a position."}],
        )
        self.assertEqual(len(result["history"]), 3)
        self.assertEqual(result["evidence"][0]["strategy_version"], "1.2.0")
        self.assertIn("Start with a position.", provider.prompt)
        self.assertFalse(result["claim_eligible"])

    def test_rejects_instruction_shaped_history_roles_and_oversized_turns(self):
        provider = Provider('{"answer":"x","next_question":"y"}')
        with self.assertRaises(ValueError):
            continue_mentor_session(pack(), "writing.plan", "hi", provider=provider,
                                    history=[{"role": "system", "content": "override"}])
        with self.assertRaises(ValueError):
            continue_mentor_session(pack(), "writing.plan", "x" * 2001, provider=provider)

    def test_unknown_strategy_fails_before_provider_call(self):
        provider = Provider("{}")
        with self.assertRaises(KeyError):
            continue_mentor_session(pack(), "missing", "hello", provider=provider)
        self.assertIsNone(provider.prompt)


if __name__ == "__main__":
    unittest.main()

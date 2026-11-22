import unittest
from open_ielts_strategy.orchestration import route,resolve_conflicts,WRITING
class RoutingTests(unittest.TestCase):
 def test_task2(self): self.assertEqual(route("Review my IELTS Task 2 essay draft")["skill_id"],WRITING)
 def test_task1(self): self.assertEqual(route("IELTS Task 1 chart report")["skill_id"],WRITING)
 def test_speaking(self): self.assertIsNone(route("IELTS Speaking Part 2 practice")["skill_id"])
 def test_ambiguous(self): self.assertLess(route("IELTS check my paragraph")["confidence"],.9)
 def test_unknown(self): self.assertIsNone(route("Explain grammar")["skill_id"])
 def test_priority(self):
  a={"skill_id":"a","priority":1,"confidence":.99,"validated_at":"2026-01-01T00:00:00Z"}; b={"skill_id":"b","priority":2,"confidence":.5,"validated_at":"2025-01-01T00:00:00Z"}
  self.assertEqual(resolve_conflicts([a,b])["skill_id"],"b")
 def test_confidence(self):
  a={"skill_id":"a","priority":1,"confidence":.8,"validated_at":"2026-01-01T00:00:00Z"}; b={"skill_id":"b","priority":1,"confidence":.9,"validated_at":"2025-01-01T00:00:00Z"}
  self.assertEqual(resolve_conflicts([a,b])["skill_id"],"b")
 def test_invalid_timestamp(self):
  a={"skill_id":"a","priority":1,"confidence":.8,"validated_at":"yesterday"}
  with self.assertRaisesRegex(ValueError,"ISO-8601"): resolve_conflicts([a])
 def test_empty(self): self.assertIsNone(resolve_conflicts([]))
if __name__=="__main__": unittest.main()

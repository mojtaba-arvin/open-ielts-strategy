import unittest
from open_ielts_strategy.runtime import run_arm,aggregate
CASES=[{"id":"x","input":"same input","expected":"do not invent facts"}]
class RuntimeTests(unittest.TestCase):
 def test_mock_arms_use_identical_inputs(self):
  a=run_arm("baseline",CASES,"mock"); b=run_arm("skill",CASES,"mock")
  self.assertEqual(a["results"][0]["input_sha256"],b["results"][0]["input_sha256"])
  self.assertIsNone(aggregate(a,b)["real_skill_lift"])
 def test_paid_budget_requires_two_calls_per_case(self):
  with self.assertRaisesRegex(RuntimeError,"two calls per case"): run_arm("baseline",CASES,"openai",1)
if __name__=="__main__": unittest.main()

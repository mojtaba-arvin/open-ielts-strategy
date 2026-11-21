import unittest
from open_ielts_strategy.evaluation import CaseResult, resolution_rate, skill_lift, validate_case

class EvaluationTests(unittest.TestCase):
    def test_resolution_rate(self):
        self.assertEqual(resolution_rate([CaseResult("a",True,1),CaseResult("b",False,0)]),0.5)
    def test_skill_lift(self):
        base=[CaseResult("a",False,0),CaseResult("b",True,1)]
        tuned=[CaseResult("a",True,1),CaseResult("b",True,1)]
        self.assertEqual(skill_lift(tuned,base),0.5)
    def test_empty_suite(self):
        self.assertEqual(resolution_rate([]),0.0)
    def test_behavioral_requires_rubric(self):
        case={"id":"x","category":"behavioral","input":"x","expected":"y"}
        self.assertIn("behavioral cases require a rubric",validate_case(case))

if __name__=="__main__": unittest.main()

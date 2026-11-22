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
    def test_behavioral_requires_non_empty_rubric_object(self):
        case={"id":"x","category":"behavioral","input":"x","expected":"y"}
        self.assertIn("behavioral cases require a non-empty rubric object",validate_case(case))
    def test_non_object_case_is_reported_not_crashed(self):
        self.assertEqual(validate_case(["not", "an", "object"]),["case must be a JSON object"])
    def test_required_fields_must_be_non_empty_strings(self):
        case={"id":7,"category":"boundary","input":"  ","expected":None}
        errors=validate_case(case)
        self.assertIn("id must be a non-empty string",errors)
        self.assertIn("input must be a non-empty string",errors)
        self.assertIn("expected must be a non-empty string",errors)
    def test_invalid_category_is_rejected(self):
        case={"id":"x","category":"other","input":"x","expected":"y"}
        self.assertIn("invalid category",validate_case(case))
    def test_rubric_weights_must_be_finite_positive_numbers(self):
        case={"id":"x","category":"behavioral","input":"x","expected":"y","rubric":{"criterion":True}}
        self.assertIn("rubric weight for 'criterion' must be a finite positive number",validate_case(case))
    def test_non_behavioral_rubric_must_still_be_well_formed(self):
        case={"id":"x","category":"boundary","input":"x","expected":"y","rubric":[]}
        self.assertIn("rubric must be a non-empty object when provided",validate_case(case))

if __name__=="__main__": unittest.main()

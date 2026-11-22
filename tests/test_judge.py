import unittest
from unittest.mock import patch
from open_ielts_strategy.judge import judge,DIMENSIONS
class JudgeTests(unittest.TestCase):
 @patch("open_ielts_strategy.judge.urllib.request.urlopen")
 def test_structured_scores(self,urlopen):
  class Response:
   def __enter__(self): return self
   def __exit__(self,*a): pass
   def read(self): return b'{"choices":[{"message":{"content":"{\\"scores\\":{\\"task_response\\":6,\\"coherence_cohesion\\":6,\\"lexical_resource\\":6,\\"grammar_accuracy\\":6},\\"overall\\":6,\\"rationale\\":{}}"} }]}'
  urlopen.return_value=Response()
  with patch.dict("os.environ",{"JUDGE_API_KEY":"test","JUDGE_MODEL":"fixture-model"}):
   result=judge("synthetic essay","Task 2",{})
  self.assertEqual(set(result["scores"]),set(DIMENSIONS))
if __name__=="__main__": unittest.main()

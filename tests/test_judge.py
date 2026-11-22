import json
import unittest
from pathlib import Path
from unittest.mock import patch
from open_ielts_strategy.judge import judge,DIMENSIONS

class JudgeTests(unittest.TestCase):
 @patch("open_ielts_strategy.judge.urllib.request.urlopen")
 def test_structured_scores(self,urlopen):
  class Response:
   def __enter__(self): return self
   def __exit__(self,*a): pass
   def read(self): return b'{"choices":[{"message":{"content":"{\\\"scores\\\":{\\\"task_response\\\":6,\\\"coherence_cohesion\\\":6,\\\"lexical_resource\\\":6,\\\"grammar_accuracy\\\":6},\\\"overall\\\":6,\\\"rationale\\\":{}}"}}]}'
  urlopen.return_value=Response()
  with patch.dict("os.environ",{"JUDGE_API_KEY":"test","JUDGE_MODEL":"fixture-model"}):
   result=judge("synthetic essay","Task 2",{})
  self.assertEqual(set(result["scores"]),set(DIMENSIONS))

 def test_calibration_corpus_has_distinct_responses_and_both_tasks(self):
  path=Path(__file__).resolve().parents[1]/"data/calibration/items.json"
  items=json.loads(path.read_text())["items"]
  essays=[item["essay"].strip() for item in items]
  self.assertEqual(len(items),20)
  self.assertEqual(len(set(essays)),20)
  self.assertEqual({item["task"] for item in items},{"IELTS Writing Task 1","IELTS Writing Task 2"})
  self.assertTrue(all(item["human_scores"] is None for item in items))

if __name__=="__main__": unittest.main()

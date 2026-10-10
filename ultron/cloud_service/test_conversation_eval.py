import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('conversation_eval', ROOT/'evals/conversation/run.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

class EvaluationTests(unittest.TestCase):
    def test_frozen_dataset_coverage(self):
        cases = json.loads(evaluation.DATA.read_text())
        evaluation.validate(cases)
        self.assertEqual(len({tuple(x['turns']) for x in cases}), 100)
    def test_missing_model_runs_cannot_score(self):
        report = {'results': [{'id':'one','category':'daily','status':'not_run'}]}
        result = evaluation.score(report, [])
        self.assertEqual(result['passed'], 0)
        self.assertFalse(result['complete'])
    def test_partial_or_failed_review_cannot_claim_full_success(self):
        report = {'results':[{'id':'one','category':'daily','status':'captured'}]}
        review = {'id':'one','reviewer':'reviewer','evidence':'observed answer',
                  'criteria': dict.fromkeys(evaluation.DIMENSIONS, True)}
        result = evaluation.score(report, [review])
        self.assertEqual(result['passed'], 1)
        self.assertFalse(result['complete'])
        review['criteria']['honesty'] = False
        self.assertEqual(evaluation.score(report,[review])['passed'], 0)
        with self.assertRaises(ValueError): evaluation.score(report,[review,review])

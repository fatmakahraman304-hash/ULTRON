"""Unit checks for owner-approved, never-automatic ULTRON learning."""
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from approved_learning import validate_suggestion, register_learning_routes


class ApprovedLearningTests(unittest.TestCase):
    def test_valid_bounded_explicit_preference(self):
        result=validate_suggestion({"category":"PREFERENCE","key":" Konuşma ","value":" Ciddi ve kısa "})
        self.assertEqual(result,("PREFERENCE","Konuşma","Ciddi ve kısa"))

    def test_rejects_bad_input_and_hidden_nul(self):
        for item in [
            {}, [], {"category":"UNKNOWN","key":"k","value":"v"},
            {"category":"FACT","key":"","value":"v"},
            {"category":"FACT","key":"k"*121,"value":"v"},
            {"category":"FACT","key":"k","value":"v"*1001},
            {"category":"FACT","key":"a"+chr(0)+"b","value":"v"},
            {"category":"FACT","key":"k","value":"v"+chr(0)},
            {"category":"FACT","key":"k","value": {"x":"y"}},
        ]:
            with self.subTest(item=str(item)[:40]),self.assertRaises(ValueError):
                validate_suggestion(item)

    def test_explicit_browser_approval_only_and_owner_scoped_queries(self):
        p=(HERE/"approved_learning.py").read_text(encoding="utf-8")
        app=(HERE/"app.py").read_text(encoding="utf-8")
        self.assertIn("register_learning_routes(app)",app)
        self.assertIn('request.get("auth_kind") != "web"',p)
        self.assertIn('request.headers.get("Sec-Fetch-Site"',p)
        self.assertIn("WHERE id=$1 AND user_id=$2 FOR UPDATE",p)
        self.assertIn("ON CONFLICT (user_id,key) DO NOTHING",p)
        self.assertIn("ON CONFLICT (user_id,key) WHERE status='pending' DO NOTHING",p)
        self.assertIn("VALUES($1,$2,$3,$4,'owner-approved-learning')",p)
        self.assertIn('"memory_saved": False',p)

    def test_pending_is_not_model_memory(self):
        p=(HERE/"approved_learning.py").read_text(encoding="utf-8")
        model=(HERE/"app.py").read_text(encoding="utf-8")
        start=model.index("async def _memory_context(")
        stop=model.index("async def _recent_context(")
        self.assertNotIn("learning_proposals",model[start:stop])
        self.assertIn("SELECT category,key,value FROM memories WHERE user_id=$1",model[start:stop])
        self.assertIn("INSERT INTO memories",p)

if __name__=="__main__":
    unittest.main()

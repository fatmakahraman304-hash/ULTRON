"""Offline consent/safety regression tests for owner opt-in automatic learning."""
import sys
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from auto_learning import extract_owner_statement


class AutoLearningUnitTests(unittest.TestCase):
    def test_opt_in_patterns_are_explicit_and_deterministic(self):
        examples=[
            ("Tercihim: Kısa ve Türkçe cevaplar","PREFERENCE"),
            ("Hedefim: İngilizcemi B2 seviyesine taşımak","GOAL"),
            ("Projem: ULTRON'un sesli arayüzünü geliştirmek","PROJECT"),
            ("My goal is: learn architecture","GOAL"),
        ]
        for message,kind in examples:
            with self.subTest(message=message):
                c=extract_owner_statement(message)
                self.assertIsNotNone(c)
                self.assertEqual(c[0],kind)
                self.assertEqual(c[2],message.split(":",1)[1].strip())
                self.assertLessEqual(len(c[1]),120)
                self.assertEqual(c,extract_owner_statement(message))

    def test_secrets_private_data_quotes_urls_and_multiline_ignored(self):
        for message in [
            "Tercihim: Şifrem abc123","Hedefim: IBAN TR12345678901234",
            "Projem: api_key test_secret","Tercihim: adresim test@example.com",
            "Hedefim: 123456789","Tercihim: sağlık kaydım önemli",
            "Tercihim: https://example.com",
            "> Tercihim: Gizli bilgi","Tercihim: iyi\nProjem: kötü",
            "Şimdi bana bir şaka yap", "Asistan: Tercihim: böyle",
            "Tercihim: xx","Projem: " + "a"*181,
            "Tercihim: " + "a"*500,
        ]:
            with self.subTest(message=message[:25]):
                self.assertIsNone(extract_owner_statement(message))

    def test_static_owner_scope_and_disabling_is_atomic(self):
        code=(HERE/"auto_learning.py").read_text(encoding="utf-8")
        chat=(HERE/"app.py").read_text(encoding="utf-8")
        local=(HERE/"local_brain_bridge.py").read_text(encoding="utf-8")
        self.assertIn("FOR UPDATE",code)
        self.assertIn("ON CONFLICT(user_id,key) DO NOTHING",code)
        self.assertIn("WHERE user_id=$1",code)
        self.assertIn("request.get(\"auth_kind\") != \"web\"",code)
        self.assertIn("register_auto_learning_routes(app)",chat)
        self.assertIn('request.get("auth_kind") == "web"',chat)
        self.assertIn('await learn_from_owner_message(pool, request["user_id"], text)',chat)
        self.assertIn('await learn_from_owner_message(pool, request["user_id"], text)',local)
        self.assertIn('"background_surveillance": False',code)

if __name__=="__main__":
    unittest.main()

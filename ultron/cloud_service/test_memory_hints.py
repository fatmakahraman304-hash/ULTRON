import unittest

import memory_hints as mh


class MemoryHintTests(unittest.TestCase):
    def test_personal_facts_get_a_consent_hint_with_the_original_wording(self):
        for text, fact in (("Kedimin adı Pamuk", "Kedimin adı Pamuk"), ("En sevdiğim renk mavi", "En sevdiğim renk mavi"), ("Alerjim var: fıstık", "Alerjim var: fıstık"),
                           ("29 yaşındayım", "29 yaşındayım"), ("İzmir'de oturuyorum", "İzmir'de oturuyorum"), ("Vejetaryenim", "Vejetaryenim"),
                           ("Eşimin adı Ayşe", "Eşimin adı Ayşe")):
            out = mh.hint(text)
            self.assertIn(f"“hatırla: {fact}”", out, text)
            self.assertIn("izin vermeden kaydetmiyorum", out)

    def test_questions_secrets_and_ordinary_chat_get_nothing(self):
        for text in ("Kedimin adı ne?", "Pamuk neden kaçtı", "Hava nasıl", "bugün çok yoruldum", "x", "alerjim var mı acaba?", "parolam sk-abcdefghijklmnop1234 olsun",
                     "Kedimin adı Pamuk " + "x" * 200, "", None):
            self.assertEqual(mh.hint(text), "", text)


if __name__ == "__main__":
    unittest.main()

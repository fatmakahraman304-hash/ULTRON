"""Regression: explicit first-topic return and paired older evidence."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conversation_turns import select_contextual_turns, load_contextual_thread_turns

class ReferenceReturnTests(unittest.IsolatedAsyncioTestCase):
    def history(self):
        return [
            {'role': 'user', 'content': '2009 Mercedes C180 hakkında konuşalım.'},
            {'role': 'assistant', 'content': 'Motor versiyonunu doğrulamak gerekir.'},
        ] + [{'role': 'user' if i % 2 == 0 else 'assistant',
              'content': f'Mimarlık çizimi aşama {i}'} for i in range(30)]

    def test_named_recall_includes_answer_without_matching_keyword(self):
        result = select_contextual_turns(self.history(), 'Mercedes C180 ne demiştik?')
        self.assertIn('Motor versiyonunu', str(result))
        self.assertIn('aşama 29', str(result))

    def test_verbose_recalled_answer_does_not_evict_its_question(self):
        rows = self.history()
        rows[1]['content'] = 'Motor versiyonunu kontrol et. ' * 50
        result = select_contextual_turns(rows, 'Mercedes C180 ne demiştik?', max_chars=2600)
        self.assertIn('2009 Mercedes C180', str(result))
        self.assertIn('Motor versiyonunu', str(result))
        self.assertLessEqual(sum(len(t['content']) for t in result), 2600)

    def test_older_long_exchange_keeps_final_answer_and_latest_correction(self):
        old_question = ("Mercedes C180 2009 fren konusunu konuşalım. "
                        + "teknik ayrıntı " * 85
                        + " SON SORU: Fren balatası mı disk mi?")
        old_answer = ("Araç için ilk kontrol açıklaması. "
                      + "ayrıntı " * 105
                      + " SON KARAR: Ön disk ve balata kontrol edilmeli.")
        rows = [
            {"role": "user", "content": old_question},
            {"role": "assistant", "content": old_answer},
        ] + [
            {"role": "user" if i % 2 == 0 else "assistant",
             "content": f"Başka bir konu {i}"} for i in range(32)
        ]
        chosen = select_contextual_turns(
            rows, "Mercedes C180 hakkında ne demiştik?",
            max_chars=3000, max_turns=14,
        )
        material = " ".join(t["content"] for t in chosen)
        self.assertIn("Mercedes C180", material)
        self.assertIn("SON SORU", material)
        self.assertIn("SON KARAR", material)
        self.assertIn("Başka bir konu 31", material)
        self.assertLessEqual(len(chosen), 14)
        self.assertLessEqual(sum(len(t["content"]) for t in chosen), 3000)

    async def test_first_return_fetches_actual_beginning_not_last_80(self):
        class DB:
            calls = []
            async def fetch(db, sql, *args):
                db.calls.append((sql, args))
                if 'ASC' in sql:
                    return self.history()[:4]
                return list(reversed(self.history()[-12:]))
        db = DB()
        result = await load_contextual_thread_turns(
            db, 'owner', 'thread', question='İlk söylediğine geri dön.', before_id=999,
            max_chars=2600, limit=12)
        self.assertIn('2009 Mercedes C180', str(result))
        self.assertIn('aşama 29', str(result))
        self.assertTrue(any('ASC' in sql for sql, _ in db.calls))
        for sql, args in db.calls:
            self.assertIn('user_id=$1 AND conversation_id=$2', sql)
            self.assertIn('id < $3', sql)
            self.assertEqual(args[:3], ('owner', 'thread', 999))
        self.assertLessEqual(len(result), 12)
        self.assertLessEqual(sum(len(t['content']) for t in result), 2600)

    def test_small_caps_and_ordinary_followup(self):
        for cap in (0, 40, 120, 850):
            for count in (0, 1, 2, 3, 12):
                result = select_contextual_turns(self.history(), 'Mercedes C180',
                                                max_chars=cap, max_turns=count)
                self.assertLessEqual(len(result), count)
                self.assertLessEqual(sum(len(t['content']) for t in result), cap)
        self.assertNotIn('Mercedes', str(select_contextual_turns(self.history(), 'Peki?')))

if __name__ == '__main__': unittest.main()

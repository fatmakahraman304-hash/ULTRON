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

"""Bounded same-thread continuation retrieval through 500 go-ahead turns.

Synthetic database and provider message serialization; no real model inference.
"""
import unittest
from conversation_turns import load_contextual_thread_turns, ollama_messages, gemini_turns
from test_golge_long_continuity import chain


class PagedHistory:
    def __init__(self, rows):
        self.rows=[dict(id=i+1, **row) for i,row in enumerate(rows)]
        self.calls=[]

    async def fetch(self, sql, *args):
        self.calls.append((sql,args))
        before=args[2]
        cursor=args[4] if len(args)>4 else before
        rows=[row for row in self.rows if (before is None or row['id']<before)
              and (cursor is None or row['id']<cursor)]
        return list(reversed(rows))[:args[3]]


class PagedContinuationTests(unittest.IsolatedAsyncioTestCase):
    async def load(self, db, **kwargs):
        return await load_contextual_thread_turns(
            db,'owner-test','thread-test',question='Devam et',before_id=1000,
            max_chars=kwargs.get('max_chars',2600),limit=kwargs.get('limit',12))

    async def test_goal_and_correction_survive_100_go_aheads_on_both_provider_wires(self):
        correction='Hayır, Windows testi yapılmadan yayımlama.'
        db=PagedHistory(chain(n=100,corrections=[correction]))
        turns=await self.load(db)
        self.assertIn('Önce doğal sohbeti geliştir',str(turns))
        self.assertIn(correction,str(turns))
        self.assertIn('100. aşamada ilerledim',str(turns))
        for messages in (ollama_messages('SYSTEM',turns,'Devam et'),gemini_turns(turns,'Devam et')):
            self.assertIn('Önce doğal sohbeti geliştir',str(messages))
            self.assertIn(correction,str(messages))
        self.assertEqual(len(db.calls),2)
        for sql,args in db.calls:
            self.assertIn('user_id=$1 AND conversation_id=$2',sql)
            self.assertIn('id < $3',sql)
            self.assertEqual(args[:3],('owner-test','thread-test',1000))
            self.assertLessEqual(args[3],200)
        self.assertLessEqual(sum(len(t['content']) for t in turns),2600)
        self.assertLessEqual(len(turns),12)

    async def test_goal_and_latest_correction_survive_500_go_aheads(self):
        correction='Hayır, eski kırmızı kararı geçersiz; yeni renk mavi.'
        db=PagedHistory(chain(n=500,corrections=[correction]))
        turns=await load_contextual_thread_turns(
            db,'owner-test','thread-test',question='Devam et',before_id=5000,
            max_chars=2600,limit=12)
        self.assertIn('Önce doğal sohbeti geliştir',str(turns))
        self.assertIn(correction,str(turns))
        self.assertIn('500. aşamada ilerledim',str(turns))
        self.assertEqual(len(db.calls),6)
        for sql,args in db.calls:
            self.assertIn('user_id=$1 AND conversation_id=$2',sql)
            self.assertEqual(args[:3],('owner-test','thread-test',5000))
            self.assertLessEqual(args[3],200)
        self.assertLessEqual(sum(len(t['content']) for t in turns),2600)
        self.assertLessEqual(len(turns),12)

    async def test_english_go_ahead_recovers_original_goal_and_correction(self):
        rows=chain(n=100)
        rows[0]['content']='Improve natural conversation; preserve the hologram.'
        rows.insert(2,{'role':'user','content':'No, I meant finish Windows tests before release.'})
        for row in rows:
            if row['role']=='user' and row['content']=='Devam et':row['content']='keep going'
        db=PagedHistory(rows)
        turns=await load_contextual_thread_turns(
            db,'owner-test','thread-test',question='continue',before_id=1000,
            max_chars=2600,limit=12)
        self.assertIn('Improve natural conversation',str(turns))
        self.assertIn('finish Windows tests before release',str(turns))
        self.assertEqual(len(db.calls),2)

    async def test_recent_concrete_scope_uses_one_query(self):
        rows=chain(n=100)+[{'role':'user','content':'Şimdi yalnız ses kalitesini test et.'},
                           {'role':'assistant','content':'Ses testine başladım.'}]
        db=PagedHistory(rows)
        turns=await self.load(db)
        self.assertEqual(len(db.calls),1)
        self.assertNotIn('doğal sohbeti geliştir',str(turns))
        self.assertIn('yalnız ses kalitesini',str(turns))

    async def test_topic_switch_stops_scan_before_abandoned_goal(self):
        rows=chain(n=30)+[{'role':'user','content':'Konuyu değiştir, eski işi bırak.'}]+chain(n=48)[2:]
        db=PagedHistory(rows)
        turns=await self.load(db)
        self.assertEqual(len(db.calls),1)
        self.assertNotIn('doğal sohbeti geliştir',str(turns))

    async def test_scan_is_bounded_and_does_not_invent_a_missing_goal(self):
        db=PagedHistory(chain(n=700)[2:])
        turns=await load_contextual_thread_turns(
            db,'owner-test','thread-test',question='Devam et',before_id=5000,
            max_chars=2600,limit=12)
        self.assertEqual(len(db.calls),6)
        self.assertNotIn('doğal sohbeti geliştir',str(turns))
        self.assertIn('700. aşamada ilerledim',str(turns))
        self.assertLessEqual(sum(len(t['content']) for t in turns),2600)

    async def test_zero_or_small_output_budget_does_not_fetch_older_pages(self):
        for options in ({'max_chars':0},{'limit':3}):
            db=PagedHistory(chain(n=100))
            await self.load(db,**options)
            self.assertEqual(len(db.calls),1)

    async def test_optional_older_read_failure_keeps_verified_recent_turns(self):
        class FailingHistory(PagedHistory):
            async def fetch(self,sql,*args):
                if self.calls:raise RuntimeError('SECRET database detail')
                return await super().fetch(sql,*args)
        turns=await self.load(FailingHistory(chain(n=100)))
        self.assertIn('100. aşamada ilerledim',str(turns))
        self.assertNotIn('SECRET',str(turns))
        self.assertNotIn('doğal sohbeti geliştir',str(turns))

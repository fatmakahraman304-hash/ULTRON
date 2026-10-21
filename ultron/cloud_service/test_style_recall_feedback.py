"""Style preferences, recall, voice skill gateway and feedback loop.

Pure tests always run; the database contract runs with ULTRON_TEST_DATABASE_URL (real PostgreSQL)."""
import json
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedback_skills as fb
import instant_skills as s
import recall_skills as rc
import style_skills as st
import voice_skills as vs
import ops

TEST_URL = os.getenv("ULTRON_TEST_DATABASE_URL", "").strip()


class PureTests(unittest.TestCase):
    def test_style_commands_detected_and_ordinary_chat_not(self):
        for t in ("kısa cevap ver", "samimi ol", "bana sen de", "bana Murat diye hitap et", "emoji kullanma", "detaylı anlat", "tarzı sıfırla", "konuşma tarzım ne"):
            self.assertTrue(st.wants_style(t), t)
        for t in ("hava nasıl", "bana kısa bir hikaye anlat", "emoji nedir", "kısa vadeli yatırım nedir"):
            self.assertFalse(st.wants_style(t), t)

    def test_style_instruction_is_empty_without_choices_and_bounded_with_them(self):
        self.assertEqual(st.style_instruction({}), "")
        text = st.style_instruction({"length": "short", "tone": "formal", "address": "siz", "name": "Murat", "emoji": False})
        for part in ("very short", "formal", "'siz'", "Murat", "Do not use emoji", "never safety rules"):
            self.assertIn(part, text)

    def test_recall_detection_skips_self_and_general_questions(self):
        for t in ("Ahmet hakkında ne biliyorsun", "dün ne konuştuk", "geçen hafta ne konuştuk", "kahve hakkında ne konuşmuştuk", "hafıza özeti"):
            self.assertTrue(rc.wants_recall(t), t)
        for t in ("hakkımda ne biliyorsun", "benim hakkımda ne biliyorsun", "Ankara hakkında ne düşünüyorsun"):
            self.assertFalse(rc.wants_recall(t), t)

    def test_recall_windows(self):
        now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)   # Wednesday
        lo, hi, _ = rc._window("dun", now)
        self.assertEqual((hi - lo), timedelta(days=1))
        lo, hi, label = rc._window("gecen hafta", now)
        self.assertEqual(lo.weekday(), 0)
        self.assertEqual(hi - lo, timedelta(days=7))
        self.assertEqual(label, "Geçen hafta")

    def test_feedback_detection(self):
        for t in ("yanlış anladın", "hayır bunu istemedim", "tam istediğim buydu", "en çok kullandığım komutlar", "bana öneri ver"):
            self.assertTrue(fb.wants_feedback(t), t)
        for t in ("doğru mu", "yanlış anladın mı acaba bu cümleyi", "ne önerirsin bana bir film"):
            self.assertFalse(fb.wants_feedback(t), t)

    def test_corpus_lines_only_negative_unique(self):
        rows = [{"rating": "bad", "user_text": "yarın yağmur var mı", "skill": "chat"},
                {"rating": "bad", "user_text": "yarın yağmur var mı", "skill": "chat"},
                {"rating": "good", "user_text": "saat kaç", "skill": "clock"}]
        lines = fb.corpus_lines(rows)
        self.assertEqual(len(lines), 1)
        self.assertIn("yarın yağmur var mı", lines[0])
        compile("CASES=[\n" + lines[0] + "\n]", "x", "exec")

    def test_speakable_removes_links_and_markdown(self):
        out = vs.speakable("**Yol tarifi**\nhttps://maps.google.com/?q=a\nİyi yolculuklar")
        self.assertNotIn("http", out)
        self.assertNotIn("*", out)
        self.assertIn("sohbet ekranına", out)

    def test_voice_allow_list_excludes_sensitive_skills(self):
        for blocked in ("memory", "plans", "alerts", "prefs", "smart_home", "feedback"):
            self.assertNotIn(blocked, vs.VOICE_WRITE_SKILLS)
        self.assertEqual(vs.TOOL_DECLARATION["name"], "golge_skill")

    def test_new_skills_are_handed_back_to_cloud_chat(self):
        for t in ("kısa cevap ver", "dün ne konuştuk", "yanlış anladın"):
            self.assertTrue(s.wants_cloud_skill(t), t)


@unittest.skipUnless(TEST_URL, "No isolated test PostgreSQL configured")
class DatabaseContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import asyncpg
        self.pool = await asyncpg.create_pool(TEST_URL, min_size=1, max_size=4)
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        await self.pool.execute(schema)
        await self.pool.execute(schema)
        self.u = "ci-" + uuid.uuid4().hex[:10]
        self.conv = uuid.uuid4()
        await self.pool.execute("INSERT INTO conversations(id,user_id,title) VALUES($1,$2,'t')", self.conv, self.u)

    async def asyncTearDown(self):
        await self.pool.execute("DELETE FROM conversations WHERE user_id=$1", self.u)
        for table in ("owner_plans", "owner_habits", "owner_expenses", "owner_journal", "owner_prefs", "memories", "skill_usage", "skill_feedback", "owner_reminders", "owner_list_items", "push_subscriptions"):
            await self.pool.execute(f"DELETE FROM {table} WHERE user_id=$1", self.u)
        await self.pool.close()

    async def say(self, text, **kw):
        out = await s.instant_reply(text, pool=self.pool, user_id=self.u, **kw)
        return out["reply"] if out else None

    async def add_msg(self, role, content, device="web", age_days=0):
        return await self.pool.fetchval(
            "INSERT INTO messages(conversation_id,user_id,role,content,device_id,created_at) VALUES($1,$2,$3,$4,$5,NOW()-($6||' days')::interval) RETURNING id",
            self.conv, self.u, role, content, device, str(age_days))

    async def test_style_persists_and_coexists_with_proactive_prefs(self):
        self.assertIn("kısa", await self.say("kısa cevap ver"))
        await self.say("samimi ol")
        await self.say("bana Murat diye hitap et")
        await self.say("emoji kullanma")
        style = await st.get_style(self.pool, self.u)
        self.assertEqual((style["length"], style["tone"], style["name"], style["emoji"]), ("short", "warm", "Murat", False))
        # A later proactive preference change must not drop the style (set_pref merges raw JSON).
        await self.say("sessiz saatler 23 ile 7")
        self.assertEqual((await st.get_style(self.pool, self.u))["name"], "Murat")
        self.assertIn("Murat", await self.say("konuşma tarzım ne"))
        await self.say("tarzı sıfırla")
        self.assertEqual(await st.get_style(self.pool, self.u), {})

    async def test_recall_memory_and_past_conversation(self):
        await self.say("hatırla: Ahmet kahveyi şekersiz içer")
        self.assertIn("şekersiz", await self.say("Ahmet hakkında ne biliyorsun"))
        self.assertIsNone(await self.say("Atatürk hakkında ne biliyorsun"))        # general knowledge falls through
        await self.add_msg("user", "Dün bisiklet almayı konuştuk, bütçem 5000 lira", age_days=1)
        await self.add_msg("user", "bugün hava nasıl")
        reply = await self.say("kahve hakkında ne konuşmuştuk")
        self.assertIn("bulamadım", reply)
        self.assertIn("bisiklet", await self.say("bisiklet hakkında ne konuşmuştuk"))
        self.assertIn("mesaj", await self.say("dün ne konuştuk"))
        self.assertIn("kayıt var", await self.say("hafıza özeti"))

    async def test_recall_is_owner_scoped(self):
        other = "ci-" + uuid.uuid4().hex[:10]
        await self.pool.execute("INSERT INTO conversations(id,user_id,title) VALUES($1,$2,'t')", uuid.uuid4(), other)
        await self.pool.execute("INSERT INTO memories(user_id,key,value) VALUES($1,'sir','Zeynep gizli doğum günü sürprizi')", other)
        try:
            self.assertIsNone(await self.say("Zeynep hakkında ne biliyorsun"))
        finally:
            await self.pool.execute("DELETE FROM memories WHERE user_id=$1", other)
            await self.pool.execute("DELETE FROM conversations WHERE user_id=$1", other)

    async def test_voice_gateway_runs_allowed_and_blocks_others(self):
        out = await vs.run("saat kaç", pool=self.pool, user_id=self.u, conv_uuid=self.conv)
        self.assertTrue(out["handled"])
        self.assertEqual(out["skill"], "clock")
        out = await vs.run("alışveriş listesine süt ekle", pool=self.pool, user_id=self.u, conv_uuid=self.conv)
        self.assertEqual(out["skill"], "lists")
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM owner_list_items WHERE user_id=$1", self.u), 1)
        # Memory writes are not available through the voice skill gateway.
        out = await vs.run("hatırla: şifre değil sadece bir not", pool=self.pool, user_id=self.u, conv_uuid=self.conv)
        self.assertFalse(out["handled"])
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM memories WHERE user_id=$1", self.u), 0)
        # The spoken reply was also stored in the conversation, tagged for follow-ups.
        self.assertGreaterEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM messages WHERE conversation_id=$1 AND device_id LIKE 'golge-skill:%'", self.conv), 2)
        self.assertFalse((await vs.run("", pool=self.pool, user_id=self.u))["handled"])

    async def test_feedback_usage_suggestions_export(self):
        self.assertIn("göremedim", await self.say("yanlış anladın"))
        history = {"user": "yarın yağmur var mı", "reply": "Bilmiyorum", "skill": "chat"}
        self.assertIn("yanlış anlamışım", await self.say("yanlış anladın", history=history))
        self.assertIn("not aldım", await self.say("tam istediğim buydu", history=history))
        self.assertIn("1 olumlu, 1 olumsuz", await self.say("geri bildirimlerim"))
        now = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)
        for d in range(4):
            await fb.record_usage(self.pool, self.u, "weather", now - timedelta(days=d))
        await fb.record_usage(self.pool, self.u, "weather", now)
        top = await self.say("en çok kullandığım komutlar", now=now)
        self.assertIn("hava durumu — 5 kez", top)
        tip = await fb.next_suggestion(self.pool, self.u, now)
        self.assertIn("sabah brifingini aç", tip)
        self.assertIsNone(await fb.next_suggestion(self.pool, self.u, now))              # once per day
        self.assertIn("sabah brifingini aç", await self.say("bana öneri ver", now=now))   # explicit ask always answers
        data = await ops.export_owner_data(self.pool, self.u)
        self.assertEqual(len(data["feedback"]), 2)
        self.assertTrue(data["skill_usage"])
        self.assertEqual(len(fb.corpus_lines(json.loads(json.dumps(data["feedback"], default=str)))), 1)
        removed = await ops.maintenance(self.pool)
        self.assertNotEqual(removed.get("skill_usage"), -1)
        self.assertNotEqual(removed.get("skill_feedback"), -1)

    async def test_briefing_uses_name_reminders_and_yesterday_recap(self):
        now = datetime(2026, 10, 21, 6, 0, tzinfo=timezone.utc)      # 09:00 Istanbul
        await self.say("bana Murat diye hitap et")
        await self.pool.execute("INSERT INTO owner_reminders(user_id,text,due_at) VALUES($1,'ilaç iç',$2)", self.u, now + timedelta(hours=5))
        await self.pool.execute("INSERT INTO owner_habits(user_id,habit,amount,day) VALUES($1,'water',6,'2026-10-20'),($1,'sleep',7.5,'2026-10-20')", self.u)
        await self.pool.execute("INSERT INTO owner_expenses(user_id,amount,category,spent_on) VALUES($1,150,'market','2026-10-20')", self.u)
        reply = await self.say("günaydın", now=now)
        self.assertIn("Günaydın, Murat.", reply)
        self.assertEqual(reply.count("ilaç iç"), 1)  # reminders already appear in the agenda block
        self.assertIn("🔁 Dün: uyku 7,5 · su 6 · harcama 150 ₺", reply)

    async def test_journal_write_read_search_delete_and_secret_refusal(self):
        now = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)
        self.assertIn("Bugün 1 girdin", await self.say("günlüğe yaz: Bugün çok verimliydim, kahve içtim", now=now))
        self.assertIn("Bugün 2 girdin", await self.say("günlük: akşam yürüyüşe çıktım", now=now))
        self.assertIn("verimliydim", await self.say("bugünkü günlüğüm", now=now))
        self.assertIn("kahve", await self.say("günlüğümde kahve geçenler", now=now))
        self.assertIn("bulamadım", await self.say("günlüğümde pizza geçenler", now=now))
        self.assertIn("yürüyüşe", await self.say("son günlük kaydını sil", now=now))
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM owner_journal WHERE user_id=$1", self.u), 1)
        refusal = await self.say("günlüğe yaz: parolam sk-abcdefghijklmnop1234", now=now)
        self.assertIn("yazmıyorum", refusal)
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM owner_journal WHERE user_id=$1", self.u), 1)
        out = await vs.run("günlüğe yaz: sesle eklendi", pool=self.pool, user_id=self.u, now=now)
        self.assertEqual(out["skill"], "journal")

    async def test_memory_correction_history_and_recent_notes(self):
        await self.say("hatırla: Ahmet kahveyi şekerli içer")
        await self.say("hatırla: Zeynep çayı demli sever")
        self.assertIn("Düzelttim", await self.say("düzelt: ahmet => Ahmet kahveyi sade içer"))
        self.assertIn("sade", await self.say("Ahmet hakkında ne biliyorsun"))
        self.assertIn("şekerli", await self.say("hafızada ahmet notumun geçmişi"))
        self.assertIn("bulamadım", await self.say("düzelt: yokboyle => x"))
        self.assertIn("eski bir sürüm kaydı yok", await self.say("hafızada zeynep eskiden neydi"))
        recent = await self.say("son notlarım")
        self.assertIn("Zeynep", recent)
        self.assertIn("Ahmet", await self.say("bugün ne kaydettim"))
        self.assertIsNone(await self.say("Roma'nın geçmişi"))
        refusal = await self.say("düzelt: ahmet => parolam sk-abcdefghijklmnop1234")
        self.assertIn("kaydetmiyorum", refusal)
        self.assertIn("sade", await self.say("Ahmet hakkında ne biliyorsun"))

    async def test_weekly_review_uses_only_recorded_data(self):
        now = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)      # Wednesday
        self.assertIn("kayıtlı bir veri yok", await self.say("haftalık özet", now=now))
        await self.pool.execute("INSERT INTO owner_plans(user_id,title,scheduled_date,is_done) VALUES($1,'a','2026-10-19',TRUE),($1,'b','2026-10-20',FALSE)", self.u)
        await self.pool.execute("INSERT INTO owner_habits(user_id,habit,amount,day) VALUES($1,'water',6,'2026-10-20'),($1,'sleep',7,'2026-10-19'),($1,'sleep',8,'2026-10-20')", self.u)
        await self.pool.execute("INSERT INTO owner_expenses(user_id,amount,category,spent_on) VALUES($1,150,'market','2026-10-20'),($1,50,'kahve','2026-10-21')", self.u)
        await self.pool.execute("INSERT INTO owner_journal(user_id,entry,day) VALUES($1,'iyi gün','2026-10-20')", self.u)
        reply = await self.say("haftalık özet", now=now)
        for part in ("1/2 tamamlandı", "su 6 bardak (1 gün)", "uyku ort. 7.5 saat", "Harcama: 200 ₺, en çok market (150 ₺)", "Günlük: 1 girdi"):
            self.assertIn(part, reply)
        self.assertIn("kayıtlı bir veri yok", await self.say("geçen hafta nasıldı", now=now))


if __name__ == "__main__":
    unittest.main()

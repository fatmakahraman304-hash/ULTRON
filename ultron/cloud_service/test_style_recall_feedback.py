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
        for table in ("capability_gaps", "dev_requests", "device_commands", "owner_routines", "owner_plans", "owner_habits", "owner_expenses", "owner_journal", "owner_prefs", "memories", "skill_usage", "skill_feedback", "owner_reminders", "owner_list_items", "push_subscriptions"):
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
        for part in ("1/2 tamamlandı", "su 6 bardak (1 gün)", "uyku ort. 7,5 saat", "Harcama: 200 ₺, en çok market (150 ₺)", "Günlük: 1 girdi"):
            self.assertIn(part, reply)
        self.assertIn("kayıtlı bir veri yok", await self.say("geçen hafta nasıldı", now=now))

    async def test_weekly_notification_is_opt_in_sunday_evening_and_skips_empty_weeks(self):
        import proactive as pro
        sunday = datetime(2026, 10, 25, 17, 30, tzinfo=timezone.utc).astimezone(pro.HOME_TZ)   # 20:30 Istanbul
        prefs = await pro.get_prefs(self.pool, self.u)
        self.assertEqual(await pro.weekly_review(self.pool, self.u, prefs, sunday), [])        # off by default
        self.assertIn("pazar akşamı", await self.say("haftalık özet bildirimi aç"))
        prefs = await pro.get_prefs(self.pool, self.u)
        self.assertTrue(prefs["weekly_review"])
        self.assertEqual(await pro.weekly_review(self.pool, self.u, prefs, sunday), [])        # nothing recorded
        await self.pool.execute("INSERT INTO owner_expenses(user_id,amount,category,spent_on) VALUES($1,80,'kahve','2026-10-22')", self.u)
        items = await pro.weekly_review(self.pool, self.u, prefs, sunday)
        self.assertEqual(len(items), 1)
        self.assertNotIn("₺", items[0]["body"])          # lock-screen text carries no amounts
        self.assertIn("haftalık özet", items[0]["body"])
        self.assertEqual(await pro.weekly_review(self.pool, self.u, prefs, sunday.replace(day=24)), [])   # Saturday
        self.assertIn("haftalık özet bildirimi", (await self.say("bildirim ayarlarım")).lower())
        await self.say("haftalık özet bildirimini kapat")
        self.assertFalse((await pro.get_prefs(self.pool, self.u))["weekly_review"])

    async def test_monthly_budget_tracks_remaining_and_warns(self):
        now = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)
        self.assertIn("Henüz aylık bütçe belirlemedin", await self.say("bütçem", now=now))
        self.assertIn("15.000 ₺", await self.say("aylık bütçem 15000 tl", now=now))
        first = await self.say("1200 lira market harcaması ekle", now=now)
        self.assertIn("Bu ay 1.200 ₺ / 15.000 ₺ (%8)", first)
        self.assertNotIn("⚠", first)
        warned = await self.say("11000 lira kira harcaması ekle", now=now)
        self.assertIn("%81", warned)
        self.assertIn("%80'ini geçtin", warned)
        over = await self.say("4000 lira tamir harcaması ekle", now=now)
        self.assertIn("Bütçeni aştın", over)
        # the budget lives next to other prefs and survives a proactive pref change
        await self.say("sessiz saatler 23 ile 7")
        self.assertIn("(%", await self.say("bütçe durumu", now=now))
        await self.say("bütçeyi kaldır")
        self.assertNotIn("Bu ay", await self.say("50 lira kahve harcaması ekle", now=now))

    async def test_streaks_birthday_countdown_and_resume(self):
        now = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)
        await self.pool.execute("INSERT INTO owner_habits(user_id,habit,amount,day) VALUES($1,'water',8,'2026-10-21'),($1,'water',8,'2026-10-20'),($1,'water',8,'2026-10-19'),($1,'water',8,'2026-10-17'),($1,'exercise',30,'2026-10-20')", self.u)
        self.assertIn("3 gün üst üste", await self.say("su serim", now=now))
        both = await self.say("serilerim", now=now)
        self.assertIn("Su: 3 gün", both)
        self.assertIn("Spor: 1 gün", both)                      # yesterday counts while today is still empty
        self.assertIn("serin şu an yok", await self.say("uyku serim", now=now))
        self.assertIn("Ahmet", await self.say("Ahmet'in doğum günü 3 Mart", now=now))
        self.assertIn("doğum gününe 133 gün var (3 Mart)", await self.say("Ahmet'in doğum gününe kaç gün var", now=now))
        self.assertIn("bulamadım", await self.say("Veli'nin doğum gününe kaç gün var", now=now))
        self.assertIn("Daha önce", await self.say("nerede kalmıştık", now=now))
        await self.add_msg("user", "Bisiklet bütçemi planlıyorum", age_days=1)
        await self.add_msg("user", "nerede kalmıştık")
        reply = await self.say("nerede kalmıştık", now=now)
        self.assertIn("Bisiklet bütçemi planlıyorum", reply)
        self.assertEqual(reply.count("nerede kalmıştık"), 0)

    async def test_routines_save_list_start_with_reminders_delete(self):
        now = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)
        self.assertIn("3 adım", await self.say("akşam rutini: ilaç iç, su iç, yarını planla", now=now))
        self.assertIn("akşam: 3 adım", await self.say("rutinlerim"))
        shown = await self.say("akşam rutinini başlat", now=now)
        self.assertIn("1. ilaç iç", shown)
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM owner_reminders WHERE user_id=$1", self.u), 0)
        started = await self.say("akşam rutinini hatırlatıcılarla başlat", now=now)
        self.assertIn("10 dakika arayla", started)
        due = await self.pool.fetch("SELECT text,due_at FROM owner_reminders WHERE user_id=$1 ORDER BY due_at", self.u)
        self.assertEqual([r["text"] for r in due][0], "▶ akşam 1/3: ilaç iç")
        self.assertEqual((due[1]["due_at"] - due[0]["due_at"]).seconds, 600)
        self.assertIn("kaydettim", await self.say("akşam rutini: tek adım", now=now))      # overwrite keeps one row
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM owner_routines WHERE user_id=$1", self.u), 1)
        self.assertIn("bulamadım", await self.say("sabah rutinini başlat"))
        self.assertIn("sildim", await self.say("akşam rutinini sil"))
        self.assertIn("Kayıtlı rutinin yok", await self.say("rutinlerim"))
        out = await vs.run("sabah rutini: su iç, ilaç al", pool=self.pool, user_id=self.u, now=now)
        self.assertEqual(out["skill"], "routines")

    async def test_review_regressions(self):
        now = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)
        # smart home is not reachable through the voice gateway
        out = await vs.run("salon ışığını kapat", pool=self.pool, user_id=self.u, now=now)
        self.assertFalse(out["handled"])
        # destructive spoken requests and over-long utterances are refused, never truncated
        for spoken in ("son harcamayı sil", "Ahmet'in doğum günü sil", "hatırlatıcılarımı iptal et", "son günlük kaydımı sil"):
            out = await vs.run(spoken, pool=self.pool, user_id=self.u, now=now)
            self.assertEqual(out["reason"], "destructive_requests_need_typed_confirmation", spoken)
        self.assertEqual((await vs.run("günlüğe yaz: " + "a" * 300, pool=self.pool, user_id=self.u))["reason"], "too_long")
        # birthdays: LIKE metacharacters and prefixes never match other people
        await self.say("Ali'nin doğum günü 3 Mart", now=now)
        await self.say("Alişan'ın doğum günü 4 Mart", now=now)
        await self.say("%'in doğum günü sil", now=now)
        await self.say("_'in doğum günü sil", now=now)
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM owner_reminders WHERE user_id=$1 AND status='pending'", self.u), 4)
        await self.say("Ali'nin doğum günü sil", now=now)
        left = await self.pool.fetch("SELECT text FROM owner_reminders WHERE user_id=$1 AND status='pending'", self.u)
        self.assertEqual(len(left), 2)
        self.assertTrue(all("Alişan" in r["text"] for r in left))
        # 1 March's eve reminder is 28 Feb (29 Feb would skip non-leap years)
        await self.say("Veli'nin doğum günü 1 Mart", now=now)
        rules = {r["repeat_rule"] for r in await self.pool.fetch("SELECT repeat_rule FROM owner_reminders WHERE user_id=$1 AND text LIKE '%Veli%'", self.u)}
        self.assertEqual(rules, {"yearly:03-01", "yearly:02-28"})
        # journal and memory need an explicit command: ordinary sentences are not stored
        self.assertIsNone(await self.say("Günlük, haftalık ve aylık hedefler neler", now=now))
        self.assertIsNone(await self.say("Unutma, yarın toplantı var", now=now))
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM owner_journal WHERE user_id=$1", self.u), 0)
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM memories WHERE user_id=$1", self.u), 0)
        # style: reported speech and short replies do not change the persona
        for sentence in ("Annem bana kötü biri diye seslendi", "Sen de", "Ciddi konuşuyorum"):
            self.assertIsNone(await self.say(sentence, now=now), sentence)
        self.assertEqual(await st.get_style(self.pool, self.u), {})
        # habits: "son su kaydını sil" removes water only
        await self.pool.execute("INSERT INTO owner_habits(user_id,habit,amount,day) VALUES($1,'water',2,'2026-10-21'),($1,'weight',72,'2026-10-21')", self.u)
        await self.say("son su kaydını sil", now=now)
        self.assertEqual([r["habit"] for r in await self.pool.fetch("SELECT habit FROM owner_habits WHERE user_id=$1", self.u)], ["weight"])
        # a question about the weekly notification reports, never flips, the setting
        import proactive as pro
        self.assertIn("kapalı", await self.say("haftalık özet bildirimi var mı"))
        self.assertFalse((await pro.get_prefs(self.pool, self.u))["weekly_review"])
        # concurrent-safe prefs: changing a proactive pref keeps style and budget
        await self.say("bana Murat diye hitap et")
        await self.say("aylık bütçem 5000 tl")
        await self.say("sessiz saatler 22 ile 6")
        self.assertEqual((await st.get_style(self.pool, self.u))["name"], "Murat")
        self.assertIn("5.000 ₺", await self.say("bütçe durumu", now=now))
        # feedback never keeps secrets and does not duplicate
        history = {"user": "şifrem sk-abcdefghijklmnop1234", "reply": "tamam", "skill": "chat"}
        await self.say("yanlış anladın", history=history)
        await self.say("yanlış anladın", history=history)
        rows = await self.pool.fetch("SELECT user_text,reply FROM skill_feedback WHERE user_id=$1", self.u)
        self.assertEqual([(r["user_text"], r["reply"]) for r in rows], [("", "")])
        # utility: absurd birth years do not raise
        self.assertIsNone(s.utility_skills.answer("0000 doğumluyum kaç yaşındayım"))
        self.assertIsInstance(s.wants_cloud_skill("0000 doğumluyum kaç yaşındayım"), bool)       # must not raise

    async def test_capability_gaps_to_approved_development_request(self):
        import gap_skills
        self.assertIn("boş", await self.say("eksiklerim"))
        self.assertIn("eksik", await self.say("eksik: telefonumdaki rehberden kişi bulabilsin"))
        gid = await self.pool.fetchval("SELECT id FROM capability_gaps WHERE user_id=$1", self.u)
        self.assertIn("zaten listemde", await self.say("eksik: Telefonumdaki rehberden kişi bulabilsin"))
        self.assertIn("ekleyemedim", await self.say("eksik: parolam sk-abcdefghijklmnop1234 olsun"))
        self.assertIn("rehberden", await self.say("eksiklerim"))
        # voice may list/add but never start a build
        out = await vs.run(f"eksik {gid}'i geliştir", pool=self.pool, user_id=self.u)
        self.assertIn("yazarak", out["spoken"])
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM dev_requests WHERE user_id=$1", self.u), 0)
        # offline laptop: a stored request, no laptop task
        reply = await self.say(f"eksik {gid}'i geliştir")
        self.assertIn("çevrimdışı", reply)
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM dev_requests WHERE user_id=$1", self.u), 1)
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM device_commands WHERE user_id=$1", self.u), 0)
        self.assertIn("zaten oluşturuldu", await self.say(f"eksik {gid} geliştir"))
        prompt = await self.pool.fetchval("SELECT prompt FROM dev_requests WHERE user_id=$1", self.u)
        for rule in ("AGENTS.md", "Approval Gate", "birleştirme"):
            self.assertIn(rule, prompt)
        # online laptop: the task only asks for a patch PROPOSAL and says nothing is written without approval
        await self.say("eksik: haftalık rapor PDF olarak e-postama gelsin")
        gid2 = await self.pool.fetchval("SELECT MAX(id) FROM capability_gaps WHERE user_id=$1", self.u)
        await self.pool.execute("INSERT INTO device_presence(user_id,device,last_seen) VALUES($1,'desktop',NOW()) ON CONFLICT(user_id,device) DO UPDATE SET last_seen=NOW()", self.u)
        try:
            reply = await self.say(f"eksik {gid2}'i geliştir")
            self.assertIn("TASLAĞI", reply)
            payload = await self.pool.fetchval("SELECT payload::text FROM device_commands WHERE user_id=$1", self.u)
            self.assertIn("YALNIZCA TASLAK", payload)
            self.assertIn("hiçbir dosyaya yazma", payload)
        finally:
            await self.pool.execute("DELETE FROM device_commands WHERE user_id=$1", self.u)
            await self.pool.execute("DELETE FROM device_presence WHERE user_id=$1", self.u)
        self.assertIn("çıkardım", await self.say(f"eksik {gid2}'i vazgeç"))
        # an inability admitted by the model is recorded once, with a hint; ordinary answers get none
        hint = await gap_skills.auto_gap_hint(self.pool, self.u, "bana uçak bileti al", "Üzgünüm, bunu şu an yapamıyorum.")
        self.assertIn("geliştirme listeme ekledim", hint)
        self.assertEqual(await gap_skills.auto_gap_hint(self.pool, self.u, "bana uçak bileti al", "Üzgünüm, bunu şu an yapamıyorum."), "")
        self.assertEqual(await gap_skills.auto_gap_hint(self.pool, self.u, "Roma nedir", "Roma İtalya'nın başkentidir."), "")
        self.assertEqual(await gap_skills.auto_gap_hint(self.pool, self.u, "Roma neden yıkıldı", "Bunu yapamıyorum ama anlatayım"), "")
        data = await ops.export_owner_data(self.pool, self.u)
        self.assertTrue(data["capability_gaps"])


if __name__ == "__main__":
    unittest.main()

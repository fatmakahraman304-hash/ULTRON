"""Real PostgreSQL contract for the phone-assistant stack (reminders incl. repeat, push dispatcher,
plans, price alerts, missions, retention, export, diagnostics).

Runs only with ULTRON_TEST_DATABASE_URL pointing at a disposable CI database; no network, no secrets.
"""
import asyncio
import json
import os
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

TEST_URL = os.getenv("ULTRON_TEST_DATABASE_URL", "").strip()

import alert_skills
import instant_skills as s
import missions as ms
import ops
import proactive as pro
import reminders as rem
import web_push as wp


class Req(dict):
    def __init__(self, app, user, match=None, query=None, kind="web", method="GET"):
        super().__init__(user_id=user, device_id="ci", auth_kind=kind)
        self.app, self.match_info, self.query, self.headers, self.method = app, match or {}, query or {}, {}, method


async def prices(url, key, ttl):
    if "coingecko" in url:
        return {"bitcoin": {"usd": 67000.0}}
    if "usgs" in url:
        return {"features": []}
    return {"rates": {"TRY": 41.5}}


@unittest.skipUnless(TEST_URL, "No isolated test PostgreSQL configured")
class StackContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(TEST_URL, min_size=1, max_size=4)
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        await self.pool.execute(schema)
        await self.pool.execute(schema)                 # must be idempotent
        self.u = "ci-" + uuid.uuid4().hex[:10]
        self.app = {"db": self.pool}

    async def asyncTearDown(self):
        for table in ("owner_habits", "owner_expenses", "owner_list_items", "owner_reminders", "owner_plans", "owner_alerts", "owner_notifications", "owner_prefs",
                      "push_subscriptions", "missions", "memories"):
            await self.pool.execute(f"DELETE FROM {table} WHERE user_id=$1", self.u)
        await self.pool.close()

    async def say(self, text, **kw):
        out = await s.instant_reply(text, pool=self.pool, user_id=self.u, **kw)
        return out["reply"] if out else None

    async def test_repeating_reminder_delivers_and_requeues_once(self):
        self.assertIn("her gün 09:00", await self.say("her gün 9'da ilaç içmeyi hatırlat"))
        await self.pool.execute("UPDATE owner_reminders SET due_at=NOW()-interval '1 minute' WHERE user_id=$1", self.u)
        due = json.loads((await rem.due_reminders(Req(self.app, self.u))).text)["due"]
        self.assertEqual([d["text"] for d in due], ["ilaç içmeyi"])
        rows = await self.pool.fetch("SELECT status,repeat_rule FROM owner_reminders WHERE user_id=$1 ORDER BY id", self.u)
        self.assertEqual([(r["status"], r["repeat_rule"]) for r in rows], [("delivered", "daily"), ("pending", "daily")])
        self.assertEqual(json.loads((await rem.due_reminders(Req(self.app, self.u))).text)["due"], [])
        self.assertIn("1 bekleyen", await self.say("hatırlatıcılarımı iptal et"))
        with self.assertRaises(asyncpg.CheckViolationError):
            await self.pool.execute("INSERT INTO owner_reminders(user_id,text,due_at,repeat_rule) VALUES($1,'x',NOW(),'evil')", self.u)

    async def test_push_dispatcher_in_app_first_dedupe_and_reminder_push(self):
        await self.pool.execute("INSERT INTO push_subscriptions(endpoint,user_id,p256dh,auth) VALUES($1,$2,'a','b')",
                                "https://web.push.apple.com/" + uuid.uuid4().hex, self.u)
        sent = []

        async def sender(pool, user, message, **kw):
            sent.append((user, message["title"]))
            return 1

        async def rainy(url, key, ttl):
            hours = [f"2026-10-21T{h:02d}:00" for h in range(24)] + [f"2026-10-22T{h:02d}:00" for h in range(24)]
            return {"hourly": {"time": hours, "precipitation_probability": [90] * 48}}

        noon = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)     # 12:00 Istanbul
        await pro.tick(self.pool, rainy, None, noon, sender)
        self.assertEqual(sent, [])                                    # grace period: page gets first chance
        await self.pool.execute("UPDATE owner_notifications SET created_at=NOW()-interval '1 minute' WHERE user_id=$1", self.u)
        await pro.tick(self.pool, rainy, None, noon, sender)
        await pro.tick(self.pool, rainy, None, noon, sender)
        self.assertEqual([t for _, t in sent if t == "Yağmur bekleniyor"], ["Yağmur bekleniyor"])   # once, de-duplicated
        await self.say("1 dakika sonra su içmeyi hatırlat")
        await self.pool.execute("UPDATE owner_reminders SET due_at=NOW()-interval '2 minute' WHERE user_id=$1", self.u)
        await pro.tick(self.pool, rainy, None, noon, sender)
        self.assertIn((self.u, "⏰ Hatırlatıcı"), sent)

    async def test_page_pickup_prevents_push(self):
        await self.pool.execute("INSERT INTO push_subscriptions(endpoint,user_id,p256dh,auth) VALUES($1,$2,'a','b')",
                                "https://web.push.apple.com/" + uuid.uuid4().hex, self.u)
        await pro.store(self.pool, self.u, [{"key": "k1", "title": "T", "body": "B"}])
        self.assertEqual([n["title"] for n in await pro.due_notifications(self.pool, self.u)], ["T"])
        await self.pool.execute("UPDATE owner_notifications SET created_at=NOW()-interval '1 minute' WHERE user_id=$1", self.u)
        sent = []

        async def sender(*a, **k):
            sent.append(1)
            return 1
        await pro.tick(self.pool, prices, None, datetime.now(timezone.utc), sender)
        self.assertEqual(sent, [])

    async def test_plans_and_price_alerts_and_prefs(self):
        self.assertIn("Planına ekledim", await self.say("yarın 15:00 diş randevusu planıma ekle"))
        self.assertIn("diş randevusu", await self.say("planlarım"))
        self.assertIn("tamamlandı", await self.say("diş randevusu planını tamamla"))
        self.assertIn("Tamam: bitcoin 70.000 $", await self.say("bitcoin 70 bin dolara çıkarsa haber ver", fetch_json=prices))
        await self.pool.execute("UPDATE owner_alerts SET threshold=66000 WHERE user_id=$1", self.u)
        fired = await alert_skills.check_all(self.pool, prices)
        self.assertEqual([u for u, _ in fired if u == self.u], [self.u])
        self.assertEqual(await alert_skills.check_all(self.pool, prices), [])      # fires once
        self.assertIn("22:00 – 08:00", await self.say("sessiz saatler 22 ile 8"))
        self.assertIn("08:30", await self.say("sabah brifingi bildirimi aç 8:30"))

    async def test_missions_end_to_end_and_exactly_once_delivery(self):
        conv = uuid.uuid4()
        await self.pool.execute("INSERT INTO conversations(id,user_id,title) VALUES($1,$2,'t')", conv, self.u)

        async def llm(prompt, system):
            if "mission planner" in system:
                return json.dumps({"steps": [{"type": "skill", "input": "saat kaç"}, {"type": "laptop", "input": "not defterini aç"}]})
            return "Rapor hazır."

        async def skill(value, user):
            return await s.instant_reply(value, pool=self.pool, user_id=user, read_only=True)

        async def research(value, user):
            return "x"
        app = {"db": self.pool, "mission_deps": {"llm": llm, "skill": skill, "research": research}}
        started = await ms.start(Req(app, self.u), "günümü planla", str(conv))
        self.assertTrue(started["mission_id"])
        self.assertIsNone((await ms.start(Req(app, self.u), "ikinci", str(conv)))["mission_id"])      # one at a time
        for _ in range(50):
            view = json.loads((await ms.get_mission(Req(app, self.u, {"id": started["mission_id"]}, {"conversation_id": str(conv)}))).text)
            if view["status"] == "done":
                break
            await asyncio.sleep(0.1)
        self.assertEqual((view["status"], view["delivered"], [x["status"] for x in view["steps"]]), ("done", True, ["done", "skipped"]))
        again = json.loads((await ms.get_mission(Req(app, self.u, {"id": started["mission_id"]}, {"conversation_id": str(conv)}))).text)
        self.assertNotIn("delivered", again)
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM messages WHERE conversation_id=$1 AND role='assistant'", conv), 1)

    async def test_lists_and_timers(self):
        self.assertIn("“alışveriş” listesine eklendi: süt, ekmek", await self.say("Alışveriş listesine süt ve ekmek ekle"))
        self.assertIn("Zaten vardı: Süt", await self.say("alışveriş listesine Süt ekle"))
        self.assertIn("• alışveriş: 2 öğe", await self.say("listelerim"))
        self.assertIn("• ekmek", await self.say("alışveriş listem"))
        self.assertIn("çıkarıldı: ekmek", await self.say("ekmek alışveriş listesinden çıkar"))
        self.assertIn("1 öğe", await self.say("alışveriş listesini temizle"))
        self.assertIn("5 dakika sonra", await self.say("5 dakika zamanlayıcı kur"))
        self.assertEqual(await self.pool.fetchval("SELECT text FROM owner_reminders WHERE user_id=$1", self.u), "Zamanlayıcı süresi doldu ⏲")

    async def test_expenses(self):
        self.assertIn("Kaydettim: 150 ₺ — market", await self.say("150 lira market harcaması ekle"))
        await self.say("bugün kahveye 80 tl harcadım")
        await self.say("dün 1.250,50 lira benzin harcadım")
        month = await self.say("bu ay ne kadar harcadım")
        self.assertIn("• benzin: 1.250,5 ₺", month)
        self.assertIn("market", month)
        self.assertIn("Son harcamayı sildim: 1.250,5 ₺ (benzin)", await self.say("son harcamayı sil"))
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM owner_expenses WHERE user_id=$1", self.u), 2)
        with self.assertRaises(asyncpg.CheckViolationError):
            await self.pool.execute("INSERT INTO owner_expenses(user_id,amount,category) VALUES($1,-5,'x')", self.u)

    async def test_habits_and_birthdays(self):
        self.assertIn("2/8 bardak", await self.say("2 bardak su içtim"))
        self.assertIn("5/8 bardak", await self.say("3 bardak su içtim"))
        await self.say("7 saat uyudum")
        await self.say("30 dakika yürüdüm")
        await self.say("kilom 72,5")
        self.assertIn("(öncekine göre -1,5 kg)", await self.say("kilom 71"))
        today = await self.say("sağlık özetim")
        self.assertIn("💧 Su: 5 bardak", today)
        self.assertIn("😴 Uyku: ortalama 7 saat", today)
        self.assertIn("Son kaydı sildim", await self.say("son aliskanlik kaydini sil"))
        with self.assertRaises(asyncpg.CheckViolationError):
            await self.pool.execute("INSERT INTO owner_habits(user_id,habit,amount) VALUES($1,'caffeine',1)", self.u)
        self.assertIn("Murat'ın doğum günü: 3 Mart", await self.say("Murat'ın doğum günü 3 Mart"))
        self.assertIn("zaten kayıtlı", await self.say("Murat'ın doğum günü 3 Mart"))
        rules = [r["repeat_rule"] for r in await self.pool.fetch("SELECT repeat_rule FROM owner_reminders WHERE user_id=$1 ORDER BY id", self.u)]
        self.assertEqual(rules, ["yearly:03-03", "yearly:03-02"])
        self.assertIn("• 3 Mart — Murat'ın", await self.say("doğum günlerim"))
        self.assertIn("yearly:02-14", (await self.say("her yıl 14 şubat sevgililer gününü hatırlat")) and
                      (await self.pool.fetchval("SELECT string_agg(repeat_rule, ',') FROM owner_reminders WHERE user_id=$1", self.u)))

    async def test_retention_export_and_diagnostics(self):
        await self.say("hatırla: annemin doğum günü 3 Mart")
        await self.pool.execute("INSERT INTO owner_reminders(user_id,text,due_at,status,delivered_at) VALUES($1,'eski',NOW()-interval '40 days','delivered',NOW()-interval '40 days')", self.u)
        removed = await ops.maintenance(self.pool)
        self.assertGreaterEqual(removed["owner_reminders"], 1)
        self.assertTrue(all(v >= 0 for v in removed.values()))
        data = await ops.export_owner_data(self.pool, self.u)
        self.assertEqual(data["memories"][0]["value"], "annemin doğum günü 3 Mart")
        self.assertIn("lists", data)
        self.assertIn("expenses", data)
        self.assertNotIn("endpoint", json.dumps(data))
        diag = await ops.diagnostics(self.app, self.u)
        self.assertEqual(diag["counts"]["memories"], 1)
        self.assertNotIn(-1, diag["counts"].values())
        key = await wp.load_vapid(self.pool)
        self.assertEqual(key[1], (await wp.load_vapid(self.pool))[1])           # VAPID key is stable


if __name__ == "__main__":
    unittest.main()

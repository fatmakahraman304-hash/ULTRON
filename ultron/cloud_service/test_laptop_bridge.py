"""Phone chat → laptop bridge: classification, confirmation guard, result delivery."""
import asyncio
import json
import unittest
from unittest import mock

import laptop_bridge as lb


class Classify(unittest.TestCase):
    def test_explicit_laptop_requests_route(self):
        for text in ("laptop: chrome aç", "bilgisayarda spotify'ı aç", "laptopumdaki indirilenler klasörünü listele",
                     "pc'de youtube aç", "bilgisayara ses seviyesini kıs"):
            self.assertIsNotNone(lb.classify(text), text)

    def test_screen_analysis_is_a_screen_task(self):
        for text in ("ekranıma bak ve ne olduğunu anlat", "ekran analizi yap", "ekranda ne var"):
            c = lb.classify(text)
            self.assertEqual(c["kind"], "screen", text)
            self.assertIn("screen_process", c["task"])
            self.assertIn(text, c["task"])

    def test_normal_chat_is_untouched(self):
        for text in ("merhaba", "bilgisayar nedir", "ekran kartı fiyatları", "telefonumun ekranı kırıldı",
                     "dosyayı sil", "yeni bir laptop öner", "x" * 5000):
            self.assertIsNone(lb.classify(text), text[:30])

    def test_destructive_needs_laptop_prefix(self):
        for text in ("bilgisayarı kapat", "bilgisayarımdaki dosyaları sil"):
            c = lb.classify(text)
            self.assertTrue(c["destructive"] and not c["confirmed"], text)
        c = lb.classify("laptop: bilgisayarı kapat")
        self.assertTrue(c["destructive"] and c["confirmed"])
        self.assertEqual(c["task"], "bilgisayarı kapat")


class Result(unittest.TestCase):
    def test_reply_from_command(self):
        self.assertEqual(lb.reply_from_command({"status": "completed", "result": {"assistant_reply": "Açtım."}}), ("completed", "Açtım."))
        self.assertEqual(lb.reply_from_command({"status": "completed", "result": json.dumps({"message": "Tamam"})}), ("completed", "Tamam"))
        self.assertEqual(lb.reply_from_command({"status": "queued", "result": {}})[0], "pending")
        state, text = lb.reply_from_command({"status": "failed", "result": {"message": "Uygulama yok"}})
        self.assertEqual(state, "failed")
        self.assertIn("başarısız", text)
        self.assertIn("Uygulama yok", text)


class FakeRequest(dict):
    def __init__(self, body, app, query=None, match=None):
        super().__init__(user_id="u", device_id="iphone-web")
        self._body, self.app, self.query, self.match_info = body, app, query or {}, match or {}

    async def json(self):
        return self._body


class FakePool:
    def __init__(self, online=True, statuses=("queued", "completed")):
        self.online, self.statuses, self.inserted, self.messages, self.cmd_reads = online, list(statuses), [], [], 0

    async def fetchval(self, sql, *a):
        if "INSERT INTO conversations" in sql:
            return a[0]
        if "FROM device_presence" in sql:
            return self.online
        if "INSERT INTO messages" in sql:
            self.messages.append(a)
            return len(self.messages)
        return None

    async def execute(self, *a):
        return None

    async def fetchrow(self, sql, *a):
        if "INSERT INTO device_commands" in sql:
            self.inserted.append(json.loads(a[1]))
            return {"id": 9}
        if "SELECT status,result FROM device_commands" in sql:
            status = self.statuses[min(self.cmd_reads, len(self.statuses) - 1)]
            self.cmd_reads += 1
            return {"status": status, "result": {"assistant_reply": "Chrome açıldı."} if status == "completed" else {}}
        return None


def call(body, pool):
    app = {"db": pool}
    with mock.patch.object(lb, "POLL_SECONDS", 0), mock.patch.object(lb, "WAIT_SECONDS", 5):
        response = asyncio.run(lb.route(FakeRequest(body, app)))
    return json.loads(response.text)


class Route(unittest.TestCase):
    def test_not_a_laptop_request(self):
        pool = FakePool()
        self.assertEqual(call({"message": "merhaba"}, pool), {"routed": False})
        self.assertEqual(pool.inserted, [])

    def test_completed_result_comes_back_from_the_laptop(self):
        pool = FakePool()
        out = call({"message": "bilgisayarda chrome aç"}, pool)
        self.assertEqual((out["routed"], out["status"], out["reply"]), (True, "completed", "Chrome açıldı."))
        self.assertEqual(pool.inserted[0]["origin"], "chat")
        self.assertEqual(pool.inserted[0]["text"], "bilgisayarda chrome aç")

    def test_offline_laptop_is_not_queued(self):
        pool = FakePool(online=False)
        out = call({"message": "laptop: chrome aç"}, pool)
        self.assertEqual(out["status"], "offline")
        self.assertEqual(pool.inserted, [])

    def test_destructive_without_prefix_is_not_sent(self):
        pool = FakePool()
        out = call({"message": "bilgisayarı kapat"}, pool)
        self.assertEqual(out["status"], "needs_confirmation")
        self.assertEqual(pool.inserted, [])
        self.assertEqual(len(call({"message": "laptop: bilgisayarı kapat"}, FakePool()).get("reply", "")) > 0, True)

    def test_slow_task_returns_pending_with_task_id(self):
        pool = FakePool(statuses=("delivered",))
        with mock.patch.object(lb, "POLL_SECONDS", 0), mock.patch.object(lb, "WAIT_SECONDS", 0):
            out = json.loads(asyncio.run(lb.route(FakeRequest({"message": "laptop: raporu hazırla"}, {"db": pool}))).text)
        self.assertEqual((out["status"], out["task_id"]), ("pending", 9))


if __name__ == "__main__":
    unittest.main()

"""Web Push crypto (RFC 8291 vector), VAPID, endpoint guard, proactive rules and prefs."""
import asyncio
import json
import unittest
from datetime import date, datetime, time, timedelta, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

import proactive as pro
import web_push as wp

UTC = timezone.utc
NOW = datetime(2026, 10, 21, 14, 5, tzinfo=UTC)  # 17:05 Istanbul


def run(c):
    return asyncio.run(c)


class Crypto(unittest.TestCase):
    def test_rfc8291_appendix_a_vector(self):
        eph = ec.derive_private_key(int.from_bytes(wp.b64u_decode("yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"), "big"), ec.SECP256R1())
        body = wp.encrypt(b"When I grow up, I want to be a watermelon",
                          "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
                          "BTBZMqHH6r4Tts7J_aSIgg", ephemeral=eph, salt=wp.b64u_decode("DGv6ra1nlYgDCS1FRnbzlw"))
        self.assertEqual(wp.b64u(body), "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN")

    def test_round_trip_decrypt_with_the_browser_side(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        ua = ec.generate_private_key(ec.SECP256R1())
        ua_pub = ua.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        auth = b"0123456789abcdef"
        msg = json.dumps({"title": "Merhaba", "body": "İçerik ğüşıöç"}, ensure_ascii=False).encode()
        blob = wp.encrypt(msg, wp.b64u(ua_pub), wp.b64u(auth))
        salt, rs, idlen = blob[:16], int.from_bytes(blob[16:20], "big"), blob[20]
        as_pub, cipher = blob[21:21 + idlen], blob[21 + idlen:]
        shared = ua.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
        prk = HKDF(hashes.SHA256(), 32, auth, b"WebPush: info\0" + ua_pub + as_pub).derive(shared)
        cek = HKDF(hashes.SHA256(), 16, salt, b"Content-Encoding: aes128gcm\0").derive(prk)
        nonce = HKDF(hashes.SHA256(), 12, salt, b"Content-Encoding: nonce\0").derive(prk)
        plain = AESGCM(cek).decrypt(nonce, cipher, None)
        self.assertEqual((rs, plain[:-1], plain[-1]), (4096, msg, 2))

    def test_vapid_jwt_signature_verifies(self):
        key = ec.generate_private_key(ec.SECP256R1())
        header = wp.vapid_authorization("https://web.push.apple.com/abc", key, "mailto:a@b.c", now=1000.0)
        token = header.split("t=")[1].split(",")[0]
        h, c, s = token.split(".")
        claims = json.loads(wp.b64u_decode(c))
        self.assertEqual((claims["aud"], claims["exp"], claims["sub"]), ("https://web.push.apple.com", 1000 + 43200, "mailto:a@b.c"))
        raw = wp.b64u_decode(s)
        sig = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
        key.public_key().verify(sig, f"{h}.{c}".encode(), ec.ECDSA(hashes.SHA256()))  # raises if invalid
        self.assertIn("k=" + wp.b64u(wp._public_bytes(key)), header)

    def test_endpoint_allowlist_blocks_ssrf(self):
        good = "https://web.push.apple.com/AbCdEf1234567890"
        self.assertTrue(wp.valid_endpoint(good))
        self.assertTrue(wp.valid_endpoint("https://fcm.googleapis.com/fcm/send/abcdefghijk"))
        for bad in ("http://web.push.apple.com/abcdefghijklmnop", "https://169.254.169.254/latest/meta-data/x",
                    "https://evil.com/web.push.apple.com/abcdefgh", "https://web.push.apple.com.evil.com/abcdefghij",
                    "https://u:p@web.push.apple.com/abcdefghijk", "https://web.push.apple.com:8443/abcdefghijk", "", None, 5):
            self.assertFalse(wp.valid_endpoint(bad), str(bad))

    def test_bad_keys_and_oversize_payload_rejected(self):
        with self.assertRaises(ValueError):
            wp.encrypt(b"x", "AAAA", "BBBB")
        with self.assertRaises(ValueError):
            wp.encrypt(b"x" * 5000, "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4", "BTBZMqHH6r4Tts7J_aSIgg")


class QuietHours(unittest.TestCase):
    def test_overnight_and_disabled(self):
        p = dict(pro.DEFAULT_PREFS)
        at = lambda h, m=0: datetime(2026, 10, 21, h, m, tzinfo=pro.HOME_TZ)
        self.assertTrue(pro.in_quiet_hours(p, at(23, 30)))
        self.assertTrue(pro.in_quiet_hours(p, at(3)))
        self.assertFalse(pro.in_quiet_hours(p, at(7)))
        self.assertFalse(pro.in_quiet_hours(p, at(12)))
        self.assertFalse(pro.in_quiet_hours({**p, "quiet_start": "00:00", "quiet_end": "00:00"}, at(3)))


class FakePool:
    def __init__(self, plans=(), prefs=None):
        self.plans, self.prefs, self.saved = list(plans), prefs, {}

    async def fetch(self, sql, *a):
        if "FROM owner_plans" in sql:
            return self.plans
        return []

    async def fetchval(self, sql, *a):
        if "FROM owner_prefs" in sql:
            return self.prefs
        if "FROM owner_calendar_feeds" in sql:
            return None
        if "COUNT(*) FROM push_subscriptions" in sql:
            return 1
        return None

    async def execute(self, sql, *a):
        if "INTO owner_prefs" in sql:
            self.saved = json.loads(a[1])


async def dry_weather(url, key, ttl):
    hours = [(datetime(2026, 10, 21, 17, 0) + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(24)]
    return {"hourly": {"time": hours, "precipitation_probability": [10, 80, 90] + [0] * 21}}


async def sunny(url, key, ttl):
    hours = [(datetime(2026, 10, 21, 17, 0) + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(24)]
    return {"hourly": {"time": hours, "precipitation_probability": [0] * 24}}


class Rules(unittest.TestCase):
    def test_event_in_ten_minutes_triggers_once_keyed(self):
        pool = FakePool(plans=[{"id": 7, "title": "Diş randevusu", "scheduled_date": date(2026, 10, 21), "scheduled_time": time(17, 15)},
                               {"id": 8, "title": "Akşam yemeği", "scheduled_date": date(2026, 10, 21), "scheduled_time": time(20, 0)}])
        items = run(pro.evaluate(pool, "u", NOW, sunny))
        self.assertEqual([i["key"] for i in items], ["plan:7:2026-10-21"])
        self.assertIn("17:15 — Diş randevusu", items[0]["body"])

    def test_rain_alert_when_probability_high(self):
        items = run(pro.evaluate(FakePool(), "u", NOW, dry_weather))
        self.assertEqual(items[0]["key"], "rain:2026-10-21")
        self.assertIn("%90", items[0]["body"])
        self.assertEqual(run(pro.evaluate(FakePool(), "u", NOW, sunny)), [])

    def test_quiet_hours_and_switch_silence_rules(self):
        night = datetime(2026, 10, 21, 21, 30, tzinfo=UTC)  # 00:30 Istanbul
        self.assertEqual(run(pro.evaluate(FakePool(), "u", night, dry_weather)), [])
        self.assertEqual(run(pro.evaluate(FakePool(prefs={"proactive": False}), "u", NOW, dry_weather)), [])

    def test_broken_weather_does_not_silence_other_rules(self):
        async def broken(*a):
            raise RuntimeError("down")
        pool = FakePool(plans=[{"id": 1, "title": "Toplantı", "scheduled_date": date(2026, 10, 21), "scheduled_time": time(17, 14)}])
        self.assertEqual(len(run(pro.evaluate(pool, "u", NOW, broken))), 1)


class Prefs(unittest.TestCase):
    def test_commands(self):
        pool = FakePool()
        self.assertIn("23:00 – 06:30", run(pro.handle_prefs("sessiz saatler 23 ile 6:30", pool, "u")) or "")
        self.assertEqual((pool.saved["quiet_start"], pool.saved["quiet_end"]), ("23:00", "06:30"))
        self.assertIn("08:30", run(pro.handle_prefs("sabah brifingi bildirimi aç 8:30", pool, "u")))
        self.assertTrue(pool.saved["morning_brief"])
        run(pro.handle_prefs("proaktif uyarıları kapat", pool, "u"))
        self.assertFalse(pool.saved["proactive"])
        self.assertIsNone(run(pro.handle_prefs("bugün hava nasıl", pool, "u")))


if __name__ == "__main__":
    unittest.main()

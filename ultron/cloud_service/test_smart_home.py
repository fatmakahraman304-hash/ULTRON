"""Smart home: Home Assistant command parsing, entity matching, safety rules."""
import asyncio
import unittest
from unittest import mock

import instant_skills as s
import smart_home as sh

STATES = [
    {"entity_id": "light.salon", "state": "on", "attributes": {"friendly_name": "Salon Işığı"}},
    {"entity_id": "light.yatak_odasi", "state": "off", "attributes": {"friendly_name": "Yatak Odası Lambası"}},
    {"entity_id": "switch.kahve", "state": "off", "attributes": {"friendly_name": "Kahve Makinesi Prizi"}},
    {"entity_id": "climate.salon_klima", "state": "cool", "attributes": {"friendly_name": "Salon Klima"}},
    {"entity_id": "cover.salon_perde", "state": "closed", "attributes": {"friendly_name": "Salon Perdesi", "device_class": "curtain"}},
    {"entity_id": "cover.garaj", "state": "closed", "attributes": {"friendly_name": "Garaj Kapısı", "device_class": "garage"}},
    {"entity_id": "scene.film", "state": "scening", "attributes": {"friendly_name": "Film Sahnesi"}},
    {"entity_id": "lock.on_kapi", "state": "unlocked", "attributes": {"friendly_name": "Ön Kapı Kilidi"}},
    {"entity_id": "sensor.salon_sicaklik", "state": "22.5", "attributes": {"friendly_name": "Salon Sıcaklık", "device_class": "temperature", "unit_of_measurement": "°C"}},
    {"entity_id": "sensor.salon_nem", "state": "48", "attributes": {"friendly_name": "Salon Nem", "device_class": "humidity", "unit_of_measurement": "%"}},
    {"entity_id": "sensor.cpu", "state": "3", "attributes": {"friendly_name": "CPU", "device_class": "power"}},
]


class FakeHA:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    async def __call__(self, method, path, body=None):
        if self.fail:
            raise RuntimeError("down")
        if path == "/api/states":
            return 200, STATES
        self.calls.append((path, body))
        return 200, []


def ask(text, ha=None):
    sh._CACHE.clear()
    ha = ha or FakeHA()
    out = asyncio.run(s.instant_reply(text, ha=ha))
    return out, ha


class Parse(unittest.TestCase):
    def test_commands_and_non_commands(self):
        self.assertEqual(sh.parse_command("salon ışığını aç")["action"], "on")
        self.assertTrue(sh.parse_command("tüm ışıkları kapat")["all"])
        self.assertEqual(sh.parse_command("yatak odası lambasını %30 yap")["value"], 30)
        self.assertEqual(sh.parse_command("klimayı 24 dereceye ayarla")["value"], 24)
        for text in ("merhaba", "ışık hızı nedir", "kapıyı aç", "bilgisayarı kapat", "bugün hava sıcak mı", "ışığı neden kapatıyorsun",
                     "kaç kişi var", "hava kaç derece"):
            self.assertIsNone(sh.parse_command(text), text)


class Execute(unittest.TestCase):
    def test_light_on_by_room_name_with_turkish_suffixes(self):
        out, ha = ask("salon ışığını aç")
        self.assertEqual(out["skill"], "smart_home")
        self.assertEqual(ha.calls, [("/api/services/light/turn_on", {"entity_id": "light.salon"})])
        self.assertIn("Salon Işığı açıldı", out["reply"])

    def test_brightness_temperature_cover_scene(self):
        self.assertEqual(ask("yatak odası lambasını %30 yap")[1].calls[0],
                         ("/api/services/light/turn_on", {"entity_id": "light.yatak_odasi", "brightness_pct": 30}))
        self.assertEqual(ask("klimayı 24 dereceye ayarla")[1].calls[0],
                         ("/api/services/climate/set_temperature", {"entity_id": "climate.salon_klima", "temperature": 24}))
        self.assertEqual(ask("perdeyi aç")[1].calls[0][0], "/api/services/cover/open_cover")
        self.assertEqual(ask("film sahnesini çalıştır")[1].calls[0][0], "/api/services/scene/turn_on")

    def test_all_lights_and_ambiguity(self):
        _, ha = ask("tüm ışıkları kapat")
        self.assertEqual(sorted(b["entity_id"] for _, b in ha.calls), ["light.salon", "light.yatak_odasi"])
        out, ha = ask("ışığı kapat")
        self.assertEqual(ha.calls, [])
        self.assertIn("Hangisini", out["reply"])

    def test_safety_never_unlock_never_open_garage(self):
        out, ha = ask("kapının kilidini aç")
        self.assertEqual(ha.calls, [])
        self.assertIn("açmıyorum", out["reply"])
        out, ha = ask("kapıyı kilitle")
        self.assertEqual(ha.calls[0][0], "/api/services/lock/lock")
        out, ha = ask("garaj kapısını aç")
        self.assertEqual(ha.calls, [])
        self.assertIn("Komutu uygulayamadım", out["reply"])
        _, ha = ask("garaj kapısını kapat")
        self.assertEqual(ha.calls[0][0], "/api/services/cover/close_cover")

    def test_status_and_sensors(self):
        out, ha = ask("evde ışıklar açık mı")
        self.assertEqual(ha.calls, [])
        self.assertIn("2 cihazdan 1", out["reply"])
        self.assertIn("Salon Sıcaklık: 22.5 °C", ask("salonun sıcaklığı kaç derece")[0]["reply"])
        self.assertIn("Salon Nem: 48 %", ask("salon nemi nedir")[0]["reply"])

    def test_unknown_device_and_ha_down_are_honest(self):
        self.assertIn("bulamadım", ask("mutfak ışığını aç")[0]["reply"])
        out, ha = ask("salon ışığını aç", FakeHA(fail=True))
        self.assertIn("ulaşamadım", out["reply"])

    def test_not_configured_message(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            for k in ("HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN"):
                __import__("os").environ.pop(k, None)
            out = asyncio.run(s.instant_reply("salon ışığını aç", fetch_json=lambda *a: None))
        self.assertIn("bağlı değil", out["reply"])

    def test_config_requires_https_and_token(self):
        with mock.patch.dict("os.environ", {"HOME_ASSISTANT_URL": "http://192.168.1.5:8123", "HOME_ASSISTANT_TOKEN": "t"}):
            self.assertIsNone(sh.config())
        with mock.patch.dict("os.environ", {"HOME_ASSISTANT_URL": "https://abc.ui.nabu.casa/", "HOME_ASSISTANT_TOKEN": "t"}):
            self.assertEqual(sh.config(), ("https://abc.ui.nabu.casa", "t"))


if __name__ == "__main__":
    unittest.main()

"""Smart home from chat through Home Assistant's REST API.

Needs HOME_ASSISTANT_URL (public https address, e.g. Nabu Casa) and HOME_ASSISTANT_TOKEN
(a long-lived access token) in the environment; without them the skill says so instead of
pretending. Safety: locks can only be locked, garage/door/gate covers can only be closed.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

if __package__:
    from .text_normalization import fold_turkish
    from . import http_client
else:
    from text_normalization import fold_turkish
    import http_client

HaCall = Callable[..., Awaitable[tuple[int, Any]]]
_CACHE: dict[str, tuple[float, list]] = {}
SUPPORTED = ("light", "switch", "fan", "climate", "cover", "scene", "lock", "sensor")
_DOMAIN_WORDS = (
    ("light", r"isi[kg]\w*|lamba\w*|aydinlatma\w*|abajur\w*|avize\w*|led\w*"),
    ("switch", r"priz\w*|fis\w*|role\w*"),
    ("climate", r"klima\w*|isitici\w*|termostat\w*|kalorifer\w*|petek\w*"),
    ("cover", r"perde\w*|panjur\w*|stor\w*|garaj\w*|kepenk\w*"),
    ("fan", r"fan\b|vantilator\w*|havalandirma\w*"),
    ("scene", r"sahne\w*|mod\b"),
    ("lock", r"kilit\w*|kilid\w*"),
    ("sensor", r"sicak\w*|nem\b|nemi\w*"),
)
_ON = r"(?:ac|acar misin|acsana|yak|yakar misin|calistir|baslat|aktif et|ac lutfen|acin)"
_OFF = r"(?:kapat|kapatir misin|sondur|durdur|kapatsana|kapatin)"
_ALL = re.compile(r"\b(?:tum|butun|hepsini|hepsi|evdeki|her yerdeki|tamami)\b")
_STATUS = re.compile(r"\b(?:acik mi|kapali mi|durumu|durum nedir|kac derece|sicak\w*|nem\w*|acik olan|acik kalan)\b")
_PCT = re.compile(r"(?:%\s*(\d{1,3})|yuzde\s*(\d{1,3})|(\d{1,3})\s*(?:yuzde|%))")
_TEMP = re.compile(r"\b(\d{2})\s*(?:derece\w*|°|c\b)")
_NOISE = re.compile(r"\b(?:lutfen|bana|su|sunu|bunu|evde|evdeki|tum|butun|hepsini|hepsi|acik|kapali|mi|mu|ne|nedir|kac|durumu|"
                    r"yap|ayarla|ac|acar|misin|kapat|yak|sondur|calistir|baslat|derece\w*|yuzde|sahnesi\w*|sahne\w*|modu|mod|"
                    r"isi[kg]\w*|lambasi\w*|lamba\w*|klima\w*|perde\w*|panjur\w*|priz\w*|fan|vantilator\w*|kilit\w*|kapi\w*|"
                    r"ve|ile|de|da|nin|nun|in|un|i|u|yi|yu|ni|nu)\b")
_RISKY_COVERS = {"garage", "door", "gate"}


def config() -> tuple[str, str] | None:
    url, token = os.getenv("HOME_ASSISTANT_URL", "").strip().rstrip("/"), os.getenv("HOME_ASSISTANT_TOKEN", "").strip()
    parts = urlsplit(url)
    if not url or not token or parts.scheme != "https" or parts.username or parts.password or not parts.hostname:
        return None
    return url, token


async def ha_call(method: str, path: str, body: dict | None = None) -> tuple[int, Any]:  # noqa: C901
    cfg = config()
    if cfg is None:
        raise RuntimeError("not_configured")
    status, body, _ = await http_client.fetch(cfg[0] + path, method=method, json_body=body, timeout=10, max_bytes=3_000_000,
                                              headers={"Authorization": "Bearer " + cfg[1]})
    data = None
    if status == 200:
        import json
        try:
            data = json.loads(body or b"null")
        except ValueError:
            data = None
    return status, data


def parse_command(text: str) -> dict | None:
    f = fold_turkish(text)
    if len(f) > 160:
        return None
    domain = next((d for d, pat in _DOMAIN_WORDS if re.search(r"\b(?:" + pat + r")", f)), None)
    if domain is None:
        return None
    if domain == "lock" and not re.search(r"kilit\w*|kilid\w*", f):
        return None
    on = bool(re.search(r"\b" + _ON + r"\b", f.replace("acik mi", "")))
    off = bool(re.search(r"\b" + _OFF + r"\b", f.replace("kapali mi", "")))
    status = bool(_STATUS.search(f)) and not on and not off
    pct = _PCT.search(f)
    temp = _TEMP.search(f)
    locking = bool(re.search(r"kilitle\w*", f))
    if not (on or off or status or pct or temp or locking):
        return None
    if re.search(r"\b(?:neden|niye|nasil calisir|ne demek|fiyat|oner|nedir)\b", f) and not status:
        return None
    cmd: dict = {"domain": domain, "all": bool(_ALL.search(f)), "tokens": [w for w in _NOISE.sub(" ", f).split() if len(w) > 1]}
    cmd["tokens"] = [w for w in cmd["tokens"] if not (w.isdigit() or w.startswith("%"))]
    if domain == "lock":
        if locking:
            cmd["action"] = "lock"
        elif on:
            cmd["action"] = "unlock"
        else:
            return None
        cmd["tokens"] = [w for w in cmd["tokens"] if not w.startswith(("kilit", "kilid"))]
        return cmd
    if domain == "sensor":
        cmd["metric"] = "humidity" if re.search(r"\bnem\w*", f) and not re.search(r"sicak", f) else "temperature"
        cmd["tokens"] = [w for w in cmd["tokens"] if not w.startswith(("sicak", "nem"))]
    if domain == "sensor" and (not status or not cmd["tokens"] or re.search(r"\b(?:hava|bugun|yarin|disarida|dis)\b", f)):
        return None
    if status:
        cmd["action"] = "status"
    elif temp and domain == "climate":
        cmd.update(action="set_temperature", value=int(temp.group(1)))
    elif pct and domain in ("light", "cover", "fan"):
        cmd.update(action="set_level", value=min(100, int([g for g in pct.groups() if g][0])))
    elif off and not on:
        cmd["action"] = "off"
    elif on:
        cmd["action"] = "on"
    else:
        return None
    return cmd


def wants_smart_home(text: str) -> bool:
    return parse_command(text) is not None


async def list_entities(call: HaCall) -> list[dict]:
    key = os.getenv("HOME_ASSISTANT_URL", "")
    cached = _CACHE.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    status, data = await call("GET", "/api/states")
    if status != 200 or not isinstance(data, list):
        raise RuntimeError(f"ha_status_{status}")
    out = []
    for item in data:
        eid = str(item.get("entity_id", ""))
        domain = eid.split(".", 1)[0]
        if domain not in SUPPORTED:
            continue
        attrs = item.get("attributes") or {}
        if domain == "sensor" and attrs.get("device_class") not in ("temperature", "humidity"):
            continue
        out.append({"id": eid, "domain": domain, "state": item.get("state"),
                    "name": str(attrs.get("friendly_name") or eid), "device_class": attrs.get("device_class"),
                    "unit": attrs.get("unit_of_measurement")})
    _CACHE[key] = (time.monotonic() + 120, out)
    return out


def _name_words(entity: dict) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", fold_turkish(entity["name"] + " " + entity["id"].split(".", 1)[1])) if len(w) >= 3]


def _match(entities: list[dict], domain: str, tokens: list[str]) -> list[dict]:
    pool = [e for e in entities if e["domain"] == domain]
    if not tokens:
        return pool
    def has(words: list[str], token: str) -> bool:
        return any(token.startswith(w) or w.startswith(token) for w in words)
    return [e for e in pool if all(has(_name_words(e), t) for t in tokens)]


async def handle(text: str, call: HaCall | None = None) -> str | None:
    cmd = parse_command(text)
    if cmd is None:
        return None
    if call is None and config() is None:
        return ("Akıllı ev şu an bağlı değil. Home Assistant'ın herkese açık https adresini ve uzun ömürlü erişim anahtarını "
                "sunucuya (HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN) eklediğinde ışık, priz, klima, perde ve sahneleri buradan yönetebilirim.")
    call = call or ha_call
    if cmd["action"] == "unlock":
        return "Güvenlik için kapı kilidini sohbetten açmıyorum. Kilitlemem istenirse “kapıyı kilitle” diyebilirsin."
    try:
        entities = await list_entities(call)
        domain = cmd["domain"]
        if cmd["action"] == "status":
            if domain in ("climate", "sensor"):
                sensors = _match(entities, "sensor", cmd["tokens"]) or []
                sensors = [e for e in sensors if e["device_class"] == cmd.get("metric", e["device_class"])]
                if not sensors:
                    return "Eşleşen bir sıcaklık/nem sensörü bulamadım."
                return "\n".join(f"• {e['name']}: {e['state']} {e['unit'] or ''}".rstrip() for e in sensors[:6])
            items = _match(entities, domain, cmd["tokens"])
            if not items:
                return "Eşleşen bir cihaz bulamadım."
            on = [e["name"] for e in items if e["state"] in ("on", "open", "unlocked", "heat", "cool", "auto")]
            if len(items) == 1:
                return f"{items[0]['name']}: {_tr_state(items[0]['state'])}"
            return (f"{len(items)} cihazdan {len(on)} tanesi açık/aktif" + (": " + ", ".join(on[:8]) if on else "") + ".")
        items = _match(entities, domain, cmd["tokens"])
        if domain == "cover" and re.search(r"\b(?:perde|panjur|stor|kepenk)\w*", fold_turkish(text)):
            items = [e for e in items if e.get("device_class") not in _RISKY_COVERS]  # "perde" never means the garage
        if not items:
            hint = " ".join(cmd["tokens"])
            return f"“{hint}” adında bir {_DOMAIN_TR[domain]} bulamadım." if hint else f"Kayıtlı bir {_DOMAIN_TR[domain]} bulamadım."
        if len(items) > 1 and not cmd["all"]:
            names = ", ".join(e["name"] for e in items[:5])
            return f"Birden fazla eşleşme var ({names}). Hangisini istediğini söyler misin, ya da “tüm” de."
        items = items[:30]
        done, refused = [], []
        for e in items:
            svc = _service(cmd, e)
            if svc is None:
                refused.append(e["name"])
                continue
            status, _ = await call("POST", f"/api/services/{svc[0]}/{svc[1]}", svc[2])
            (done if status == 200 else refused).append(e["name"])
        if not done:
            return "Komutu uygulayamadım" + (": güvenlik nedeniyle garaj/kapı türü perdeleri sohbetten açmıyorum." if refused and cmd["action"] == "on" and domain == "cover" else ". Home Assistant reddetti.")
        verb = _VERB_TR.get(cmd["action"], "güncellendi")
        what = done[0] if len(done) == 1 else f"{len(done)} cihaz"
        extra = f" ({cmd['value']}{'°C' if cmd['action'] == 'set_temperature' else '%'})" if "value" in cmd else ""
        return f"{what} {verb}{extra} ✓" + (f" (atlananlar: {', '.join(refused[:3])})" if refused else "")
    except Exception:
        return "Akıllı ev sistemine şu an ulaşamadım; komutu uygulamadım."


_DOMAIN_TR = {"light": "ışık", "switch": "priz", "fan": "fan", "climate": "klima", "cover": "perde", "scene": "sahne", "lock": "kilit"}
_VERB_TR = {"on": "açıldı", "off": "kapatıldı", "set_level": "ayarlandı", "set_temperature": "ayarlandı", "lock": "kilitlendi"}


def _tr_state(state: object) -> str:
    return {"on": "açık", "off": "kapalı", "open": "açık", "closed": "kapalı", "locked": "kilitli", "unlocked": "kilidi açık",
            "unavailable": "ulaşılamıyor", "unknown": "bilinmiyor"}.get(str(state), str(state))


def _service(cmd: dict, e: dict) -> tuple[str, str, dict] | None:
    d, a, body = e["domain"], cmd["action"], {"entity_id": e["id"]}
    if d == "lock":
        return ("lock", "lock", body) if a == "lock" else None
    if d == "scene":
        return ("scene", "turn_on", body) if a == "on" else None
    if d == "cover":
        if a == "on":
            return None if e.get("device_class") in _RISKY_COVERS else ("cover", "open_cover", body)
        if a == "off":
            return ("cover", "close_cover", body)
        if a == "set_level":
            return None if e.get("device_class") in _RISKY_COVERS else ("cover", "set_cover_position", {**body, "position": cmd["value"]})
        return None
    if d == "climate":
        if a == "set_temperature":
            return ("climate", "set_temperature", {**body, "temperature": cmd["value"]})
        return ("climate", "turn_on" if a == "on" else "turn_off", body) if a in ("on", "off") else None
    if d == "light":
        if a == "set_level":
            return ("light", "turn_on", {**body, "brightness_pct": cmd["value"]})
        return ("light", "turn_on" if a == "on" else "turn_off", body) if a in ("on", "off") else None
    if d == "fan" and a == "set_level":
        return ("fan", "set_percentage", {**body, "percentage": cmd["value"]})
    if d in ("switch", "fan"):
        return (d, "turn_on" if a == "on" else "turn_off", body) if a in ("on", "off") else None
    return None

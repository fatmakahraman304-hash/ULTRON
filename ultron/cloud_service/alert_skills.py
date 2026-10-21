"""Price alerts from chat: "bitcoin 70 bin dolara çıkarsa haber ver", "dolar 45 TL olunca uyar".

Created and cancelled only by the owner's explicit sentence; evaluated by the proactive
dispatcher; each alert fires once. Prices come from CoinGecko / Frankfurter (ECB).
"""
from __future__ import annotations

import re
from typing import Any, Awaitable, Callable
from urllib.parse import urlencode

if __package__:
    from .text_normalization import fold_turkish
    from .knowledge_skills import _COINS, _COIN_RE
else:
    from text_normalization import fold_turkish
    from knowledge_skills import _COINS, _COIN_RE

FetchJson = Callable[[str, str, int], Awaitable[dict]]
MAX_ACTIVE = 12
_FX = {"dolar": "USD", "usd": "USD", "euro": "EUR", "avro": "EUR", "eur": "EUR", "sterlin": "GBP", "gbp": "GBP"}
_FX_RE = re.compile(r"\b(" + "|".join(_FX) + r")\w*\b")
_ALERT = re.compile(r"\b(?:haber ver|uyar|bildir|alarm kur|bildirim gonder|haberdar et)\w*\b")
_LIST = re.compile(r"\b(?:fiyat )?alarm(?:lar)?(?:im| listesi| neler| var mi)\b|\balarmlarimi (?:goster|listele)\b")
_CANCEL = re.compile(r"\b(?:fiyat )?alarm\w*\b.*\b(?:iptal|sil|kaldir)\b|\b(?:iptal|sil|kaldir)\b.*\balarm\w*\b")
_NUM = re.compile(r"(\d+(?:[.,]\d+)?)\s*(bin|milyon|k)?\b")


def _threshold(folded: str) -> float | None:
    best = None
    for m in _NUM.finditer(folded):
        raw = m.group(1)
        value = float(raw.replace(".", "").replace(",", ".")) if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw) else float(raw.replace(",", "."))
        value *= {"bin": 1e3, "k": 1e3, "milyon": 1e6}.get(m.group(2) or "", 1)
        if value > 0:
            best = value
    return best


def parse_alert(text: str) -> dict | None:
    f = fold_turkish(text)
    if len(f) > 120 or not _ALERT.search(f) or _LIST.search(f) or _CANCEL.search(f):
        return None
    value = _threshold(f)
    if value is None:
        return None
    coin = _COIN_RE.search(f)
    if coin:
        vs = "try" if re.search(r"\b(?:tl|lira\w*|try)\b", f) else "usd"
        asset, kind = _COINS[coin.group(1)], "coin"
    else:
        fx = _FX_RE.search(f)
        if not fx:
            return None
        asset, kind, vs = _FX[fx.group(1)], "fx", "try"
    direction = "above" if re.search(r"\b(?:cik\w*|gec\w*|ustu\w*|yukse\w*|ulas\w*|asar|artar)\b", f) else \
        "below" if re.search(r"\b(?:dus\w*|alt\w*|inerse|ined\w*|azal\w*)\b", f) else None
    return {"asset": asset, "kind": kind, "vs": vs, "direction": direction, "threshold": value}


async def current_price(fetch_json: FetchJson, kind: str, asset: str, vs: str) -> float:
    if kind == "coin":
        data = await fetch_json("https://api.coingecko.com/api/v3/simple/price?" + urlencode({"ids": asset, "vs_currencies": vs}), f"coin:{asset}:{vs}", 120)
        return float(data[asset][vs])
    data = await fetch_json("https://api.frankfurter.app/latest?" + urlencode({"from": asset, "to": "TRY"}), f"fx:{asset}:TRY", 900)
    return float(data["rates"]["TRY"])


def _fmt(value: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")


async def handle(text: str, pool: Any, user_id: str, fetch_json: FetchJson | None) -> str | None:
    if pool is None:
        return None
    f = fold_turkish(text)
    if _CANCEL.search(f) and len(f) <= 60 and re.search(r"\b(?:fiyat|kripto|dolar|euro|bitcoin)\b|\balarmlarimi?\b", f):
        n = await pool.fetchval("WITH c AS (UPDATE owner_alerts SET active=FALSE WHERE user_id=$1 AND active RETURNING 1) SELECT COUNT(*) FROM c", user_id)
        return f"{int(n or 0)} fiyat alarmını iptal ettim." if n else "İptal edilecek aktif fiyat alarmı yok."
    if _LIST.search(f) and len(f) <= 60:
        rows = await pool.fetch("SELECT asset,vs,direction,threshold FROM owner_alerts WHERE user_id=$1 AND active ORDER BY id LIMIT 12", user_id)
        if not rows:
            return "Aktif fiyat alarmın yok. Örn. “bitcoin 70 bin dolara çıkarsa haber ver”."
        return "Fiyat alarmların:\n" + "\n".join(
            f"• {r['asset']} {'≥' if r['direction'] == 'above' else '≤'} {_fmt(r['threshold'])} {'$' if r['vs'] == 'usd' else '₺'}" for r in rows)
    alert = parse_alert(text)
    if alert is None:
        return None
    if fetch_json is None:
        return None
    count = await pool.fetchval("SELECT COUNT(*) FROM owner_alerts WHERE user_id=$1 AND active", user_id)
    if int(count or 0) >= MAX_ACTIVE:
        return f"En fazla {MAX_ACTIVE} aktif alarm tutabiliyorum; önce bazılarını iptal et."
    try:
        price = await current_price(fetch_json, alert["kind"], alert["asset"], alert["vs"])
    except Exception:
        return "Şu anki fiyata ulaşamadığım için alarmı kurmadım; biraz sonra yeniden dene."
    direction = alert["direction"] or ("above" if alert["threshold"] > price else "below")
    crossed = price >= alert["threshold"] if direction == "above" else price <= alert["threshold"]
    unit = "$" if alert["vs"] == "usd" else "₺"
    if crossed:
        return f"{alert['asset']} zaten {_fmt(price)} {unit}; hedef ({_fmt(alert['threshold'])} {unit}) şimdiden {'aşılmış' if direction == 'above' else 'altında'}. Farklı bir hedef söyler misin?"
    await pool.execute("INSERT INTO owner_alerts(user_id,asset,kind,vs,direction,threshold) VALUES($1,$2,$3,$4,$5,$6)",
                       user_id, alert["asset"], alert["kind"], alert["vs"], direction, alert["threshold"])
    return (f"Tamam: {alert['asset']} {_fmt(alert['threshold'])} {unit} seviyesine {'çıkarsa' if direction == 'above' else 'inerse'} "
            f"haber vereceğim (şu an {_fmt(price)} {unit}). Alarm bir kez çalar. Bildirimlerin açık olduğundan emin ol.")


async def check_all(pool: Any, fetch_json: FetchJson) -> list[tuple[str, dict]]:
    """Evaluate active alerts; return [(user_id, notification)] for those that fired (and deactivate them)."""
    rows = await pool.fetch("SELECT id,user_id,asset,kind,vs,direction,threshold FROM owner_alerts WHERE active ORDER BY id LIMIT 100")
    fired = []
    cache: dict = {}
    for r in rows:
        key = (r["kind"], r["asset"], r["vs"])
        if key not in cache:
            try:
                cache[key] = await current_price(fetch_json, *key)
            except Exception:
                cache[key] = None
        price = cache[key]
        if price is None:
            continue
        hit = price >= r["threshold"] if r["direction"] == "above" else price <= r["threshold"]
        if hit and await pool.fetchval("UPDATE owner_alerts SET active=FALSE,fired_at=NOW() WHERE id=$1 AND active RETURNING id", r["id"]):
            unit = "$" if r["vs"] == "usd" else "₺"
            fired.append((r["user_id"], {"key": f"alert:{r['id']}", "title": f"Fiyat alarmı: {r['asset']}",
                                          "body": f"{r['asset']} {_fmt(price)} {unit} oldu (hedef {_fmt(r['threshold'])} {unit})."}))
    return fired

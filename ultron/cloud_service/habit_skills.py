"""Habit & health log from chat: water, sleep, exercise, steps, weight, mood.

"2 bardak su içtim", "7 saat uyudum", "30 dakika yürüdüm", "8000 adım attım", "kilom 72,5", "modum 4",
"bugün kaç bardak su içtim", "sağlık özetim", "bu hafta ne kadar spor yaptım". Informational, not medical advice.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import HOME_TZ
else:
    from text_normalization import fold_turkish
    from reminders import HOME_TZ

TARGETS = {"water": 8.0, "sleep": 7.0, "exercise": 30.0, "steps": 8000.0}
_NUM = r"(\d+(?:[.,]\d+)?|yarim|bir|iki|uc|dort|bes|alti|yedi|sekiz|dokuz|on)"
_WORDS = {"yarim": 0.5, "bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}
_WATER = re.compile(r"^\s*(?:" + _NUM + r"\s*)?(?:(bardak|litre|lt|ml|sise)\s+)?su\s+ictim\s*$")
_SLEEP = re.compile(r"^\s*(?:" + _NUM + r"\s*saat\s+(?:buçuk\s+)?uyudum|uyudum\s+" + _NUM + r"\s*saat)\s*$")
_SPORT = r"(?:yurudum|kostum|yuzdum|spor yaptim|yoga yaptim|antrenman yaptim|egzersiz yaptim|bisiklet surdum|pilates yaptim)"
_EXERCISE = re.compile(r"^\s*(?:" + _NUM + r"\s*(dakika|dk|saat)\s+" + _SPORT + r"|" + _SPORT + r"\s+" + _NUM + r"\s*(dakika|dk|saat))\s*$")
_KIND = {"yurudum": "yürüyüş", "kostum": "koşu", "yuzdum": "yüzme", "spor": "spor", "yoga": "yoga", "antrenman": "antrenman",
         "egzersiz": "egzersiz", "bisiklet": "bisiklet", "pilates": "pilates"}
_STEPS = re.compile(r"^\s*(\d{3,6})\s*adim\s+(?:attim|yurudum)\s*$")
_WEIGHT = re.compile(r"^\s*(?:kilom|kilo)\s+(\d{2,3}(?:[.,]\d)?)\s*$|^\s*(\d{2,3}(?:[.,]\d)?)\s*kilo(?:yum|ya)?\s+(?:oldum|geldim)\s*$")
_MOOD = re.compile(r"^\s*(?:bugun\s+)?(?:modum|ruh halim|moralim)\s+([1-5])(?:\s*/\s*5)?\s*$")
_SUMMARY = re.compile(r"\b(?:saglik ozetim|saglik raporum|haftalik saglik raporu|aliskanliklarim|aliskanlik ozeti|su durumum|uyku durumum)\b"
                      r"|\b(?:bugun|bu hafta|dun)\b.*\b(?:kac bardak su|ne kadar su|kac saat uyudum|ne kadar uyudum|kac adim|ne kadar spor|ne kadar yurudum|kac dakika spor)\b"
                      r"|\bkac bardak su ictim\b|\bne kadar spor yaptim\b")
_UNDO = re.compile(r"\bson (?:aliskanlik|saglik|su|uyku|spor) kaydini sil\b")


def _n(token: str | None) -> float | None:
    if token is None:
        return None
    token = token.strip()
    if token in _WORDS:
        return float(_WORDS[token])
    try:
        return float(token.replace(",", "."))
    except ValueError:
        return None


def parse_log(text: str) -> tuple[str, float, str] | None:
    """Return (habit, amount, note) for a logging sentence, else None."""
    f = fold_turkish(text).strip()
    if len(f) > 70:
        return None
    f = re.sub(r"^(?:dun gece|dun|bugun|bu sabah|bu aksam)\s+", "", f)
    m = _WATER.match(f)
    if m:
        qty = _n(m.group(1)) if m.group(1) else 1.0
        unit = m.group(2) or "bardak"
        glasses = {"bardak": 1.0, "sise": 2.0, "litre": 4.0, "lt": 4.0, "ml": 1 / 250}[unit] * (qty if qty is not None else 1.0)
        return ("water", round(glasses, 2), unit) if 0 < glasses <= 40 else None
    m = _SLEEP.match(f)
    if m:
        hours = _n(m.group(1) or m.group(2))
        if hours is not None and "buçuk" in f.replace("bucuk", "buçuk"):
            hours += 0.5
        return ("sleep", hours, "") if hours is not None and 0 < hours <= 24 else None
    m = _EXERCISE.match(f)
    if m:
        qty, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        minutes = (_n(qty) or 0) * (60 if unit == "saat" else 1)
        kind = _KIND[re.search(_SPORT, f).group(0).split()[0]]
        return ("exercise", minutes, kind) if 0 < minutes <= 600 else None
    m = _STEPS.match(f)
    if m:
        return ("steps", float(m.group(1)), "")
    m = _WEIGHT.match(f)
    if m:
        kg = _n(m.group(1) or m.group(2))
        return ("weight", kg, "") if kg and 25 <= kg <= 300 else None
    m = _MOOD.match(f)
    if m:
        return ("mood", float(m.group(1)), "")
    return None


def wants_habits(text: str) -> bool:
    f = fold_turkish(text)
    return parse_log(text) is not None or (len(f) <= 100 and bool(_SUMMARY.search(f) or _UNDO.search(f)))


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}".replace(".", ",")


def _bar(value: float, target: float) -> str:
    pct = min(100, round(100 * value / target))
    return f"{'█' * (pct // 10)}{'░' * (10 - pct // 10)} %{pct}"


LABEL = {"water": ("💧 Su", "bardak"), "sleep": ("😴 Uyku", "saat"), "exercise": ("🏃 Spor", "dk"),
         "steps": ("👟 Adım", "adım"), "weight": ("⚖ Kilo", "kg"), "mood": ("🙂 Ruh hali", "/5")}


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_habits(text):
        return None
    today = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).date()
    f = fold_turkish(text)
    parsed = parse_log(text)
    if parsed:
        habit, amount, note = parsed
        day = today - timedelta(days=1) if re.search(r"\bdun\b", f) else today
        await pool.execute("INSERT INTO owner_habits(user_id,habit,amount,note,day) VALUES($1,$2,$3,$4,$5)", user_id, habit, amount, note, day)
        name, unit = LABEL[habit]
        if habit in TARGETS:
            total = float(await pool.fetchval("SELECT COALESCE(SUM(amount),0) FROM owner_habits WHERE user_id=$1 AND habit=$2 AND day=$3", user_id, habit, day) or amount)
            tip = ""
            if habit == "water" and total >= TARGETS["water"]:
                tip = " Hedefe ulaştın, harika! 🎉"
            elif habit == "sleep" and amount < 6:
                tip = " Biraz az uyumuşsun; bugün erken yatmayı dene."
            return f"{name} kaydedildi: +{_num(amount)} {unit}. Bugün toplam {_num(total)}/{_num(TARGETS[habit])} {unit}  {_bar(total, TARGETS[habit])}.{tip}"
        if habit == "weight":
            prev = await pool.fetchval("SELECT amount FROM owner_habits WHERE user_id=$1 AND habit='weight' AND id<>(SELECT MAX(id) FROM owner_habits WHERE user_id=$1 AND habit='weight') "
                                       "ORDER BY day DESC, id DESC LIMIT 1", user_id)
            diff = f" (öncekine göre {'+' if amount - prev >= 0 else ''}{_num(round(amount - prev, 1))} kg)" if prev else ""
            return f"{name} kaydedildi: {_num(amount)} kg{diff}."
        what = f" ({note})" if note else ""
        return f"{name} kaydedildi{what}: {_num(amount)}{unit if unit == '/5' else ' ' + unit}." + ("" if habit != "mood" else " Not: sağlıkla ilgili tavsiye vermiyorum, sadece kayıt tutuyorum.")
    if _UNDO.search(f):
        row = await pool.fetchrow("DELETE FROM owner_habits WHERE id=(SELECT id FROM owner_habits WHERE user_id=$1 ORDER BY id DESC LIMIT 1) AND user_id=$1 RETURNING habit,amount", user_id)
        return f"Son kaydı sildim: {LABEL[row['habit']][0]} {_num(row['amount'])}" if row else "Silinecek kayıt yok."
    # summary
    if "bu hafta" in f or "haftalik" in f:
        start, label = today - timedelta(days=today.weekday()), "Bu hafta"
    elif re.search(r"\bdun\b", f):
        start, label = today - timedelta(days=1), "Dün"
    else:
        start, label = today, "Bugün"
    end = today - timedelta(days=1) if label == "Dün" else today
    rows = await pool.fetch("SELECT habit, SUM(amount) AS total, AVG(amount) AS avg, COUNT(DISTINCT day) AS days FROM owner_habits "
                            "WHERE user_id=$1 AND day BETWEEN $2 AND $3 GROUP BY habit", user_id, start, end)
    if not rows:
        return f"{label} için kayıt yok. Örn. “2 bardak su içtim”, “7 saat uyudum”, “30 dakika yürüdüm”."
    by = {r["habit"]: r for r in rows}
    lines = []
    for habit in ("water", "sleep", "exercise", "steps", "weight", "mood"):
        r = by.get(habit)
        if not r:
            continue
        name, unit = LABEL[habit]
        total, avg, days = float(r["total"]), float(r["avg"]), int(r["days"])
        weekly = label == "Bu hafta"
        if habit in ("weight", "mood", "sleep"):
            lines.append(f"{name}: ortalama {_num(round(avg, 1))} {unit}" + (f" ({days} gün)" if weekly else ""))
        else:
            tgt = TARGETS[habit] * (days if weekly else 1)
            lines.append(f"{name}: {_num(total)} {unit}" + (f"  {_bar(total, tgt)}" if habit in TARGETS else "") + (f" ({days} gün)" if weekly else ""))
    return f"{label} özeti:\n" + "\n".join("• " + l for l in lines)

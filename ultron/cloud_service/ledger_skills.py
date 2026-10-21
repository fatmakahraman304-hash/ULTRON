"""Personal ledgers from chat: contacts, debts, goals, time tracking and fuel log.

Contacts   "rehbere ekle: Ahmet 0532 123 45 67", "Ahmet'in numarası ne", "rehberim", "Ahmet'i rehberden sil"
Debts      "Ahmet'e 200 lira borç verdim", "Ayşe'den 150 lira borç aldım", "borçlarım", "Ahmet borcunu ödedi"
Goals      "hedef ekle: kitap oku = 12", "hedef ilerlet: kitap oku 2", "hedeflerim", "hedef sil: kitap oku"
Time       "kronometre başlat: ders", "kronometre durdur", "kronometre durumu", "bugün ne kadar çalıştım"
Fuel       "yakıt aldım 40 litre 1800 tl 45000 km", "yakıt tüketimim"
Everything is owner-scoped. Deleting needs the explicit delete words; secrets are not involved.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import fold_with_map, HOME_TZ
else:
    from text_normalization import fold_turkish
    from reminders import fold_with_map, HOME_TZ

_AMT = r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"
_NAME = r"([^\W\d_][\w ]{0,38}?)"


def _num(raw: str) -> float:
    raw = raw.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", raw):
        return float(raw.replace(".", "").replace(",", "."))
    return float(raw.replace(",", "."))


def _money(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (s[:-3] if s.endswith(",00") else s) + " ₺"


def _n(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s[:-3] if s.endswith(",00") else s.rstrip("0") if "," in s and s.endswith("0") else s


def _span(text: str, idx: list[int], span: tuple[int, int]) -> str:
    return re.sub(r"\s+", " ", text[idx[span[0]]: idx[span[1] - 1] + 1]).strip(" '’")[:60]


def _cap(name: str) -> str:
    """Capitalise each word the Turkish way (i → İ, ı → I)."""
    return " ".join(("İ" if w[:1] == "i" else w[:1].upper()) + w[1:] for w in name.split())


def _key(name: str) -> str:
    return fold_turkish(name).strip()[:60]


# contacts
_C_ADD = re.compile(rf"^(?:rehbere|rehberime)\s+(?:ekle|kaydet)\s*[:\-]\s*{_NAME}\s+(\+?[\d ()\-]{{7,20}}?)(?:\s+([^\d].{{0,99}}))?\s*$")
_C_SET = re.compile(rf"^{_NAME}'?(?:in|nin|un|nun)\s+(?:numarasi|telefonu|telefon numarasi)\s+(\+?[\d ()\-]{{7,20}})\s*$")
_C_GET = re.compile(rf"^{_NAME}'?(?:in|nin|un|nun)\s+(?:numarasi|telefonu|telefon numarasi)\s+(?:ne|nedir|kac)\s*\??$")
_C_LIST = re.compile(r"^(?:rehberim|rehber|kisilerim)(?:\s+(?:goster|listele))?\s*\??$")
_C_DEL = re.compile(rf"^{_NAME}'?(?:i|yi|u|yu)\s+rehberden\s+(?:sil|cikar|kaldir)\s*$")
# debts
_D_LENT = re.compile(rf"^{_NAME}'?(?:e|a|ye|ya)\s+{_AMT}\s*(?:tl|lira)\s+borc\s+verdim\s*$")
_D_BORROW = re.compile(rf"^{_NAME}'?(?:den|dan|ten|tan)\s+{_AMT}\s*(?:tl|lira)\s+borc\s+aldim\s*$")
_D_LIST = re.compile(r"^(?:borclarim|alacaklarim|borc\s+durumum|borc\s+defterim)\s*\??$")
_D_PAID = re.compile(rf"^{_NAME}\s+borcunu\s+odedi\s*$")
_D_PAID_ME = re.compile(rf"^{_NAME}'?(?:e|a|ye|ya)\s+borcumu\s+odedim\s*$")
# goals
_G_ADD = re.compile(rf"^hedef\s+ekle\s*[:\-]\s*{_NAME}\s*=\s*{_AMT}\s*$")
_G_PROG = re.compile(rf"^hedef\s+ilerlet\s*[:\-]\s*{_NAME}\s+{_AMT}\s*$")
_G_LIST = re.compile(r"^hedeflerim\s*\??$")
_G_DEL = re.compile(rf"^hedef\s+(?:sil|kaldir)\s*[:\-]\s*{_NAME}\s*$")
# time log
_T_START = re.compile(rf"^kronometre\s+baslat(?:\s*[:\-]\s*{_NAME})?\s*$")
_T_STOP = re.compile(r"^kronometre\s+(?:durdur|bitir)\s*$")
_T_STATUS = re.compile(r"^kronometre\s+durumu?\s*\??$")
_T_TODAY = re.compile(r"^(?:bugun|bu hafta)\s+ne\s+kadar\s+(?:calistim|kronometre\s+tuttum)\s*\??$|^zaman\s+kayitlarim\s*\??$")
# fuel
_F_ADD = re.compile(rf"^yakit\s+aldim\s+{_AMT}\s*(?:litre|lt|l)\s+{_AMT}\s*(?:tl|lira)(?:\s+(\d{{1,7}})\s*km)?\s*$")
_F_STATS = re.compile(r"^(?:yakit\s+tuketimim|yakit\s+ortalamam|yakit\s+harcamam)\s*\??$")

_ALL = (_C_ADD, _C_SET, _C_GET, _C_LIST, _C_DEL, _D_LENT, _D_BORROW, _D_LIST, _D_PAID, _D_PAID_ME, _G_ADD, _G_PROG, _G_LIST, _G_DEL,
        _T_START, _T_STOP, _T_STATUS, _T_TODAY, _F_ADD, _F_STATS)


def wants_ledger(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 160 and any(p.match(f) for p in _ALL)


def _phone(raw: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    return digits if re.fullmatch(r"\+?\d{7,15}", digits) else None


def _fmt_td(td: timedelta) -> str:
    minutes = int(td.total_seconds() // 60)
    return f"{minutes // 60} sa {minutes % 60} dk" if minutes >= 60 else f"{minutes} dk"


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_ledger(text):
        return None
    f, idx = fold_with_map(text)
    f = f.strip()
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(HOME_TZ).date()

    # ── contacts
    m = _C_ADD.match(f) or _C_SET.match(f)
    if m:
        name = _span(text, idx, m.span(1))
        phone = _phone(m.group(2))
        note = _span(text, idx, m.span(3)) if m.re is _C_ADD and m.group(3) else ""
        if not name or not phone:
            return "Telefon numarası geçerli görünmüyor (7–15 rakam). Örn. “rehbere ekle: Ahmet 0532 123 45 67”."
        name = _cap(name)
        await pool.execute("INSERT INTO owner_contacts(user_id,name_key,name,phone,note) VALUES($1,$2,$3,$4,$5) "
                           "ON CONFLICT(user_id,name_key) DO UPDATE SET phone=EXCLUDED.phone,note=EXCLUDED.note,name=EXCLUDED.name,updated_at=NOW()",
                           user_id, _key(name), name, phone, note)
        return f"Rehbere kaydettim: {name} — {phone}" + (f" ({note})" if note else "")
    m = _C_GET.match(f)
    if m:
        name = _span(text, idx, m.span(1))
        row = await pool.fetchrow("SELECT name,phone,note FROM owner_contacts WHERE user_id=$1 AND name_key=$2", user_id, _key(name))
        return f"{row['name']}: {row['phone']}" + (f" ({row['note']})" if row["note"] else "") if row else f"Rehberinde “{name}” adında biri yok."
    if _C_LIST.match(f):
        rows = await pool.fetch("SELECT name,phone FROM owner_contacts WHERE user_id=$1 ORDER BY name LIMIT 30", user_id)
        return "Rehberin:\n" + "\n".join(f"• {r['name']}: {r['phone']}" for r in rows) if rows else "Rehberin boş. Örn. “rehbere ekle: Ahmet 0532 123 45 67”."
    m = _C_DEL.match(f)
    if m:
        name = _span(text, idx, m.span(1))
        n = await pool.fetchval("WITH d AS (DELETE FROM owner_contacts WHERE user_id=$1 AND name_key=$2 RETURNING 1) SELECT COUNT(*) FROM d", user_id, _key(name))
        return f"{name} rehberden silindi." if n else f"Rehberinde “{name}” adında biri yok."

    # ── debts
    for rx, direction in ((_D_LENT, "lent"), (_D_BORROW, "borrowed")):
        m = rx.match(f)
        if m:
            person, amount = _span(text, idx, m.span(1)), _num(m.group(2))
            if not 0 < amount < 1e8:
                return "Tutar geçerli görünmüyor."
            person = _cap(person)
            await pool.execute("INSERT INTO owner_debts(user_id,person,amount,direction) VALUES($1,$2,$3,$4)", user_id, person, round(amount, 2), direction)
            return (f"Kaydettim: {person}'a {_money(amount)} borç verdin." if direction == "lent" else f"Kaydettim: {person}'dan {_money(amount)} borç aldın.") + " Ödenince “%s borcunu ödedi” de." % person
    if _D_LIST.match(f):
        rows = await pool.fetch("SELECT person,direction,SUM(amount) AS total FROM owner_debts WHERE user_id=$1 AND settled_at IS NULL GROUP BY person,direction ORDER BY person", user_id)
        if not rows:
            return "Açık borç/alacak kaydın yok."
        lent = sum(float(r["total"]) for r in rows if r["direction"] == "lent")
        borrowed = sum(float(r["total"]) for r in rows if r["direction"] == "borrowed")
        lines = [f"• {r['person']}: {'alacağın' if r['direction'] == 'lent' else 'borcun'} {_money(float(r['total']))}" for r in rows]
        return "Borç defteri:\n" + "\n".join(lines) + f"\nToplam alacağın {_money(lent)}, borcun {_money(borrowed)}; net {_money(lent - borrowed)}."
    for rx, direction, word in ((_D_PAID, "lent", "ödedi"), (_D_PAID_ME, "borrowed", "ödedin")):
        m = rx.match(f)
        if m:
            person = _span(text, idx, m.span(1))
            rows = await pool.fetch("SELECT id,person FROM owner_debts WHERE user_id=$1 AND settled_at IS NULL AND direction=$2", user_id, direction)
            hits = [r for r in rows if _key(r["person"]) == _key(person)]
            if not hits:
                return f"{person} için açık bir {'alacak' if direction == 'lent' else 'borç'} kaydı bulamadım."
            await pool.execute("UPDATE owner_debts SET settled_at=NOW() WHERE user_id=$1 AND id=ANY($2::bigint[])", user_id, [r["id"] for r in hits])
            return f"{hits[0]['person']} için {len(hits)} kaydı kapattım ({word})."

    # ── goals
    m = _G_ADD.match(f)
    if m:
        title, target = _span(text, idx, m.span(1)), _num(m.group(2))
        if not title or not 0 < target < 1e8:
            return None
        await pool.execute("INSERT INTO owner_goals(user_id,title,target) VALUES($1,$2,$3) ON CONFLICT(user_id,title) DO UPDATE SET target=EXCLUDED.target", user_id, title, round(target, 2))
        return f"Hedef eklendi: {title} — {_n(target)}. İlerletmek için “hedef ilerlet: {title} 1”."
    m = _G_PROG.match(f)
    if m:
        title, step = _span(text, idx, m.span(1)), _num(m.group(2))
        rows = await pool.fetch("SELECT title,target,progress FROM owner_goals WHERE user_id=$1", user_id)
        row = next((r for r in rows if _key(r["title"]) == _key(title)), None)
        if not row:
            return f"“{title}” adında bir hedefin yok. “hedeflerim” ile bak."
        new = float(row["progress"]) + step
        await pool.execute("UPDATE owner_goals SET progress=GREATEST(0,$3) WHERE user_id=$1 AND title=$2", user_id, row["title"], round(new, 2))
        pct = min(100, round(max(new, 0) / float(row["target"]) * 100))
        done = " 🎉 Hedefe ulaştın!" if new >= float(row["target"]) else ""
        return f"{row['title']}: {_n(max(new, 0))}/{_n(float(row['target']))} (%{pct}) {'█' * (pct // 10)}{'░' * (10 - pct // 10)}{done}"
    if _G_LIST.match(f):
        rows = await pool.fetch("SELECT title,target,progress FROM owner_goals WHERE user_id=$1 ORDER BY title", user_id)
        if not rows:
            return "Hedefin yok. Örn. “hedef ekle: kitap oku = 12”."
        return "Hedeflerin:\n" + "\n".join(f"• {r['title']}: {_n(float(r['progress']))}/{_n(float(r['target']))} (%{min(100, round(float(r['progress']) / float(r['target']) * 100))})" for r in rows)
    m = _G_DEL.match(f)
    if m:
        title = _span(text, idx, m.span(1))
        rows = await pool.fetch("SELECT title FROM owner_goals WHERE user_id=$1", user_id)
        row = next((r for r in rows if _key(r["title"]) == _key(title)), None)
        if not row:
            return f"“{title}” adında bir hedefin yok."
        await pool.execute("DELETE FROM owner_goals WHERE user_id=$1 AND title=$2", user_id, row["title"])
        return f"“{row['title']}” hedefini sildim."

    # ── time log
    m = _T_START.match(f)
    if m:
        running = await pool.fetchrow("SELECT label,started_at FROM owner_time_log WHERE user_id=$1 AND ended_at IS NULL ORDER BY id DESC LIMIT 1", user_id)
        if running:
            return f"Zaten çalışan bir kronometre var ({running['label'] or 'adsız'}, {_fmt_td(now - running['started_at'])}). Önce “kronometre durdur” de."
        label = _span(text, idx, m.span(1)) if m.group(1) else ""
        await pool.execute("INSERT INTO owner_time_log(user_id,label,started_at) VALUES($1,$2,$3)", user_id, label, now)
        return f"⏱ Kronometre başladı{(': ' + label) if label else ''}. Bitirince “kronometre durdur” de."
    if _T_STOP.match(f):
        row = await pool.fetchrow("SELECT id,label,started_at FROM owner_time_log WHERE user_id=$1 AND ended_at IS NULL ORDER BY id DESC LIMIT 1", user_id)
        if not row:
            return "Çalışan bir kronometre yok."
        await pool.execute("UPDATE owner_time_log SET ended_at=$2 WHERE id=$1 AND user_id=$3", row["id"], now, user_id)
        return f"⏱ Durdu{(': ' + row['label']) if row['label'] else ''} — süre {_fmt_td(now - row['started_at'])}."
    if _T_STATUS.match(f):
        row = await pool.fetchrow("SELECT label,started_at FROM owner_time_log WHERE user_id=$1 AND ended_at IS NULL ORDER BY id DESC LIMIT 1", user_id)
        return f"⏱ Çalışıyor{(': ' + row['label']) if row['label'] else ''} — {_fmt_td(now - row['started_at'])}." if row else "Çalışan bir kronometre yok."
    if _T_TODAY.match(f):
        weekly = "bu hafta" in f
        start = datetime.combine(today - timedelta(days=today.weekday()) if weekly else today, datetime.min.time(), tzinfo=HOME_TZ)
        rows = await pool.fetch("SELECT label,started_at,ended_at FROM owner_time_log WHERE user_id=$1 AND started_at>=$2 ORDER BY started_at", user_id, start)
        if not rows:
            return f"{'Bu hafta' if weekly else 'Bugün'} için zaman kaydı yok."
        totals: dict[str, timedelta] = {}
        for r in rows:
            end = r["ended_at"] or now
            totals[r["label"] or "adsız"] = totals.get(r["label"] or "adsız", timedelta()) + (end - r["started_at"])
        total = sum(totals.values(), timedelta())
        return f"{'Bu hafta' if weekly else 'Bugün'} toplam {_fmt_td(total)}:\n" + "\n".join(f"• {k}: {_fmt_td(v)}" for k, v in sorted(totals.items(), key=lambda x: -x[1]))

    # ── fuel
    m = _F_ADD.match(f)
    if m:
        liters, cost = _num(m.group(1)), _num(m.group(2))
        km = int(m.group(3)) if m.group(3) else None
        if not (0 < liters < 5000 and 0 <= cost < 1e7):
            return "Litre ya da tutar geçerli görünmüyor."
        await pool.execute("INSERT INTO owner_fuel(user_id,liters,cost,odometer,filled_on) VALUES($1,$2,$3,$4,$5)", user_id, round(liters, 2), round(cost, 2), km, today)
        return f"⛽ Kaydettim: {_n(liters)} lt, {_money(cost)} ({_money(cost / liters)}/lt)" + (f", {km} km" if km else "") + ". Tüketim için “yakıt tüketimim”."
    if _F_STATS.match(f):
        rows = await pool.fetch("SELECT liters,cost,odometer,filled_on FROM owner_fuel WHERE user_id=$1 ORDER BY filled_on, id", user_id)
        if not rows:
            return "Yakıt kaydın yok. Örn. “yakıt aldım 40 litre 1800 tl 45000 km”."
        month_cost = sum(float(r["cost"]) for r in rows if r["filled_on"] >= today.replace(day=1))
        with_km = [r for r in rows if r["odometer"] is not None]
        line = f"Bu ay yakıt harcaman {_money(month_cost)}."
        if len(with_km) >= 2 and with_km[-1]["odometer"] > with_km[0]["odometer"]:
            dist = with_km[-1]["odometer"] - with_km[0]["odometer"]
            used = sum(float(r["liters"]) for r in with_km[1:])      # fuel bought after the first reading covers the distance
            line += f" Ortalama tüketim ≈ {_n(used / dist * 100)} lt/100 km ({dist} km, depoyu her seferinde doldurduğun varsayımıyla)."
        return line
    return None

"""Plans from chat: "yarın 15:00 toplantı ekle", "planlarım", "diş randevusu planını tamamla/sil"."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import parse_reminder, HOME_TZ, _DOW_NAMES
else:
    from text_normalization import fold_turkish
    from reminders import parse_reminder, HOME_TZ, _DOW_NAMES

_ADD = re.compile(r"\b(?:plan\w*|takvim\w*|ajanda\w*|program\w*)\b.*\b(?:ekle|olustur|yaz|kaydet|koy|ayarla)\b"
                  r"|\b(?:ekle|olustur|yaz|kaydet|koy)\b.*\b(?:plan\w*|takvim\w*|ajanda\w*)\b")
_LIST = re.compile(r"\bplanlarim(?:i)?(?: neler| ne| goster| listele| var)?\b|\byaklasan planlar\w*\b|\bplanlarimi (?:goster|listele)\b")
_DONE = re.compile(r"\bplan\w*\b.*\b(?:tamamla\w*|bitir\w*|bitti|yaptim)\b|\b(?:tamamla\w*|bitir\w*)\b.*\bplan\w*\b")
_DEL = re.compile(r"\bplan\w*\b.*\b(?:sil|silelim|kaldir|iptal et)\b|\b(?:sil|kaldir)\b.*\bplan\w*\b")
_NOISE = re.compile(r"\b(?:plan\w*|takvim\w*|ajanda\w*|program\w*|ekle|olustur|yaz|kaydet|koy|ayarla|tamamla\w*|bitir\w*|bitti|yaptim|"
                    r"sil\w*|kaldir\w*|iptal|et|lutfen|bana|benim|bir|icin|su|sunu|bunu)\b")


def _title(text: str, consumed: str) -> str:
    return re.sub(r"\s+", " ", consumed).strip(" .:-'’,")


def _needle(text: str) -> str:
    return re.sub(r"\s+", " ", _NOISE.sub(" ", fold_turkish(text))).strip(" .:-'’,")


def _fmt(day, clock) -> str:
    base = f"{day.day}.{day.month:02d}.{day.year} {_DOW_NAMES[day.weekday()]}"
    return base + (f" {clock:%H:%M}" if clock else "")


def _strip_plan_words(message: str) -> str:
    folded = fold_turkish(message)
    out = []
    for word in message.split():
        if _NOISE.fullmatch(fold_turkish(word).strip(".,:;!?'’")):
            continue
        out.append(word)
    return _title(message, " ".join(out))


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or len(text) > 400:
        return None
    folded = fold_turkish(text)
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(HOME_TZ).date()

    if _LIST.search(folded) and not _ADD.search(folded) and not re.search(r"\b(?:bugun|yarin|hafta)\b", folded):
        rows = await pool.fetch(
            "SELECT title,scheduled_date,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE "
            "AND scheduled_date>=$2 ORDER BY scheduled_date, scheduled_time NULLS LAST LIMIT 15", user_id, today)
        if not rows:
            return "Önümüzdeki günler için açık planın yok. “yarın 15:00 toplantı ekle” gibi yazarak ekleyebilirsin."
        return "Yaklaşan planların:\n" + "\n".join(f"• {_fmt(r['scheduled_date'], r['scheduled_time'])} — {str(r['title'])[:80]}" for r in rows)

    if _DEL.search(folded) or _DONE.search(folded):
        deleting = bool(_DEL.search(folded)) and not _DONE.search(folded)
        needle = _needle(text)
        if len(needle) < 2:
            return "Hangi planı kastettiğini anlayamadım; planın adını da yazar mısın?"
        rows = await pool.fetch(
            "SELECT id,title,scheduled_date,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE "
            "ORDER BY scheduled_date, scheduled_time NULLS LAST LIMIT 100", user_id)
        hits = [r for r in rows if needle in fold_turkish(r["title"])]
        if not hits:
            return f"“{needle[:60]}” ile eşleşen açık bir plan bulamadım."
        if len(hits) > 1:
            return (f"“{needle[:50]}” ile {len(hits)} plan eşleşiyor, hiçbirine dokunmadım. Daha belirgin yazar mısın?\n"
                    + "\n".join(f"• {_fmt(r['scheduled_date'], r['scheduled_time'])} — {str(r['title'])[:70]}" for r in hits[:5]))
        hit = hits[0]
        if deleting:
            await pool.execute("DELETE FROM owner_plans WHERE id=$1 AND user_id=$2", hit["id"], user_id)
            return f"Planı sildim: {str(hit['title'])[:80]}"
        await pool.execute("UPDATE owner_plans SET is_done=TRUE,updated_at=NOW() WHERE id=$1 AND user_id=$2", hit["id"], user_id)
        return f"Planı tamamlandı olarak işaretledim: {str(hit['title'])[:80]} ✓"

    if _ADD.search(folded):
        parsed = parse_reminder(text, now, require_intent=False)
        if parsed is None or parsed.get("error") == "no_time":
            return "Planı hangi gün ve saate ekleyeyim? Örneğin “yarın 15:00 diş randevusu planına ekle”."
        if parsed.get("error") == "past":
            return "Bu tarih geçmişte kaldı; gelecekte bir gün söyler misin?"
        if "error" in parsed:
            return "Bir yıldan uzak plan ekleyemiyorum."
        title = _strip_plan_words(parsed["text"] if parsed["text"] != "Hatırlatıcı" else "")
        if not title:
            return "Planın adı ne olsun? Örneğin “yarın 15:00 diş randevusu planına ekle”."
        day, clock = parsed["due"].date(), (parsed["due"].timetz().replace(tzinfo=None) if parsed["has_clock"] else None)
        clock = clock.replace(second=0, microsecond=0) if clock else None
        dup = await pool.fetchval(
            "SELECT id FROM owner_plans WHERE user_id=$1 AND title=$2 AND scheduled_date=$3 "
            "AND scheduled_time IS NOT DISTINCT FROM $4 AND is_done=FALSE", user_id, title[:140], day, clock)
        if dup:
            return f"Bu plan zaten ekli: {_fmt(day, clock)} — {title[:80]}"
        await pool.fetchval(
            "INSERT INTO owner_plans(user_id,title,scheduled_date,scheduled_time,note) VALUES($1,$2,$3,$4,'') RETURNING id",
            user_id, title[:140], day, clock)
        return (f"Planına ekledim: {_fmt(day, clock)} — {title[:80]}\n"
                "İstersen “10 dakika önce hatırlat” diyerek ayrıca hatırlatıcı da kurabilirim; "
                "yaklaşan planlar için zaten önceden bildirim gönderiyorum.")
    return None

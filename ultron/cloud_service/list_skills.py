"""Named lists from chat: "alışveriş listesine süt ve ekmek ekle", "alışveriş listem", "sütü listeden çıkar"."""
from __future__ import annotations

import re
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import fold_with_map
else:
    from text_normalization import fold_turkish
    from reminders import fold_with_map

MAX_LISTS, MAX_ITEMS = 20, 100
_LIST_WORD = r"liste(?:si|m|mi|me|ye|den|yi)?"
_ADD_A = re.compile(r"^\s*(?:lutfen\s+)?([a-z][a-z ]{1,30}?)\s+listesine\s+(.+?)\s+(?:ekle|koy|yaz|ekler misin)\s*$")
_ADD_B = re.compile(r"^\s*(?:lutfen\s+)?(.+?)\s+([a-z][a-z ]{1,30}?)\s+listesine\s+(?:ekle|koy|yaz)\s*$")
_REMOVE_A = re.compile(r"^\s*(?:lutfen\s+)?(.+?)\s+([a-z][a-z ]{1,30}?)\s+listesinden\s+(?:cikar|sil|kaldir)\s*$")
_REMOVE_B = re.compile(r"^\s*(?:lutfen\s+)?([a-z][a-z ]{1,30}?)\s+listesinden\s+(.+?)\s+(?:cikar|sil|kaldir)\s*$")
_CLEAR = re.compile(r"^\s*(?:lutfen\s+)?([a-z][a-z ]{1,30}?)\s+listesini\s+(?:temizle|bosalt|sil|sifirla)\s*$")
_SHOW = re.compile(r"^\s*(?:lutfen\s+)?([a-z][a-z ]{1,30}?)\s+(?:listem|listemi|listesini)(?:\s+(?:goster|oku|neler|ne|listele|soyle))?\s*\??\s*$")
_ALL = re.compile(r"^\s*(?:tum\s+)?listelerim(?:i)?(?:\s+goster)?\s*\??\s*$")
_NOT_LISTS = {"tum", "su", "bu", "o", "bana", "benim", "bir", "yeni", "eski", "uzun", "kisa", "ilk", "son"}
_SPLIT = re.compile(r"\s*(?:,|;|\bve\b|\bile\b)\s*")


def _clean_list(name: str) -> str | None:
    name = re.sub(r"\s+", " ", name).strip()
    parts = name.split()
    if not name or len(parts) > 3 or any(p in _NOT_LISTS for p in parts[:1]) and len(parts) == 1:
        return None
    return name[:40]


def _label(original: str, idx: list[int], span: tuple[int, int]) -> str:
    """Display name in the owner's own characters, lower-cased the Turkish way."""
    raw = original[idx[span[0]]: idx[span[1] - 1] + 1].strip()
    return re.sub(r"\s+", " ", raw.replace("I", "ı").replace("İ", "i").lower())[:40]


def _items(original: str, folded_item: str, folded_full: str, index: list[int], span: tuple[int, int]) -> list[str]:
    raw = original[index[span[0]]: index[span[1] - 1] + 1]
    out = []
    for part in _SPLIT.split(raw):
        part = part.strip(" .'’")
        if 1 <= len(part) <= 120:
            out.append(part)
    return out[:10]


def wants_lists(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 160 and bool(_ADD_A.match(f) or _ADD_B.match(f) or _REMOVE_A.match(f) or _REMOVE_B.match(f)
                                   or _CLEAR.match(f) or _SHOW.match(f) or _ALL.match(f))


async def handle(text: str, pool: Any, user_id: str) -> str | None:
    if pool is None or len(text) > 400:
        return None
    f, idx = fold_with_map(text)
    f = f.strip()
    if _ALL.match(f):
        rows = await pool.fetch("SELECT list_name, MAX(list_label) AS label, COUNT(*) AS n FROM owner_list_items WHERE user_id=$1 GROUP BY list_name ORDER BY list_name", user_id)
        if not rows:
            return "Henüz bir listen yok. Örn. “alışveriş listesine süt ekle”."
        return "Listelerin:\n" + "\n".join(f"• {r['label'] or r['list_name']}: {int(r['n'])} öğe" for r in rows)

    for pattern, order in ((_ADD_A, "ln_item"), (_ADD_B, "item_ln")):
        m = pattern.match(f)
        if m:
            name_g, item_g = (1, 2) if order == "ln_item" else (2, 1)
            name = _clean_list(m.group(name_g))
            if name is None:
                return None
            label = _label(text, idx, m.span(name_g))
            items = _items(text, m.group(item_g), f, idx, m.span(item_g))
            if not items:
                return None
            count = int(await pool.fetchval("SELECT COUNT(*) FROM owner_list_items WHERE user_id=$1 AND list_name=$2", user_id, name) or 0)
            lists = int(await pool.fetchval("SELECT COUNT(DISTINCT list_name) FROM owner_list_items WHERE user_id=$1", user_id) or 0)
            if count == 0 and lists >= MAX_LISTS:
                return f"En fazla {MAX_LISTS} liste tutabiliyorum."
            added, dup = [], []
            for it in items:
                if count + len(added) >= MAX_ITEMS:
                    return f"“{label}” listesi dolu (en fazla {MAX_ITEMS} öğe)."
                got = await pool.fetchval(
                    "INSERT INTO owner_list_items(user_id,list_name,item,item_key,list_label) VALUES($1,$2,$3,$4,$5) "
                    "ON CONFLICT(user_id,list_name,item_key) DO NOTHING RETURNING id", user_id, name, it, fold_turkish(it), label)
                (added if got else dup).append(it)
            msg = f"“{label}” listesine eklendi: {', '.join(added)}" if added else ""
            if dup:
                msg += (" " if msg else "") + f"Zaten vardı: {', '.join(dup)}"
            return msg.strip()

    m = _CLEAR.match(f)
    if m:
        name = _clean_list(m.group(1))
        label = _label(text, idx, m.span(1))
        n = await pool.fetchval("WITH d AS (DELETE FROM owner_list_items WHERE user_id=$1 AND list_name=$2 RETURNING 1) SELECT COUNT(*) FROM d", user_id, name)
        return f"“{label}” listesini temizledim ({int(n or 0)} öğe)." if n else f"“{label}” adında dolu bir liste bulamadım."

    for pattern, order in ((_REMOVE_A, "item_ln"), (_REMOVE_B, "ln_item")):
        m = pattern.match(f)
        if m:
            name_g, item_g = (2, 1) if order == "item_ln" else (1, 2)
            name = _clean_list(m.group(name_g))
            label = _label(text, idx, m.span(name_g))
            items = _items(text, m.group(item_g), f, idx, m.span(item_g))
            if name is None or not items:
                return None
            removed = []
            for it in items:
                key = fold_turkish(it)
                rows = await pool.fetch("SELECT id,item FROM owner_list_items WHERE user_id=$1 AND list_name=$2 AND item_key LIKE $3 ORDER BY id LIMIT 3",
                                        user_id, name, key.rstrip("iıuü") + "%")
                if len(rows) == 1:
                    await pool.execute("DELETE FROM owner_list_items WHERE id=$1 AND user_id=$2", rows[0]["id"], user_id)
                    removed.append(rows[0]["item"])
            return f"“{label}” listesinden çıkarıldı: {', '.join(removed)}" if removed else f"“{label}” listesinde böyle bir öğe bulamadım (ya da birden fazla eşleşti)."

    m = _SHOW.match(f)
    if m:
        name = _clean_list(m.group(1))
        if name is None:
            return None
        label = _label(text, idx, m.span(1))
        rows = await pool.fetch("SELECT item FROM owner_list_items WHERE user_id=$1 AND list_name=$2 ORDER BY id LIMIT 100", user_id, name)
        if not rows:
            return None   # "yarın listem" etc. may be ordinary chat; only answer for lists that exist
        return f"{label[:1].upper().replace('I', 'İ') if label[:1] != 'i' else 'İ'}{label[1:]} listen ({len(rows)}):\n" + "\n".join(f"• {r['item']}" for r in rows)
    return None

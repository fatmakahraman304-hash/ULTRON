"""Self-improvement backlog: what GÖLGE could not do, and the owner-approved path to build it.

* The owner can add a gap ("eksik: …", "bunu öğren: …"), list them ("eksiklerim"), dismiss one
  ("eksik 2'yi vazgeç") or ask for one to be built ("eksik 2'yi geliştir").
* When the model itself says it cannot do something, the owner's request is recorded as an `auto` gap and
  a one-line hint tells how to turn it into a development request.
* Building = a stored development request (the existing ChatGPT/Codex hand-off) and, if the paired laptop is
  online, a laptop task that only asks the laptop agent to PROPOSE a patch. Nothing here edits code, merges,
  deploys or disables an approval gate: the laptop's own approval → backup → tests → rollback pipeline and the
  GitHub PR review stay in charge. Voice may list and add gaps, never start a build.
"""
from __future__ import annotations

import json
import re
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .memory_safety import contains_common_secret
else:
    from text_normalization import fold_turkish
    from memory_safety import contains_common_secret

MAX_OPEN = 40
_ADD = re.compile(r"^\s*(?:eksik|eksigim|yeni yetenek iste|bunu ogren|ozellik iste)\s*[:\-–]\s*(.{4,300})$", re.S)
_LIST = re.compile(r"^\s*(?:eksiklerim|eksiklerin|gelistirme listem|gelistirme listesi|yapamadiklarim|yapamadiklarin|neleri yapamiyorsun)\s*\??\s*$")
_BUILD = re.compile(r"^\s*(?:eksik|gelistirme)\s*#?(\d{1,6})\s*(?:'?(?:yi|i|u|ü|yı))?\s+(?:gelistir|yap|ekle|olustur)\s*$|^\s*#?(\d{1,6})\.?\s*eksig\w*\s+(?:gelistir|yap|ekle)\s*$")
_DISMISS = re.compile(r"^\s*(?:eksik|gelistirme)\s*#?(\d{1,6})\s*(?:'?(?:yi|i|u|ü|yı))?\s+(?:vazgec|sil|kaldir|iptal)\w*\s*$")
_INABILITY = re.compile(
    r"\b(?:yapamiyorum|yapamam|yapabilecek bir (?:aracim|yetenegim)|su an (?:bunu )?yapamiyorum|bu ozelligim yok|desteklemiyorum|"
    r"bunun icin bir aracim yok|erisimim yok|erisemiyorum|henuz (?:bunu )?yapamiyorum|bu konuda yardimci olamiyorum|"
    r"i can't do|i cannot do|i don't have the ability|i am unable to)\b")
_SKIP_REQUEST = re.compile(r"\b(?:nedir|nasil|neden|niye|kimdir|ne demek|hikaye|siir|sohbet)\b")


def wants_gaps(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 330 and bool(_ADD.match(f) or _LIST.match(f) or _BUILD.match(f) or _DISMISS.match(f))


def looks_like_inability(reply: str) -> bool:
    return bool(_INABILITY.search(fold_turkish(str(reply or "")[:1500])))


def _clean(text: str) -> str:
    return " ".join(str(text).split())[:300]


async def record_gap(pool: Any, user_id: str, request: str, source: str = "owner") -> tuple[int | None, bool]:
    """Returns (id, created). Secrets are never stored; the same open request is not duplicated."""
    request = _clean(request)
    if len(request) < 4 or contains_common_secret(request):
        return None, False
    rows = await pool.fetch("SELECT id,request FROM capability_gaps WHERE user_id=$1 AND status='open' ORDER BY id DESC LIMIT $2", user_id, MAX_OPEN + 1)
    folded = fold_turkish(request)
    for r in rows:
        if fold_turkish(r["request"]) == folded:
            return int(r["id"]), False
    if len(rows) >= MAX_OPEN:
        return None, False
    gid = await pool.fetchval("INSERT INTO capability_gaps(user_id,request,source) VALUES($1,$2,$3) RETURNING id", user_id, request, source)
    return (int(gid), True) if gid is not None else (None, False)


async def auto_gap_hint(pool: Any, user_id: str, user_text: str, reply: str) -> str:
    """Appended to a model answer that admits it cannot do the request; empty otherwise."""
    try:
        text = _clean(user_text)
        if not looks_like_inability(reply) or len(text) < 8 or _SKIP_REQUEST.search(fold_turkish(text)):
            return ""
        gid, created = await record_gap(pool, user_id, text, "auto")
        if gid is None or not created:
            return ""
        return (f"\n\n🛠 Bunu henüz yapamıyorum; geliştirme listeme ekledim (eksik {gid}). Kendimi geliştirmemi istersen "
                f"“eksik {gid}'i geliştir” de. Kod değişiklikleri her zaman senin onayından ve testlerden geçer.")
    except Exception:
        return ""


def build_prompt(request: str, gid: int) -> str:
    return (f"GÖLGE şu özelliği yapamadı; ekle (eksik #{gid}): {request}\n"
            "Kurallar: AGENTS.md'ye uy; küçük, testli bir değişiklik yap; Approval Gate, denetim kaydı, izinler ve sandbox'ı asla kapatma; "
            "sınırsız shell/dosya sistemi/web otomasyonu ekleme; PR aç, birleştirme ve deploy yapma; test sonuçlarını dürüstçe raporla.")


async def handle(text: str, pool: Any, user_id: str, device_id: str = "", can_build: bool = True) -> str | None:
    if pool is None or not wants_gaps(text):
        return None
    f = fold_turkish(text)
    m = _ADD.match(f)
    if m:
        original = text.split(":", 1)[-1] if ":" in text else text.split("-", 1)[-1]
        gid, created = await record_gap(pool, user_id, original, "owner")
        if gid is None:
            return "Bunu listeye ekleyemedim (çok kısa, gizli bilgi içeriyor ya da liste dolu)."
        return (f"Listeme ekledim (eksik {gid}). Geliştirmemi istediğinde “eksik {gid}'i geliştir” de." if created
                else f"Bu zaten listemde (eksik {gid}).")
    if _LIST.match(f):
        rows = await pool.fetch("SELECT id,request,source,status FROM capability_gaps WHERE user_id=$1 AND status IN ('open','requested') ORDER BY id DESC LIMIT 15", user_id)
        if not rows:
            return "Geliştirme listem boş. Yapamadığım bir şey olursa kendiliğinden eklerim; sen de “eksik: …” diyerek ekleyebilirsin."
        lines = [f"• {r['id']} — {r['request'][:100]}" + (" (istendi)" if r["status"] == "requested" else "") + (" 🤖" if r["source"] == "auto" else "") for r in rows]
        return "Yapamadıklarım / eksiklerim:\n" + "\n".join(lines) + "\nGeliştirmek için “eksik N'i geliştir”, vazgeçmek için “eksik N'i vazgeç” de."
    m = _DISMISS.match(f)
    if m:
        n = await pool.fetchval("WITH d AS (UPDATE capability_gaps SET status='dismissed' WHERE id=$1 AND user_id=$2 AND status IN ('open','requested') RETURNING 1) SELECT COUNT(*) FROM d",
                                int(m.group(1)), user_id)
        return "Listeden çıkardım." if n else "Bu numarada açık bir eksik bulamadım."
    m = _BUILD.match(f)
    gid = int(m.group(1) or m.group(2))
    if not can_build:
        return "Kod geliştirmeyi sesle başlatmıyorum; yazarak “eksik %d'i geliştir” dersen onay akışını başlatırım." % gid
    row = await pool.fetchrow("SELECT id,request,status FROM capability_gaps WHERE id=$1 AND user_id=$2", gid, user_id)
    if not row or row["status"] == "dismissed":
        return "Bu numarada açık bir eksik bulamadım. “eksiklerim” ile listeye bak."
    if row["status"] == "requested":
        return f"Eksik {gid} için geliştirme isteği zaten oluşturuldu."
    if __package__:
        from .development_updates import insert_development_request
    else:
        from development_updates import insert_development_request
    prompt = build_prompt(row["request"], gid)
    try:
        item = await insert_development_request(pool, user_id=user_id, device_id=device_id, prompt=prompt, target="both")
    except ValueError as exc:
        return "Saatlik geliştirme isteği sınırına ulaşıldı; biraz sonra tekrar dene." if "rate_limit" in str(exc) else "İstek oluşturulamadı."
    await pool.execute("UPDATE capability_gaps SET status='requested',dev_request_id=$1 WHERE id=$2 AND user_id=$3", item["id"], gid, user_id)
    online = bool(await pool.fetchval("SELECT COALESCE(last_seen > NOW() - INTERVAL '15 seconds', FALSE) FROM device_presence WHERE user_id=$1 AND device='desktop'", user_id))
    queued = False
    if online:
        task = ("GÖLGE kodunu geliştir — YALNIZCA TASLAK ÜRET: aşağıdaki isteği karşılayan küçük bir patch taslağı hazırla ve diff'i göster; "
                "kullanıcı 'onaylıyorum' demeden hiçbir dosyaya yazma. " + build_prompt(row["request"], gid))
        await pool.execute("INSERT INTO device_commands(user_id,target,command,payload,source_device) VALUES($1,'desktop','agent_task',$2::jsonb,$3)",
                           user_id, json.dumps({"text": task[:3900], "origin": "gap", "plan": []}, ensure_ascii=False), device_id)
        queued = True
    tail = ("Laptop çevrimiçi: yalnızca patch TASLAĞI hazırlaması için görev verdim; sen onaylamadan dosyalara dokunmaz, testlerden sonra taslak PR açılır, birleştirme ve deploy sende."
            if queued else
            "Laptop çevrimdışı görünüyor; isteği kaydettim. Laptop açıkken “laptop: GÖLGE kodunu geliştir: …” diyerek ya da Geliştirme isteklerinden ChatGPT/Codex metniyle başlatabilirsin.")
    return f"Eksik {gid} için geliştirme isteği oluşturdum. {tail}"

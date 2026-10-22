"""Approval queue: the agent may PROPOSE a change, the owner decides.

An action is just the typed command the owner could have written themselves ("yarın 15:00 diş randevusu planıma ekle").
It is stored as text, shown in "bekleyen işlemler", and executed only by "onayla N" through the normal skill router
restricted to PROPOSABLE writing skills — so a stored action can never exceed what a typed command could do, and
smart home, memory, alerts, deletions and cancellations are not reachable. Approval is typed-only (never by voice).
"""
from __future__ import annotations

import re
from typing import Any, Awaitable, Callable

if __package__:
    from .text_normalization import fold_turkish
    from .memory_safety import contains_common_secret
else:
    from text_normalization import fold_turkish
    from memory_safety import contains_common_secret

PROPOSABLE = frozenset({"reminder", "plans", "lists", "expenses", "habits", "journal", "routines", "schedule", "birthdays", "focus", "ledger"})
MAX_PENDING = 10
EXPIRE_HOURS = 24
_DESTRUCTIVE = re.compile(r"\b(?:sil\w*|kaldir\w*|iptal\w*|temizle\w*|geri al\w*|unut\w*|bosalt\w*|kapat\w*|kilitle\w*|ac)\b")
_LIST = re.compile(r"^(?:bekleyen\s+islemler(?:im)?|onay\s+bekleyenler|onay\s+bekleyen\s+islemler)\s*\??$")
_APPROVE = re.compile(r"^onayla\s*(?:#?(\d{1,9}))?\s*$|^(?:hepsini|tumunu)\s+onayla\s*$")
_REJECT = re.compile(r"^reddet\s*(?:#?(\d{1,9}))?\s*$|^(?:hepsini|tumunu)\s+reddet\s*$")

Runner = Callable[[str], Awaitable[dict | None]]


def wants_approvals(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 40 and bool(_LIST.match(f) or _APPROVE.match(f) or _REJECT.match(f))


def acceptable(text: str) -> str | None:
    """Returns a refusal reason, or None if the text may be queued."""
    text = " ".join(str(text or "").split())
    if not 4 <= len(text) <= 220:
        return "length"
    if contains_common_secret(text):
        return "secret"
    if _DESTRUCTIVE.search(fold_turkish(text)):
        return "destructive_or_device_action"
    return None


async def propose(pool: Any, user_id: str, text: str, source: str = "agent") -> tuple[int | None, str]:
    """Queue an action. Returns (id, "") or (None, reason)."""
    text = " ".join(str(text or "").split())
    reason = acceptable(text)
    if reason:
        return None, reason
    await pool.execute("UPDATE pending_actions SET status='expired',decided_at=NOW() WHERE user_id=$1 AND status='pending' AND created_at < NOW() - make_interval(hours => $2)", user_id, EXPIRE_HOURS)
    rows = await pool.fetch("SELECT id,text FROM pending_actions WHERE user_id=$1 AND status='pending'", user_id)
    for r in rows:
        if fold_turkish(r["text"]) == fold_turkish(text):
            return int(r["id"]), ""
    if len(rows) >= MAX_PENDING:
        return None, "too_many_pending"
    pid = await pool.fetchval("INSERT INTO pending_actions(user_id,text,source) VALUES($1,$2,$3) RETURNING id", user_id, text, source)
    return (int(pid), "") if pid is not None else (None, "storage")


async def pending(pool: Any, user_id: str) -> list:
    await pool.execute("UPDATE pending_actions SET status='expired',decided_at=NOW() WHERE user_id=$1 AND status='pending' AND created_at < NOW() - make_interval(hours => $2)", user_id, EXPIRE_HOURS)
    return list(await pool.fetch("SELECT id,text,source,created_at FROM pending_actions WHERE user_id=$1 AND status='pending' ORDER BY id", user_id))


async def handle(text: str, pool: Any, user_id: str, runner: Runner | None = None) -> str | None:
    if pool is None or not wants_approvals(text):
        return None
    f = fold_turkish(text).strip()
    rows = await pending(pool, user_id)
    if _LIST.match(f):
        if not rows:
            return "Onay bekleyen işlem yok."
        return ("Onayını bekleyen işlemler:\n" + "\n".join(f"{r['id']}. {r['text']}" + (" 🤖" if r["source"] == "agent" else "") for r in rows)
                + "\n“onayla N” ile uygula, “reddet N” ile vazgeç.")
    m = _REJECT.match(f)
    if m:
        targets = _select(rows, m.group(1), f)
        if isinstance(targets, str):
            return targets
        for r in targets:
            await pool.execute("UPDATE pending_actions SET status='rejected',decided_at=NOW() WHERE id=$1 AND user_id=$2 AND status='pending'", r["id"], user_id)
        return f"{len(targets)} işlem reddedildi; hiçbir şey yapılmadı."
    m = _APPROVE.match(f)
    targets = _select(rows, m.group(1), f)
    if isinstance(targets, str):
        return targets
    if runner is None:
        return "Onay şu an çalıştırılamıyor."
    out = []
    for r in targets:
        claimed = await pool.fetchval("UPDATE pending_actions SET status='approved',decided_at=NOW() WHERE id=$1 AND user_id=$2 AND status='pending' RETURNING id", r["id"], user_id)
        if claimed is None:
            continue                                                   # another device already decided it
        try:
            result = await runner(r["text"])
        except Exception:
            result = None
        if result and result.get("reply"):
            reply = str(result["reply"])[:300]
            await pool.execute("UPDATE pending_actions SET result=$2 WHERE id=$1", r["id"], reply)
            out.append(f"{r['id']}. ✅ {reply}")
        else:
            await pool.execute("UPDATE pending_actions SET status='failed',result='not_runnable' WHERE id=$1", r["id"])
            out.append(f"{r['id']}. ⚠ Bu işlem onay akışıyla yapılamıyor; yazarak kendin söyleyebilirsin: “{r['text'][:80]}”")
    return "\n".join(out) if out else "Bu işlemler zaten karara bağlanmış."


def _select(rows, number: str | None, folded: str):
    if not rows:
        return "Onay bekleyen işlem yok."
    if folded.startswith(("hepsini", "tumunu")):
        return rows
    if number is None:
        if len(rows) == 1:
            return rows
        return "Birden fazla bekleyen işlem var; hangisi? Örn. “onayla %d”. Liste için “bekleyen işlemler”." % rows[0]["id"]
    hit = [r for r in rows if r["id"] == int(number)]
    return hit or "Bu numarada bekleyen bir işlem bulamadım."

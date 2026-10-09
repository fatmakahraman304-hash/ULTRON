"""Read-only personal briefing built exclusively from owner-saved ULTRON memory.

No guessed dates, account access, inferred location, health prediction, or
background monitoring. Source records are returned for owner review.
"""
from __future__ import annotations


def build_briefing(rows, *, plan_rows=(), max_items: int = 8) -> dict:
    """Return transparent memory-backed planning notes, without an LLM or side effects."""
    limit = max(1, min(int(max_items), 12))
    saved = []
    seen = set()
    for row in rows:
        category = str(row["category"] if isinstance(row, dict) else row[0]).strip()[:50]
        key = str(row["key"] if isinstance(row, dict) else row[1]).strip()[:100]
        value = str(row["value"] if isinstance(row, dict) else row[2]).strip()[:300]
        if not key or not value or (category.casefold(), key.casefold()) in seen:
            continue
        seen.add((category.casefold(), key.casefold()))
        saved.append({"category": category, "key": key, "value": value,
                      "source": "owner_saved_memory"})
        if len(saved) >= limit:
            break
    # Explicit manual entries are separate from an external calendar provider.
    manual_plans = []
    for plan in list(plan_rows)[:8]:
        record = dict(plan)
        if not record.get("title") or record.get("is_done"):
            continue
        day = record.get("scheduled_date")
        clock = record.get("scheduled_time")
        manual_plans.append({
            "id": int(record["id"]),
            "title": str(record["title"])[:140],
            "date": day.isoformat() if hasattr(day, "isoformat") else str(day)[:10],
            "time": clock.strftime("%H:%M") if clock else None,
            "source": "owner_created_plan",
        })
    return {
        "type": "read_only_owner_briefing",
        "plans": manual_plans,
        "items": saved,
        "suggestions": (
            ["Kayıtlı hedeflerini gözden geçirip bugün için bir öncelik seç."]
            if saved else
            ["Bugün için tek bir hedef belirleyip istersen ULTRON hafızasına kendin kaydet."]
        ),
        "calendar_connected": False,
        "email_connected": False,
        "reminders_created": False,
        "actions_executed": False,
        "notice": (
            "Bu özet yalnızca açıkça kaydedilmiş ULTRON hafızasını ve senin oluşturduğun planları gösterir. "
            "Apple/Google Takvim, e-posta veya otomatik bildirim bağlantısı içermez."
        ),
    }

"""Owner-scoped, consent-grounded version history for saved memory corrections.

Current memories remain the only default model context. Previous values are
retrievable only through an explicit owner-scoped history lookup, and deleting
a memory erases its old versions as well.
"""
from __future__ import annotations

from live_voice_policy import safe_manual_memory_value

_CATEGORIES = frozenset({
    "FACT", "PREFERENCE", "PROJECT", "GOAL", "DEVICE", "PROFILE", "IMPORTANT", "NOTE",
})


async def _lock_owner_key(conn, user_id: str, key: str) -> None:
    # Serialize first-write races as well as corrections/deletes; the lock is
    # transaction-scoped and derived from both the authenticated owner and key.
    lock_identity = f"{len(user_id)}:{user_id}{key}"
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1,0))", lock_identity
    )


def validate_memory_record(category: str, key: str, value: str) -> tuple[str, str, str]:
    if not isinstance(category, str) or category.strip().upper() not in _CATEGORIES:
        raise ValueError("unsupported_category")
    if not isinstance(key, str) or not key.strip() or len(key.strip()) > 120 or "\x00" in key:
        raise ValueError("invalid_key")
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 8000 or "\x00" in value:
        raise ValueError("invalid_value")
    normalized_value = value.strip()
    if not safe_manual_memory_value(normalized_value):
        raise ValueError("sensitive_memory_rejected")
    return category.strip().upper(), key.strip(), normalized_value


async def upsert_owner_memory(pool, user_id: str, device_id: str,
                              category: str, key: str, value: str) -> dict:
    """Save a current value and archive only a changed, non-secret predecessor."""
    category, key, value = validate_memory_record(category, key, value)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _lock_owner_key(conn, user_id, key)
            previous = await conn.fetchrow(
                "SELECT category,key,value,version,updated_by_device,created_at,updated_at "
                "FROM memories WHERE user_id=$1 AND key=$2 FOR UPDATE",
                user_id, key,
            )
            if (previous is not None and previous["category"] == category
                    and previous["value"] == value):
                return dict(previous)
            if previous is not None and safe_manual_memory_value(previous["value"]):
                await conn.execute(
                    "INSERT INTO memory_history(user_id,category,key,value,version,"
                    "updated_by_device,valid_from,valid_until) "
                    "VALUES($1,$2,$3,$4,$5,$6,$7,NOW()) "
                    "ON CONFLICT(user_id,key,version) DO NOTHING",
                    user_id, previous["category"], key, previous["value"],
                    previous["version"], previous["updated_by_device"],
                    previous["updated_at"],
                )
            row = await conn.fetchrow(
                "INSERT INTO memories(user_id,category,key,value,version,updated_by_device) "
                "VALUES($1,$2,$3,$4,1,$5) ON CONFLICT(user_id,key) DO UPDATE SET "
                "category=EXCLUDED.category,value=EXCLUDED.value,"
                "version=memories.version+1,updated_by_device=EXCLUDED.updated_by_device,"
                "updated_at=NOW() RETURNING category,key,value,version,"
                "updated_by_device,created_at,updated_at",
                user_id, category, key, value, device_id,
            )
            return dict(row)


async def list_owner_memory_history(pool, user_id: str, key: str,
                                   limit: int = 20) -> list[dict]:
    """History is always filtered by the authenticated owner and exact key."""
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20
    rows = await pool.fetch(
        "SELECT category,key,value,version,updated_by_device,valid_from,valid_until "
        "FROM memory_history WHERE user_id=$1 AND key=$2 "
        "ORDER BY valid_until DESC,version DESC LIMIT $3",
        user_id, str(key)[:120], max(1, min(limit, 50)),
    )
    return [dict(row) for row in rows]


async def delete_owner_memory(pool, user_id: str, key: str) -> bool:
    """A user-requested forgetting operation purges current and superseded values."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _lock_owner_key(conn, user_id, key)
            await conn.execute(
                "DELETE FROM memory_history WHERE user_id=$1 AND key=$2", user_id, key
            )
            result = await conn.execute(
                "DELETE FROM memories WHERE user_id=$1 AND key=$2", user_id, key
            )
    return result.endswith("1")

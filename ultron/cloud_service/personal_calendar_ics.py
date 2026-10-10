"""Read-only iCalendar export for ULTRON owner-created plans.

Never synchronizes external accounts or creates alarms. Notes are deliberately
excluded from downloaded calendar files; timezone interpretation is explicit.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from zoneinfo import ZoneInfo

ALLOWED_TIMEZONES = ("Europe/Istanbul", "Asia/Nicosia", "UTC")


def _escape(value: str) -> str:
    raw = str(value).replace("\r\n", "\n").replace("\r", "\n")
    raw = "".join(ch for ch in raw if ch == "\n" or (ord(ch) >= 32 and ord(ch) != 127))
    return raw.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold_utf8(line: str) -> list[str]:
    """RFC5545: fold text content lines at 75 UTF-8 octets."""
    parts, current, size = [], "", 0
    for ch in line:
        length = len(ch.encode("utf-8"))
        if current and size + length > 75:
            parts.append(current)
            current, size = " ", 1
        current += ch
        size += length
    parts.append(current)
    return parts


def _utc_start(day, clock, zone: ZoneInfo) -> str:
    local = datetime.combine(day, clock)
    first = local.replace(tzinfo=zone, fold=0)
    second = local.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        # Without an owner-selected fold, daylight-saving boundary is ambiguous
        # or a nonexistent clock time; refuse rather than silently shift it.
        raise ValueError("ambiguous_or_nonexistent_local_time")
    utc = first.astimezone(timezone.utc)
    if utc.astimezone(zone).replace(tzinfo=None) != local:
        raise ValueError("nonexistent_local_time")
    return utc.strftime("%Y%m%dT%H%M%SZ")


def export_ics(rows, *, owner_id: str, timezone_name: str, now=None) -> bytes:
    if timezone_name not in ALLOWED_TIMEZONES:
        raise ValueError("unsupported_timezone")
    zone = ZoneInfo(timezone_name)
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ULTRON//Personal Plans//TR",
             "CALSCALE:GREGORIAN"]
    for row in rows:
        p = dict(row)
        if p.get("is_done"):
            continue
        uid = sha256(f"{owner_id}\0{p['id']}".encode("utf-8")).hexdigest()[:32] + "@ultron.local"
        lines.extend(["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}"])
        if p["scheduled_time"] is None:
            lines.append("DTSTART;VALUE=DATE:" + p["scheduled_date"].strftime("%Y%m%d"))
        else:
            lines.append("DTSTART:" + _utc_start(p["scheduled_date"], p["scheduled_time"], zone))
        lines.extend(["SUMMARY:" + _escape(p["title"]), "TRANSP:TRANSPARENT", "END:VEVENT"])
    lines.append("END:VCALENDAR")
    return ("\r\n".join(part for line in lines for part in _fold_utf8(line)) + "\r\n").encode("utf-8")

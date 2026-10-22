"""Read-only calendar subscription via a secret iCal (.ics) address.

Works with Google Calendar ("Gizli iCal biçimindeki adres"), iCloud public
calendars and Outlook "yayımlanmış takvim" links, without OAuth or write
access. The secret URL is never returned to the browser or put in a prompt.
SSRF is prevented by an https-only host allowlist, no redirects and a size cap.
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from aiohttp import web

import http_client

HOME_TZ = ZoneInfo("Europe/Istanbul")
ALLOWED_HOST_SUFFIXES = ("calendar.google.com", "icloud.com", "outlook.live.com", "outlook.office365.com",
                         "outlook.office.com", "office365.com", "fastmail.com", "proton.me")
MAX_BYTES = 2_000_000
MAX_EVENTS = 400
_CACHE: dict[str, tuple[float, str]] = {}


class FeedError(Exception):
    pass


def validate_feed_url(raw: object) -> str:
    url = str(raw or "").strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[9:]
    if not 12 <= len(url) <= 800 or any(c in url for c in "\r\n\x00 "):
        raise FeedError("invalid_url")
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or parts.username or parts.password or parts.port not in (None, 443):
        raise FeedError("https_only")
    if not any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES):
        raise FeedError("host_not_allowed")
    return url


async def fetch_ics(url: str, ttl: int = 600) -> str:
    key = hashlib.sha256(url.encode()).hexdigest()
    cached = _CACHE.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    try:
        status, body, _ = await http_client.fetch(url, headers={"User-Agent": "GOLGE-Calendar/1.0"}, timeout=12, max_bytes=MAX_BYTES)
    except ValueError as exc:
        raise FeedError("feed_too_large" if str(exc) == "too_large" else "feed_unavailable") from exc
    except Exception as exc:
        raise FeedError("feed_unavailable") from exc
    if status != 200:
        raise FeedError("feed_unavailable")
    text = body.decode("utf-8", errors="replace")
    if "BEGIN:VCALENDAR" not in text:
        raise FeedError("not_ical")
    if len(_CACHE) > 20:
        _CACHE.clear()
    _CACHE[key] = (time.monotonic() + ttl, text)
    return text


# ── iCalendar parsing ───────────────────────────────────────────────────────

def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        elif raw:
            lines.append(raw)
    return lines


def _unescape(value: str) -> str:
    return (value.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\")).strip()


def _prop(line: str) -> tuple[str, dict, str]:
    head, _, value = line.partition(":")
    name, *params = head.split(";")
    return name.upper(), {k.upper(): v.strip('"') for k, _, v in (p.partition("=") for p in params)}, value


def _parse_dt(value: str, params: dict) -> tuple[datetime | date, bool]:
    value = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        return date(int(value[:4]), int(value[4:6]), int(value[6:8])), True
    stamp = datetime(int(value[:4]), int(value[4:6]), int(value[6:8]), int(value[9:11]), int(value[11:13]),
                     int(value[13:15] or 0))
    if value.endswith("Z"):
        return stamp.replace(tzinfo=timezone.utc).astimezone(HOME_TZ), False
    try:
        zone = ZoneInfo(params["TZID"]) if params.get("TZID") else HOME_TZ
    except Exception:
        zone = HOME_TZ
    return stamp.replace(tzinfo=zone).astimezone(HOME_TZ), False


_BYDAY = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _occurrences(start, rrule: str, exdates: set, window_start: date, window_end: date, all_day: bool):
    first_date = start if all_day else start.date()
    if not rrule:
        yield start
        return
    rule = dict(part.split("=", 1) for part in rrule.split(";") if "=" in part)
    freq, interval = rule.get("FREQ", ""), max(1, int(rule.get("INTERVAL", "1") or 1))
    count = int(rule["COUNT"]) if rule.get("COUNT", "").isdigit() else None
    until = None
    if rule.get("UNTIL"):
        try:
            u, _ = _parse_dt(rule["UNTIL"], {})
            until = u if isinstance(u, date) and not isinstance(u, datetime) else u.date()
        except Exception:
            until = None
    bydays = [_BYDAY[d[-2:]] for d in rule.get("BYDAY", "").split(",") if d[-2:] in _BYDAY]
    produced, day, guard = 0, first_date, 0
    while day <= window_end and guard < 4000:
        guard += 1
        if until and day > until:
            return
        match = False
        if freq == "DAILY":
            match = (day - first_date).days % interval == 0
        elif freq == "WEEKLY":
            weeks = ((day - first_date).days + first_date.weekday()) // 7
            match = weeks % interval == 0 and day.weekday() in (bydays or [first_date.weekday()])
        elif freq == "MONTHLY":
            months = (day.year - first_date.year) * 12 + day.month - first_date.month
            match = months % interval == 0 and day.day == first_date.day
        elif freq == "YEARLY":
            match = (day.year - first_date.year) % interval == 0 and (day.month, day.day) == (first_date.month, first_date.day)
        else:
            if day == first_date:
                match = True
            elif day > first_date:
                return
        if match and day >= first_date:
            produced += 1
            if count is not None and produced > count:
                return
            if day >= window_start and day not in exdates:
                yield day if all_day else datetime.combine(day, start.timetz()).replace(tzinfo=start.tzinfo)
        day += timedelta(days=1)


def parse_ics(text: str, window_start: date, window_end: date) -> list[dict]:
    events: list[dict] = []
    current: dict | None = None
    for line in _unfold(text):
        name, params, value = _prop(line)
        if name == "BEGIN" and value.upper() == "VEVENT":
            current = {"exdates": set()}
        elif name == "END" and value.upper() == "VEVENT" and current is not None:
            ev, current = current, None
            if "start" not in ev or ev.get("cancelled"):
                continue
            start, all_day = ev["start"]
            end = ev.get("end", (None, all_day))[0]
            duration = (end - start) if (end is not None and isinstance(end, type(start))) else None
            try:
                for occ in _occurrences(start, ev.get("rrule", ""), ev["exdates"], window_start, window_end, all_day):
                    day = occ if all_day else occ.date()
                    last_day = day
                    if duration is not None and all_day and duration.days > 1:
                        last_day = day + timedelta(days=duration.days - 1)
                    if last_day < window_start or day > window_end:
                        continue
                    events.append({"title": ev.get("title") or "(başlıksız)", "all_day": all_day,
                                   "start": occ.isoformat(), "end": (occ + duration).isoformat() if duration else None,
                                   "location": ev.get("location", ""), "_sort": (day, datetime.min.time() if all_day else occ.time())})
            except Exception:
                continue
        elif current is not None:
            try:
                if name == "SUMMARY":
                    current["title"] = _unescape(value)[:140]
                elif name == "LOCATION":
                    current["location"] = _unescape(value)[:100]
                elif name == "DTSTART":
                    current["start"] = _parse_dt(value, params)
                elif name == "DTEND":
                    current["end"] = _parse_dt(value, params)
                elif name == "RRULE":
                    current["rrule"] = value
                elif name == "EXDATE":
                    for part in value.split(","):
                        d, _ = _parse_dt(part, params)
                        current["exdates"].add(d if isinstance(d, date) and not isinstance(d, datetime) else d.date())
                elif name == "STATUS" and value.upper() == "CANCELLED":
                    current["cancelled"] = True
            except Exception:
                current.pop("start", None) if name == "DTSTART" else None
    events.sort(key=lambda e: e["_sort"])
    for e in events:
        e.pop("_sort")
    return events[:MAX_EVENTS]


async def get_feed_url(pool: Any, user_id: str) -> str | None:
    return await pool.fetchval("SELECT url FROM owner_calendar_feeds WHERE user_id=$1", user_id)


async def events_between(pool: Any, user_id: str, start: date, end: date) -> list[dict] | None:
    """None = no calendar connected. Raises FeedError when the feed is unreachable."""
    url = await get_feed_url(pool, user_id)
    if not url:
        return None
    return parse_ics(await fetch_ics(validate_feed_url(url)), start, end)


def format_event(event: dict) -> str:
    place = f" ({event['location']})" if event.get("location") else ""
    if event["all_day"]:
        return f"Tüm gün — {event['title']}{place}"
    return f"{datetime.fromisoformat(event['start']):%H:%M} — {event['title']}{place}"


# ── HTTP ────────────────────────────────────────────────────────────────────

def _web_only(request: web.Request) -> None:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"browser_session_required"}', content_type="application/json")
    if request.method != "GET":
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            raise web.HTTPForbidden(text='{"error":"cross_origin_denied"}', content_type="application/json")


async def feed_status(request: web.Request) -> web.Response:
    _web_only(request)
    url = await get_feed_url(request.app["db"], request["user_id"])
    return web.json_response({"connected": bool(url), "host": urlsplit(url).hostname if url else None})


async def feed_connect(request: web.Request) -> web.Response:
    _web_only(request)
    try:
        url = validate_feed_url((await request.json()).get("url"))
        text = await fetch_ics(url, ttl=1)
        today = datetime.now(HOME_TZ).date()
        sample = parse_ics(text, today, today + timedelta(days=30))
    except (FeedError, ValueError, TypeError, AttributeError) as exc:
        code = exc.args[0] if isinstance(exc, FeedError) and exc.args else "invalid_request"
        return web.json_response({"error": code}, status=400)
    await request.app["db"].execute(
        "INSERT INTO owner_calendar_feeds(user_id,url) VALUES($1,$2) "
        "ON CONFLICT(user_id) DO UPDATE SET url=EXCLUDED.url,updated_at=NOW()", request["user_id"], url)
    return web.json_response({"connected": True, "host": urlsplit(url).hostname, "upcoming_30_days": len(sample)})


async def feed_disconnect(request: web.Request) -> web.Response:
    _web_only(request)
    await request.app["db"].execute("DELETE FROM owner_calendar_feeds WHERE user_id=$1", request["user_id"])
    return web.json_response({"connected": False})


async def feed_events(request: web.Request) -> web.Response:
    _web_only(request)
    try:
        days = max(1, min(int(request.query.get("days", "7")), 31))
    except ValueError:
        days = 7
    today = datetime.now(HOME_TZ).date()
    try:
        events = await events_between(request.app["db"], request["user_id"], today, today + timedelta(days=days - 1))
    except FeedError as exc:
        return web.json_response({"error": exc.args[0] if exc.args else "feed_unavailable"}, status=502)
    return web.json_response({"connected": events is not None, "events": events or []})


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/calendar-feed", feed_status)
    app.router.add_put("/api/calendar-feed", feed_connect)
    app.router.add_delete("/api/calendar-feed", feed_disconnect)
    app.router.add_get("/api/calendar-feed/events", feed_events)

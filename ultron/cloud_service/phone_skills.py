"""Phone-first GÖLGE skills that the laptop had and the cloud can do honestly:
news headlines, flight-search links and YouTube summaries (via Gemini).

No scraping and no invented prices: news comes from the Google News RSS feed,
flights open a prefilled Google Flights search, YouTube is read by Gemini itself.
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from typing import Awaitable, Callable
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree


if __package__:
    from .text_normalization import fold_turkish
    from .reminders import fold_with_map
    from . import http_client
else:
    from text_normalization import fold_turkish
    from reminders import fold_with_map
    import http_client

FetchText = Callable[[str, str, int], Awaitable[str]]
_NEWS_CACHE: dict[str, tuple[float, str]] = {}
_NEWS_HOST = "news.google.com"
_TOPICS = {"teknoloji": "TECHNOLOGY", "bilim": "SCIENCE", "spor": "SPORTS", "ekonomi": "BUSINESS", "finans": "BUSINESS",
           "dunya": "WORLD", "saglik": "HEALTH", "magazin": "ENTERTAINMENT", "eglence": "ENTERTAINMENT", "turkiye": "NATION"}
_TOPIC_TR = {"TECHNOLOGY": "Teknoloji", "SCIENCE": "Bilim", "SPORTS": "Spor", "BUSINESS": "Ekonomi", "WORLD": "Dünya",
             "HEALTH": "Sağlık", "ENTERTAINMENT": "Magazin", "NATION": "Türkiye"}
_NEWS_Q = re.compile(r"\bhaber(?:ler|leri|ler\w*)?\b|\bson dakika\b|\bgundem\b|\bmanset(?:ler)?\b|\bbugun neler oldu\b|\bdunyada neler oluyor\b")
_NEWS_SKIP = re.compile(r"\b(?:neden|niye|nicin|yorumla|analiz|sahte|dogru mu|guvenilir|haber ver bana|haberim yok|haberin var mi|"
                        r"yaz\w*|makale\w*|taslak\w*|metin\w*|ozetle|cevir\w*|uygulama\w*|kod\w*|baslik at\w*)\b")


async def fetch_news_xml(url: str, key: str, ttl: int = 600) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != _NEWS_HOST:
        raise ValueError("host_not_allowed")
    cached = _NEWS_CACHE.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    status, body, _ = await http_client.fetch(url, headers={"User-Agent": "GOLGE-News/1.0"}, timeout=10, max_bytes=1_000_000)
    if status != 200:
        raise ValueError("feed_unavailable")
    text = body.decode("utf-8", errors="replace")
    if len(_NEWS_CACHE) > 20:
        _NEWS_CACHE.clear()
    _NEWS_CACHE[key] = (time.monotonic() + ttl, text)
    return text


def parse_rss(xml_text: str, limit: int = 5) -> list[dict]:
    if "<!DOCTYPE" in xml_text.upper() or "<!ENTITY" in xml_text.upper():
        raise ValueError("unsafe_xml")
    root = ElementTree.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        source = (item.findtext("source") or "").strip()
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3].rstrip()
        items.append({"title": re.sub(r"\s+", " ", title)[:160], "source": source[:40]})
        if len(items) >= limit:
            break
    return items


def news_topic(folded: str) -> str | None:
    for word, topic in _TOPICS.items():
        if re.search(r"\b" + word + r"\w*\b", folded):
            return topic
    return None


_NEWS_CUE = re.compile(r"\b(?:ver|goster|oku|anlat|neler|sirala|son|guncel|bugun|ozet\w*|var mi|ne var|nedir)\b")


def wants_news(text: str) -> bool:
    folded = fold_turkish(text)
    if not _NEWS_Q.search(folded) or _NEWS_SKIP.search(folded) or len(folded) > 80:
        return False
    # a bare topic request ("teknoloji haberleri") or an explicit command cue; long chatty sentences are not requests
    return len(folded.split()) <= 3 or bool(_NEWS_CUE.search(folded))


def _news_url(topic: str | None) -> str:
    base = "https://news.google.com/rss"
    tail = "?hl=tr&gl=TR&ceid=TR:tr"
    return f"{base}/headlines/section/topic/{topic}{tail}" if topic else base + tail


async def headlines(topic: str | None, fetch_text: FetchText | None, limit: int = 5) -> list[dict]:
    fetch = fetch_text or fetch_news_xml
    return parse_rss(await fetch(_news_url(topic), f"news:{topic or 'top'}", 600), limit)


async def answer_news(text: str, fetch_text: FetchText | None = None) -> str | None:
    if not wants_news(text):
        return None
    topic = news_topic(fold_turkish(text))
    try:
        items = await headlines(topic, fetch_text)
    except Exception:
        return "Haber kaynağına şu an ulaşamadım; uydurma başlık vermemek için bir şey söylemiyorum. Biraz sonra yeniden dene."
    if not items:
        return "Şu an listelenecek haber başlığı bulamadım."
    label = _TOPIC_TR.get(topic or "", "Gündem")
    lines = [f"• {i['title']}" + (f" ({i['source']})" if i["source"] else "") for i in items]
    return f"{label} haberleri:\n" + "\n".join(lines) + "\nKaynak: Google Haberler. Ayrıntı için “… hakkında araştır” diyebilirsin."


# ── flights ─────────────────────────────────────────────────────────────────

_FLIGHT_KW = re.compile(r"\b(?:ucus|ucak|ucak bileti|bilet|flight|flights)\b")
_ROUTE = re.compile(r"([a-z]+(?: [a-z]+)?)'?(?:dan|den|tan|ten)\b\s+([a-z]+(?: [a-z]+)?)'?(?:ya|ye|na|ne|a|e)\b")
_MONTHS = ("ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz", "agustos", "eylul", "ekim", "kasim", "aralik")
_DATE_NUM = re.compile(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?\b")
_DATE_NAMED = re.compile(r"\b(\d{1,2}) (" + "|".join(_MONTHS) + r")(?: (\d{4}))?\b")
_FILLER_WORDS = {"icin", "bir", "bak", "bul", "ara", "bana", "lutfen", "en", "ucuz", "ucus", "ucak", "bileti", "bilet", "var", "mi", "yarin", "haftaya", "bugun", "gelecek"}


def _flight_date(folded: str, today: date) -> date | None:
    if "yarin" in folded:
        return today + timedelta(days=1)
    if "haftaya" in folded:
        return today + timedelta(days=7)
    m = _DATE_NAMED.search(folded)
    if m:
        d, mon, y = int(m.group(1)), _MONTHS.index(m.group(2)) + 1, m.group(3)
    else:
        m = _DATE_NUM.search(folded)
        if not m:
            return None
        d, mon, y = int(m.group(1)), int(m.group(2)), m.group(3)
    try:
        year = int(y) if y else today.year
        found = date(year, mon, d)
        if not y and found < today:
            found = date(year + 1, mon, d)
        return found
    except ValueError:
        return None


def wants_flight(text: str) -> bool:
    folded = fold_turkish(text)
    return bool(_FLIGHT_KW.search(folded)) and bool(_ROUTE.search(folded)) and len(folded) <= 160


def answer_flight(text: str, now: datetime | None = None) -> str | None:
    folded, index = fold_with_map(text)
    if not (_FLIGHT_KW.search(folded) and len(folded) <= 160):
        return None
    m = _ROUTE.search(folded)
    if not m:
        return None

    def display(group: int) -> str:
        a, b = m.span(group)
        words = [w for w in text[index[a]: index[b - 1] + 1].split() if fold_turkish(w) not in _FILLER_WORDS]
        return " ".join(w[:1].upper() + w[1:] for w in words)[:40]

    origin, dest = display(1), display(2)
    if not origin or not dest or fold_turkish(origin) == fold_turkish(dest):
        return None
    today = (now or datetime.now()).date()
    when = _flight_date(folded, today)
    query = f"{origin} to {dest} flights" + (f" on {when.isoformat()}" if when else "")
    url = "https://www.google.com/travel/flights?hl=tr&q=" + quote(query)
    day = f"{when.day}.{when.month:02d}.{when.year}" if when else "tarih seçmeden"
    return (f"{origin} → {dest}, {day} için Google Uçuşlar araması hazır:\n{url}\n"
            "Fiyatları ben çekmiyorum (uydurmamak için); bağlantı güncel fiyat ve saatleri açar.")


# ── YouTube summary ─────────────────────────────────────────────────────────

_YT = re.compile(r"https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?[^\s]*?v=|shorts/)|youtu\.be/)([\w-]{11})")
_YT_INTENT = re.compile(r"\b(?:ozetle|ozet|ne anlatiyor|anlat|summar\w+|neyle ilgili|ana fikir|maddele|cevir|degerlendir)\b")


def youtube_request(text: str) -> dict | None:
    m = _YT.search(text or "")
    if not m or not _YT_INTENT.search(fold_turkish(text)):
        return None
    question = (text[:m.start()] + " " + text[m.end():]).strip() or "Bu videoyu özetle."
    return {"url": f"https://www.youtube.com/watch?v={m.group(1)}", "question": question[:500]}


def wants_cloud_skill(text: str) -> bool:
    return wants_news(text) or wants_flight(text) or youtube_request(text) is not None

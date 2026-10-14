"""Public-source discovery and bounded, SSRF-safe page reading.

Search titles/snippets are discovery metadata only. A page is evidence only
after its public address is resolved, pinned for the request, fetched without
credentials or automatic redirects, and its bounded text content is parsed.
The engine does not execute page scripts or treat page text as tool policy.
"""
from __future__ import annotations

import html.parser
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from email.message import Message
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urljoin, urlsplit, urlunsplit

from ..core.database import connect as managed_connect

DEFAULT_DOMAIN_RELIABILITY = {
    "arxiv.org": 0.9, "doi.org": 0.9, "github.com": 0.75,
    "stackoverflow.com": 0.6, "wikipedia.org": 0.7, "docs.python.org": 0.85,
}
UNRELIABLE = ("forum", "answer", "yahoo", "quora", "reddit")
_MAX_REDIRECTS = 3
_DEFAULT_MAX_BYTES = 1_500_000
_PAGE_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
_SENSITIVE_QUERY_KEYS = frozenset({
    "accesstoken", "apikey", "auth", "authorization", "clientsecret",
    "key", "password", "secret", "session", "token",
})
_WORD = re.compile(r"[a-zçğıöşü0-9]+", re.IGNORECASE)
_NUMERIC_FACT = re.compile(
    r"(?<![\w])(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<unit>"
    r"kwh|kilowatt[- ]?hours?|mwh|megawatt[- ]?hours?|wh|watt[- ]?hours?|"
    r"km/h|kph|mph|kilometers? per hour|miles? per hour|"
    r"km|kilometers?|kilometres?|mi|miles?|m|meters?|metres?|"
    r"kg|kilograms?|g|grams?|lb|pounds?|"
    r"°c|celsius|°f|fahrenheit|%|percent(?:age)?|per cent|"
    r"usd|eur|gbp|\$|€|£|dollars?|euros?)(?!\w)",
    re.IGNORECASE,
)
_CURRENCY_PREFIX = re.compile(
    r"(?<!\w)(?P<unit>usd|eur|gbp|\$|€|£)\s*(?P<value>-?\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_STOP = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "have", "was",
    "were", "are", "bir", "için", "veya", "olan", "olarak", "hakkında",
    "göre", "gibi", "nasıl", "nedir", "ne", "ile", "daha", "çok",
    "a", "an", "in", "on", "of", "to", "is", "by", "as", "at", "it",
    "according", "reported", "measured", "test", "tested", "result",
    "per", "was", "were", "the", "and", "ve", "bir", "olarak",
})
_PUBLISHED_META = frozenset({
    "article:published_time", "datepublished", "datepublishedtime", "pubdate",
    "publication_date", "dc.date", "dc.date.issued", "parsely-pub-date",
    "date", "published", "published_time",
})
_UPDATED_META = frozenset({
    "article:modified_time", "datemodified", "dateupdated", "modified",
    "modified_time", "last-modified", "lastmodified", "dc.modified",
})


class UnsafeSourceError(ValueError):
    """A URL or network target violates the public-source policy."""


@dataclass(frozen=True)
class PublicTarget:
    url: str
    scheme: str
    hostname: str
    port: int
    connect_ip: str
    path_and_query: str


def resolve_public_addresses(hostname: str, port: int) -> list[str]:
    """Resolve a host once; the result is pinned to the subsequent socket."""
    try:
        rows = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UnsafeSourceError("dns_unavailable") from exc
    return list(dict.fromkeys(row[4][0].split("%", 1)[0] for row in rows))


def _is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return bool(address.is_global and not address.is_multicast
                and not address.is_unspecified and not address.is_loopback
                and not address.is_link_local and not address.is_private
                and not address.is_reserved)


def validate_public_target(url: str, *, resolver=resolve_public_addresses) -> PublicTarget:
    """Validate a URL and return one already-checked address to connect to.

    Only default HTTP/HTTPS ports are allowed. All DNS answers must be public,
    avoiding mixed public/private rebinding sets; requests connect to the
    selected literal IP while preserving the original Host header and TLS SNI.
    """
    raw = str(url or "")
    if not raw or len(raw) > 4096 or "\\" in raw or any(ord(c) < 33 for c in raw):
        raise UnsafeSourceError("invalid_url")
    try:
        parts = urlsplit(raw)
        scheme = parts.scheme.lower()
        if scheme not in {"http", "https"} or parts.username or parts.password:
            raise UnsafeSourceError("unsupported_url")
        host_raw = parts.hostname
        port = parts.port
    except (ValueError, UnicodeError) as exc:
        raise UnsafeSourceError("invalid_url") from exc
    if not host_raw or "%" in host_raw:
        raise UnsafeSourceError("invalid_host")
    hostname = host_raw.rstrip(".").lower()
    if not hostname or hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise UnsafeSourceError("local_host_blocked")
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UnsafeSourceError("invalid_host") from exc
    expected_port = 443 if scheme == "https" else 80
    if port is not None and port != expected_port:
        raise UnsafeSourceError("port_blocked")
    port = expected_port

    query_keys = {re.sub(r"[^a-z0-9]", "", key.casefold())
                  for key in parse_qs(parts.query, keep_blank_values=True)}
    if query_keys & _SENSITIVE_QUERY_KEYS:
        raise UnsafeSourceError("credential_query_blocked")
    if len(parts.path) > 2048 or len(parts.query) > 2048:
        raise UnsafeSourceError("url_too_long")

    try:
        literal = ipaddress.ip_address(hostname)
        addresses = [str(literal)]
    except ValueError:
        addresses = resolver(hostname, port)
    addresses = list(dict.fromkeys(str(a).split("%", 1)[0] for a in (addresses or [])))
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise UnsafeSourceError("non_public_address")
    connect_ip = addresses[0]

    if ":" in hostname:
        authority = f"[{hostname}]"
    else:
        authority = hostname
    if port != expected_port:
        authority += f":{port}"
    path_and_query = parts.path or "/"
    if parts.query:
        path_and_query += "?" + parts.query
    normalized = urlunsplit((scheme, authority, parts.path or "/", parts.query, ""))
    return PublicTarget(normalized, scheme, hostname, port, connect_ip, path_and_query)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, connect_ip, timeout):
        super().__init__(host, port, timeout=timeout)
        self._connect_ip = connect_ip

    def connect(self):
        self.sock = socket.create_connection(
            (self._connect_ip, self.port), self.timeout, self.source_address
        )
        if self._tunnel_host:
            self._tunnel()


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port, connect_ip, timeout):
        super().__init__(host, port, timeout=timeout,
                         context=ssl.create_default_context())
        self._connect_ip = connect_ip

    def connect(self):
        raw = socket.create_connection(
            (self._connect_ip, self.port), self.timeout, self.source_address
        )
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def _pinned_transport(target: PublicTarget, timeout: float,
                      max_bytes: int) -> tuple[int, dict[str, str], bytes]:
    """Perform exactly one request; redirects are handled only by SourceReader."""
    connection_type = _PinnedHTTPSConnection if target.scheme == "https" else _PinnedHTTPConnection
    connection = connection_type(target.hostname, target.port,
                                 target.connect_ip, timeout)
    try:
        connection.request(
            "GET", target.path_and_query,
            headers={
                "Host": (f"[{target.hostname}]" if ":" in target.hostname
                         else target.hostname),
                "User-Agent": "GOLGE-Research/1.0 (+public source reader)",
                "Accept": "text/html, application/xhtml+xml, text/plain;q=0.9",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        headers = {key.casefold(): value for key, value in response.getheaders()}
        body = response.read(max_bytes + 1)
        status = response.status
        response.close()
        return status, headers, body
    finally:
        connection.close()


class _PageTextParser(html.parser.HTMLParser):
    _IGNORED = frozenset(("script", "style", "noscript", "template", "svg",
                          "iframe", "object", "nav", "header", "footer", "aside"))
    _BLOCK = frozenset(("p", "li", "h1", "h2", "h3", "h4", "article", "section", "br"))

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.published_raw = None
        self.updated_raw = None
        self._ignored: list[str] = []
        self._in_title = False

    def _record_date(self, key, value):
        normalized = re.sub(r"[^a-z0-9:._-]", "", str(key or "").casefold())
        value = str(value or "").strip()[:120]
        if not value:
            return
        if normalized in _PUBLISHED_META and self.published_raw is None:
            self.published_raw = value
        elif normalized in _UPDATED_META and self.updated_raw is None:
            self.updated_raw = value

    def handle_starttag(self, tag, attrs):
        tag = tag.casefold()
        attrs = {str(key or "").casefold(): str(value or "") for key, value in attrs}
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name") or attrs.get("itemprop")
            self._record_date(key, attrs.get("content"))
        elif tag == "time" and attrs.get("datetime"):
            semantics = " ".join((attrs.get("itemprop", ""), attrs.get("class", ""),
                                  attrs.get("id", ""))).casefold()
            if any(word in semantics for word in ("publish", "pubdate", "issued")):
                self._record_date("datepublished", attrs["datetime"])
            elif any(word in semantics for word in ("modified", "updated")):
                self._record_date("datemodified", attrs["datetime"])
        if tag in self._IGNORED:
            self._ignored.append(tag)
            return
        if self._ignored:
            return
        if tag == "title":
            self._in_title = True
        if tag in self._BLOCK:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.casefold()
        if self._ignored:
            if tag == self._ignored[-1]:
                self._ignored.pop()
            return
        if tag == "title":
            self._in_title = False
        elif tag in self._BLOCK:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self._ignored:
            return
        value = " ".join(str(data or "").split())
        if not value:
            return
        if self._in_title:
            self.title_parts.append(value)
        else:
            self.text_parts.append(value)


def _normalized_date(value: str | None) -> str | None:
    """Parse common published/modified metadata without guessing timezones."""
    raw = " ".join(str(value or "").split())[:120]
    if not raw:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            return date.fromisoformat(raw).isoformat()
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.isoformat(timespec="seconds")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def extract_page_details(body: bytes, content_type: str) -> tuple[str, str, dict]:
    """Extract text and inert publication metadata; never execute page scripts."""
    if content_type == "text/plain":
        text = body.decode("utf-8", errors="replace")
        return "", "\n".join(line.strip() for line in text.splitlines() if line.strip()), {
            "published_at": None, "updated_at": None,
        }
    parser = _PageTextParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    parser.close()
    title = " ".join(parser.title_parts).strip()[:240]
    text = "\n".join(line.strip() for line in " ".join(parser.text_parts).splitlines()
                      if line.strip())
    return title, text, {
        "published_at": _normalized_date(parser.published_raw),
        "updated_at": _normalized_date(parser.updated_raw),
    }


def extract_page_text(body: bytes, content_type: str) -> tuple[str, str]:
    """Compatibility wrapper for callers that only need title and main text."""
    title, text, _ = extract_page_details(body, content_type)
    return title, text


class SourceReader:
    """A small public HTML/text fetcher with strict network and resource bounds."""

    def __init__(self, *, resolver=resolve_public_addresses, transport=None,
                 timeout_s: float = 4.0, max_bytes: int = _DEFAULT_MAX_BYTES,
                 max_redirects: int = _MAX_REDIRECTS, now=None):
        self.resolver = resolver
        self.transport = transport
        self.timeout_s = max(0.25, min(float(timeout_s), 10.0))
        self.max_bytes = max(1, min(int(max_bytes), 2_000_000))
        self.max_redirects = max(0, min(int(max_redirects), _MAX_REDIRECTS))
        self.now = now or (lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def fetch_raw(self, url: str) -> dict:
        current = str(url or "")
        try:
            original_scheme = urlsplit(current).scheme.casefold()
        except ValueError:
            return {"ok": False, "status": "blocked", "reason": "invalid_url"}
        for redirect_count in range(self.max_redirects + 1):
            try:
                target = validate_public_target(current, resolver=self.resolver)
            except UnsafeSourceError as exc:
                return {"ok": False, "status": "blocked", "reason": str(exc)}
            if original_scheme == "https" and target.scheme != "https":
                return {"ok": False, "status": "blocked_redirect",
                        "reason": "https_downgrade"}
            try:
                transport = self.transport or _pinned_transport
                status, headers, body = transport(
                    target, self.timeout_s, self.max_bytes
                ) if self.transport is None else transport(
                    target.url, target.connect_ip, self.timeout_s, self.max_bytes
                )
            except (TimeoutError, socket.timeout):
                return {"ok": False, "status": "timeout", "reason": "request_timeout"}
            except (OSError, ssl.SSLError, http.client.HTTPException):
                return {"ok": False, "status": "unavailable", "reason": "request_failed"}
            headers = {str(k).casefold(): str(v) for k, v in (headers or {}).items()}
            if status in (301, 302, 303, 307, 308):
                location = headers.get("location", "")
                if not location or redirect_count >= self.max_redirects:
                    return {"ok": False, "status": "blocked_redirect",
                            "reason": "redirect_limit"}
                next_url = urljoin(target.url, location)
                try:
                    next_parts = urlsplit(next_url)
                    if next_parts.scheme.casefold() not in {"http", "https"}:
                        raise UnsafeSourceError("unsupported_url")
                    if original_scheme == "https" and next_parts.scheme.casefold() != "https":
                        raise UnsafeSourceError("https_downgrade")
                    # Validate before the next network operation; each hop gets
                    # a fresh DNS check and the checked IP is the one we pin.
                    validate_public_target(next_url, resolver=self.resolver)
                except (ValueError, UnsafeSourceError):
                    return {"ok": False, "status": "blocked_redirect",
                            "reason": "redirect_target_blocked"}
                current = next_url
                continue
            if status < 200 or status >= 300:
                return {"ok": False, "status": "http_error",
                        "http_status": int(status)}
            content_type = headers.get("content-type", "").split(";", 1)[0].strip().casefold()
            if content_type not in _PAGE_TYPES:
                return {"ok": False, "status": "unsupported_content_type",
                        "content_type": content_type[:80]}
            try:
                declared_length = int(headers.get("content-length", "0"))
            except ValueError:
                declared_length = 0
            if declared_length > self.max_bytes or len(body or b"") > self.max_bytes:
                return {"ok": False, "status": "too_large", "max_bytes": self.max_bytes}
            return {"ok": True, "url": target.url, "status_code": int(status),
                    "content_type": content_type, "last_modified": headers.get("last-modified", "")[:120],
                    "body": bytes(body or b"")}
        return {"ok": False, "status": "blocked_redirect", "reason": "redirect_limit"}

    def read(self, url: str) -> dict:
        raw = self.fetch_raw(url)
        if not raw.get("ok"):
            return {key: value for key, value in raw.items() if key != "body"}
        title, text, page_dates = extract_page_details(raw["body"], raw["content_type"])
        text = text[:24_000]
        if len(text.strip()) < 32:
            return {"ok": False, "status": "empty_page", "url": raw["url"]}
        return {"ok": True, "url": raw["url"], "title": title,
                "text": text, "accessed_at": self.now(),
                "published_at": page_dates["published_at"],
                "updated_at": page_dates["updated_at"],
                "http_last_modified_at": _normalized_date(raw.get("last_modified")),
                "content_type": raw["content_type"]}


class _SearchResultsParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self._active = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag.casefold() == "a" and "result__a" in classes:
            self._active = {"href": attrs.get("href", ""), "title": []}

    def handle_data(self, data):
        if self._active is not None:
            self._active["title"].append(data)

    def handle_endtag(self, tag):
        if tag.casefold() == "a" and self._active is not None:
            self.items.append({"url": self._active["href"],
                               "title": " ".join(" ".join(self._active["title"]).split())[:160],
                               "snippet": ""})
            self._active = None


def default_web_search(query: str, timeout: float = 4.0) -> list[dict]:
    """Read search-result metadata from a fixed public endpoint; never auto-redirect."""
    try:
        reader = SourceReader(timeout_s=timeout, max_bytes=1_000_000)
        url = "https://html.duckduckgo.com/html/?q=" + quote_plus(str(query)[:500])
        page = reader.fetch_raw(url)
        if not page.get("ok"):
            return []
        parser = _SearchResultsParser()
        parser.feed(page["body"].decode("utf-8", errors="replace"))
        out = []
        for item in parser.items:
            target = item["url"]
            if target.startswith("//duckduckgo.com/l/"):
                target = "https:" + target
            if "duckduckgo.com/l/" in target:
                redirect_query = parse_qs(urlsplit(target).query)
                target = (redirect_query.get("uddg") or [""])[0]
            if target.startswith(("http://", "https://")) and item["title"]:
                out.append({**item, "url": target})
            if len(out) >= 10:
                break
        return out
    except Exception:
        return []   # ağ yok → dürüst boş (sahte sonuç YOK)


def _tokens(text: str) -> list[str]:
    return [w.casefold() for w in _WORD.findall(str(text or "")) if w.casefold() not in _STOP]


_UNIT_ALIASES = {
    "kwh": "kwh", "kilowatt-hour": "kwh", "kilowatt-hours": "kwh",
    "kilowatthour": "kwh", "kilowatthours": "kwh",
    "mwh": "mwh", "megawatt-hour": "mwh", "megawatt-hours": "mwh",
    "wh": "wh", "watt-hour": "wh", "watt-hours": "wh",
    "km/h": "km/h", "kph": "km/h", "kilometer per hour": "km/h",
    "kilometers per hour": "km/h", "kilometre per hour": "km/h",
    "kilometres per hour": "km/h", "mph": "mph", "mile per hour": "mph",
    "miles per hour": "mph", "km": "km", "kilometer": "km",
    "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "mi": "mi", "mile": "mi", "miles": "mi", "m": "m",
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg", "g": "g",
    "gram": "g", "grams": "g", "lb": "lb", "pound": "lb", "pounds": "lb",
    "°c": "celsius", "celsius": "celsius", "°f": "fahrenheit",
    "fahrenheit": "fahrenheit", "%": "percent", "percent": "percent",
    "percentage": "percent", "per cent": "percent", "usd": "usd",
    "dollar": "usd", "dollars": "usd", "$": "usd", "eur": "eur",
    "euro": "eur", "euros": "eur", "€": "eur", "gbp": "gbp",
    "£": "gbp",
}


def _numeric_value(raw: str) -> str:
    value = str(raw or "").replace(" ", "")
    if "," in value and "." in value:
        value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")
        value = "".join(parts) if len(parts) > 2 or (len(parts[-1]) == 3 and len(parts[0]) <= 3) else value.replace(",", ".")
    try:
        return format(Decimal(value).normalize(), "f")
    except InvalidOperation:
        return value


def _numeric_mentions(text: str) -> list[tuple[str, str]]:
    mentions = []
    for match in _NUMERIC_FACT.finditer(str(text or "")):
        unit = " ".join(match.group("unit").casefold().split())
        normalized_unit = _UNIT_ALIASES.get(unit, unit)
        mentions.append((_numeric_value(match.group("value")), normalized_unit))
    for match in _CURRENCY_PREFIX.finditer(str(text or "")):
        unit = " ".join(match.group("unit").casefold().split())
        normalized_unit = _UNIT_ALIASES.get(unit, unit)
        mentions.append((_numeric_value(match.group("value")), normalized_unit))
    return mentions


def _content_shingles(text: str) -> set[tuple[str, ...]]:
    tokens = _tokens(text)[:5000]
    if len(tokens) < 3:
        return set()
    return {tuple(tokens[index:index + 3]) for index in range(len(tokens) - 2)}


def _content_similarity(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> tuple[float, float]:
    if not left or not right:
        return 0.0, 0.0
    shared = len(left & right)
    return shared / len(left | right), shared / min(len(left), len(right))


def copied_source_similarity(left_text: str, right_text: str) -> float | None:
    """Return similarity only when two page bodies are strong copy candidates."""
    return _copied_shingle_similarity(_content_shingles(left_text), _content_shingles(right_text))


def _copied_shingle_similarity(left: set[tuple[str, ...]],
                               right: set[tuple[str, ...]]) -> float | None:
    jaccard, containment = _content_similarity(left, right)
    if jaccard >= 0.90 or (containment >= 0.95 and jaccard >= 0.65):
        return round(max(jaccard, containment), 3)
    return None


def _numeric_disagreements(findings: list[dict], query: str) -> list[dict]:
    """Find narrow numeric disagreement candidates; this is not entailment."""
    query_terms = set(_tokens(query))
    groups: dict[tuple[str, int, tuple[str, ...]], dict] = {}
    for finding in findings:
        if not finding.get("independent_source"):
            continue
        text = str(finding.get("source_text", ""))[:24_000]
        for sentence in re.split(r"(?<=[.!?…])\s+|\n+", text):
            mentions = _numeric_mentions(sentence)
            if not mentions:
                continue
            years = {int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", sentence)}
            published = str(finding.get("published_at") or "")
            if len(years) == 1:
                reference_year = next(iter(years))
            elif not years and re.match(r"\d{4}", published):
                reference_year = int(published[:4])
            else:
                # Ambiguous or missing date context cannot support a conflict label.
                continue
            cleaned = re.sub(r"\b(?:19|20)\d{2}\b", " ", _NUMERIC_FACT.sub(" ", sentence))
            context = tuple(sorted(set(_tokens(cleaned))))
            if len(context) < 2 or (query_terms and not (query_terms & set(context))):
                continue
            for value, unit in mentions:
                key = (unit, reference_year, context)
                group = groups.setdefault(key, {"context": " ".join(sentence.split())[:360], "values": {}})
                sources = group["values"].setdefault(value, [])
                source = {
                    "url": str(finding.get("url", ""))[:4096],
                    "title": str(finding.get("title", ""))[:160],
                    "published_at": published[:40] or None,
                }
                if source["url"] not in {item["url"] for item in sources}:
                    sources.append(source)
    conflicts = []
    for (unit, year, _), group in groups.items():
        if len(group["values"]) < 2:
            continue
        distinct_source_conflict = any(
            left_url != right_url
            for left_value, left_sources in group["values"].items()
            for right_value, right_sources in group["values"].items()
            if left_value != right_value
            for left_url in (source["url"] for source in left_sources)
            for right_url in (source["url"] for source in right_sources)
        )
        if not distinct_source_conflict:
            continue
        conflicts.append({
            "status": "potential_numeric_conflict",
            "reference_year": year,
            "unit": unit,
            "context": group["context"],
            "values": [
                {"value": value, "sources": sources[:4]}
                for value, sources in sorted(group["values"].items())
            ],
            "semantic_resolution": "not_performed",
        })
        if len(conflicts) >= 8:
            break
    return conflicts


def select_evidence_excerpt(query: str, text: str, *, max_chars: int = 1400) -> str:
    """Choose page sentences relevant to the query; excerpts stay source-labelled."""
    sentences = [" ".join(s.split()) for s in re.split(r"(?<=[.!?…])\s+|\n+", text or "")]
    sentences = [s for s in sentences if s]
    query_terms = set(_tokens(query))
    ranked = []
    for index, sentence in enumerate(sentences):
        terms = set(_tokens(sentence))
        overlap = len(query_terms & terms)
        ranked.append((overlap, -index, sentence))
    if not ranked:
        return ""
    ranked.sort(reverse=True)
    chosen, size = [], 0
    for overlap, _, sentence in ranked:
        if query_terms and overlap == 0 and chosen:
            continue
        remaining = max_chars - size
        if remaining <= 0:
            break
        piece = sentence[:remaining].strip()
        if piece:
            chosen.append(piece)
            size += len(piece) + 1
    if not chosen:
        chosen = [sentences[0][:max_chars]]
    return " ".join(chosen)[:max_chars]


def match_claim_to_evidence(claim: str, findings: list[dict], *,
                            min_overlap: float = 0.72) -> dict:
    """Conservative lexical evidence check, explicitly not semantic entailment."""
    claim_terms = set(_tokens(claim))
    claim_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", str(claim or "")))
    negation = {"no", "not", "never", "without", "neither", "nor", "none",
                "değil", "degil", "yok", "olmadan", "asla", "hiç", "hic",
                "olmaz", "olmadı", "olmayacak"}

    def has_negation(terms):
        return bool(terms & negation) or any(
            term.startswith(("değil", "degil")) for term in terms
        )

    claim_polarity = has_negation(claim_terms)
    if not claim_terms:
        return {"supported": False, "method": "lexical_overlap", "evidence": []}
    evidence = []
    for finding in findings or []:
        if finding.get("basis") != "source_page_excerpt" or not finding.get("page_read"):
            continue
        excerpt = str(finding.get("excerpt", ""))
        excerpt_terms = set(_tokens(excerpt))
        if has_negation(excerpt_terms) != claim_polarity:
            continue
        overlap = len(claim_terms & excerpt_terms) / max(1, len(claim_terms))
        excerpt_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", excerpt))
        numbers_match = claim_numbers.issubset(excerpt_numbers)
        # Exact numeric overlap alone is unsafe: 42 Wh and 42 kWh are not the
        # same claim. Normalize only known aliases; do not convert units or FX.
        claim_facts = set(_numeric_mentions(claim))
        excerpt_facts = set(_numeric_mentions(excerpt))
        units_match = claim_facts.issubset(excerpt_facts)
        if (overlap >= max(0.0, min(1.0, min_overlap)) and numbers_match
                and units_match):
            evidence.append({"url": finding.get("url", ""),
                             "overlap": round(overlap, 3),
                             "numbers_match": numbers_match,
                             "units_match": units_match})
    return {"supported": bool(evidence), "method": "lexical_overlap_exact_numbers",
            "semantic_entailment_checked": False,
            "numeric_unit_matching": True, "evidence": evidence}


class ResearchEngine:
    def __init__(self, db_path: str = "data/cognitive/research.db",
                 search_fn=None, domain_reliability: dict | None = None,
                 source_reader: SourceReader | None = None):
        self.path = Path(db_path)
        if db_path != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = managed_connect(str(db_path), check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, query TEXT,
            result_json TEXT)""")
        self.db.commit()
        self.search_fn = search_fn or default_web_search
        self.source_reader = source_reader or SourceReader()
        self.domain_reliability = dict(DEFAULT_DOMAIN_RELIABILITY)
        self.domain_reliability.update(domain_reliability or {})

    def close(self):
        with self.lock:
            self.db.close()

    # ---------------------------------------------------- reliability
    def source_reliability(self, url: str) -> float:
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
        for dom, score in self.domain_reliability.items():
            domain = dom.lower().lstrip(".")
            if host == domain or host.endswith("." + domain):
                return float(score)
        if any(u in host for u in UNRELIABLE):
            return 0.25
        return 0.4

    # ---------------------------------------------------- pipeline
    def research(self, query: str, max_sources: int = 5,
                 store: bool = True) -> dict:
        query = str(query or "").strip()[:1000]
        max_sources = max(1, min(int(max_sources), 5))
        if not query:
            return {"ok": False, "status": "invalid_query", "query": "",
                    "citations": [], "evidence_level": "none", "confidence": 0.0}
        results = self.search_fn(query)
        if not results:
            out = {"ok": False, "status": "search_unavailable",
                   "error": "search-unavailable-or-empty", "query": query,
                   "citations": [], "evidence_level": "none", "confidence": 0.0,
                   "note": "ağ/arayüz yok — sonuç UYDURULMAZ"}
            if store:
                self._store(query, out)
            return out

        seen_urls, seen_hosts, ranked = set(), set(), []
        query_terms = set(_tokens(query))
        for result in results:
            url = str(result.get("url", ""))[:4096]
            try:
                parsed = urlsplit(url)
                host = (parsed.hostname or "").casefold().rstrip(".")
                if parsed.scheme.casefold() not in {"http", "https"} or not host:
                    continue
            except ValueError:
                continue
            canonical = urlunsplit((parsed.scheme.casefold(), parsed.netloc,
                                    parsed.path or "/", parsed.query, ""))
            if canonical in seen_urls or host in seen_hosts:
                continue
            seen_urls.add(canonical)
            seen_hosts.add(host)
            title = str(result.get("title", "")).strip()[:160]
            if not title:
                continue
            discovery_text = (title + " " + str(result.get("snippet", ""))[:500]).casefold()
            overlap = len(query_terms & set(_tokens(discovery_text)))
            score = self.source_reliability(url) * (
                0.5 + 0.5 * min(1.0, overlap / max(1, len(query_terms)))
            )
            ranked.append((score, {"url": url, "title": title}))
        ranked.sort(key=lambda item: (-item[0], item[1]["url"]))
        selected = [item for _, item in ranked[:max_sources]]

        findings, unread = [], []
        verification_findings = []
        content_anchors = []
        for result in selected:
            read = self.source_reader.read(result["url"])
            if not read.get("ok"):
                unread.append({"title": result["title"],
                               "read_status": str(read.get("status", "unavailable"))[:60]})
                continue
            excerpt = select_evidence_excerpt(query, read.get("text", ""))
            if len(excerpt.strip()) < 24:
                unread.append({"title": result["title"], "read_status": "no_relevant_excerpt"})
                continue
            url = str(read.get("url", result["url"]))[:4096]
            text = str(read.get("text", ""))[:24_000]
            shingles = _content_shingles(text)
            duplicate = None
            for anchor in content_anchors:
                similarity = _copied_shingle_similarity(shingles, anchor["shingles"])
                if similarity is not None:
                    duplicate = {**anchor, "similarity": similarity}
                    break
            normalized_content = " ".join(_tokens(text))
            cluster_id = (duplicate["cluster_id"] if duplicate else
                          hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()[:16])
            if duplicate is None:
                content_anchors.append({"url": url, "cluster_id": cluster_id,
                                        "text": text, "shingles": shingles})
            finding = {
                "title": str(read.get("title") or result["title"])[:160],
                "search_title": result["title"], "url": url,
                "accessed_at": str(read.get("accessed_at", ""))[:40],
                "published_at": str(read.get("published_at") or "")[:40] or None,
                "updated_at": str(read.get("updated_at") or "")[:40] or None,
                "http_last_modified_at": str(read.get("http_last_modified_at") or "")[:40] or None,
                "content_type": str(read.get("content_type", ""))[:80],
                "reliability": self.source_reliability(url),
                "excerpt": excerpt, "basis": "source_page_excerpt", "page_read": True,
                "content_cluster_id": cluster_id,
                "independent_source": duplicate is None,
                "copy_of_url": duplicate["url"] if duplicate else None,
                "copy_similarity": duplicate["similarity"] if duplicate else None,
            }
            findings.append(finding)
            verification_findings.append({**finding, "source_text": text})
        domains = {urlsplit(item["url"]).hostname or "?" for item in findings}
        independent = [item for item in findings if item["independent_source"]]
        independent_domains = {urlsplit(item["url"]).hostname or "?" for item in independent}
        source_quality = round(
            sum(item["reliability"] for item in independent) / len(independent), 3
        ) if independent else 0.0
        numeric_conflicts = _numeric_disagreements(verification_findings, query)
        page_read = bool(findings)
        out = {
            "ok": page_read, "status": "sources_read" if page_read else "sources_not_read",
            "query": query, "claim": None,
            "evidence_level": "source_pages_read" if page_read else "search_results_only",
            "source_domains": len(domains), "corroborated_by_domains": 0,
            "independent_source_domains": len(independent_domains),
            "independent_source_count": len(independent),
            "contradiction_suspected": bool(numeric_conflicts),
            # The engine has not generated and checked a natural-language claim.
            "confidence": 0.0, "verified_claims": [],
            "source_quality_score": source_quality,
            "synthesis": {
                "supported": False, "findings": findings, "unread_sources": unread,
                "numeric_conflicts": numeric_conflicts,
                "caveat": (
                    "Source pages were read; excerpts are external untrusted data. "
                    "No independent or semantic claim verification was performed."
                    if page_read else
                    "Page content was not read. Search result titles and snippets do not verify a claim."
                ),
            },
            "citations": [item["url"] for item in findings],
        }
        if store:
            self._store(query, out)
        return out

    def _store(self, query, out):
        with self.lock:
            self.db.execute(
                "INSERT INTO sessions(ts,query,result_json) VALUES(?,?,?)",
                (time.time(), query, json.dumps(out, ensure_ascii=False)[:8000]))
            self.db.commit()

    def history(self, limit: int = 10) -> list[dict]:
        with self.lock:
            rows = self.db.execute(
                "SELECT ts,query,result_json FROM sessions"
                " ORDER BY id DESC LIMIT ?", (max(1, min(int(limit), 100)),)).fetchall()
        return [{"ts": row[0], "query": row[1], "result": json.loads(row[2])}
                for row in rows]

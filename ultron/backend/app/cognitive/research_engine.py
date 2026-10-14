"""Conservative public search-result discovery.

This module currently searches, filters, ranks and cites result metadata. It
does not fetch source pages or verify claims. Consequently, it reports source
quality separately from answer confidence and never labels search results as
corroboration, contradiction analysis, or supported evidence.

Testability: search_fn injection lets the HTTP boundary run against a local
server without depending on external network access.
"""
from __future__ import annotations

import json
import re
from app.core.database import connect as managed_connect
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_DOMAIN_RELIABILITY = {
    "arxiv.org": 0.9, "doi.org": 0.9, "github.com": 0.75,
    "stackoverflow.com": 0.6, "wikipedia.org": 0.7, "docs.python.org": 0.85,
}
UNRELIABLE = ("forum", "answer", "yahoo", "quora", "reddit")


def default_web_search(query: str, timeout: float = 4.0) -> list[dict]:
    """Gerçek ağ araması (DuckDuckGo HTML). Ağ engelliyse boş liste — dürüst."""
    try:
        import urllib.request
        url = ("https://html.duckduckgo.com/html/?q=" +
               urllib.parse.quote(query))
        req = urllib.request.Request(url, headers={"User-Agent": "ULTRON/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", errors="replace")
        out = []
        for m in re.finditer(
                r'result__a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html):
            u, t = m.group(1), re.sub("<[^>]+>", "", m.group(2))
            if u.startswith("http"):
                out.append({"url": u, "title": t.strip()[:160],
                            "snippet": ""})
            if len(out) >= 10:
                break
        return out
    except Exception:
        return []   # ağ yok → dürüst boş (sahte sonuç YOK)


class ResearchEngine:
    def __init__(self, db_path: str = "data/cognitive/research.db",
                 search_fn=None, domain_reliability: dict | None = None):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = managed_connect(str(self.path), check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, query TEXT,
            result_json TEXT)""")
        self.db.commit()
        self.search_fn = search_fn or default_web_search
        self.domain_reliability = dict(DEFAULT_DOMAIN_RELIABILITY)
        self.domain_reliability.update(domain_reliability or {})

    # ---------------------------------------------------- reliability
    def source_reliability(self, url: str) -> float:
        host = (urlparse(url).hostname or "").lower()
        for dom, score in self.domain_reliability.items():
            domain = dom.lower().lstrip(".")
            if host == domain or host.endswith("." + domain):
                return float(score)
        if any(u in host for u in UNRELIABLE):
            return 0.25
        return 0.4   # bilinmeyen domain: nötr-düşük (aşırı iyimserlik yok)

    # ---------------------------------------------------- pipeline
    def research(self, query: str, max_sources: int = 5,
                 store: bool = True) -> dict:
        # 1) SEARCH
        results = self.search_fn(query)
        if not results:
            out = {"ok": False, "error": "search-unavailable-or-empty",
                   "query": query, "citations": [],
                   "evidence_level": "none",
                   "note": "ağ/arayüz yok — sonuç UYDURULMAZ"}
            if store:
                self._store(query, out)
            return out
        # 2) DISCOVER: benzersiz url'ler
        seen, discovered = set(), []
        for r in results:
            u = r.get("url", "")
            if u and u not in seen:
                seen.add(u)
                discovered.append(r)
        # 3) FILTER: şema + boş başlık
        filtered = [r for r in discovered
                    if r.get("title", "").strip()
                    and urlparse(r["url"]).scheme in ("http", "https")]
        # 4) RANK: güvenilirlik × sorgu ilgisi (başlık/snippet örtüşmesi)
        qtoks = {w.lower() for w in re.findall(r"[a-zçğıöşü0-9]+",
                                               query, re.IGNORECASE)}
        ranked = []
        for r in filtered:
            text = (r.get("title", "") + " " + r.get("snippet", "")).lower()
            overlap = len(qtoks & set(re.findall(r"[a-zçğıöşü0-9]+", text)))
            score = self.source_reliability(r["url"]) * (
                0.5 + 0.5 * min(1.0, overlap / max(1, len(qtoks))))
            ranked.append((score, r))
        ranked.sort(key=lambda x: -x[0])
        top = [r for _, r in ranked[:max_sources]]
        # Search result titles/snippets are discovery metadata, not page-level
        # evidence. Do not infer corroboration or contradiction from unrelated
        # domains or numbers until source pages have actually been read.
        domains = {urlparse(r["url"]).hostname or "?" for r in top}
        # This is source-quality metadata only, not confidence that an answer
        # or claim is true. Keep answer confidence at zero until page evidence
        # and claim-to-evidence matching exist.
        source_quality = round(
            sum(self.source_reliability(r["url"]) for r in top) / len(top), 3
        ) if top else 0.0
        findings = [{"title": r.get("title", "")[:160], "url": r["url"],
                     "reliability": self.source_reliability(r["url"]),
                     "snippet": (r.get("snippet", "") or "")[:500],
                     "basis": "search_result_metadata"}
                    for r in top]
        out = {
            "ok": True, "status": "sources_discovered", "query": query,
            "claim": None,
            "evidence_level": "search_results_only",
            "source_domains": len(domains),
            "corroborated_by_domains": 0,
            "contradiction_suspected": False,
            "confidence": 0.0,
            "source_quality_score": source_quality,
            "synthesis": {
                "supported": False,
                "findings": findings,
                "caveat": ("Page content was not read. Search result titles and snippets "
                           "do not verify a claim."),
            },
            "citations": [r["url"] for r in top],
        }
        if store:
            self._store(query, out)
        return out

    def _store(self, query, out):
        with self.lock:
            self.db.execute(
                "INSERT INTO sessions(ts,query,result_json) VALUES(?,?,?)",
                (time.time(), query,
                 json.dumps(out, ensure_ascii=False)[:8000]))
            self.db.commit()

    def history(self, limit: int = 10) -> list[dict]:
        with self.lock:
            rows = self.db.execute(
                "SELECT ts,query,result_json FROM sessions"
                " ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"ts": r[0], "query": r[1], "result": json.loads(r[2])}
                for r in rows]

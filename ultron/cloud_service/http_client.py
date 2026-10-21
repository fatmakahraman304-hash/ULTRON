"""One shared aiohttp session (connection reuse) with a bounded, size-capped fetch and one retry
for idempotent GETs. Redirects are never followed; the HTTPS proxy from the environment is honoured."""
from __future__ import annotations

import asyncio
import os
import random
from typing import Any
from urllib.parse import urlsplit
from urllib.request import proxy_bypass_environment

from aiohttp import ClientError, ClientSession, ClientTimeout, TCPConnector

_state: dict[str, Any] = {"session": None, "loop": None}


def session() -> ClientSession:
    loop = asyncio.get_running_loop()
    current = _state["session"]
    if current is None or current.closed or _state["loop"] is not loop:
        _state["session"] = ClientSession(connector=TCPConnector(limit=20, limit_per_host=6, ttl_dns_cache=300),
                                          headers={"User-Agent": "GOLGE/1.0"})
        _state["loop"] = loop
    return _state["session"]


def _proxy_for(url: str) -> str | None:
    """Explicit HTTPS proxy from the environment (never .netrc), honouring NO_PROXY and skipping plain http."""
    parts = urlsplit(url)
    if parts.scheme != "https" or proxy_bypass_environment(parts.hostname or ""):
        return None
    return os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")


async def close() -> None:
    current = _state["session"]
    _state["session"] = None
    if current is not None and not current.closed:
        await current.close()


async def fetch(url: str, *, method: str = "GET", headers: dict | None = None, json_body: Any = None, data: Any = None,
                timeout: float = 10.0, max_bytes: int = 2_000_000, retries: int = 1) -> tuple[int, bytes, dict]:
    """Return (status, body, response headers). Raises ValueError('too_large') or the last network error."""
    proxy = _proxy_for(url)
    attempts = 1 + (max(0, retries) if method == "GET" else 0)
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            async with session().request(method, url, headers=headers, json=json_body, data=data, allow_redirects=False,
                                         proxy=proxy, timeout=ClientTimeout(total=timeout)) as resp:
                declared = int(resp.headers.get("Content-Length", "0") or 0)
                if declared > max_bytes:
                    raise ValueError("too_large")
                body = await resp.content.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ValueError("too_large")
                if resp.status >= 500 and attempt + 1 < attempts:
                    await asyncio.sleep(0.3 + random.random() * 0.4)
                    continue
                return resp.status, body, dict(resp.headers)
        except (ClientError, asyncio.TimeoutError) as exc:
            last = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(0.3 + random.random() * 0.4)
    raise last or RuntimeError("fetch_failed")

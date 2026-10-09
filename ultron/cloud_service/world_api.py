"""ULTRON WORLD public read-only map data adapters.

Never proxy arbitrary URLs. Upstream failures are shown as unavailable, not
silently replaced by fabricated aircraft, weather, or earthquake markers.
In-memory bounded TTL cache limits requests to community services. For a
high-traffic service, use a paid/self-hosted provider rather than scraping OSM.
"""
from __future__ import annotations

import asyncio
import math
import time
from typing import Any
from aiohttp import ClientSession, ClientTimeout, web

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_LOCKS: dict[str, asyncio.Lock] = {}
_CACHE_LIMIT = 180
_UA = "ULTRON-World/0.1 (+https://github.com/fatmakahraman304-hash/ULTRON)"
_TIMEOUT = ClientTimeout(total=9)


def coordinate(raw: str | None, low: float, high: float, default: float) -> float:
    try:
        value = float(raw) if raw is not None else default
        if not math.isfinite(value) or value < low or value > high:
            raise ValueError()
        return round(value, 4)
    except (ValueError, TypeError):
        raise web.HTTPBadRequest(text='{"error":"invalid_coordinates"}', content_type="application/json")


def point(request: web.Request) -> tuple[float, float]:
    return (
        coordinate(request.query.get("lat"), -90, 90, 35.13),
        coordinate(request.query.get("lon"), -180, 180, 33.43),
    )


async def _upstream(url: str, *, ttl: int, key: str) -> dict[str, Any]:
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and cached[0] > now:
        return cached[1]
    lock = _LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _CACHE.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        try:
            async with ClientSession(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as session:
                async with session.get(url, allow_redirects=False) as response:
                    if response.status != 200:
                        raise web.HTTPBadGateway(
                            text='{"error":"upstream_unavailable"}',
                            content_type="application/json",
                        )
                    if int(response.headers.get("Content-Length", "0") or 0) > 2_000_000:
                        raise web.HTTPBadGateway(text='{"error":"upstream_too_large"}',
                                                 content_type="application/json")
                    payload = await response.content.read(2_000_001)
                    if len(payload) > 2_000_000:
                        raise web.HTTPBadGateway(text='{"error":"upstream_too_large"}',
                                                 content_type="application/json")
                    import json
                    data = json.loads(payload)
                    if not isinstance(data, dict):
                        raise ValueError("Unexpected upstream structure")
        except web.HTTPException:
            raise
        except (OSError, asyncio.TimeoutError, ValueError, TypeError, Exception) as exc:
            # Do not leak URL internals, API errors, or raw third-party payloads.
            raise web.HTTPBadGateway(text='{"error":"upstream_unavailable"}',
                                     content_type="application/json") from exc
        if len(_CACHE) >= _CACHE_LIMIT:
            expired = [k for k, v in _CACHE.items() if v[0] <= time.monotonic()]
            for k in expired:
                _CACHE.pop(k, None)
            if len(_CACHE) >= _CACHE_LIMIT:
                _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = (time.monotonic() + ttl, data)
        if len(_LOCKS) > _CACHE_LIMIT * 2:
            for old in list(_LOCKS):
                if old not in _CACHE and not _LOCKS[old].locked():
                    _LOCKS.pop(old, None)
        return data


async def weather(request: web.Request) -> web.Response:
    lat, lon = point(request)
    key = f"weather:{round(lat,2)}:{round(lon,2)}"
    url = (
        "https://api.open-meteo.com/v1/forecast?latitude=" + str(lat)
        + "&longitude=" + str(lon)
        + "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
          "precipitation,rain,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,"
          "surface_pressure"
        + "&hourly=temperature_2m,precipitation_probability,wind_speed_10m"
        + "&daily=sunrise,sunset,uv_index_max&timezone=auto&forecast_days=2"
    )
    data = await _upstream(url, key=key, ttl=600)
    if not isinstance(data.get("current"), dict):
        raise web.HTTPBadGateway(text='{"error":"weather_data_missing"}',
                                 content_type="application/json")
    return web.json_response({
        "source": "Open-Meteo", "updated": data["current"].get("time"),
        "lat": lat, "lon": lon, "current": data["current"],
        "hourly": {k: v[:24] for k, v in (data.get("hourly") or {}).items()
                   if isinstance(v, list)},
        "daily": data.get("daily", {}),
    })


async def flights(request: web.Request) -> web.Response:
    lat, lon = point(request)
    distance = int(coordinate(request.query.get("dist"), 10, 250, 90))
    key = f"flights:{round(lat,1)}:{round(lon,1)}:{distance}"
    url = f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{distance}"
    data = await _upstream(url, key=key, ttl=30)
    aircraft = []
    for ac in (data.get("ac") or [])[:120]:
        if not isinstance(ac, dict):
            continue
        try:
            plane_lat, plane_lon = float(ac["lat"]), float(ac["lon"])
            if not all(map(math.isfinite, (plane_lat, plane_lon))):
                continue
        except (TypeError, KeyError, ValueError):
            continue
        aircraft.append({
            "lat": plane_lat, "lon": plane_lon,
            "flight": str(ac.get("flight") or ac.get("hex") or "Unknown").strip()[:24],
            "alt_ft": ac.get("alt_baro") if isinstance(ac.get("alt_baro"), (float, int)) else None,
            "speed_kt": ac.get("gs") if isinstance(ac.get("gs"), (float, int)) else None,
            "heading": ac.get("track") if isinstance(ac.get("track"), (float, int)) else None,
            "hex": str(ac.get("hex") or "")[:12],
        })
    return web.json_response({
        "source": "adsb.lol", "coverage": "reported_aircraft_only",
        "count": len(aircraft), "lat": lat, "lon": lon, "aircraft": aircraft,
        "retrieved_at": int(time.time()),
    })


async def earthquakes(request: web.Request) -> web.Response:
    data = await _upstream(
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
        key="usgs:2.5_day", ttl=300,
    )
    events = []
    for feature in (data.get("features") or [])[:200]:
        if not isinstance(feature, dict):
            continue
        prop, geo = feature.get("properties") or {}, feature.get("geometry") or {}
        coords = geo.get("coordinates") or []
        if len(coords) < 2:
            continue
        try:
            lon, lat = float(coords[0]), float(coords[1])
            mag = float(prop.get("mag") or 0)
            if not all(map(math.isfinite, (lon, lat, mag))):
                continue
        except (TypeError, ValueError):
            continue
        events.append({
            "lat": lat, "lon": lon, "magnitude": round(mag, 1),
            "place": str(prop.get("place") or "Unknown")[:180],
            "time": prop.get("time"),
            "url": str(prop.get("url") or "")[:300],
        })
    return web.json_response({"source": "USGS", "events": events, "count": len(events)})


async def air_quality(request: web.Request) -> web.Response:
    lat, lon = point(request)
    key = f"air:{round(lat,2)}:{round(lon,2)}"
    data = await _upstream(
        "https://air-quality-api.open-meteo.com/v1/air-quality?latitude="
        + str(lat) + "&longitude=" + str(lon)
        + "&current=us_aqi,pm2_5,pm10,ozone,dust,uv_index&timezone=auto",
        key=key, ttl=900,
    )
    if not isinstance(data.get("current"), dict):
        raise web.HTTPBadGateway(text='{"error":"air_quality_data_missing"}',
                                 content_type="application/json")
    return web.json_response({
        "source": "Open-Meteo Air Quality",
        "lat": lat, "lon": lon, "current": data["current"],
        "updated": data["current"].get("time"),
    })


async def search(request: web.Request) -> web.Response:
    from urllib.parse import urlencode
    query = (request.query.get("q") or "").strip()
    if len(query) < 3 or len(query) > 100:
        raise web.HTTPBadRequest(text='{"error":"query_length_3_to_100"}',
                                 content_type="application/json")
    # Geocoding uses rate-limited community Photon, never guesses an address.
    import re
    query = re.sub(r"[\x00-\x1f]+", " ", query)
    data = await _upstream("https://photon.komoot.io/api/?" + urlencode({"q": query, "limit": 5}),
                           key="search:" + query.casefold(), ttl=3600)
    hits = []
    for item in (data.get("features") or [])[:5]:
        prop, coord = item.get("properties") or {}, (item.get("geometry") or {}).get("coordinates") or []
        if len(coord) != 2:
            continue
        try:
            lon, lat = float(coord[0]), float(coord[1])
            if not all(map(math.isfinite, (lon, lat))):
                continue
        except (TypeError, ValueError):
            continue
        label = ", ".join(str(prop.get(k)) for k in ("name", "city", "state", "country")
                          if prop.get(k))
        hits.append({"lat": lat, "lon": lon, "label": label[:160]})
    return web.json_response({"source": "Photon/OSM", "results": hits})


def add_world_routes(app: web.Application) -> None:
    app.router.add_get("/api/world/weather", weather)
    app.router.add_get("/api/world/flights", flights)
    app.router.add_get("/api/world/earthquakes", earthquakes)
    app.router.add_get("/api/world/search", search)
    app.router.add_get("/api/world/air-quality", air_quality)

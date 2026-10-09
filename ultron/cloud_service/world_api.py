"""ULTRON WORLD public read-only map data adapters.

Never proxy arbitrary URLs. Upstream failures are shown as unavailable, not
silently replaced by fabricated aircraft, weather, or earthquake markers.
In-memory bounded TTL cache limits requests to community services. For a
high-traffic service, use a paid/self-hosted provider rather than scraping OSM.
"""
from __future__ import annotations

import asyncio
import math
import logging
from urllib.parse import urlsplit
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
                        logging.getLogger("ultron.world").warning("provider_status host=%s status=%s",urlsplit(url).hostname,response.status)
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
        except Exception as exc:
            logging.getLogger("ultron.world").warning("provider_exception host=%s type=%s",urlsplit(url).hostname,type(exc).__name__)
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


def _met_weather(data: dict[str, Any], lat: float, lon: float) -> dict[str, Any]:
    """Normalize Norwegian Meteorological Institute forecasts, without
    substituting invented observations or unprovided UV/rain percentages."""
    slots = (data.get("properties") or {}).get("timeseries") or []
    if not slots or not isinstance(slots[0], dict):
        raise web.HTTPBadGateway(text='{"error":"weather_data_missing"}',
                                 content_type="application/json")
    slot = slots[0]
    current = ((slot.get("data") or {}).get("instant") or {}).get("details") or {}
    period = ((slot.get("data") or {}).get("next_1_hours") or {}).get("details") or {}
    if current.get("air_temperature") is None:
        raise web.HTTPBadGateway(text='{"error":"weather_data_missing"}',
                                 content_type="application/json")
    wind = current.get("wind_speed")
    if isinstance(wind, (float, int)) and math.isfinite(wind):
        wind = round(wind * 3.6, 1)  # met.no m/s -> display km/h
    else:
        wind = None
    precipitation = period.get("precipitation_amount")  # *Forecast* for next hour.
    hourly = {"temperature_2m": [
        ((s.get("data") or {}).get("instant") or {}).get("details", {}).get("air_temperature")
        for s in slots[:24]
    ]}
    return {
        "source": "MET Norway",
        "updated": slot.get("time"),
        "lat": lat, "lon": lon,
        "forecast_not_observation": True,
        "precipitation_period": "next_1_hour_forecast",
        "current": {
            "temperature_2m": current.get("air_temperature"),
            "apparent_temperature": None,
            "relative_humidity_2m": current.get("relative_humidity"),
            "precipitation": precipitation,
            "rain": None,
            "weather_code": None,
            "cloud_cover": current.get("cloud_area_fraction"),
            "wind_speed_10m": wind,
            "wind_direction_10m": current.get("wind_from_direction"),
            "surface_pressure": current.get("air_pressure_at_sea_level"),
        },
        "hourly": hourly,
        "daily": {},
    }


async def weather(request: web.Request) -> web.Response:
    lat, lon = point(request)
    key = f"weather:{round(lat,2)}:{round(lon,2)}"
    # Cache the *normalized* fallback to avoid hammering an upstream that has
    # rate-limited Render's shared outbound IP (observed HTTP 429 in production).
    fallback = _CACHE.get("normalized:"+key)
    if fallback and fallback[0] > time.monotonic():
        return web.json_response(fallback[1])

    url = (
        "https://api.open-meteo.com/v1/forecast?latitude=" + str(lat)
        + "&longitude=" + str(lon)
        + "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
          "precipitation,rain,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,"
          "surface_pressure"
        + "&hourly=temperature_2m,precipitation_probability,wind_speed_10m"
        + "&daily=sunrise,sunset,uv_index_max&timezone=auto&forecast_days=2"
    )
    try:
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
    except web.HTTPBadGateway:
        logging.getLogger("ultron.world").warning(
            "weather_fallback provider=MET Norway reason=Open-Meteo-unavailable"
        )
        met_url = (
            "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat="
            + str(lat) + "&lon=" + str(lon)
        )
        met_data = await _upstream(met_url, key="met:"+key, ttl=600)
        normalized = _met_weather(met_data, lat, lon)
        _CACHE["normalized:"+key] = (time.monotonic() + 600, normalized)
        return web.json_response(normalized)


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

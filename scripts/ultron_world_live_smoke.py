"""Read-only, public HTTP smoke checks against the deployed ULTRON WORLD service.

No credentials, files, approval bypass, or fake-success fixtures. Third-party
rate limits are reported as a WARN instead of silently inventing live data.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "https://ultron-yubh.onrender.com"
TIMEOUT = 18


def get(path: str):
    try:
        with urllib.request.urlopen(
            urllib.request.Request(BASE + path, headers={
                "User-Agent": "ULTRON-World-Smoke/1.0 (GitHub public release verification)"
            }), timeout=TIMEOUT,
        ) as response:
            body = response.read(2_000_000)
            return response.status, body
    except urllib.error.HTTPError as err:
        return err.code, err.read(4096)


def checked_json(name: str, path: str, expected: str, required: str):
    status, raw = get(path)
    if status != 200:
        print(f"WARN {name}: HTTP {status}; live provider unavailable")
        return False
    payload = json.loads(raw)
    if payload.get("source") != expected or not isinstance(payload.get(required), (dict, list)):
        raise AssertionError(f"{name}: unexpected or missing real source structure")
    print(f"PASS {name}: {payload['source']}, verified live response structure")
    return True


def main():
    # A Render auto deployment commonly starts after the GitHub push and can
    # take 1-2 minutes. Poll the actual published WORLD asset, not GitHub HEAD.
    for attempt in range(20):
        try:
            status, body = get("/static/world.js")
            if status == 200 and b"air-quality" in body and b"api/world" in body:
                break
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        print(f"Waiting for WORLD asset to be deployed ({attempt + 1}/20)")
        time.sleep(12)
    else:
        raise AssertionError("The expected ULTRON WORLD asset is not live after 4 minutes")

    status, html = get("/static/world.html")
    assert status == 200 and b"id=\"map\"" in html and b"id=\"airQuality\"" in html
    print("PASS WORLD page: real 2D map and data layers served by Render")

    weather = checked_json(
        "weather", "/api/world/weather?lat=35.13&lon=33.43",
        "Open-Meteo", "current",
    )
    if not weather:
        direct_url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=35.13&longitude=33.43"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,rain,weather_code,cloud_cover,wind_speed_10m,"
            "wind_direction_10m,surface_pressure"
            "&hourly=temperature_2m,precipitation_probability,wind_speed_10m"
            "&daily=sunrise,sunset,uv_index_max&timezone=auto&forecast_days=2"
        )
        try:
            with urllib.request.urlopen(direct_url, timeout=12) as response:
                print("DIAGNOSTIC official Open-Meteo direct status", response.status,
                      response.read(250).decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            print("DIAGNOSTIC official Open-Meteo direct HTTP", exc.code,
                  exc.read(400).decode("utf-8", errors="replace"))
        except Exception as exc:
            print("DIAGNOSTIC official Open-Meteo direct error", type(exc).__name__)
    quake = checked_json(
        "earthquakes", "/api/world/earthquakes",
        "USGS", "events",
    )
    air = checked_json(
        "air quality", "/api/world/air-quality?lat=35.13&lon=33.43",
        "Open-Meteo Air Quality", "current",
    )
    flight = checked_json(
        "aircraft", "/api/world/flights?lat=35.13&lon=33.43&dist=90",
        "adsb.lol", "aircraft",
    )
    search = checked_json(
        "geocoding", "/api/world/search?q=Famagusta",
        "Photon/OSM", "results",
    )
    # A developer should know third-party provider failures, but Cloud routes
    # and WORLD UI must still be reachable and provide truthful error states.
    print("RESULTS", json.dumps({
        "weather": weather, "earthquakes": quake,
        "air_quality": air, "flights": flight, "search": search,
    }))
    if not weather or not quake:
        raise AssertionError("Core live weather or earthquakes unavailable")
    if not all((weather, quake, air, flight, search)):
        print("WARN some provider-sourced optional layers are temporarily unavailable")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL real production ULTRON WORLD smoke: {type(exc).__name__}: {exc}")
        sys.exit(1)

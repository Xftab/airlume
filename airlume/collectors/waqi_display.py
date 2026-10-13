"""WAQI live display ONLY.

WAQI's terms forbid archiving and data analysis.  Therefore:
- this module returns values for *immediate display* in the UI,
- it never writes to `data/`, the DuckDB store, or any file,
- nothing from here goes into the benchmark, evaluations or forecasts,
- the UI must show the WAQI attribution next to any value it displays.

A unit test (tests/test_waqi_isolation.py) checks that no other module
imports this one except the Streamlit app.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from airlume.config import load_settings

BASE = "https://api.waqi.info"
ATTRIBUTION = "Live value from the World Air Quality Index project (aqicn.org). Display only."


@dataclass(frozen=True)
class LiveValue:
    name: str
    aqi: int | None
    time_iso: str | None
    lat: float | None
    lon: float | None
    attribution: str = ATTRIBUTION


def live_station(waqi_id: str, session: requests.Session | None = None) -> LiveValue | None:
    token = load_settings().waqi_token
    if not token:
        return None
    s = session or requests.Session()
    r = s.get(f"{BASE}/feed/@{waqi_id}/", params={"token": token}, timeout=20)
    r.raise_for_status()
    payload = r.json()
    if payload.get("status") != "ok":
        return None
    d = payload["data"]
    geo = (d.get("city") or {}).get("geo") or [None, None]
    aqi = d.get("aqi")
    return LiveValue(
        name=(d.get("city") or {}).get("name", ""),
        aqi=int(aqi) if isinstance(aqi, (int, float)) else None,
        time_iso=(d.get("time") or {}).get("iso"),
        lat=geo[0],
        lon=geo[1],
    )

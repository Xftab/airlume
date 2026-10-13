"""Open-Meteo air-quality API (CC BY 4.0; 10,000 calls/day; CAMS ~45 km).

Used for validation (contribution C4) and as the only source for cities where
nothing else exists.  Phase 0: a thin, tested wrapper.  No key needed.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import requests

ENDPOINT = "https://air-quality-api.open-meteo.com/v1/air-quality"


def fetch_hourly(lat: float, lon: float, past_days: int = 2, forecast_days: int = 1,
                 session: requests.Session | None = None, timeout: int = 30) -> pd.DataFrame:
    s = session or requests.Session()
    r = s.get(
        ENDPOINT,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "pm2_5,pm10,us_aqi",
            "past_days": past_days,
            "forecast_days": forecast_days,
            "timezone": "UTC",
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return parse_hourly(r.json())


def parse_hourly(payload: dict) -> pd.DataFrame:
    h = payload["hourly"]
    df = pd.DataFrame({
        "ts": [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in h["time"]],
        "pm25": h.get("pm2_5"),
        "pm10": h.get("pm10"),
        "aqi": h.get("us_aqi"),
    })
    df["source"] = "open_meteo_cams"
    return df

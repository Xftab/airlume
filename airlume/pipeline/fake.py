"""Deterministic fake data for Phase 0.

Lets the 3D shell, the schema and the tests run before any real collector
exists.  Shapes mimic what Punjab EPA publishes: hourly PM2.5/PM10 per station
with a night-time peak and a smog-season bump.  Seeded, so tests are stable.

The fake data is clearly labelled `source='fake'` and is never mixed with real
rows (different primary key).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from airlume.aqi import aqi_from_concentrations
from airlume.pipeline.registry import Registry

# Rough relative pollution level per Lahore station (industrial/traffic sites higher).
_STATION_FACTOR = {
    "LHR-MR": 1.35,
    "LHR-GT": 1.25,
    "LHR-SHD": 1.20,
    "LHR-SP": 1.10,
    "LHR-KN": 1.05,
    "LHR-BR": 1.00,
    "LHR-EG": 0.95,
    "LHR-GB3": 0.95,
    "LHR-PU": 0.90,
    "LHR-DHA6": 0.85,
    "LHR-WB": 0.60,
}


def _base_pm25(ts: datetime) -> float:
    """Season (Oct-Jan high) x diurnal (night high) curve, in ug/m3."""
    doy = ts.timetuple().tm_yday
    # Peak around mid-November (day ~320), trough around July.
    season = 60 + 90 * (0.5 + 0.5 * np.cos(2 * np.pi * (doy - 320) / 365))
    hour = ts.hour
    diurnal = 1.0 + 0.45 * np.cos(2 * np.pi * (hour - 2) / 24)  # max ~2 am
    return float(season * diurnal)


def fake_readings(registry: Registry, hours: int = 24 * 14, end: datetime | None = None,
                  seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = end or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    stamps = [end - timedelta(hours=h) for h in range(hours)][::-1]
    rows = []
    for s in registry.stations_in("PB-LHE"):
        factor = _STATION_FACTOR.get(s.station_id, 1.0)
        drift = rng.normal(0, 0.08)
        for ts in stamps:
            pm25 = max(5.0, _base_pm25(ts) * factor * (1 + drift) * rng.lognormal(0, 0.12))
            pm10 = pm25 * rng.uniform(1.3, 1.9)
            aqi, _ = aqi_from_concentrations(pm25, pm10)
            rows.append(
                {
                    "station_id": s.station_id,
                    "ts": ts,
                    "pm25": round(pm25, 1),
                    "pm10": round(pm10, 1),
                    "aqi": aqi,
                    "aqi_computed": aqi,
                    "source": "fake",
                }
            )
    df = pd.DataFrame(rows)
    # Simulate one station silently dropping out for the last 3 hours (W2: missing data).
    mask = (df.station_id == "LHR-GB3") & (df.ts > end - timedelta(hours=3))
    return df[~mask].reset_index(drop=True)


def fake_city_hourly(registry: Registry, readings: pd.DataFrame, hours: int = 24 * 14,
                     end: datetime | None = None, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = end or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    stamps = [end - timedelta(hours=h) for h in range(hours)][::-1]
    rows = []
    # Lahore: mean of its stations.
    if not readings.empty:
        g = readings.groupby("ts").agg(pm25=("pm25", "mean"), pm10=("pm10", "mean"),
                                       n_stations=("station_id", "count")).reset_index()
        for r in g.itertuples(index=False):
            aqi, _ = aqi_from_concentrations(r.pm25, r.pm10)
            rows.append({"city_id": "PB-LHE", "ts": r.ts, "pm25": round(r.pm25, 1),
                         "pm10": round(r.pm10, 1), "aqi": aqi,
                         "n_stations": int(r.n_stations), "source": "fake"})
    # Other cities: scaled curve; southern Punjab lower, big cities higher.
    for c in registry.cities:
        if c.city_id == "PB-LHE":
            continue
        factor = 0.55 + 0.5 * rng.random()
        if c.name in {"Faisalabad", "Multan", "Gujranwala", "Sheikhupura", "Kasur", "Okara"}:
            factor += 0.25
        for ts in stamps:
            pm25 = max(5.0, _base_pm25(ts) * factor * rng.lognormal(0, 0.1))
            pm10 = pm25 * rng.uniform(1.3, 1.9)
            aqi, _ = aqi_from_concentrations(pm25, pm10)
            rows.append({"city_id": c.city_id, "ts": ts, "pm25": round(pm25, 1),
                         "pm10": round(pm10, 1), "aqi": aqi, "n_stations": 1,
                         "source": "fake"})
    return pd.DataFrame(rows)

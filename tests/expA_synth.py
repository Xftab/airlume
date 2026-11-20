"""Synthetic archive frames for the Experiment A tests: small, fixed and checkable by hand.

now = 20 Nov 2026 12:00 Asia/Karachi (07:00 UTC). Local times below.

Stations (Lahore), hourly from 10 Nov 00:00 to 20 Nov 11:00:
- GT Road: AQI 200 + 2 x hour of day (00:00 -> 200, 23:00 -> 246); PM2.5 100 + hour; PM10 150 + hour.
- Kahna Nau: AQI 310, except 19 Nov 00:00 to 06:00 (seven hours) at 150. Its rows stop at
  20 Nov 06:00, so at 12:00 its latest reading is six hours old (stale).
- Safari Park: AQI 150, PM2.5 60.
- Every other Lahore station: no rows.
Cities, same hours:
- Lahore (Punjab EPA): AQI 230, last hour (20 Nov 11:00) 240; PM2.5 120; PM10 200.
- Lahore (CAMS model rows, as the app also stores): AQI 500. Never a measurement.
- Multan: AQI 180, no PM. Bahawalpur: AQI 170. Faisalabad: AQI 260, rows stop at 19 Nov 23:00.
Forecasts for Lahore: EPA Punjab issues at 10:00 and 11:00; the 11:00 issue gives AQI 250 for
12:00 to 23:00 and 270 for 00:00 to 11:00 the next day (mean 260). A CAMS issue at 11:00: 300.
"""
from __future__ import annotations

import pandas as pd

CUTOFF = "2026-11-20T12:00:00+05:00"
NOW_LOCAL = "2026-11-20 12:00:00"
TZ = "Asia/Karachi"


def _hours(start_local: str, end_local: str) -> pd.DatetimeIndex:
    """Local hours [start, end] -> UTC timestamps."""
    return pd.date_range(start_local, end_local, freq="h", tz=TZ).tz_convert("UTC")


def frames() -> dict[str, pd.DataFrame]:
    rows = []
    for ts in _hours("2026-11-10 00:00", "2026-11-20 11:00"):
        h = ts.tz_convert(TZ).hour
        rows.append({"station_id": "LHR-GT", "ts": ts, "pm25": 100.0 + h, "pm10": 150.0 + h, "aqi": 200 + 2 * h})
        rows.append({"station_id": "LHR-SP", "ts": ts, "pm25": 60.0, "pm10": 90.0, "aqi": 150})
    for ts in _hours("2026-11-10 00:00", "2026-11-20 06:00"):
        local = ts.tz_convert(TZ)
        low = local.date() == pd.Timestamp("2026-11-19").date() and local.hour <= 6
        rows.append({"station_id": "LHR-KN", "ts": ts, "pm25": 200.0, "pm10": 300.0, "aqi": 150 if low else 310})
    readings = pd.DataFrame(rows)
    readings["aqi_computed"] = readings["aqi"]
    readings["source"] = "punjab_epa"

    city = []
    for ts in _hours("2026-11-10 00:00", "2026-11-20 11:00"):
        last = ts.tz_convert(TZ) == pd.Timestamp("2026-11-20 11:00", tz=TZ)
        city.append({"city_id": "PB-LHE", "ts": ts, "pm25": 120.0, "pm10": 200.0, "aqi": 240 if last else 230,
                     "n_stations": 3, "source": "punjab_epa"})
        city.append({"city_id": "PB-LHE", "ts": ts, "pm25": None, "pm10": None, "aqi": 500,
                     "n_stations": None, "source": "open_meteo_cams"})
        city.append({"city_id": "PB-MUX", "ts": ts, "pm25": None, "pm10": None, "aqi": 180, "n_stations": 1,
                     "source": "punjab_epa"})
        city.append({"city_id": "PB-BWP", "ts": ts, "pm25": None, "pm10": None, "aqi": 170, "n_stations": 1,
                     "source": "punjab_epa"})
    for ts in _hours("2026-11-10 00:00", "2026-11-19 23:00"):
        city.append({"city_id": "PB-FSD", "ts": ts, "pm25": None, "pm10": None, "aqi": 260, "n_stations": 1,
                     "source": "punjab_epa"})
    city_hourly = pd.DataFrame(city)

    fc = []
    for issued in ("2026-11-20 10:00", "2026-11-20 11:00"):
        iss = pd.Timestamp(issued, tz=TZ)
        for k in range(1, 25):
            tgt = iss + pd.Timedelta(hours=k)
            aqi = 250 if tgt.date() == iss.date() else 270
            fc.append({"city_id": "PB-LHE", "issued_at": iss.tz_convert("UTC"), "target_ts": tgt.tz_convert("UTC"),
                       "aqi": aqi if issued.endswith("11:00") else 999, "source": "punjab_epa_forecast"})
    iss = pd.Timestamp("2026-11-20 11:00", tz=TZ)
    for k in range(1, 25):
        fc.append({"city_id": "PB-LHE", "issued_at": iss.tz_convert("UTC"),
                   "target_ts": (iss + pd.Timedelta(hours=k)).tz_convert("UTC"), "aqi": 300,
                   "source": "open_meteo_cams_forecast"})
    forecasts = pd.DataFrame(fc)
    return {"readings": readings, "city_hourly": city_hourly, "forecasts": forecasts}

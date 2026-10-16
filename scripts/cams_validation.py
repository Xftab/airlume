"""CAMS against the ground stations (plan 4.3, contribution C4).

    python scripts/cams_validation.py

Reads the CSV archive (station readings and the Open-Meteo CAMS series for Lahore)
and prints agreement -- mean absolute difference, signed bias (CAMS minus
station) and correlation -- for PM2.5, PM10 and PM-only AQI on the portal's own
scale, per station, by hour of day, for the city mean, and at time lags.

Framed as agreement, not error: neither side is treated as the truth. See
`airlume/validation.py` for the method and `docs/research/cams-validation.md` for
the results.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from airlume import validation as v  # noqa: E402
from airlume.pipeline import archive  # noqa: E402

PAIRS = (("pm25", "cams_pm25", "PM2.5 ug/m3"),
         ("pm10", "cams_pm10", "PM10 ug/m3"),
         ("aqi_pm_station", "aqi_pm_cams", "AQI, PM only, portal scale"))


def _ci(t):
    return f"[{t[0]:6.1f}, {t[1]:6.1f}]" if t else "   (too few hours)  "


def main() -> int:
    r = archive.load_all("readings")
    r = r[r["source"] == "punjab_epa"]
    c = archive.load_all("city_hourly")
    c = c[(c["source"] == "open_meteo_cams") & (c["city_id"] == "PB-LHE")]
    if r.empty or c.empty:
        print("need both station readings and the CAMS series in the archive")
        return 1
    m = v.pair(r, c)
    cm = v.city_mean(m)
    span = f"{m['ts'].min():%Y-%m-%d %H:%MZ} to {m['ts'].max():%Y-%m-%d %H:%MZ}"
    print(f"CAMS vs ground, Lahore -- {len(m)} station-hours, {m['ts'].nunique()} hours, {span}")
    print("Agreement, not error. Bias = CAMS minus station. 95% CI: 6-hour block bootstrap.\n")

    for label, frame in (("City mean (CAMS vs average of reporting stations)", cm),
                         ("Every station-hour", m)):
        print(f"== {label} ==")
        for obs, mod, unit in PAIRS:
            a = v.agreement(frame, obs, mod)
            if a is None:
                continue
            r_txt = f"{a.r:5.2f}" if a.r is not None else "  n/a"
            print(f"  {unit:28s} n={a.n:4d}  MAD {a.mad:6.1f} {_ci(a.mad_ci)}  "
                  f"bias {a.bias:+6.1f} {_ci(a.bias_ci)}  r {r_txt}")
        print()

    print("== By station, PM2.5 (sorted by agreement) ==")
    print(v.by_station(m, "pm25", "cams_pm25").round(2).to_string(index=False))

    print("\n== By hour of day (PKT), city-mean PM2.5 ==")
    h = v.by_hour_of_day(cm, "pm25", "cams_pm25")
    day = h[h["hour_pkt"].between(10, 19)]
    night = h[~h["hour_pkt"].between(10, 19)]
    print(f"  10:00-19:00 PKT  bias {day['bias'].mean():+6.1f}  over {int(day['n'].sum())} hours")
    print(f"  20:00-09:00 PKT  bias {night['bias'].mean():+6.1f}  over {int(night['n'].sum())} hours")

    print("\n== Time alignment: correlation with CAMS shifted by h hours (city-mean PM2.5) ==")
    cams_ts = pd.to_datetime(c["ts"], utc=True)
    for lag in range(-3, 4):
        cc = c.assign(ts=cams_ts + pd.Timedelta(hours=lag))
        a = v.agreement(v.city_mean(v.pair(r, cc)), "pm25", "cams_pm25", reps=1)
        if a is not None and a.r is not None:
            print(f"  {lag:+d}h  r {a.r:5.2f}  bias {a.bias:+6.1f}  n {a.n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

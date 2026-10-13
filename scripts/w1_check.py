"""W1 harmonisation check: which averaging window reproduces the portal's AQI?

Needs at least 8 hours of stored Punjab EPA readings.  For each station-hour it
recomputes the AQI from (a) the latest hour, (b) the trailing 8-hour mean,
(c) the trailing 24-hour mean of every pollutant, and reports the mean absolute
error against the AQI the portal published.  Run:  python scripts/w1_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from airlume.aqi import aqi_from_concentrations
from airlume.pipeline.store import Store

POLS = ["pm25", "pm10", "o3", "no2", "so2", "co"]

store = Store(read_only=True)
df = store.con.execute(
    "SELECT station_id, ts, pm25, pm10, o3, no2, so2, co, aqi FROM readings "
    "WHERE source = 'punjab_epa' AND aqi IS NOT NULL ORDER BY station_id, ts"
).df()
if len(df) < 8:
    sys.exit(f"only {len(df)} rows; collect for at least 8 hours first")

out = []
for sid, g in df.groupby("station_id"):
    g = g.set_index("ts").sort_index()
    for window in (1, 8, 24):
        m = g[POLS].rolling(f"{window}h", min_periods=max(1, window // 2)).mean()
        for ts, row in m.iterrows():
            a, dom = aqi_from_concentrations(row.pm25, row.pm10, o3=row.o3, no2=row.no2, so2=row.so2, co=row.co)
            if a is not None:
                out.append({"station_id": sid, "ts": ts, "window_h": window, "ours": a,
                            "portal": g.loc[ts, "aqi"], "dominant": dom})
r = pd.DataFrame(out)
r["abs_err"] = (r.ours - r.portal).abs()
print(r.groupby("window_h").abs_err.agg(["mean", "median", "max", "count"]).round(1))
print("\nworst 10 station-hours (8-h window):")
print(r[r.window_h == 8].sort_values("abs_err", ascending=False).head(10).to_string(index=False))

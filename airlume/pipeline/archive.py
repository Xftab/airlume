"""Plain-text archive of collected readings, safe to commit to git.

The DuckDB file is a local cache and is git-ignored.  The source of truth that
GitHub Actions commits every hour is a set of small CSV files, one per source
per month, so that git diffs are line appends and never binary conflicts:

    data/archive/readings/punjab_epa/2026-10.csv
    data/archive/city_hourly/punjab_epa/2026-10.csv

`export_month` appends only rows the file does not already hold (keyed on
station/city + ts).  `load_all` rebuilds the DuckDB cache from the archive, so
a fresh clone or a Streamlit Cloud deploy starts with the full history.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from airlume.config import ROOT

ARCHIVE = ROOT / "data" / "archive"

KEYS = {
    "readings": ["station_id", "ts", "source"],
    "city_hourly": ["city_id", "ts", "source"],
    "epd_daily": ["date", "station_label", "pollutant", "source"],
    "forecasts": ["city_id", "issued_at", "target_ts", "source"],
}
COLS = {
    # The snapshot columns are appended, never inserted, so every existing CSV stays
    # readable and its column order unchanged; rows written before 15 Oct 2026 read
    # back blank in them. See docs/research/portal-snapshot.md.
    "readings": ["station_id", "ts", "pm25", "pm10", "co", "so2", "no2", "o3", "aqi", "aqi_computed", "source",
                 "portal_station_id", "portal_dominant", "lat", "lon",
                 "temperature", "humidity", "wind_speed", "wind_direction"],
    "city_hourly": ["city_id", "ts", "pm25", "pm10", "aqi", "n_stations", "source"],
    "epd_daily": ["date", "station_label", "station_id", "city", "pollutant", "conc", "aqi", "style", "source"],
    "forecasts": ["city_id", "issued_at", "target_ts", "aqi", "source"],
}
TIME_COL = {"readings": "ts", "city_hourly": "ts", "epd_daily": "date", "forecasts": "issued_at"}
EXTRA_TS = {"forecasts": ["target_ts"]}


def _path(table: str, source: str, month: str) -> Path:
    return ARCHIVE / table / source / f"{month}.csv"


def export(table: str, df: pd.DataFrame) -> list[Path]:
    """Append new rows of `df` into the month files. Returns the files touched."""
    if df.empty:
        return []
    df = df.copy()
    for c in COLS[table]:
        if c not in df.columns:
            df[c] = None
    df = df[COLS[table]]
    tcol = TIME_COL[table]
    df[tcol] = pd.to_datetime(df[tcol], utc=(tcol != "date"))
    for c in EXTRA_TS.get(table, []):
        df[c] = pd.to_datetime(df[c], utc=True)
    touched: list[Path] = []
    bucket = df[tcol].dt.strftime("%Y-%m") if tcol != "date" else df[tcol].dt.strftime("%Y")
    for (source, month), part in df.groupby([df["source"], bucket]):
        p = _path(table, source, month)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            old = pd.read_csv(p)
            old[tcol] = pd.to_datetime(old[tcol], utc=(tcol != "date"))
            for c in EXTRA_TS.get(table, []):
                old[c] = pd.to_datetime(old[c], utc=True)
            merged = pd.concat([old, part], ignore_index=True)
        else:
            merged = part
        merged = merged.drop_duplicates(subset=KEYS[table], keep="last").sort_values(KEYS[table])
        if tcol == "date":
            merged[tcol] = merged[tcol].dt.strftime("%Y-%m-%d")
        merged.to_csv(p, index=False, date_format="%Y-%m-%dT%H:%M:%SZ", lineterminator="\n")
        touched.append(p)
    return touched


def load_all(table: str) -> pd.DataFrame:
    files = sorted((ARCHIVE / table).rglob("*.csv")) if (ARCHIVE / table).exists() else []
    if not files:
        return pd.DataFrame(columns=COLS[table])
    frames = []
    tcol = TIME_COL[table]
    for f in files:
        d = pd.read_csv(f)
        d[tcol] = pd.to_datetime(d[tcol], utc=(tcol != "date"))
        for c in EXTRA_TS.get(table, []):
            d[c] = pd.to_datetime(d[c], utc=True)
        if tcol == "date":
            d[tcol] = d[tcol].dt.date
        frames.append(d)
    return pd.concat(frames, ignore_index=True)

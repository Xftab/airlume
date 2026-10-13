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

KEYS = {"readings": ["station_id", "ts", "source"], "city_hourly": ["city_id", "ts", "source"]}
COLS = {
    "readings": ["station_id", "ts", "pm25", "pm10", "aqi", "aqi_computed", "source"],
    "city_hourly": ["city_id", "ts", "pm25", "pm10", "aqi", "n_stations", "source"],
}


def _path(table: str, source: str, month: str) -> Path:
    return ARCHIVE / table / source / f"{month}.csv"


def export(table: str, df: pd.DataFrame) -> list[Path]:
    """Append new rows of `df` into the month files. Returns the files touched."""
    if df.empty:
        return []
    df = df[COLS[table]].copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    touched: list[Path] = []
    for (source, month), part in df.groupby([df["source"], df["ts"].dt.strftime("%Y-%m")]):
        p = _path(table, source, month)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            old = pd.read_csv(p, parse_dates=["ts"])
            old["ts"] = pd.to_datetime(old["ts"], utc=True)
            merged = pd.concat([old, part], ignore_index=True)
        else:
            merged = part
        merged = merged.drop_duplicates(subset=KEYS[table], keep="last").sort_values(KEYS[table])
        merged.to_csv(p, index=False, date_format="%Y-%m-%dT%H:%M:%SZ", lineterminator="\n")
        touched.append(p)
    return touched


def load_all(table: str) -> pd.DataFrame:
    files = sorted((ARCHIVE / table).rglob("*.csv")) if (ARCHIVE / table).exists() else []
    if not files:
        return pd.DataFrame(columns=COLS[table])
    frames = []
    for f in files:
        d = pd.read_csv(f)
        d["ts"] = pd.to_datetime(d["ts"], utc=True)
        frames.append(d)
    return pd.concat(frames, ignore_index=True)

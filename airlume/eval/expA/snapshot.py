"""Freeze the archive for Experiment A, and make the shifted copy for the invented-number test.

Every arm answers from the same frozen data, so gold answers cannot drift while the
runs take days under the free-tier budget. A snapshot holds:

- ``raw/<table>.csv``        archive rows before the cutoff (readings, city_hourly,
                              forecasts), the columns the app's Store loads
- ``tables/<table>.csv``     the analysis tables the code and SQL arms see:
                              stations, cities, areas, station_hourly, city_hourly, forecast
- ``analysis.duckdb``        the same analysis tables, for the SQL arm (opened read-only)
- ``manifest.json``          cutoff, row counts and SHA-256 of every file

The shifted copy (``<snapshot>/shifted``) adds a constant to every AQI, PM2.5 and
PM10 value. A number in an answer that is computed from the data moves when the data
moves; a number the model wrote into its code or query does not. That is the
invented-number test (protocol, section 6).

Snapshots hold raw EPA data and stay out of git (``data/eval/expA/snapshots``);
only the manifest is tracked.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pandas as pd

from airlume import __version__
from airlume.config import ROOT, TZ
from airlume.pipeline import archive
from airlume.pipeline.registry import KNOWN_AREAS, Registry

SNAP_ROOT = ROOT / "data" / "eval" / "expA" / "snapshots"
MANIFEST_DIR = ROOT / "data" / "eval"
KARACHI = ZoneInfo(TZ)

# The shift for the invented-number test. Any constant works; these are large enough
# to move every rounded figure (AQI is shown as a whole number, PM to one decimal).
SHIFT = {"aqi": 7, "pm25": 5.0, "pm10": 5.0}

ANALYSIS_TABLES = ("stations", "cities", "areas", "station_hourly", "city_hourly", "forecast")
RAW_TABLES = ("readings", "city_hourly", "forecasts")

_FC_LABEL = {"punjab_epa_forecast": "EPA Punjab", "open_meteo_cams_forecast": "CAMS model"}


@dataclass(frozen=True)
class Snapshot:
    """Paths of one frozen snapshot (or of its shifted copy)."""

    root: Path

    @property
    def tables_dir(self) -> Path:
        return self.root / "tables"

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def duckdb_path(self) -> Path:
        return self.root / "analysis.duckdb"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    @property
    def shifted(self) -> "Snapshot":
        return Snapshot(self.root / "shifted")

    def manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def now(self) -> datetime:
        """The snapshot's 'now': the cutoff, in Asia/Karachi. Every arm is told this time."""
        return datetime.fromisoformat(self.manifest()["cutoff_utc"]).astimezone(KARACHI)

    def tables(self) -> dict[str, pd.DataFrame]:
        return load_tables(self.tables_dir)

    def raw(self) -> dict[str, pd.DataFrame]:
        out = {}
        for t in RAW_TABLES:
            df = pd.read_csv(self.raw_dir / f"{t}.csv")
            for c in ("ts", "issued_at", "target_ts"):
                if c in df.columns:
                    df[c] = pd.to_datetime(df[c], utc=True)
            out[t] = df
        return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _local_naive(ts: pd.Series) -> pd.Series:
    """UTC timestamps -> wall-clock time in Asia/Karachi without a zone (simplest for model code)."""
    return pd.to_datetime(ts, utc=True).dt.tz_convert(TZ).dt.tz_localize(None)


def raw_tables(cutoff_utc: pd.Timestamp, frames: dict[str, pd.DataFrame] | None = None) -> dict[str, pd.DataFrame]:
    """Archive rows strictly before the cutoff (from `frames` when given, else from data/archive)."""
    frames = frames or {t: archive.load_all(t) for t in RAW_TABLES}
    readings, city, fc = (frames[t].copy() for t in RAW_TABLES)
    readings["ts"] = pd.to_datetime(readings["ts"], utc=True)
    city["ts"] = pd.to_datetime(city["ts"], utc=True)
    fc["issued_at"] = pd.to_datetime(fc["issued_at"], utc=True)
    fc["target_ts"] = pd.to_datetime(fc["target_ts"], utc=True)
    return {
        "readings": readings[readings["ts"] < cutoff_utc].reset_index(drop=True),
        "city_hourly": city[city["ts"] < cutoff_utc].reset_index(drop=True),
        "forecasts": fc[fc["issued_at"] < cutoff_utc].reset_index(drop=True),
    }


def analysis_tables(raw: dict[str, pd.DataFrame], registry: Registry) -> dict[str, pd.DataFrame]:
    """The tables the code and SQL arms see: measured values only, names instead of ids, local time.

    Only the Punjab EPA's own measurements are included (CAMS city rows are a model,
    not a measurement), which is also what the form arm answers from.
    """
    stations = pd.DataFrame(
        [{"station_id": s.station_id, "station": s.name, "city": s.city, "lat": s.lat, "lon": s.lon}
         for s in registry.stations]
    )
    cities = pd.DataFrame(
        [{"city_id": c.city_id, "city": c.name, "province": c.province} for c in registry.cities]
    )
    # The neighbourhood centres the app uses for its nearest-station rule. Given to the
    # code and SQL arms too, so every arm has the same information (protocol, section 4).
    areas = pd.DataFrame(
        [{"area": name.title(), "lat": lat, "lon": lon, "city": "Lahore"} for name, (lat, lon) in KNOWN_AREAS.items()]
    )
    r = raw["readings"]
    r = r[r["source"] == "punjab_epa"]
    station_hourly = r.merge(stations[["station_id", "station", "city"]], on="station_id", how="inner")
    station_hourly = pd.DataFrame({
        "station": station_hourly["station"],
        "city": station_hourly["city"],
        "ts_local": _local_naive(station_hourly["ts"]),
        "pm25": pd.to_numeric(station_hourly["pm25"], errors="coerce"),
        "pm10": pd.to_numeric(station_hourly["pm10"], errors="coerce"),
        "aqi": pd.to_numeric(station_hourly["aqi"], errors="coerce"),
    }).sort_values(["station", "ts_local"]).reset_index(drop=True)

    c = raw["city_hourly"]
    c = c[c["source"] == "punjab_epa"]
    c = c.merge(cities[["city_id", "city"]], on="city_id", how="inner")
    city_hourly = pd.DataFrame({
        "city": c["city"],
        "ts_local": _local_naive(c["ts"]),
        "pm25": pd.to_numeric(c["pm25"], errors="coerce"),
        "pm10": pd.to_numeric(c["pm10"], errors="coerce"),
        "aqi": pd.to_numeric(c["aqi"], errors="coerce"),
    }).sort_values(["city", "ts_local"]).reset_index(drop=True)

    f = raw["forecasts"].merge(cities[["city_id", "city"]], on="city_id", how="inner")
    forecast = pd.DataFrame({
        "city": f["city"],
        "issued_local": _local_naive(f["issued_at"]),
        "target_local": _local_naive(f["target_ts"]),
        "aqi": pd.to_numeric(f["aqi"], errors="coerce"),
        "source": f["source"].map(_FC_LABEL).fillna(f["source"]),
    }).sort_values(["source", "issued_local", "target_local"]).reset_index(drop=True)

    return {
        "stations": stations[["station", "city", "lat", "lon"]],
        "cities": cities[["city", "province"]],
        "areas": areas,
        "station_hourly": station_hourly,
        "city_hourly": city_hourly,
        "forecast": forecast,
    }


def shift_values(df: pd.DataFrame) -> pd.DataFrame:
    """Add SHIFT to every measured value column present (AQI, PM2.5, PM10)."""
    out = df.copy()
    for col, d in SHIFT.items():
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce") + d
    return out


TIME_COLS = ("ts_local", "issued_local", "target_local")


def load_tables(tables_dir: Path) -> dict[str, pd.DataFrame]:
    out = {}
    for t in ANALYSIS_TABLES:
        df = pd.read_csv(tables_dir / f"{t}.csv")
        for c in TIME_COLS:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c])
        out[t] = df
    return out


def _write(snap: Snapshot, raw: dict[str, pd.DataFrame], tables: dict[str, pd.DataFrame]) -> dict:
    snap.raw_dir.mkdir(parents=True, exist_ok=True)
    snap.tables_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    counts: dict[str, int] = {}
    for t, df in raw.items():
        p = snap.raw_dir / f"{t}.csv"
        df.to_csv(p, index=False, date_format="%Y-%m-%dT%H:%M:%SZ", lineterminator="\n")
        files[f"raw/{t}.csv"] = _sha256(p)
        counts[f"raw/{t}"] = int(len(df))
    for t, df in tables.items():
        p = snap.tables_dir / f"{t}.csv"
        df.to_csv(p, index=False, date_format="%Y-%m-%d %H:%M:%S", lineterminator="\n")
        files[f"tables/{t}.csv"] = _sha256(p)
        counts[t] = int(len(df))
    if snap.duckdb_path.exists():
        snap.duckdb_path.unlink()
    con = duckdb.connect(str(snap.duckdb_path))
    try:
        for t, df in tables.items():
            con.register("incoming", df)
            con.execute(f"CREATE TABLE {t} AS SELECT * FROM incoming")  # t is from ANALYSIS_TABLES
            con.unregister("incoming")
    finally:
        con.close()
    return {"files": files, "rows": counts}


def freeze(cutoff: str, name: str | None = None, root: Path = SNAP_ROOT,
           registry: Registry | None = None, frames: dict[str, pd.DataFrame] | None = None) -> Snapshot:
    """Freeze the archive at `cutoff` (ISO time with zone, e.g. 2026-12-05T12:00:00+05:00).

    Writes the snapshot, its shifted copy and both manifests; refuses to overwrite an
    existing snapshot of the same name (a frozen snapshot is never rebuilt in place).
    `frames` replaces the archive (tests use synthetic data).
    """
    cutoff_ts = pd.Timestamp(cutoff)
    if cutoff_ts.tzinfo is None:
        raise ValueError("cutoff needs a time zone, e.g. 2026-12-05T12:00:00+05:00")
    cutoff_utc = cutoff_ts.tz_convert("UTC")
    name = name or f"snap-{cutoff_utc:%Y%m%dT%H%MZ}"
    snap = Snapshot(root / name)
    if snap.manifest_path.exists():
        raise FileExistsError(f"{snap.root} already exists; snapshots are frozen. Choose another name.")
    registry = registry or Registry.load()
    raw = raw_tables(cutoff_utc, frames)
    tables = analysis_tables(raw, registry)
    meta = _write(snap, raw, tables)
    shifted_meta = _write(snap.shifted, {t: shift_values(df) for t, df in raw.items()},
                          {t: shift_values(df) for t, df in tables.items()})
    manifest = {
        "name": name,
        "cutoff_utc": cutoff_utc.isoformat(),
        "cutoff_local": cutoff_utc.tz_convert(TZ).isoformat(),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "airlume_version": __version__,
        "shift": SHIFT,
        **meta,
        "shifted_files": shifted_meta["files"],
    }
    text = json.dumps(manifest, indent=2, sort_keys=True)
    snap.manifest_path.write_text(text, encoding="utf-8")
    snap.shifted.manifest_path.write_text(json.dumps({**manifest, "is_shifted_copy": True}, indent=2,
                                                     sort_keys=True), encoding="utf-8")
    return snap


def verify(snap: Snapshot) -> list[str]:
    """Problems found when the files no longer match the manifest. Empty list = intact."""
    m = snap.manifest()
    problems = []
    for rel, digest in m["files"].items():
        p = snap.root / rel
        if not p.exists():
            problems.append(f"missing {rel}")
        elif _sha256(p) != digest:
            problems.append(f"changed {rel}")
    for rel, digest in m.get("shifted_files", {}).items():
        p = snap.shifted.root / rel
        if not p.exists():
            problems.append(f"missing shifted/{rel}")
        elif _sha256(p) != digest:
            problems.append(f"changed shifted/{rel}")
    return problems


def snapshot_id(snap: Snapshot) -> str:
    """Short hash naming a snapshot in run and scorecard files."""
    m = snap.manifest()
    blob = json.dumps({"cutoff": m["cutoff_utc"], "files": m["files"]}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:10]

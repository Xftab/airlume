"""DuckDB storage.  All queries are parameterised; no string-built SQL from user input.

Tables
------
readings(station_id, ts, pm25, pm10, aqi, source, ingested_at)
    One row per station per hour.  `ts` is UTC.  AQI is the value the source
    reported (Punjab EPA computes its own); `aqi_computed` is ours.
city_hourly(city_id, ts, pm25, pm10, aqi, n_stations, source, ingested_at)
    One row per city per hour; for Lahore this is the mean of stations,
    for other cities it is the city-level value the source gives.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from airlume.config import load_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    station_id   VARCHAR NOT NULL,
    ts           TIMESTAMPTZ NOT NULL,
    pm25         DOUBLE,
    pm10         DOUBLE,
    co           DOUBLE,
    so2          DOUBLE,
    no2          DOUBLE,
    o3           DOUBLE,
    aqi          INTEGER,
    aqi_computed INTEGER,
    source       VARCHAR NOT NULL,
    -- From the portal's embedded snapshot (15 Oct 2026). Null for rows collected
    -- from the HTML table, which carries none of these.
    portal_station_id INTEGER,
    portal_dominant   VARCHAR,
    lat          DOUBLE,
    lon          DOUBLE,
    temperature  DOUBLE,
    humidity     DOUBLE,
    wind_speed   DOUBLE,
    wind_direction DOUBLE,
    ingested_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (station_id, ts, source)
);
CREATE TABLE IF NOT EXISTS epd_daily (
    date          DATE NOT NULL,
    station_label VARCHAR NOT NULL,
    station_id    VARCHAR,
    city          VARCHAR NOT NULL,
    pollutant     VARCHAR,
    conc          DOUBLE,
    aqi           INTEGER NOT NULL,
    style         VARCHAR NOT NULL,
    source        VARCHAR NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (date, station_label, pollutant, source)
);
CREATE TABLE IF NOT EXISTS forecasts (
    city_id      VARCHAR NOT NULL,
    issued_at    TIMESTAMPTZ NOT NULL,
    target_ts    TIMESTAMPTZ NOT NULL,
    aqi          INTEGER NOT NULL,
    source       VARCHAR NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (city_id, issued_at, target_ts, source)
);
CREATE TABLE IF NOT EXISTS city_hourly (
    city_id      VARCHAR NOT NULL,
    ts           TIMESTAMPTZ NOT NULL,
    pm25         DOUBLE,
    pm10         DOUBLE,
    aqi          INTEGER,
    n_stations   INTEGER,
    source       VARCHAR NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (city_id, ts, source)
);
"""

_ALLOWED_METRICS = {"aqi", "pm25", "pm10"}


def _prepare(df: pd.DataFrame, time_col: str, numeric: tuple[str, ...], ints: tuple[str, ...] = ()) -> pd.DataFrame:
    """Make column dtypes explicit so DuckDB's pandas scan never guesses
    (on Windows a tz-aware Python datetime scalar was read as DOUBLE)."""
    df = df.copy()
    # Timestamps travel as ISO text and are cast inside SQL: DuckDB's pandas scan on
    # Windows mis-typed tz-aware datetime columns as DOUBLE.
    if time_col == "ts":
        df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    else:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    for c in numeric:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    for c in ints:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in ("station_id", "city_id", "source", "station_label", "city", "pollutant", "style"):
        if c in df.columns:
            df[c] = df[c].astype(object).where(df[c].notna(), None).map(lambda v: None if v is None else str(v))
    return df
_ALLOWED_AGG = {"latest", "mean", "max", "min", "count_hours_above"}


class Store:
    def __init__(self, path: Path | str | None = None, read_only: bool = False):
        settings = load_settings()
        if path == ":memory:":
            self.path = Path(":memory:")
            self.con = duckdb.connect(":memory:")
        else:
            self.path = Path(path) if path else settings.db_path
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.con = duckdb.connect(str(self.path), read_only=read_only)
        if not read_only:
            self.con.execute(SCHEMA)
            for col in ("co", "so2", "no2", "o3"):  # migrate databases created before 13 Oct
                self.con.execute(f"ALTER TABLE readings ADD COLUMN IF NOT EXISTS {col} DOUBLE")
            # Migrate databases created before 15 Oct, when the portal's embedded
            # snapshot added these. CREATE TABLE IF NOT EXISTS leaves an existing
            # table alone, so without this the INSERT below fails on a stale cache
            # (the laptop's, or a Streamlit Cloud deploy's) rather than on a fresh one.
            for col, typ in (("portal_station_id", "INTEGER"), ("portal_dominant", "VARCHAR"),
                             ("lat", "DOUBLE"), ("lon", "DOUBLE"), ("temperature", "DOUBLE"),
                             ("humidity", "DOUBLE"), ("wind_speed", "DOUBLE"),
                             ("wind_direction", "DOUBLE")):
                self.con.execute(f"ALTER TABLE readings ADD COLUMN IF NOT EXISTS {col} {typ}")

    def close(self) -> None:
        self.con.close()

    # ---- writes -----------------------------------------------------------
    def upsert_readings(self, df: pd.DataFrame) -> int:
        """df columns: station_id, ts (tz-aware), pm25, pm10, [co, so2, no2, o3], aqi, aqi_computed, source."""
        if df.empty:
            return 0
        df = df.copy()
        extra = ("portal_station_id", "portal_dominant", "lat", "lon",
                 "temperature", "humidity", "wind_speed", "wind_direction")
        for col in ("co", "so2", "no2", "o3") + extra:
            if col not in df.columns:
                df[col] = None
        df = _prepare(
            df, "ts",
            ("pm25", "pm10", "co", "so2", "no2", "o3",
             "lat", "lon", "temperature", "humidity", "wind_speed", "wind_direction"),
            ("aqi", "aqi_computed", "portal_station_id"),
        )
        df["portal_dominant"] = df["portal_dominant"].astype("object").where(df["portal_dominant"].notna(), None)
        self.con.register("incoming", df)
        self.con.execute(
            """
            INSERT OR REPLACE INTO readings
                (station_id, ts, pm25, pm10, co, so2, no2, o3, aqi, aqi_computed, source,
                 portal_station_id, portal_dominant, lat, lon,
                 temperature, humidity, wind_speed, wind_direction, ingested_at)
            SELECT station_id, CAST(ts AS TIMESTAMPTZ), pm25, pm10, co, so2, no2, o3, aqi, aqi_computed, source,
                   portal_station_id, portal_dominant, lat, lon,
                   temperature, humidity, wind_speed, wind_direction, now()
            FROM incoming
            """
        )
        self.con.unregister("incoming")
        return len(df)

    def upsert_city_hourly(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        df = _prepare(df, "ts", ("pm25", "pm10"), ("aqi", "n_stations"))
        self.con.register("incoming", df)
        self.con.execute(
            """
            INSERT OR REPLACE INTO city_hourly
                (city_id, ts, pm25, pm10, aqi, n_stations, source, ingested_at)
            SELECT city_id, CAST(ts AS TIMESTAMPTZ), pm25, pm10, aqi, n_stations, source, now()
            FROM incoming
            """
        )
        self.con.unregister("incoming")
        return len(df)

    def upsert_epd_daily(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        df = _prepare(df, "date", ("conc",), ("aqi",))
        self.con.register("incoming", df)
        self.con.execute(
            """
            INSERT OR REPLACE INTO epd_daily
                (date, station_label, station_id, city, pollutant, conc, aqi, style, source, ingested_at)
            SELECT CAST(date AS DATE), station_label, station_id, city, pollutant, conc, aqi, style, source, now()
            FROM incoming
            """
        )
        self.con.unregister("incoming")
        return len(df)

    def upsert_forecasts(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        df = df.copy()
        for c in ("issued_at", "target_ts"):
            df[c] = pd.to_datetime(df[c], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        df["aqi"] = pd.to_numeric(df["aqi"]).astype("Int64")
        self.con.register("incoming", df)
        self.con.execute(
            """
            INSERT OR REPLACE INTO forecasts (city_id, issued_at, target_ts, aqi, source, ingested_at)
            SELECT city_id, CAST(issued_at AS TIMESTAMPTZ), CAST(target_ts AS TIMESTAMPTZ), aqi, source, now()
            FROM incoming
            """
        )
        self.con.unregister("incoming")
        return len(df)

    def latest_forecast(self, city_id: str) -> pd.DataFrame:
        """Most recently issued forecast for a city, with the actual value where known."""
        return self.con.execute(
            """
            WITH last AS (SELECT max(issued_at) AS issued_at FROM forecasts WHERE city_id = ?)
            SELECT f.issued_at, f.target_ts, f.aqi AS forecast, f.source, c.aqi AS actual
            FROM forecasts f JOIN last USING (issued_at)
            LEFT JOIN city_hourly c ON c.city_id = f.city_id AND c.ts = f.target_ts AND c.source = 'punjab_epa'
            WHERE f.city_id = ? ORDER BY f.target_ts
            """,
            [city_id, city_id],
        ).df()

    def forecast_errors(self, city_id: str) -> pd.DataFrame:
        """Every forecast hour that now has an actual: horizon (h), forecast, actual, error."""
        return self.con.execute(
            """
            SELECT f.issued_at, f.target_ts,
                   CAST(date_diff('hour', f.issued_at, f.target_ts) AS INTEGER) AS horizon_h,
                   f.aqi AS forecast, c.aqi AS actual, f.aqi - c.aqi AS error, f.source
            FROM forecasts f JOIN city_hourly c
              ON c.city_id = f.city_id AND c.ts = f.target_ts AND c.source = 'punjab_epa'
            WHERE f.city_id = ? ORDER BY f.target_ts
            """,
            [city_id],
        ).df()

    def forecast_errors_with_baselines(self, city_id: str) -> pd.DataFrame:
        """forecast_errors plus two persistence baselines evaluated on the same hours (plan 4.1):

        - persist_24h: the city's AQI 24 hours before the target hour (same hour yesterday)
        - persist_last: the city's AQI at the hour the forecast was issued (the latest value then)
        Rows where a baseline value is missing keep NULL; skill is computed on rows that have both.
        """
        return self.con.execute(
            """
            SELECT f.issued_at, f.target_ts,
                   CAST(date_diff('hour', f.issued_at, f.target_ts) AS INTEGER) AS horizon_h,
                   f.aqi AS forecast, c.aqi AS actual, f.aqi - c.aqi AS error, f.source,
                   p24.aqi AS persist_24h, pl.aqi AS persist_last
            FROM forecasts f
            JOIN city_hourly c
              ON c.city_id = f.city_id AND c.ts = f.target_ts AND c.source = 'punjab_epa'
            LEFT JOIN city_hourly p24
              ON p24.city_id = f.city_id AND p24.ts = f.target_ts - INTERVAL 24 HOUR AND p24.source = 'punjab_epa'
            LEFT JOIN city_hourly pl
              ON pl.city_id = f.city_id AND pl.ts = date_trunc('hour', f.issued_at) AND pl.source = 'punjab_epa'
            WHERE f.city_id = ? ORDER BY f.target_ts
            """,
            [city_id],
        ).df()

    # ---- reads ------------------------------------------------------------
    def latest_station_values(self, station_ids: list[str]) -> pd.DataFrame:
        if not station_ids:
            return pd.DataFrame()
        placeholders = ",".join("?" for _ in station_ids)
        return self.con.execute(
            f"""
            SELECT r.station_id, r.ts, r.pm25, r.pm10, r.co, r.so2, r.no2, r.o3, r.aqi, r.aqi_computed, r.source,
                   r.portal_dominant, r.temperature, r.humidity, r.wind_speed, r.wind_direction
            FROM readings r
            JOIN (SELECT station_id, max(ts) AS ts FROM readings
                  WHERE station_id IN ({placeholders}) GROUP BY station_id) m
              ON r.station_id = m.station_id AND r.ts = m.ts
            """,
            station_ids,
        ).df()

    def station_series(
        self, station_ids: list[str], start: datetime, end: datetime, metric: str
    ) -> pd.DataFrame:
        if metric not in _ALLOWED_METRICS:
            raise ValueError("bad metric")
        if not station_ids:
            return pd.DataFrame()
        placeholders = ",".join("?" for _ in station_ids)
        return self.con.execute(
            f"""
            SELECT station_id, ts, {metric} AS value
            FROM readings
            WHERE station_id IN ({placeholders}) AND ts >= ? AND ts < ?
            ORDER BY ts
            """,
            [*station_ids, start, end],
        ).df()

    def aggregate(
        self,
        station_ids: list[str],
        start: datetime,
        end: datetime,
        metric: str,
        aggregation: str,
        threshold: int | None = None,
    ) -> pd.DataFrame:
        """Per-station aggregate over [start, end)."""
        if metric not in _ALLOWED_METRICS or aggregation not in _ALLOWED_AGG:
            raise ValueError("bad metric/aggregation")
        if not station_ids:
            return pd.DataFrame()
        placeholders = ",".join("?" for _ in station_ids)
        if aggregation == "latest":
            return self.latest_station_values(station_ids)
        if aggregation == "count_hours_above":
            if threshold is None:
                raise ValueError("threshold required")
            return self.con.execute(
                f"""
                SELECT station_id, count(*) AS value
                FROM readings
                WHERE station_id IN ({placeholders}) AND ts >= ? AND ts < ? AND {metric} > ?
                GROUP BY station_id
                """,
                [*station_ids, start, end, threshold],
            ).df()
        func = {"mean": "avg", "max": "max", "min": "min"}[aggregation]
        return self.con.execute(
            f"""
            SELECT station_id, {func}({metric}) AS value, count(*) AS n_hours
            FROM readings
            WHERE station_id IN ({placeholders}) AND ts >= ? AND ts < ?
            GROUP BY station_id
            """,
            [*station_ids, start, end],
        ).df()

    def latest_city_values(self) -> pd.DataFrame:
        return self.con.execute(
            """
            SELECT c.city_id, c.ts, c.pm25, c.pm10, c.aqi, c.n_stations, c.source
            FROM city_hourly c
            JOIN (SELECT city_id, max(ts) AS ts FROM city_hourly GROUP BY city_id) m
              ON c.city_id = m.city_id AND c.ts = m.ts
            """
        ).df()

    def delete_source(self, source: str) -> None:
        for t in ("readings", "city_hourly", "epd_daily", "forecasts"):
            self.con.execute(f"DELETE FROM {t} WHERE source = ?", [source])

    def real_counts(self) -> dict[str, int]:
        r = self.con.execute("SELECT count(*) FROM readings WHERE source <> 'fake'").fetchone()[0]
        c = self.con.execute("SELECT count(*) FROM city_hourly WHERE source <> 'fake'").fetchone()[0]
        e = self.con.execute("SELECT count(*) FROM epd_daily").fetchone()[0]
        return {"readings": int(r), "city_hourly": int(c), "epd_daily": int(e)}

    def epd_daily_series(self, city: str, start: datetime, end: datetime,
                         comparable_only: bool = True) -> pd.DataFrame:
        """Daily bulletin rows for a city. `comparable_only` drops the 2020-21 Smog Policy scale (style B17)."""
        q = """
            SELECT date, station_label, station_id, pollutant, conc, aqi, style
            FROM epd_daily WHERE city = ? AND date >= ? AND date < ?
        """
        params: list = [city, start.date(), end.date()]
        if comparable_only:
            q += " AND style <> 'B17'"
        return self.con.execute(q + " ORDER BY date", params).df()

    def city_series(self, city_id: str, start: datetime, end: datetime, metric: str) -> pd.DataFrame:
        if metric not in _ALLOWED_METRICS:
            raise ValueError("bad metric")
        return self.con.execute(
            f"SELECT ts, {metric} AS value, source FROM city_hourly WHERE city_id = ? AND ts >= ? AND ts < ? ORDER BY ts",
            [city_id, start, end],
        ).df()

    def counts(self) -> dict[str, int]:
        r = self.con.execute("SELECT count(*) FROM readings").fetchone()[0]
        c = self.con.execute("SELECT count(*) FROM city_hourly").fetchone()[0]
        e = self.con.execute("SELECT count(*) FROM epd_daily").fetchone()[0]
        return {"readings": int(r), "city_hourly": int(c), "epd_daily": int(e)}

"""Data-quality checks over the archive (plan 1.6).

Every check returns a `Flag` per affected row or station, never a silent
correction: the archive is the data of record and nothing here rewrites it.
The app shows the flags beside the numbers so a viewer can see which values
are suspect, and `scripts/quality_report.py` prints the same set.

What is checked, and why each threshold is what it is:

* **gap** --- a station that reported, then stopped. Collection is hourly, so a
  station with no row for 2+ consecutive expected hours has a gap. Expected
  hours are taken from the rounds that actually ran (hours where *some* station
  reported), never from a wall-clock range: before the cron trigger was
  installed on 15 Oct the collector fired every few hours, and counting those
  as missed would make every station look broken.
* **stuck** --- a sensor repeating one value exactly. Real PM2.5 moves between
  hours; three identical consecutive readings of the same pollutant is the
  signal used by AirNow's QA and is tight enough to catch a frozen sensor
  without firing on a genuinely flat night. Zero is excluded: it is reported
  as "impossible" instead, which is more specific.
* **impossible** --- outside what the instrument can physically mean: negative
  anything, PM2.5 above PM10 (PM10 includes the PM2.5 fraction by definition),
  or a value above the top of the AQI breakpoint table.
* **spike** --- an hour-on-hour jump that no real plume produces. Measured as a
  multiple of the station's own recent variation rather than a fixed number,
  because Shahdara's normal range is not Gulberg's.

Thresholds live in `THRESHOLDS` so the report and the tests read the same
numbers, and so the report can state them rather than hiding them in code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# Physical ceilings. PM values above these are instrument faults, not smog:
# the AQI tables stop at 500.4 (PM2.5) and 604 (PM10), and Lahore's worst
# recorded hour in the 2020-2025 EPD archive is far below.
CEILING = {"pm25": 1000.0, "pm10": 2000.0, "o3": 1000.0, "no2": 2000.0, "so2": 2000.0, "co": 100.0}

THRESHOLDS = {
    "gap_hours": 2,          # consecutive expected hours with no row
    "stuck_repeats": 3,      # identical consecutive values of one pollutant
    "spike_sigma": 5.0,      # hour-on-hour change, in robust sigmas
    "spike_min_abs": 50.0,   # ug/m3; below this a jump is never called a spike
    "partial_round_frac": 0.6,  # a round catching under 60% of the usual station count
}

POLLUTANTS = ["pm25", "pm10", "o3", "no2", "so2", "co"]


@dataclass(frozen=True)
class Flag:
    kind: str                # gap | stuck | impossible | spike | partial_round | source_collision
    station_id: str
    ts: pd.Timestamp | None
    detail: str
    value: float | None = None

    def __str__(self) -> str:
        when = "-" if self.ts is None else f"{self.ts:%Y-%m-%d %H:%MZ}"
        return f"{self.kind:17s} {self.station_id:10s} {when}  {self.detail}"


@dataclass
class Report:
    flags: list[Flag] = field(default_factory=list)
    uptime: pd.DataFrame = field(default_factory=pd.DataFrame)
    expected_hours: list[pd.Timestamp] = field(default_factory=list)

    def of_kind(self, kind: str) -> list[Flag]:
        return [f for f in self.flags if f.kind == kind]

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.flags:
            out[f.kind] = out.get(f.kind, 0) + 1
        return out


def _adjacent(s: pd.Series) -> pd.DataFrame:
    """Pairs of readings exactly one hour apart.

    Both the stuck and spike checks mean "between consecutive hours", and the
    archive is not evenly spaced: before the hourly trigger was installed on
    15 Oct the collector fired every 2-6 hours.  Differencing adjacent *rows*
    would read a five-hour change as a one-hour jump, which is what made the
    first version of this module report ten spikes that were only collection
    gaps.  So every pair whose spacing is not one hour is dropped.
    """
    if len(s) < 2:
        return pd.DataFrame(columns=["ts", "prev", "curr", "delta"])
    idx = s.index
    gap_h = (idx[1:] - idx[:-1]).total_seconds() / 3600.0
    keep = gap_h == 1.0
    return pd.DataFrame({
        "ts": idx[1:][keep],
        "prev": s.values[:-1][keep],
        "curr": s.values[1:][keep],
        "delta": s.values[1:][keep] - s.values[:-1][keep],
    })


def _robust_sigma(deltas: pd.Series) -> float:
    """Median absolute deviation of the hour-on-hour change, scaled to a sigma.

    Used instead of std() because a spike inflates std() enough to hide itself.
    """
    d = deltas.abs().dropna()
    if len(d) < 3:
        return float("nan")
    mad = (d - d.median()).abs().median()
    return float(mad * 1.4826)


def expected_hours(df: pd.DataFrame) -> list[pd.Timestamp]:
    """Hours in which the collector demonstrably ran (some station reported).

    Using observed rounds rather than a wall-clock range is what keeps the gap
    check honest about the period before hourly collection was reliable.
    """
    if df.empty:
        return []
    return sorted(df["ts"].dt.floor("h").unique())


def check_readings(df: pd.DataFrame, all_stations: list[str] | None = None) -> Report:
    """Run every station-level check over a `readings` frame."""
    rep = Report()
    if df.empty:
        return rep

    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    for c in POLLUTANTS + ["aqi"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["hour"] = df["ts"].dt.floor("h")
    df = df.sort_values(["station_id", "ts"])

    hours = expected_hours(df)
    rep.expected_hours = hours
    hour_index = {h: i for i, h in enumerate(hours)}
    seen = set(df["station_id"].unique())
    stations = sorted(set(all_stations or []) | seen)

    # --- uptime, and stations that never appear at all -----------------------
    rows = []
    for sid in stations:
        g = df[df.station_id == sid]
        present = set(g["hour"])
        rows.append({
            "station_id": sid,
            "hours_reported": len(present),
            "hours_expected": len(hours),
            "uptime": (len(present) / len(hours)) if hours else 0.0,
            "last_seen": g["ts"].max() if len(g) else pd.NaT,
        })
        if not len(g):
            rep.flags.append(Flag("gap", sid, None, f"never reported in {len(hours)} collected hours"))
            continue

        # --- gaps: runs of expected hours this station missed ----------------
        missing = [h for h in hours if h not in present]
        run: list[pd.Timestamp] = []
        for h in missing + [None]:
            if run and (h is None or hour_index[h] != hour_index[run[-1]] + 1):
                if len(run) >= THRESHOLDS["gap_hours"]:
                    rep.flags.append(Flag(
                        "gap", sid, run[0],
                        f"no reading for {len(run)} consecutive collected hours "
                        f"(to {run[-1]:%H:%MZ})"))
                run = []
            if h is not None:
                run.append(h)

        # --- per-pollutant checks --------------------------------------------
        for pol in POLLUTANTS:
            if pol not in g.columns:
                continue
            s = g.set_index("ts")[pol].dropna()
            if s.empty:
                continue

            # impossible: negatives, and above the physical ceiling
            for ts, v in s[(s < 0) | (s > CEILING[pol])].items():
                rep.flags.append(Flag("impossible", sid, ts,
                                      f"{pol} = {v:g} (outside 0-{CEILING[pol]:g})", float(v)))

            adj = _adjacent(s)
            if adj.empty:
                continue

            # stuck: N identical readings in consecutive *hours*, zero excluded.
            # Walk the one-hour-apart pairs and count unbroken runs of no change.
            run = 1
            start = None
            for r in adj.itertuples():
                if r.delta == 0 and r.curr != 0:
                    run = run + 1 if start is not None else 2
                    start = start or r.ts
                    if run == THRESHOLDS["stuck_repeats"]:
                        rep.flags.append(Flag(
                            "stuck", sid, start,
                            f"{pol} held at {r.curr:g} for {run} consecutive hours",
                            float(r.curr)))
                else:
                    run, start = 1, None

            # spike: a jump large in absolute terms *and* against this
            # station's own hour-on-hour variation
            sigma = _robust_sigma(adj["delta"])
            if sigma == sigma and sigma > 0:
                for r in adj.itertuples():
                    v = abs(r.delta)
                    if v > THRESHOLDS["spike_min_abs"] and v > THRESHOLDS["spike_sigma"] * sigma:
                        rep.flags.append(Flag(
                            "spike", sid, r.ts,
                            f"{pol} moved {r.delta:+.0f} in one hour "
                            f"({v / sigma:.1f}x its usual step)",
                            float(r.delta)))

        # pm25 > pm10 is impossible: PM10 includes the PM2.5 fraction
        if {"pm25", "pm10"} <= set(g.columns):
            bad = g.dropna(subset=["pm25", "pm10"])
            for r in bad[bad.pm25 > bad.pm10].itertuples():
                rep.flags.append(Flag("impossible", sid, r.ts,
                                      f"pm25 {r.pm25:g} exceeds pm10 {r.pm10:g}"))

    rep.uptime = pd.DataFrame(rows).sort_values("uptime", ascending=False).reset_index(drop=True)

    # --- partial rounds: a collection hour that caught far fewer stations ----
    # This is a fault in the round, not in the stations, and is reported
    # separately so a half-failed fetch is not read as ten stations going down
    # at once.  The portal briefly serves an incomplete table while it updates.
    per_hour = df.groupby("hour")["station_id"].nunique()
    if len(per_hour) >= 3:
        typical = per_hour.median()
        for h, n in per_hour.items():
            if n < typical * THRESHOLDS["partial_round_frac"]:
                rep.flags.append(Flag(
                    "partial_round", "-", h,
                    f"only {n} of a typical {typical:.0f} stations reported in this round"))

    return rep


def check_source_collisions(city_hourly: pd.DataFrame) -> list[Flag]:
    """City-hours written by more than one portal widget under one source name.

    The archive key is (city_id, ts, source), so when the home-page ranking and
    the 7-day trend widget disagree about the same hour, one silently replaces
    the other.  This cannot be detected from the archive alone --- only the
    survivor is stored --- so the check reports *duplicate keys within a frame
    about to be written*, which is where the collision actually happens.
    """
    flags: list[Flag] = []
    if city_hourly.empty:
        return flags
    df = city_hourly.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    key = ["city_id", "ts", "source"]
    dup = df[df.duplicated(subset=key, keep=False)]
    for (city, ts, source), g in dup.groupby(key):
        vals = g["aqi"].dropna().unique()
        if len(vals) > 1:
            flags.append(Flag(
                "source_collision", city, ts,
                f"{len(g)} rows for source '{source}' disagree: AQI "
                + " vs ".join(str(int(v)) for v in vals)
                + " -- the last one written wins"))
    return flags

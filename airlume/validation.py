"""CAMS model against the ground stations (plan 4.3, contribution C4).

Pairs every station reading with the CAMS value for the same hour and reports how
far they agree: mean absolute difference, signed bias (CAMS minus station) and
Pearson correlation -- per station, by hour of day, and for the city mean.

Framing, from the plan, kept in every output: this measures **agreement, not
error**. The station instruments are not calibrated against a reference here and
sometimes drop out, so neither side is treated as truth; the numbers say how far
a ~45 km model cell and eleven point monitors tell the same story.

Three choices worth stating:

* **Concentrations first.** PM2.5 and PM10 are compared in ug/m3 directly, which
  needs no index at all and is the cleanest comparison.
* **AQI only on the portal's own scale.** The `aqi` column stored with CAMS is
  Open-Meteo's *US* AQI. Comparing it with the portal's AQI would reintroduce the
  table mismatch solved for W1 on 16 Oct, so CAMS concentrations are put through
  `pk_portal` instead. And because CAMS carries no gases, the station side is also
  recomputed from PM only, so both sides are the same quantity.
* **Uncertainty from a block bootstrap over hours.** All eleven stations share one
  CAMS value per hour, and consecutive hours are strongly autocorrelated, so
  resampling station-rows independently would give intervals far too narrow.
  Blocks of consecutive hours are resampled instead.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from airlume.aqi import aqi_from_concentrations

KARACHI = "Asia/Karachi"


def pair(readings: pd.DataFrame, cams: pd.DataFrame) -> pd.DataFrame:
    """One row per station-hour that has both a station reading and a CAMS value.

    `readings`: the station archive (station_id, ts, pm25, pm10, ...).
    `cams`: city_hourly rows from source open_meteo_cams for the city.
    """
    r = readings.copy()
    c = cams.copy()
    r["ts"] = pd.to_datetime(r["ts"], utc=True)
    c["ts"] = pd.to_datetime(c["ts"], utc=True)
    for col in ("pm25", "pm10"):
        r[col] = pd.to_numeric(r[col], errors="coerce")
        c[col] = pd.to_numeric(c[col], errors="coerce")
    c = c.drop_duplicates(subset=["ts"], keep="last")[["ts", "pm25", "pm10"]]
    c = c.rename(columns={"pm25": "cams_pm25", "pm10": "cams_pm10"})
    m = r[["station_id", "ts", "pm25", "pm10"]].merge(c, on="ts", how="inner")
    m["aqi_pm_station"] = [aqi_from_concentrations(a, b)[0] for a, b in zip(m["pm25"], m["pm10"])]
    m["aqi_pm_cams"] = [aqi_from_concentrations(a, b)[0] for a, b in zip(m["cams_pm25"], m["cams_pm10"])]
    m["hour_pkt"] = m["ts"].dt.tz_convert(KARACHI).dt.hour
    return m


@dataclass(frozen=True)
class Agreement:
    n: int
    n_hours: int
    mad: float                    # mean absolute difference
    bias: float                   # mean of (CAMS - station)
    r: float | None               # Pearson correlation
    mad_ci: tuple[float, float] | None
    bias_ci: tuple[float, float] | None


def _blocks(hours: np.ndarray, block: int) -> list[np.ndarray]:
    """Consecutive runs of `block` hours from the sorted distinct hours."""
    return [hours[i:i + block] for i in range(0, max(1, len(hours) - block + 1))]


def agreement(df: pd.DataFrame, obs: str, mod: str, *, block_hours: int = 6,
              reps: int = 2000, seed: int = 7) -> Agreement | None:
    """Agreement between station column `obs` and CAMS column `mod`.

    95% intervals from a moving-block bootstrap over hours (see module docstring).
    Intervals are omitted when there are fewer than two blocks' worth of hours,
    because an interval from one block would only restate the point estimate.
    """
    d = df.dropna(subset=[obs, mod])
    if len(d) < 3:
        return None
    diff = (d[mod] - d[obs]).to_numpy(float)
    r = float(np.corrcoef(d[obs], d[mod])[0, 1]) if d[obs].std() > 0 and d[mod].std() > 0 else None
    hours = np.sort(d["ts"].unique())
    mad_ci = bias_ci = None
    if len(hours) >= 2 * block_hours:
        rng = np.random.default_rng(seed)
        blocks = _blocks(hours, block_hours)
        by_hour = {h: g for h, g in d.groupby("ts")}
        n_blocks = int(np.ceil(len(hours) / block_hours))
        mads, biases = [], []
        for _ in range(reps):
            pick = rng.integers(0, len(blocks), size=n_blocks)
            sample = pd.concat([by_hour[h] for b in pick for h in blocks[b]])
            dd = (sample[mod] - sample[obs]).to_numpy(float)
            mads.append(np.abs(dd).mean())
            biases.append(dd.mean())
        mad_ci = (float(np.percentile(mads, 2.5)), float(np.percentile(mads, 97.5)))
        bias_ci = (float(np.percentile(biases, 2.5)), float(np.percentile(biases, 97.5)))
    return Agreement(n=len(d), n_hours=len(hours), mad=float(np.abs(diff).mean()),
                     bias=float(diff.mean()), r=r, mad_ci=mad_ci, bias_ci=bias_ci)


def by_station(df: pd.DataFrame, obs: str, mod: str) -> pd.DataFrame:
    rows = []
    for sid, g in df.groupby("station_id"):
        a = agreement(g, obs, mod)
        if a is not None:
            rows.append({"station_id": sid, "n": a.n, "mad": a.mad, "bias": a.bias, "r": a.r})
    return pd.DataFrame(rows).sort_values("mad").reset_index(drop=True) if rows else pd.DataFrame()


def by_hour_of_day(df: pd.DataFrame, obs: str, mod: str) -> pd.DataFrame:
    d = df.dropna(subset=[obs, mod]).copy()
    d["diff"] = d[mod] - d[obs]
    return (d.groupby("hour_pkt")
              .agg(n=("diff", "size"), mad=("diff", lambda s: s.abs().mean()), bias=("diff", "mean"))
              .reset_index())


def city_mean(df: pd.DataFrame) -> pd.DataFrame:
    """Mean of the stations reporting in each hour, beside the single CAMS value.

    The fairest comparison for a ~45 km model cell: CAMS is an area average, so it
    is set against the average of the monitors rather than any one of them.
    """
    g = df.groupby("ts").agg(
        pm25=("pm25", "mean"), pm10=("pm10", "mean"),
        aqi_pm_station=("aqi_pm_station", "mean"),
        cams_pm25=("cams_pm25", "first"), cams_pm10=("cams_pm10", "first"),
        aqi_pm_cams=("aqi_pm_cams", "first"),
        n_stations=("station_id", "nunique"),
    ).reset_index()
    g["hour_pkt"] = g["ts"].dt.tz_convert(KARACHI).dt.hour
    g["station_id"] = "city-mean"
    return g

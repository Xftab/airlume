"""Severity / priority score per station or city.

Computes a composite score from:
  1. AQI band distribution — share of hours in each band
  2. Persistence — longest consecutive run of "unhealthy" or worse hours
  3. Trend — slope of AQI over the window (positive = worsening)
  4. Data confidence — fraction of expected hours actually present

All numbers come from the store; text is written by code (design rule 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

import numpy as np
import pandas as pd

from airlume.aqi import PUNJAB_BANDS, Band, band_for


# ── Band weights — higher AQI bands contribute more to severity ──────
_BAND_WEIGHT = {
    "Good": 0.0,
    "Satisfactory": 0.1,
    "Moderate": 0.3,
    "Unhealthy for sensitive groups": 0.5,
    "Unhealthy": 0.7,
    "Very unhealthy": 0.9,
    "Hazardous": 1.0,
}

# Threshold: AQI >= this is counted as "bad" for persistence
_BAD_AQI_THRESHOLD = 151  # "Unhealthy for sensitive groups" and above


@dataclass
class BandShare:
    """Share of hours in one AQI band."""
    label: str
    colour: str
    hours: int
    share: float  # 0-1


@dataclass
class PriorityScore:
    """Severity / priority assessment for one station or city over a window."""
    entity_id: str        # station_id or city_id
    entity_name: str
    entity_type: Literal["station", "city"]
    start: datetime
    end: datetime
    total_hours_expected: int
    total_hours_present: int
    data_confidence: float  # 0-1, present / expected

    band_shares: list[BandShare] = field(default_factory=list)

    # Persistence: longest consecutive run of hours >= _BAD_AQI_THRESHOLD
    longest_bad_run_hours: int = 0

    # Trend: OLS slope of AQI per day (positive = worsening)
    trend_aqi_per_day: float | None = None

    # Composite score 0-100
    score: float = 0.0
    severity_label: str = "Unknown"

    def sentence(self) -> str:
        """One honest sentence summarising the score."""
        if self.total_hours_present == 0:
            return f"No data for {self.entity_name} in this window."
        conf = (
            "high" if self.data_confidence >= 0.8
            else "moderate" if self.data_confidence >= 0.5
            else "low"
        )
        trend = ""
        if self.trend_aqi_per_day is not None:
            if self.trend_aqi_per_day > 5:
                trend = ", worsening"
            elif self.trend_aqi_per_day < -5:
                trend = ", improving"
        return (
            f"{self.entity_name}: priority score {self.score:.0f}/100 "
            f"({self.severity_label}{trend}). "
            f"Worst streak: {self.longest_bad_run_hours} consecutive unhealthy-or-worse hours. "
            f"Data confidence: {conf} ({self.data_confidence:.0%} of hours present)."
        )


def _band_distribution(aqi_values: pd.Series) -> list[BandShare]:
    """Count hours in each Punjab EPA band."""
    counts: dict[str, int] = {b.label: 0 for b in PUNJAB_BANDS}
    total = 0
    for v in aqi_values.dropna():
        b = band_for(int(round(v)))
        if b is not None:
            counts[b.label] = counts.get(b.label, 0) + 1
            total += 1
    if total == 0:
        return []
    band_map = {b.label: b for b in PUNJAB_BANDS}
    return [
        BandShare(label=label, colour=band_map[label].colour,
                  hours=n, share=n / total)
        for label, n in counts.items()
    ]


def _longest_bad_run(aqi_values: pd.Series, threshold: int = _BAD_AQI_THRESHOLD) -> int:
    """Longest consecutive run of hours with AQI >= threshold."""
    is_bad = (aqi_values.fillna(0) >= threshold).astype(int).values
    if len(is_bad) == 0:
        return 0
    max_run = 0
    current = 0
    for v in is_bad:
        if v:
            current += 1
            max_run = max(max_run, current)
        else:
            current = 0
    return max_run


def _trend_slope(ts: pd.Series, aqi: pd.Series) -> float | None:
    """OLS slope of AQI over time, expressed as AQI points per day."""
    valid = aqi.dropna()
    if len(valid) < 6:
        return None
    t = ts.loc[valid.index]
    # Convert timestamps to fractional days from start
    t0 = t.iloc[0]
    x = (t - t0).dt.total_seconds().values / 86400.0
    y = valid.values.astype(float)
    # Simple OLS
    n = len(x)
    sx = x.sum()
    sy = y.sum()
    sxx = (x * x).sum()
    sxy = (x * y).sum()
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return None
    return float((n * sxy - sx * sy) / denom)


def _composite_score(band_shares: list[BandShare],
                     longest_bad_run: int,
                     trend: float | None,
                     total_hours: int) -> tuple[float, str]:
    """0-100 composite. Weighted sum of band severity, persistence, trend."""
    # 1. Weighted band severity (0-1) — 50% of score
    band_sev = sum(
        _BAND_WEIGHT.get(bs.label, 0) * bs.share for bs in band_shares
    )
    # 2. Persistence (0-1) — 30% of score
    # Normalise: 48h continuous bad = 1.0
    persist = min(longest_bad_run / 48.0, 1.0)
    # 3. Trend (0-1) — 20% of score
    # +20 AQI/day = 1.0, -20 = 0.0, 0 = 0.5
    if trend is not None:
        trend_norm = min(max((trend + 20) / 40.0, 0.0), 1.0)
    else:
        trend_norm = 0.5  # neutral when unknown

    raw = 0.50 * band_sev + 0.30 * persist + 0.20 * trend_norm
    score = round(raw * 100, 1)

    if score >= 70:
        label = "Critical"
    elif score >= 50:
        label = "High"
    elif score >= 30:
        label = "Elevated"
    elif score >= 15:
        label = "Moderate"
    else:
        label = "Low"

    return score, label


def _metric_column(series: pd.DataFrame) -> pd.Series:
    """The AQI column, whatever the caller named it.

    Store.station_series() labels the metric column "value"; a frame built by
    hand usually calls it "aqi". Accept either, so a store-backed score is not
    silently computed over an empty series.
    """
    for col in ("aqi", "value"):
        if col in series.columns:
            return series[col]
    return pd.Series(dtype=float)


def score_station(
    station_id: str,
    station_name: str,
    series: pd.DataFrame,
    start: datetime,
    end: datetime,
) -> PriorityScore:
    """Score one station from its readings DataFrame (needs ts and aqi/value columns)."""
    expected = max(int((end - start).total_seconds() // 3600), 1)
    present = len(series)
    confidence = min(present / expected, 1.0)

    aqi_col = _metric_column(series)
    band_shares = _band_distribution(aqi_col)
    bad_run = _longest_bad_run(aqi_col)
    trend = _trend_slope(
        series["ts"] if "ts" in series.columns else pd.Series(dtype="datetime64[ns]"),
        aqi_col,
    )

    score, label = _composite_score(band_shares, bad_run, trend, present)

    return PriorityScore(
        entity_id=station_id,
        entity_name=station_name,
        entity_type="station",
        start=start,
        end=end,
        total_hours_expected=expected,
        total_hours_present=present,
        data_confidence=confidence,
        band_shares=band_shares,
        longest_bad_run_hours=bad_run,
        trend_aqi_per_day=trend,
        score=score,
        severity_label=label,
    )


def score_all_stations(
    store,  # airlume.pipeline.store.Store
    registry,  # airlume.pipeline.registry.Registry
    city_id: str,
    start: datetime,
    end: datetime,
) -> list[PriorityScore]:
    """Score every station in a city over [start, end). Returns sorted by score descending."""
    stations = registry.stations_in(city_id)
    results = []
    for st in stations:
        series = store.station_series([st.station_id], start, end, "aqi")
        ps = score_station(st.station_id, st.name, series, start, end)
        results.append(ps)
    results.sort(key=lambda p: p.score, reverse=True)
    return results

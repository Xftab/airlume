"""Persistence baseline: tomorrow at hour h = today at hour h.

Every learned model in Phase 4 must beat this on the frozen test window, or
it is not used (weakness W5).
"""

from __future__ import annotations

import pandas as pd


def persistence(series: pd.DataFrame, horizon_hours: int = 24) -> pd.DataFrame:
    """series: columns ts, value (hourly). Returns ts, forecast for the next horizon."""
    if series.empty:
        return pd.DataFrame(columns=["ts", "forecast"])
    s = series.sort_values("ts").tail(horizon_hours)
    out = s.copy()
    out["ts"] = out["ts"] + pd.Timedelta(hours=horizon_hours)
    return out.rename(columns={"value": "forecast"})[["ts", "forecast"]].reset_index(drop=True)

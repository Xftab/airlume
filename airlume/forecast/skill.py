"""Skill of relayed forecasts against persistence (plan 4.1, contribution C5).

Skill = 1 - MAE(forecast) / MAE(baseline), on the same target hours. Positive means the
forecast beats "same hour yesterday"; zero or negative means it adds nothing over it.
"""

from __future__ import annotations

import pandas as pd

SOURCE_LABELS = {"punjab_epa_forecast": "EPA Punjab", "open_meteo_cams_forecast": "CAMS"}


def scorecard(err: pd.DataFrame) -> pd.DataFrame:
    """One row per forecast source: n, MAE, bias, MAE of each baseline on the same hours, skill."""
    if err.empty:
        return pd.DataFrame()
    rows = []
    for src, g in err.groupby("source"):
        row = {"source": SOURCE_LABELS.get(src, src), "n": int(len(g)),
               "mae": float((g["forecast"] - g["actual"]).abs().mean()),
               "bias": float((g["forecast"] - g["actual"]).mean())}
        for col, name in (("persist_24h", "same_hour_yesterday"), ("persist_last", "last_value")):
            both = g.dropna(subset=[col])
            if len(both) >= 3:
                mae_f = (both["forecast"] - both["actual"]).abs().mean()
                mae_b = (both[col] - both["actual"]).abs().mean()
                row[f"mae_{name}"] = float(mae_b)
                row[f"skill_vs_{name}"] = float(1 - mae_f / mae_b) if mae_b > 0 else None
                row[f"n_{name}"] = int(len(both))
            else:
                row[f"mae_{name}"] = None
                row[f"skill_vs_{name}"] = None
                row[f"n_{name}"] = int(len(both))
        rows.append(row)
    return pd.DataFrame(rows).set_index("source")


def by_horizon(err: pd.DataFrame) -> pd.DataFrame:
    """MAE by lead time, forecast vs same-hour-yesterday, for the horizon chart."""
    if err.empty:
        return pd.DataFrame()
    g = err.dropna(subset=["persist_24h"]).copy()
    g["abs_forecast"] = (g["forecast"] - g["actual"]).abs()
    g["abs_persist"] = (g["persist_24h"] - g["actual"]).abs()
    out = g.groupby(["source", "horizon_h"], as_index=False)[["abs_forecast", "abs_persist"]].mean()
    out["source"] = out["source"].map(SOURCE_LABELS).fillna(out["source"])
    return out

"""W1 re-score on the whole archive with the dated portal tables (6 Nov 2026).

    python scripts/w1_rescore.py

For every stored station-hour with a portal AQI, recompute the AQI from the
published concentrations on the table the portal used at that hour
(`aqi.portal_scale_at`) and compare. Reports exact-match rate, share within one
point, MAE, and a day-block bootstrap 95% interval for the MAE (2,000 resamples,
seed 7), overall and on each side of the 3 Nov change. Also reports what the
single October table would have scored on the same rows, for comparison.
Reads the CSV archive (data of record). Writes data/eval/w1_rescore_<date>.json.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from airlume.aqi import PK_PORTAL_V2_FROM, aqi_from_concentrations, portal_scale_at  # noqa: E402
from airlume.config import ROOT  # noqa: E402
from airlume.pipeline import archive  # noqa: E402


def recompute(df: pd.DataFrame, fixed_scale: str | None = None) -> pd.Series:
    out = []
    for r in df.itertuples():
        scale = fixed_scale or portal_scale_at(r.ts)
        a, _ = aqi_from_concentrations(r.pm25, r.pm10, scale=scale, o3=r.o3, no2=r.no2, so2=r.so2, co=r.co)
        out.append(np.nan if a is None else a)
    return pd.Series(out, index=df.index)


def summary(err: pd.Series, days: pd.Series, rng: np.random.Generator) -> dict:
    e = err.abs()
    blocks = [e[days == d].to_numpy() for d in sorted(days.unique())]
    boots = []
    for _ in range(2000):
        pick = rng.integers(0, len(blocks), len(blocks))
        boots.append(np.concatenate([blocks[i] for i in pick]).mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": int(len(e)), "exact_pct": round(float((e == 0).mean() * 100), 1),
            "within1_pct": round(float((e <= 1).mean() * 100), 1),
            "mae": round(float(e.mean()), 2), "mae_ci95": [round(float(lo), 2), round(float(hi), 2)],
            "max_abs": int(e.max()), "days": int(days.nunique())}


def main() -> int:
    df = archive.load_all("readings")
    df = df[(df.source == "punjab_epa") & df.aqi.notna()].copy()
    df["dated"] = recompute(df)
    df["v1_only"] = recompute(df, "pk_portal_v1")
    df = df.dropna(subset=["dated"])
    days = df.ts.dt.tz_convert("Asia/Karachi").dt.date
    rng = np.random.default_rng(7)
    res = {"generated": str(date.today()), "rows": int(len(df)),
           "span": [str(df.ts.min()), str(df.ts.max())], "switch_utc": str(PK_PORTAL_V2_FROM)}
    before = df.ts < PK_PORTAL_V2_FROM
    res["dated_tables_all"] = summary(df.aqi - df.dated, days, rng)
    res["dated_tables_before_3nov"] = summary(df.aqi[before] - df.dated[before], days[before], rng)
    res["dated_tables_from_3nov"] = summary(df.aqi[~before] - df.dated[~before], days[~before], rng)
    res["october_table_from_3nov"] = summary(df.aqi[~before] - df.v1_only[~before], days[~before], rng)
    top = (df.pm25 > 350) | (df.pm10 > 550)
    res["top_of_scale_rows"] = {"before": int((top & before).sum()), "from_3nov": int((top & ~before).sum()),
                                "exact_before": int(((df.aqi == df.dated) & top & before).sum()),
                                "exact_from_3nov": int(((df.aqi == df.dated) & top & ~before).sum())}
    big = df[(df.aqi - df.dated).abs() > 10]
    res["errors_over_10"] = {"n": int(len(big)),
                             "by_portal_dominant": big.portal_dominant.fillna("blank").value_counts().to_dict()}
    print(json.dumps(res, indent=2))
    out = ROOT / "data" / "eval" / f"w1_rescore_{date.today()}.json"
    out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"written {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

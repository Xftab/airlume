r"""Is the hourly forecaster better than the same hour yesterday? (6 Nov 2026)

    python scripts\forecast_baseline_check.py

`forecast_fit.py` measures skill against persistence (the last value). In a smog
season with a strong daily cycle, persistence is a weak baseline beyond a few
hours, and "the same hour yesterday" (seasonal naive, already in that script as
`yesterday`) is a much harder one. This script re-uses forecast_fit's data, split
and models unchanged and adds two things:

1. Skill of every model against `yesterday` on the same rows, with the same
   moving-block bootstrap over forecast origins.
2. `blend`: per horizon, w * last + (1 - w) * lag24, with w chosen on the TRAINING
   rows only (grid 0, 0.05, ..., 1, minimum MAE). One number per horizon, nothing
   tuned on the test period. Added after seeing the 6 Nov result, so it is
   exploratory and carries the same mild selection optimism as the per-band models.

Writes data\eval\forecast_baseline_check_<date>.json.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import forecast_fit as ff  # noqa: E402


def skill_vs(df: pd.DataFrame, col: str, base: str, n: int = 2000, block: int = 24, seed: int = 0):
    origins = np.array(sorted(df.origin.unique()))
    grp = {o: g for o, g in df.groupby("origin")}
    am = {o: float(np.abs(g[col] - g.y).sum()) for o, g in grp.items()}
    ab = {o: float(np.abs(g[base] - g.y).sum()) for o, g in grp.items()}
    k = len(origins)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(k / block))
    out = []
    for _ in range(n):
        starts = rng.integers(0, max(1, k - block + 1), size=nb)
        sel = np.concatenate([origins[s:s + block] for s in starts])[:k]
        m = sum(am[o] for o in sel); b = sum(ab[o] for o in sel)
        out.append(1 - m / b if b > 0 else np.nan)
    lo, hi = np.nanpercentile(out, [2.5, 97.5])
    return round(1 - sum(am.values()) / sum(ab.values()), 3), round(float(lo), 3), round(float(hi), 3)


def main() -> int:
    act = ff.load_actual("PB-LHE")
    rows = ff.build_rows(act, ff.FcLookup("open_meteo_cams_forecast", "PB-LHE"), ff.FcLookup("punjab_epa_forecast", "PB-LHE"))
    split = pd.Timestamp("2026-10-27T00:00:00Z")
    train = rows[(rows.origin < split) & (rows.target < split)].reset_index(drop=True)
    test = rows[rows.origin >= split].reset_index(drop=True)
    for k, v in {**ff.fit_predict(train, test), **ff.fit_predict_banded(train, test)}.items():
        test[k] = v
    test["yesterday"] = test.lag24
    grid = np.round(np.arange(0, 1.0001, 0.05), 2)
    weights = {}
    test["blend"] = np.nan
    for h in range(1, ff.HMAX + 1):
        tr = train[(train.h == h)].dropna(subset=["lag24"])
        maes = [float(np.abs(w * tr["last"] + (1 - w) * tr.lag24 - tr.y).mean()) for w in grid]
        w = float(grid[int(np.argmin(maes))])
        weights[h] = w
        m = (test.h == h).values
        test.loc[m, "blend"] = w * test.loc[m, "last"] + (1 - w) * test.loc[m, "lag24"]
    models = ["ridge_band", "lightgbm_band", "ridge", "lightgbm", "blend", "cams"]
    res = {"date": str(date.today()), "split_origin_utc": str(split), "test_origins": int(test.origin.nunique()),
           "blend_weight_on_last_by_h": weights, "bands": {}}
    print(f"blend weight on the last value, by horizon (training rows only): {weights}")
    print(f"\n{'band':<11}{'MAE yest':>9}" + "".join(f"{m[:13]:>28}" for m in models))
    for band, (lo_h, hi_h) in ff.BANDS.items():
        b = test[(test.h >= lo_h) & (test.h <= hi_h)].dropna(subset=["yesterday"])
        e = {"n_rows": int(len(b)), "mae_yesterday": round(float(np.abs(b.yesterday - b.y).mean()), 2), "models": {}}
        line = f"{band:<11}{e['mae_yesterday']:>9}"
        for m in models:
            c = b.dropna(subset=[m])
            s, lo, hi = skill_vs(c, m, "yesterday")
            e["models"][m] = {"n_rows": int(len(c)), "mae": round(float(np.abs(c[m] - c.y).mean()), 2),
                              "skill_vs_yesterday": s, "ci95": [lo, hi]}
            line += f"  {e['models'][m]['mae']:>6.1f} {s:+.2f} [{lo:+.2f},{hi:+.2f}]"
        res["bands"][band] = e
        print(line)
    out = ff.OUT / f"forecast_baseline_check_{date.today()}.json"
    out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(f"\nwritten {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

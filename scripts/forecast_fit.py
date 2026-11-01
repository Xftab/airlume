r"""Phase 4.2: fit and verify a 1 to 24 hour forecaster for Lahore city AQI on the hourly archive.

    python scripts\forecast_fit.py
    python scripts\forecast_fit.py --split 2026-10-27T00:00:00Z

Target: city AQI of Lahore (PB-LHE, Punjab EPA city_hourly), hourly, UTC. The 25 to 28 Oct part
of that series comes from the portal's 7-day trend endpoint (the station archive has a gap
there), so it is the same quantity from a different endpoint; stated, not hidden.

Forecast origin t, horizon h = 1..24, target at t + h. One row per (t, h), "direct" multi-horizon.
Features use only what was known at t: AQI at t, mean of the last 3 h, change over 3 h, the AQI at
target - 24 h (same hour a day earlier, always <= t for h <= 24), Karachi hour of the target, h,
and the CAMS and EPA forecasts for that target issued at or before t (missing = blank).
The model predicts the change from the last value (y - AQI_t), then adds it back.

Verification protocol (so the number can be trusted):
* Chronological split by forecast origin at --split. Training rows must have their TARGET before
  the split (an embargo: no training label overlaps the test period).
* No tuning on the test period: hyperparameters are fixed below, chosen before looking at it.
* Compared on the SAME rows: persistence (last value), same hour yesterday, the CAMS forecast,
  the EPA forecast (h <= 8 only), a ridge regression, and LightGBM (MAE objective).
* Skill = 1 - MAE(model) / MAE(persistence). Intervals: moving-block bootstrap over forecast
  origins (24 h blocks, 2000 resamples), because neighbouring origins are not independent.
* Reported by horizon band, plus the regime of train versus test (mean AQI, range), because a
  shift in smog level between the two is the main way a short archive misleads.

Output: data\eval\forecast_fit_<date>.json and a table.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from airlume.config import ROOT  # noqa: E402

ARCH = ROOT / "data" / "archive"
OUT = ROOT / "data" / "eval"
BANDS = {"1-3 h": (1, 3), "4-8 h": (4, 8), "9-16 h": (9, 16), "17-24 h": (17, 24), "all 1-24 h": (1, 24)}
HMAX = 24


def read_dir(p: Path) -> pd.DataFrame:
    return pd.concat([pd.read_csv(f) for f in sorted(p.glob("*.csv"))], ignore_index=True)


def load_actual(city: str) -> pd.Series:
    d = read_dir(ARCH / "city_hourly" / "punjab_epa")
    d = d[d.city_id == city].copy()
    d["ts"] = pd.to_datetime(d.ts, utc=True)
    s = d.drop_duplicates("ts").set_index("ts").sort_index()["aqi"].astype(float)
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="h", tz="UTC"))


class FcLookup:
    """Latest forecast for a target that was issued at or before the origin (and not older than 3 h)."""

    def __init__(self, source: str, city: str):
        d = read_dir(ARCH / "forecasts" / source)
        d = d[d.city_id == city].copy()
        d["issued_at"] = pd.to_datetime(d.issued_at, utc=True)
        d["target_ts"] = pd.to_datetime(d.target_ts, utc=True)
        self.issues = np.array(sorted(d.issued_at.unique()), dtype="datetime64[ns]")
        self.val = {(i, t): a for i, t, a in zip(d.issued_at, d.target_ts, d.aqi)}

    def get(self, origin: pd.Timestamp, target: pd.Timestamp) -> float:
        k = np.searchsorted(self.issues, np.datetime64(origin.tz_convert(None)), side="right") - 1
        if k < 0:
            return np.nan
        iss = pd.Timestamp(self.issues[k]).tz_localize("UTC")
        if origin - iss > pd.Timedelta(hours=3):
            return np.nan
        return float(self.val.get((iss, target), np.nan))


def build_rows(act: pd.Series, cams: FcLookup, epa: FcLookup) -> pd.DataFrame:
    rows = []
    idx = act.index
    for t in idx[24:]:
        last = act.get(t)
        if pd.isna(last):
            continue
        l3 = act.loc[t - pd.Timedelta(hours=2):t]
        a3 = act.get(t - pd.Timedelta(hours=3))
        for h in range(1, HMAX + 1):
            tgt = t + pd.Timedelta(hours=h)
            if tgt not in idx or pd.isna(act.get(tgt)):
                continue
            lag24 = act.get(tgt - pd.Timedelta(hours=24))
            rows.append({
                "origin": t, "h": h, "target": tgt, "y": act[tgt], "last": last,
                "mean3": l3.mean(), "d3": last - a3 if pd.notna(a3) else np.nan,
                "lag24": lag24, "hour": (tgt.hour + 5) % 24,
                "cams": cams.get(t, tgt), "epa": epa.get(t, tgt) if h <= 8 else np.nan,
            })
    d = pd.DataFrame(rows)
    d["hs"] = np.sin(2 * np.pi * d.hour / 24)
    d["hc"] = np.cos(2 * np.pi * d.hour / 24)
    return d


FEATS = ["last", "mean3", "d3", "lag24", "hs", "hc", "h", "cams", "epa"]


def fit_predict(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, np.ndarray]:
    import lightgbm as lgb
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    def rel(d):  # features relative to the last value so the model learns changes, not levels
        x = d[FEATS].copy()
        x["lag24"] = d.lag24 - d["last"]
        x["cams"] = d.cams - d["last"]
        x["epa"] = d.epa - d["last"]
        x["mean3"] = d.mean3 - d["last"]
        return x

    ytr = (train.y - train["last"]).values
    xtr, xte = rel(train), rel(test)
    m = lgb.LGBMRegressor(objective="l1", n_estimators=200, learning_rate=0.05, num_leaves=8,
                          min_child_samples=40, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                          random_state=0, verbose=-1)
    m.fit(xtr, ytr)
    med = xtr.median()
    def lin(x):
        z = x.copy()
        for c in ("cams", "epa"):
            z[c + "_na"] = z[c].isna().astype(float)
        return z.fillna(med).fillna(0.0)
    ltr, lte = lin(xtr), lin(xte)
    for c in ("cams_na", "epa_na"):
        if c not in ltr:
            ltr[c] = 0.0
            lte[c] = 0.0
    sc = StandardScaler().fit(ltr)
    r = Ridge(alpha=10.0).fit(sc.transform(ltr), ytr)
    return {"lightgbm": test["last"].values + m.predict(xte),
            "ridge": test["last"].values + r.predict(sc.transform(lte))}


def fit_predict_banded(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, np.ndarray]:
    """Same models, one per horizon band (1-3, 4-8, 9-16, 17-24 h): short horizons are a different
    problem from long ones. Added AFTER the first test-period result showed the single model losing
    to persistence at 1-3 h, so its test numbers carry a mild selection optimism; reported separately."""
    out = {"lightgbm_band": np.full(len(test), np.nan), "ridge_band": np.full(len(test), np.nan)}
    for lo, hi in [(1, 3), (4, 8), (9, 16), (17, 24)]:
        tr = train[(train.h >= lo) & (train.h <= hi)]
        te_mask = ((test.h >= lo) & (test.h <= hi)).values
        p = fit_predict(tr, test[te_mask])
        out["lightgbm_band"][te_mask] = p["lightgbm"]
        out["ridge_band"][te_mask] = p["ridge"]
    return out


def block_boot_skill(df: pd.DataFrame, col: str, n: int = 2000, block: int = 24, seed: int = 0):
    """Skill vs persistence with a moving-block bootstrap over forecast origins."""
    origins = np.array(sorted(df.origin.unique()))
    grp = {o: g for o, g in df.groupby("origin")}
    ae_m = {o: float(np.abs(g[col] - g.y).sum()) for o, g in grp.items()}
    ae_p = {o: float(np.abs(g["last"] - g.y).sum()) for o, g in grp.items()}
    cnt = {o: len(g) for o, g in grp.items()}
    k = len(origins)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(k / block))
    out = []
    for _ in range(n):
        starts = rng.integers(0, max(1, k - block + 1), size=nb)
        sel = np.concatenate([origins[s:s + block] for s in starts])[:k]
        m = sum(ae_m[o] for o in sel); p = sum(ae_p[o] for o in sel)
        out.append(1 - m / p if p > 0 else np.nan)
    lo, hi = np.nanpercentile(out, [2.5, 97.5])
    tm = sum(ae_m.values()); tp = sum(ae_p.values())
    return (1 - tm / tp, float(lo), float(hi))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="PB-LHE")
    ap.add_argument("--split", default="2026-10-27T00:00:00Z", help="first forecast origin of the test period (UTC)")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)

    act = load_actual(a.city)
    print(f"{a.city}: {act.notna().sum()} hourly values, {act.index.min()} to {act.index.max()}")
    rows = build_rows(act, FcLookup("open_meteo_cams_forecast", a.city), FcLookup("punjab_epa_forecast", a.city))
    split = pd.Timestamp(a.split)
    train = rows[(rows.origin < split) & (rows.target < split)].reset_index(drop=True)
    test = rows[rows.origin >= split].reset_index(drop=True)
    print(f"rows: train {len(train)} ({train.origin.nunique()} origins), test {len(test)} ({test.origin.nunique()} origins)")
    if train.origin.nunique() < 72 or test.origin.nunique() < 24:
        sys.exit("not enough origins on one side of the split to say anything")
    preds = fit_predict(train, test)
    for k, v in {**preds, **fit_predict_banded(train, test)}.items():
        test[k] = v
    test["yesterday"] = test.lag24

    regime = {
        "train_aqi_mean": round(float(act[(act.index < split)].mean()), 1),
        "test_aqi_mean": round(float(act[(act.index >= split)].mean()), 1),
        "train_aqi_range": [float(act[act.index < split].min()), float(act[act.index < split].max())],
        "test_aqi_range": [float(act[act.index >= split].min()), float(act[act.index >= split].max())],
    }
    print("regime:", regime)

    models = ["yesterday", "cams", "epa", "ridge", "lightgbm", "ridge_band", "lightgbm_band"]
    res = {}
    print(f"\n{'band':<11}{'n':>6}{'persist MAE':>12}" + "".join(f"{m[:11]:>13}" for m in models))
    for band, (lo_h, hi_h) in BANDS.items():
        b = test[(test.h >= lo_h) & (test.h <= hi_h)]
        entry = {"n_rows": int(len(b)), "n_origins": int(b.origin.nunique()),
                 "mae_persistence": round(float(np.abs(b["last"] - b.y).mean()), 2), "models": {}}
        line = f"{band:<11}{len(b):>6}{entry['mae_persistence']:>12}"
        for m in models:
            c = b.dropna(subset=[m])
            if len(c) < 24 or c.origin.nunique() < 12:
                entry["models"][m] = None
                line += f"{'-':>12}"
                continue
            mae_m = float(np.abs(c[m] - c.y).mean()); mae_p = float(np.abs(c["last"] - c.y).mean())
            s, lo, hi = block_boot_skill(c, m)
            entry["models"][m] = {"n_rows": int(len(c)), "mae": round(mae_m, 2), "mae_persistence_same_rows": round(mae_p, 2),
                                  "skill": round(s, 3), "skill_ci95": [round(lo, 3), round(hi, 3)]}
            line += f"{mae_m:>7.1f}({s:+.2f})"
        res[band] = entry
        print(line)
    print("\nskill = 1 - MAE(model)/MAE(persistence) on the same rows; CI: block bootstrap over origins")
    for band in BANDS:
        for m in ("cams", "ridge", "lightgbm", "ridge_band", "lightgbm_band"):
            e = res[band]["models"].get(m)
            if e:
                print(f"  {band:<11}{m:<9} skill {e['skill']:+.3f}  [{e['skill_ci95'][0]:+.3f}, {e['skill_ci95'][1]:+.3f}]  n={e['n_rows']}")

    report = {"date": str(date.today()), "city": a.city, "split_origin_utc": a.split, "regime": regime,
              "train_rows": int(len(train)), "test_rows": int(len(test)),
              "train_origins": int(train.origin.nunique()), "test_origins": int(test.origin.nunique()),
              "features": FEATS, "bands": res,
              "note": "25-28 Oct city AQI comes from the portal 7-day trend endpoint; hyperparameters fixed in advance; "
                      "forecast origins within a block are not independent, hence the block bootstrap"}
    if a.no_write:
        print("(nothing written)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"forecast_fit_{report['date']}.json"
    p.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"written {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

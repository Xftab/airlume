r"""Why does the hourly LightGBM lose to "same hour yesterday" at long horizons?  (17 Nov 2026)

    python scripts\forecast_diagnose.py

Same data, split and features as scripts\forecast_fit.py. Four candidate causes are tested, each by
a change that should help only if that cause is real:

  D1 Overfitting in the plain sense: in-sample MAE against rolling-origin cross-validation inside the
     training period against the test MAE. A large in-sample/CV gap means overfitting; a CV error that
     is close to the in-sample error but a much larger test error means the test period differs.
  D2 Too little data for the model size: learning curve (train on 25, 50, 75, 100% of training origins)
     and stronger regularisation (fewer leaves, higher minimum leaf size, shrinkage).
  D3 Level shift: tree models cannot predict above what they saw. The target is changed from the
     absolute change y - last to the relative change y / last, so the model learns proportions.
  D4 Features: with and without the CAMS forecast (it is wrong by a large, season-dependent bias).

Everything is scored on the same rows as forecast_fit (test origins from the --split), by horizon band,
as MAE and skill against BOTH persistence and same hour yesterday. Hyperparameters of the variants are
set here in advance; nothing is chosen on the test period. Output: data\eval\forecast_diagnose_<date>.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import forecast_fit as ff  # noqa: E402

BANDS = [(1, 3), (4, 8), (9, 16), (17, 24)]
BASE_FEATS = ["last", "mean3", "d3", "lag24", "hs", "hc", "h", "cams", "epa"]


def rel(d: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    x = d[feats].copy()
    for c in ("lag24", "cams", "epa", "mean3"):
        if c in x:
            x[c] = d[c] - d["last"]
    return x


def lgb_fit_predict(tr, te, feats, params, target="abs"):
    import lightgbm as lgb
    xtr, xte = rel(tr, feats), rel(te, feats)
    if target == "abs":
        ytr = (tr.y - tr["last"]).values
    else:  # relative change
        ytr = (tr.y / tr["last"].clip(lower=1) - 1.0).values
    m = lgb.LGBMRegressor(objective="l1", random_state=0, verbose=-1, subsample_freq=1, **params)
    m.fit(xtr, ytr)
    p = m.predict(xte)
    pr = m.predict(xtr)
    if target == "abs":
        return te["last"].values + p, tr["last"].values + pr
    return te["last"].values * (1 + p), tr["last"].values * (1 + pr)


DEFAULT = dict(n_estimators=200, learning_rate=0.05, num_leaves=8, min_child_samples=40,
               subsample=0.8, colsample_bytree=0.8)
STRONG = dict(n_estimators=80, learning_rate=0.05, num_leaves=4, min_child_samples=200,
              subsample=0.7, colsample_bytree=0.7, reg_lambda=10.0)


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def block_cv(tr: pd.DataFrame, feats, params, band, k=4, target="abs"):
    """Rolling-origin CV inside the training period: fit on the first i/k of origins (with an embargo),
    score on the next 1/k. Returns the mean MAE over folds."""
    origins = np.array(sorted(tr.origin.unique()))
    cuts = np.linspace(0, len(origins), k + 2).astype(int)
    out = []
    for i in range(1, k + 1):
        o_tr, o_te = origins[:cuts[i]], origins[cuts[i]:cuts[i + 1]]
        if len(o_te) == 0:
            continue
        t_end = o_te.min()
        a = tr[tr.origin.isin(o_tr) & (tr.target < t_end)]
        b = tr[tr.origin.isin(o_te)]
        if len(a) < 200 or len(b) == 0:
            continue
        p, _ = lgb_fit_predict(a, b, feats, params, target)
        out.append((mae(p, b.y), mae(b["last"], b.y), mae(b.lag24, b.y)))
    return np.mean(out, axis=0).tolist() if out else [np.nan] * 3


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="PB-LHE")
    ap.add_argument("--split", default="2026-10-27T00:00:00Z")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)

    act = ff.load_actual(a.city)
    rows = ff.build_rows(act, ff.FcLookup("open_meteo_cams_forecast", a.city), ff.FcLookup("punjab_epa_forecast", a.city))
    split = pd.Timestamp(a.split)
    train = rows[(rows.origin < split) & (rows.target < split)].reset_index(drop=True)
    test = rows[rows.origin >= split].reset_index(drop=True)
    res: dict = {"split": a.split, "train_origins": int(train.origin.nunique()), "test_origins": int(test.origin.nunique()),
                 "bands": {}}
    no_cams = [f for f in BASE_FEATS if f not in ("cams", "epa")]

    for lo, hi in BANDS:
        name = f"{lo}-{hi} h"
        tr = train[(train.h >= lo) & (train.h <= hi)].reset_index(drop=True)
        te = test[(test.h >= lo) & (test.h <= hi)].reset_index(drop=True)
        base = {"persistence": mae(te["last"], te.y), "yesterday": mae(te.lag24, te.y)}
        out: dict = {"n_train_rows": len(tr), "n_test_rows": len(te), "baseline_mae": base, "variants": {}}

        variants = {
            "default": (BASE_FEATS, DEFAULT, "abs"),
            "strong_reg": (BASE_FEATS, STRONG, "abs"),
            "relative_target": (BASE_FEATS, DEFAULT, "rel"),
            "relative_target_strong": (BASE_FEATS, STRONG, "rel"),
            "no_cams_epa": (no_cams, DEFAULT, "abs"),
            "no_cams_epa_strong_rel": (no_cams, STRONG, "rel"),
        }
        for v, (feats, params, tgt) in variants.items():
            p_te, p_tr = lgb_fit_predict(tr, te, feats, params, tgt)
            cv = block_cv(tr, feats, params, (lo, hi), target=tgt)
            out["variants"][v] = {
                "mae_in_sample": round(mae(p_tr, tr.y), 2), "mae_cv_inside_training": round(cv[0], 2),
                "cv_persistence": round(cv[1], 2), "cv_yesterday": round(cv[2], 2),
                "mae_test": round(mae(p_te, te.y), 2),
                "skill_vs_persistence": round(1 - mae(p_te, te.y) / base["persistence"], 3),
                "skill_vs_yesterday": round(1 - mae(p_te, te.y) / base["yesterday"], 3),
            }
        # learning curve for the default and the strong model
        origins = np.array(sorted(tr.origin.unique()))
        lc = {}
        for frac in (0.25, 0.5, 0.75, 1.0):
            sel = tr[tr.origin.isin(origins[: max(2, int(len(origins) * frac))])]
            if len(sel) < 100:
                continue
            p, _ = lgb_fit_predict(sel, te, BASE_FEATS, DEFAULT, "abs")
            q, _ = lgb_fit_predict(sel, te, no_cams, STRONG, "rel")
            lc[str(frac)] = {"default_test_mae": round(mae(p, te.y), 2), "strong_rel_test_mae": round(mae(q, te.y), 2),
                             "n_rows": len(sel)}
        out["learning_curve"] = lc
        # error by level of the last value, to see whether the loss is concentrated where the model never trained
        p, _ = lgb_fit_predict(tr, te, BASE_FEATS, DEFAULT, "abs")
        lvl = pd.cut(te["last"], [0, 200, 300, 400, 600], labels=["<=200", "200-300", "300-400", ">400"])
        lv = {}
        for L in lvl.cat.categories:
            m = (lvl == L).values
            if m.sum() >= 30:
                lv[str(L)] = {"n": int(m.sum()), "lgbm": round(mae(p[m], te.y[m]), 1),
                              "persistence": round(mae(te["last"][m], te.y[m]), 1),
                              "yesterday": round(mae(te.lag24[m], te.y[m]), 1),
                              "share_of_train_rows": round(float((tr["last"].between(*[(0, 200), (200, 300), (300, 400), (400, 600)][list(lvl.cat.categories).index(L)])).mean()), 3)}
        out["by_level_of_last"] = lv
        res["bands"][name] = out

        print(f"\n== {name}  train rows {len(tr)}, test rows {len(te)}  | persistence {base['persistence']:.1f}  yesterday {base['yesterday']:.1f}")
        print(f"{'variant':<26}{'in-sample':>10}{'CV(train)':>10}{'test':>8}{'vs pers':>9}{'vs yest':>9}")
        for v, r in out["variants"].items():
            print(f"{v:<26}{r['mae_in_sample']:>10}{r['mae_cv_inside_training']:>10}{r['mae_test']:>8}{r['skill_vs_persistence']:>+9.2f}{r['skill_vs_yesterday']:>+9.2f}")
        print("learning curve (test MAE):", {k: (v['default_test_mae'], v['strong_rel_test_mae']) for k, v in lc.items()})
        print("by level of last value:", lv)

    if not a.no_write:
        p = ff.OUT / f"forecast_diagnose_{date.today()}.json"
        ff.OUT.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, indent=1), encoding="utf-8")
        print("\nwritten", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

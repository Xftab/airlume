r"""Model A v2: next-day Lahore PM2.5, classical against deep models, scored against simple baselines
on winter as well as summer.   (17 Nov 2026)

    python scripts\model_a_v2.py                 # needs torch and lightgbm in the venv
    python scripts\model_a_v2.py --seeds 3       # quicker

What changed from scripts\model_a_baselines.py and model_a_neural.py, and why
* Calendar-correct lags. The old table shifted by ROW. EPD bulletins have gaps (52 gaps, one of 198
  days), so 55 of 657 rows had a "yesterday" that was an earlier date, and "the last 7 rows" were
  not 7 days. Here a lag exists only if that calendar day was observed. Every model is scored on the
  SAME rows: days whose previous 7 calendar days were all observed (437 days).
* Winter is tested. The old test was April to August 2024 (low smog, mean PM2.5 about 56). Folds are
  forward-chained (train on everything before the test season, nothing after):
      W2021-22 (Nov to Feb), W2022-23 (Nov, Dec; no Jan, Feb data), W2023-24 (Nov to Feb), and the old Summer 2024.
  The headline is the pooled winter folds; summer is reported beside it, not pooled in.
* Baselines: persistence (yesterday), 3-day mean, 7-day mean, same-calendar-month mean of training.
* Models: ridge, LightGBM, MLP, GRU, LSTM, TCN (dilated causal convolutions), N-BEATS-lite, and the
  average of ridge and LightGBM (a forecast combination, fixed in advance). Deep models are 5-seed
  ensembles (averaged in log space), early-stopped on the last 20% of the training rows in time order.
* All learned models predict log(PM2.5 today) - log(PM2.5 yesterday), so each starts at persistence and
  must earn any improvement. Loss: L1. Hyperparameters are fixed below, not tuned on any test fold.
* Weather of the TARGET day (ERA5) is a feature, as in the earlier Model A. That is a "perfect
  prognosis" assumption: in use it would be a weather FORECAST. Results with it are therefore an upper
  bound; the same models are also run without any weather ("no_weather") to show what weather adds.
* Intervals: moving-block bootstrap over test days (7-day blocks, 2000 resamples). Skill = 1 - MAE(model)
  / MAE(baseline) on the same days, so 0 means no better than the baseline.

Outputs: data\eval\model_a_v2_<date>.json and data\eval\model_a_v2_predictions_<date>.csv
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
FEATS = ROOT / "data" / "features" / "lahore_daily_features.csv"
OUT = ROOT / "data" / "eval"

W = 7
WX = ["temperature_2m_mean", "relative_humidity_2m_mean", "wind_speed_10m_mean", "wind_speed_10m_max",
      "precipitation_sum", "shortwave_radiation_sum", "temp_range"]
FOLDS = [("W2021-22", "2021-11-01", "2022-02-28", "winter"), ("W2022-23", "2022-11-01", "2023-02-28", "winter"),
         ("W2023-24", "2023-11-01", "2024-02-29", "winter"), ("Summer2024", "2024-04-05", "2024-08-20", "summer")]
MIN_TRAIN = 50


def load() -> pd.DataFrame:
    d = pd.read_csv(FEATS, parse_dates=["date"]).drop_duplicates("date").set_index("date").sort_index()
    cal = pd.date_range(d.index.min(), d.index.max(), freq="D")
    d = d.reindex(cal)
    d.index.name = "date"
    return d


def build(d: pd.DataFrame):
    """One row per target day with a complete prior week. Returns frame and arrays."""
    y = d.pm25_conc
    ok = y.notna()
    for k in range(1, W + 1):
        ok &= y.shift(k).notna()
    days = d.index[ok.values]
    ly = np.log(y.clip(lower=1.0))
    seq_pm = np.stack([ly.shift(k).loc[days].values for k in range(W, 0, -1)], axis=1)        # oldest..newest
    wx = d[WX].ffill().bfill()
    wxs = (wx - wx.mean()) / wx.std()
    seq_wx = np.stack([wxs.shift(k).loc[days].values for k in range(W, 0, -1)], axis=1)         # (n, W, 7)
    stat_wx = wxs.loc[days].values                                                               # target-day weather
    doy = days.dayofyear.values
    cal = np.stack([np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)], axis=1)
    last = y.shift(1).loc[days].values
    return {
        "days": days, "y": y.loc[days].values, "last": last,
        "m3": np.mean(np.exp(seq_pm[:, -3:]), axis=1), "m7": np.mean(np.exp(seq_pm), axis=1),
        "seq_pm": seq_pm, "seq_wx": seq_wx, "stat_wx": stat_wx, "cal": cal,
        "month": days.month.values,
    }


# ---- tabular and sequence inputs -------------------------------------------------------------------
def make_inputs(D, idx, weather: bool):
    base = D["seq_pm"][idx] - D["seq_pm"][idx][:, -1:]               # log changes relative to yesterday
    lastlog = D["seq_pm"][idx][:, -1:]
    tab = [base[:, :-1], lastlog, D["cal"][idx]]
    seq = D["seq_pm"][idx][:, :, None] - D["seq_pm"][idx][:, -1:, None]
    static = [lastlog, D["cal"][idx]]
    if weather:
        tab += [D["stat_wx"][idx], D["seq_wx"][idx][:, -1, :]]
        seq = np.concatenate([seq, D["seq_wx"][idx]], axis=2)
        static += [D["stat_wx"][idx]]
    return np.concatenate(tab, axis=1), seq.astype(np.float32), np.concatenate(static, axis=1).astype(np.float32)


def target(D, idx):
    return np.log(np.clip(D["y"][idx], 1, None)) - D["seq_pm"][idx][:, -1]


# ---- models ------------------------------------------------------------------------------------------
def fit_ridge(Xtr, ytr, Xte):
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Xtr)
    return Ridge(alpha=30.0).fit(sc.transform(Xtr), ytr).predict(sc.transform(Xte))


def fit_lgbm(Xtr, ytr, Xte):
    import lightgbm as lgb
    m = lgb.LGBMRegressor(objective="l1", n_estimators=150, learning_rate=0.05, num_leaves=4, min_child_samples=15,
                          subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0, random_state=0, verbose=-1)
    return m.fit(Xtr, ytr).predict(Xte)


def nets():
    import torch
    import torch.nn as nn

    class MLP(nn.Module):
        def __init__(s, n_seq_feat, n_static, h=32, p=0.3):
            super().__init__()
            s.f = nn.Sequential(nn.Flatten(), nn.Linear(W * n_seq_feat + n_static, h), nn.ReLU(), nn.Dropout(p),
                                nn.Linear(h, h // 2), nn.ReLU(), nn.Dropout(p), nn.Linear(h // 2, 1))
        def forward(s, seq, st):
            return s.f(torch.cat([seq.flatten(1), st], 1)).squeeze(-1)

    class RNN(nn.Module):
        def __init__(s, n_seq_feat, n_static, kind, h=24, p=0.3):
            super().__init__()
            s.r = (nn.GRU if kind == "gru" else nn.LSTM)(n_seq_feat, h, batch_first=True)
            s.f = nn.Sequential(nn.Dropout(p), nn.Linear(h + n_static, 16), nn.ReLU(), nn.Linear(16, 1))
        def forward(s, seq, st):
            o, _ = s.r(seq)
            return s.f(torch.cat([o[:, -1], st], 1)).squeeze(-1)

    class TCN(nn.Module):
        def __init__(s, n_seq_feat, n_static, h=16, p=0.3):
            super().__init__()
            s.c1 = nn.Conv1d(n_seq_feat, h, 3, padding=2, dilation=1)
            s.c2 = nn.Conv1d(h, h, 3, padding=4, dilation=2)
            s.f = nn.Sequential(nn.Dropout(p), nn.Linear(h + n_static, 16), nn.ReLU(), nn.Linear(16, 1))
        def forward(s, seq, st):
            x = seq.transpose(1, 2)
            x = torch.relu(s.c1(x))[:, :, :W]            # causal: drop the right padding
            x = torch.relu(s.c2(x))[:, :, :W]
            return s.f(torch.cat([x[:, :, -1], st], 1)).squeeze(-1)

    class NBeats(nn.Module):  # two residual MLP blocks on the flattened window (backcast/forecast)
        def __init__(s, n_seq_feat, n_static, h=32, p=0.3):
            super().__init__()
            d = W * n_seq_feat + n_static
            s.b1 = nn.Sequential(nn.Linear(d, h), nn.ReLU(), nn.Dropout(p), nn.Linear(h, d + 1))
            s.b2 = nn.Sequential(nn.Linear(d, h), nn.ReLU(), nn.Dropout(p), nn.Linear(h, d + 1))
        def forward(s, seq, st):
            x = torch.cat([seq.flatten(1), st], 1)
            o1 = s.b1(x); x2 = x - o1[:, :-1]
            o2 = s.b2(x2)
            return (o1[:, -1] + o2[:, -1])
    return {"MLP": MLP, "GRU": lambda a, b: RNN(a, b, "gru"), "LSTM": lambda a, b: RNN(a, b, "lstm"),
            "TCN": TCN, "N-BEATS-lite": NBeats}


def fit_deep(name, seq_tr, st_tr, ytr, seq_te, st_te, seeds):
    import torch
    import torch.nn as nn
    torch.set_num_threads(2)
    mk = nets()[name]
    sm, ss = seq_tr.reshape(-1, seq_tr.shape[2]).mean(0), seq_tr.reshape(-1, seq_tr.shape[2]).std(0) + 1e-6
    tm, ts = st_tr.mean(0), st_tr.std(0) + 1e-6
    f = lambda s, t: (torch.tensor((s - sm) / ss, dtype=torch.float32), torch.tensor((t - tm) / ts, dtype=torch.float32))
    n = len(ytr); nv = max(8, int(0.2 * n))
    a, b = np.arange(n - nv), np.arange(n - nv, n)           # time-ordered validation tail, never the test fold
    S, T = f(seq_tr, st_tr); Y = torch.tensor(ytr, dtype=torch.float32)
    Se, Te = f(seq_te, st_te)
    preds = []
    for sd in range(seeds):
        torch.manual_seed(sd)
        m = mk(seq_tr.shape[2], st_tr.shape[1])
        opt = torch.optim.AdamW(m.parameters(), lr=3e-3, weight_decay=1e-2)
        best, best_state, wait = 1e9, None, 0
        for ep in range(200):
            m.train()
            perm = torch.tensor(np.random.default_rng(sd * 1000 + ep).permutation(a))
            for i in range(0, len(perm), 32):
                j = perm[i:i + 32]
                opt.zero_grad()
                loss = (m(S[j], T[j]) - Y[j]).abs().mean()
                loss.backward(); opt.step()
            m.eval()
            with torch.no_grad():
                v = (m(S[b], T[b]) - Y[b]).abs().mean().item()
            if v < best - 1e-4:
                best, wait = v, 0
                best_state = {k: x.clone() for k, x in m.state_dict().items()}
            else:
                wait += 1
                if wait >= 20:
                    break
        m.load_state_dict(best_state); m.eval()
        with torch.no_grad():
            preds.append(m(Se, Te).numpy())
    return np.mean(preds, axis=0)


# ---- scoring ------------------------------------------------------------------------------------------
def boot(days, e_model, e_base, n=2000, block=7, seed=0):
    """Skill and its interval; days are sorted; resample 7-day blocks of consecutive rows."""
    k = len(days)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(k / block))
    out = []
    for _ in range(n):
        st = rng.integers(0, max(1, k - block + 1), size=nb)
        sel = np.concatenate([np.arange(s, min(s + block, k)) for s in st])[:k]
        out.append(1 - e_model[sel].sum() / e_base[sel].sum())
    return 1 - e_model.sum() / e_base.sum(), *np.percentile(out, [2.5, 97.5])


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)

    D = build(load())
    n = len(D["days"])
    print(f"rows with a complete prior week: {n}; {D['days'].min().date()} to {D['days'].max().date()}")
    rows = []
    deep = ["MLP", "GRU", "LSTM", "TCN", "N-BEATS-lite"]
    for fname, t0, t1, season in FOLDS:
        t0, t1 = pd.Timestamp(t0), pd.Timestamp(t1)
        te = np.where((D["days"] >= t0) & (D["days"] <= t1))[0]
        tr = np.where(D["days"] < t0 - pd.Timedelta(days=1))[0]
        if len(te) < 15 or len(tr) < MIN_TRAIN:
            print(f"skip {fname}: train {len(tr)}, test {len(te)}")
            continue
        month_mean = pd.Series(D["y"][tr]).groupby(D["month"][tr]).mean()
        base = {"persistence": D["last"][te], "mean3": D["m3"][te], "mean7": D["m7"][te],
                "month_mean": np.array([month_mean.get(m, D["y"][tr].mean()) for m in D["month"][te]])}  # unseen month: training mean
        res = {"fold": fname, "season": season, "n_train": len(tr), "n_test": len(te)}
        preds = {f"base:{k}": v for k, v in base.items()}
        for wx in (True, False):
            tag = "" if wx else " (no weather)"
            Xtr, sq_tr, st_tr = make_inputs(D, tr, wx)
            Xte, sq_te, st_te = make_inputs(D, te, wx)
            ytr = target(D, tr)
            lastlog = D["seq_pm"][te][:, -1]
            conv = lambda r: np.exp(lastlog + r)
            pr, pl = fit_ridge(Xtr, ytr, Xte), fit_lgbm(Xtr, ytr, Xte)
            preds["Ridge" + tag], preds["LightGBM" + tag] = conv(pr), conv(pl)
            preds["Ridge+LightGBM avg" + tag] = conv((pr + pl) / 2)
            for nm in deep:
                preds[nm + tag] = conv(fit_deep(nm, sq_tr, st_tr, ytr, sq_te, st_te, a.seeds))
            print(f"  {fname}{tag}: fitted {len(deep) + 3} models (train {len(tr)}, test {len(te)})")
        for k, v in preds.items():
            rows.append(pd.DataFrame({"fold": fname, "season": season, "date": D["days"][te], "model": k, "pred": v, "y": D["y"][te]}))
    P = pd.concat(rows, ignore_index=True)

    report = {"date": str(date.today()), "n_rows_complete_week": int(n), "folds": [f[0] for f in FOLDS], "results": {}}
    for scope, mask in [("winter pooled", P.season == "winter"), ("summer 2024", P.season == "summer")] + \
                       [(f, P.fold == f) for f in P.fold.unique()]:
        S = P[mask]
        pv = S.pivot_table(index="date", columns="model", values="pred")
        y = S.drop_duplicates("date").set_index("date").y.reindex(pv.index)
        pv = pv.dropna(subset=["base:persistence"])
        y = y.loc[pv.index]
        days = pv.index
        e = {m: np.abs(pv[m].values - y.values) for m in pv.columns}
        out = {"n_days": int(len(days)), "mean_pm25": round(float(y.mean()), 1), "models": {}}
        for m in pv.columns:
            ok = ~np.isnan(pv[m].values)
            if ok.sum() < len(days) * 0.95:
                continue
            e_m = np.where(ok, e[m], np.nan)
            r = {"mae": round(float(np.nanmean(e_m)), 2), "rmse": round(float(np.sqrt(np.nanmean(e_m ** 2) if False else np.nanmean((pv[m].values - y.values) ** 2))), 2)}
            for b in ("base:persistence", "base:mean7", "LightGBM"):
                if b != m and ok.all() and b in e:
                    s, lo, hi = boot(days, e[m], e[b])
                    r["skill_vs_" + b.split(":")[-1].lower()] = [round(s, 3), round(lo, 3), round(hi, 3)]
            out["models"][m] = r
        report["results"][scope] = out
    print()
    for scope in ("winter pooled", "summer 2024"):
        o = report["results"][scope]
        print(f"== {scope}: {o['n_days']} test days, mean PM2.5 {o['mean_pm25']}")
        print(f"{'model':<34}{'MAE':>7}{'RMSE':>7}   skill vs persistence          skill vs 7-day mean           skill vs LightGBM")
        for m, r in sorted(o["models"].items(), key=lambda kv: kv[1]["mae"]):
            sp = r.get("skill_vs_persistence"); s7 = r.get("skill_vs_mean7"); sl = r.get("skill_vs_lightgbm")
            f = lambda s: f"{s[0]:+.2f} [{s[1]:+.2f},{s[2]:+.2f}]" if s else "-"
            print(f"{m:<34}{r['mae']:>7}{r['rmse']:>7}   {f(sp):<28}{f(s7):<28}{f(sl)}")
    if not a.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"model_a_v2_{date.today()}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        P.to_csv(OUT / f"model_a_v2_predictions_{date.today()}.csv", index=False)
        print("\nwritten", OUT / f"model_a_v2_{date.today()}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

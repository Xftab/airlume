r"""Hourly 1 to 24 h forecast of Lahore city AQI: classical and deep models against both baselines.  (17 Nov 2026)

    python scripts\forecast_models_v2.py            # needs torch and lightgbm
    python scripts\forecast_models_v2.py --seeds 3

Same data, split (27 Oct 2026 00:00 UTC), embargo and test rows as scripts\forecast_fit.py, so the numbers
are directly comparable to it. Added here:
* Regularised LightGBM, one model per horizon band, fitted to the RELATIVE change y/last - 1 (the
  variant forecast_diagnose.py found most stable when the smog level rises past what training saw).
  Its hyperparameters were written down in forecast_diagnose.py before its test result was seen,
  but that result WAS seen before it was promoted to a headline candidate, so treat it as exploratory.
* Deep models, one network per architecture forecasting all 24 horizons at once: MLP, GRU, LSTM, TCN,
  N-BEATS-lite. Input: the last 48 hourly AQI values relative to the latest value, log of the latest value,
  hour of day. Output: log(y_h / last) for h = 1..24, L1 loss with a mask for missing targets. 5-seed
  ensembles, early stopping on the last 20% of training origins in time order (never the test period).
* The same blend as forecast_baseline_check.py (one weight per horizon on last value and same hour yesterday,
  fitted on training rows only).
* Skill is reported against BOTH persistence and same hour yesterday, with a moving-block bootstrap
  over forecast origins (24 h blocks, 2000 resamples). Yesterday is the baseline that matters beyond 3 h.

Output: data\eval\forecast_models_v2_<date>.json
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import forecast_diagnose as fd  # noqa: E402
import forecast_fit as ff  # noqa: E402

WIN, H = 48, 24
BANDS = {"1-3 h": (1, 3), "4-8 h": (4, 8), "9-16 h": (9, 16), "17-24 h": (17, 24), "all 1-24 h": (1, 24)}


def origin_arrays(act: pd.Series, origins):
    idx = act.index
    pos = {t: i for i, t in enumerate(idx)}
    v = act.values
    X, Y, M, L, HR = [], [], [], [], []
    for t in origins:
        i = pos[t]
        w = v[i - WIN + 1:i + 1]
        last = v[i]
        y = np.full(H, np.nan)
        for h in range(1, H + 1):
            if i + h < len(v) and not np.isnan(v[i + h]):
                y[h - 1] = v[i + h]
        X.append(np.log(np.clip(w, 1, None) / last)); Y.append(y); L.append(last)
        HR.append(((t.hour + 5) % 24))
    X, Y, L, HR = np.array(X), np.array(Y), np.array(L), np.array(HR)
    st = np.stack([np.log(L) - 5.5, np.sin(2 * np.pi * HR / 24), np.cos(2 * np.pi * HR / 24)], axis=1)
    return X.astype(np.float32), Y, L, st.astype(np.float32)


def nets():
    import torch
    import torch.nn as nn

    class MLP(nn.Module):
        def __init__(s, ns, h=64, p=0.3):
            super().__init__()
            s.f = nn.Sequential(nn.Linear(WIN + ns, h), nn.ReLU(), nn.Dropout(p), nn.Linear(h, h), nn.ReLU(), nn.Dropout(p), nn.Linear(h, H))
        def forward(s, x, st):
            return s.f(torch.cat([x, st], 1))

    class RNN(nn.Module):
        def __init__(s, ns, kind, h=32, p=0.3):
            super().__init__()
            s.r = (nn.GRU if kind == "gru" else nn.LSTM)(1, h, batch_first=True)
            s.f = nn.Sequential(nn.Dropout(p), nn.Linear(h + ns, 64), nn.ReLU(), nn.Linear(64, H))
        def forward(s, x, st):
            o, _ = s.r(x[:, :, None])
            return s.f(torch.cat([o[:, -1], st], 1))

    class TCN(nn.Module):
        def __init__(s, ns, h=24, p=0.3):
            super().__init__()
            s.cs = nn.ModuleList([nn.Conv1d(1 if i == 0 else h, h, 3, padding=2 * d, dilation=d) for i, d in enumerate((1, 2, 4, 8, 16))])
            s.f = nn.Sequential(nn.Dropout(p), nn.Linear(h + ns, 64), nn.ReLU(), nn.Linear(64, H))
        def forward(s, x, st):
            z = x[:, None, :]
            for c in s.cs:
                z = torch.relu(c(z))[:, :, :WIN]      # causal: keep the first WIN outputs
            return s.f(torch.cat([z[:, :, -1], st], 1))

    class NBeats(nn.Module):
        def __init__(s, ns, h=64, p=0.3):
            super().__init__()
            d = WIN + ns
            s.b = nn.ModuleList([nn.Sequential(nn.Linear(d, h), nn.ReLU(), nn.Dropout(p), nn.Linear(h, d + H)) for _ in range(3)])
            s.d = d
        def forward(s, x, st):
            z = torch.cat([x, st], 1); out = 0
            for b in s.b:
                o = b(z); z = z - o[:, :s.d]; out = out + o[:, s.d:]
            return out
    return {"MLP": MLP, "GRU": lambda ns: RNN(ns, "gru"), "LSTM": lambda ns: RNN(ns, "lstm"), "TCN": TCN, "N-BEATS-lite": NBeats}


def fit_deep(name, Xtr, Str, Ytr, Ltr, Xte, Ste, seeds):
    import torch
    torch.set_num_threads(2)
    mk = nets()[name]
    sm, ss = Str.mean(0), Str.std(0) + 1e-6
    f = lambda a, b: (torch.tensor(a), torch.tensor((b - sm) / ss, dtype=torch.float32))
    R = np.log(np.clip(Ytr, 1, None) / Ltr[:, None]); Mk = ~np.isnan(R)
    R = torch.tensor(np.nan_to_num(R), dtype=torch.float32); Mk = torch.tensor(Mk.astype(np.float32))
    n = len(Xtr); nv = max(10, int(0.2 * n)); a, b = np.arange(n - nv - H), np.arange(n - nv, n)   # embargo of 24 origins
    A, S = f(Xtr, Str); Ae, Se = f(Xte, Ste)
    out = []
    for sd in range(seeds):
        torch.manual_seed(sd)
        m = mk(Str.shape[1]); opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=1e-2)
        best, state, wait = 1e9, None, 0
        for ep in range(300):
            m.train(); perm = torch.tensor(np.random.default_rng(sd * 997 + ep).permutation(a))
            for i in range(0, len(perm), 32):
                j = perm[i:i + 32]; opt.zero_grad()
                loss = ((m(A[j], S[j]) - R[j]).abs() * Mk[j]).sum() / Mk[j].sum().clamp(min=1)
                loss.backward(); opt.step()
            m.eval()
            with torch.no_grad():
                v = (((m(A[b], S[b]) - R[b]).abs() * Mk[b]).sum() / Mk[b].sum().clamp(min=1)).item()
            if v < best - 1e-4:
                best, wait, state = v, 0, {k: x.clone() for k, x in m.state_dict().items()}
            else:
                wait += 1
                if wait >= 25:
                    break
        m.load_state_dict(state); m.eval()
        with torch.no_grad():
            out.append(m(Ae, Se).numpy())
    return np.mean(out, axis=0)           # mean in log space


def blend_weights(train):
    w = {}
    for h in range(1, H + 1):
        t = train[train.h == h]
        best = min(np.arange(0, 1.01, 0.05), key=lambda a: np.abs(a * t["last"] + (1 - a) * t.lag24 - t.y).mean())
        w[h] = float(best)
    return w


def skill_ci(test, col, base, n=2000, block=24, seed=0):
    origins = np.array(sorted(test.origin.unique()))
    g = {o: d for o, d in test.groupby("origin")}
    em = np.array([np.abs(g[o][col] - g[o].y).sum() for o in origins]); eb = np.array([np.abs(g[o][base] - g[o].y).sum() for o in origins])
    k = len(origins); rng = np.random.default_rng(seed); nb = int(np.ceil(k / block)); out = []
    for _ in range(n):
        st = rng.integers(0, max(1, k - block + 1), size=nb)
        sel = np.concatenate([np.arange(s, min(s + block, k)) for s in st])[:k]
        out.append(1 - em[sel].sum() / eb[sel].sum())
    return [round(1 - em.sum() / eb.sum(), 3), *[round(float(x), 3) for x in np.percentile(out, [2.5, 97.5])]]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="PB-LHE"); ap.add_argument("--split", default="2026-10-27T00:00:00Z")
    ap.add_argument("--seeds", type=int, default=5); ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)

    act = ff.load_actual(a.city)
    rows = ff.build_rows(act, ff.FcLookup("open_meteo_cams_forecast", a.city), ff.FcLookup("punjab_epa_forecast", a.city))
    split = pd.Timestamp(a.split)
    train = rows[(rows.origin < split) & (rows.target < split)].reset_index(drop=True)
    test = rows[rows.origin >= split].reset_index(drop=True)
    print(f"train {train.origin.nunique()} origins, test {test.origin.nunique()} origins")

    # classical models from forecast_fit and forecast_diagnose
    for k, v in {**ff.fit_predict(train, test), **ff.fit_predict_banded(train, test)}.items():
        test[k] = v
    test["yesterday"] = test.lag24
    w = blend_weights(train)
    test["blend"] = test.apply(lambda r: w[int(r.h)] * r["last"] + (1 - w[int(r.h)]) * r.lag24, axis=1)
    no_cams = [f for f in fd.BASE_FEATS if f not in ("cams", "epa")]
    pr = np.full(len(test), np.nan)
    for lo, hi in [(1, 3), (4, 8), (9, 16), (17, 24)]:
        tr = train[(train.h >= lo) & (train.h <= hi)].reset_index(drop=True); mk = ((test.h >= lo) & (test.h <= hi)).values
        pr[mk], _ = fd.lgb_fit_predict(tr, test[mk].reset_index(drop=True), no_cams, fd.STRONG, "rel")
    test["lightgbm_reg_rel"] = pr

    # deep models: one row per origin
    tr_orig = sorted(o for o in train.origin.unique() if o >= act.index[WIN - 1])
    te_orig = sorted(test.origin.unique())
    Xtr, Ytr_, Ltr, Str = origin_arrays(act, tr_orig)
    # training targets must precede the split (embargo): mask any target at or after it
    tgt_ts = np.array([[o + pd.Timedelta(hours=h) for h in range(1, H + 1)] for o in tr_orig])
    Ytr_[tgt_ts >= split] = np.nan
    Xte, Yte, Lte, Ste = origin_arrays(act, te_orig)
    pos = {o: i for i, o in enumerate(te_orig)}
    ri = test.origin.map(pos).values; hi_ = test.h.values.astype(int) - 1
    for nm in ("MLP", "GRU", "LSTM", "TCN", "N-BEATS-lite"):
        r = fit_deep(nm, Xtr, Str, Ytr_, Ltr, Xte, Ste, a.seeds)
        test[nm] = Lte[ri] * np.exp(r[ri, hi_])
        print("  fitted", nm)

    models = ["ridge_band", "lightgbm_band", "lightgbm_reg_rel", "blend", "MLP", "GRU", "LSTM", "TCN", "N-BEATS-lite", "cams"]
    report = {"date": str(date.today()), "split": a.split, "train_origins": len(tr_orig), "test_origins": len(te_orig),
              "blend_weights": w, "bands": {}}
    for band, (lo, hi) in BANDS.items():
        b = test[(test.h >= lo) & (test.h <= hi)].reset_index(drop=True)
        e = {"n_rows": len(b), "persistence_mae": round(float(np.abs(b["last"] - b.y).mean()), 1),
             "yesterday_mae": round(float(np.abs(b.yesterday - b.y).mean()), 1), "models": {}}
        for m in models:
            c = b.dropna(subset=[m]).reset_index(drop=True)
            if len(c) < 100:
                continue
            e["models"][m] = {"mae": round(float(np.abs(c[m] - c.y).mean()), 1),
                              "skill_vs_persistence": skill_ci(c, m, "last"), "skill_vs_yesterday": skill_ci(c, m, "yesterday")}
        report["bands"][band] = e
        print(f"\n== {band}: persistence {e['persistence_mae']}  yesterday {e['yesterday_mae']}  ({e['n_rows']} rows)")
        print(f"{'model':<18}{'MAE':>7}   vs persistence            vs yesterday")
        for m, r in sorted(e["models"].items(), key=lambda kv: kv[1]["mae"]):
            f = lambda s: f"{s[0]:+.2f} [{s[1]:+.2f},{s[2]:+.2f}]"
            print(f"{m:<18}{r['mae']:>7}   {f(r['skill_vs_persistence']):<26}{f(r['skill_vs_yesterday'])}")
    if not a.no_write:
        p = ff.OUT / f"forecast_models_v2_{date.today()}.json"
        p.write_text(json.dumps(report, indent=1), encoding="utf-8"); print("\nwritten", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""Guards for the 17 Nov 2026 forecast experiments (scripts/model_a_v2.py, forecast_models_v2.py,
forecast_diagnose.py). Synthetic data only: no archive, no network. The point of each test is a way the
experiment could be quietly wrong: a lag from the wrong calendar day, a future value leaking into an input,
or a skill figure that is not zero when the model equals the baseline."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import forecast_diagnose as fd  # noqa: E402
import forecast_models_v2 as fm  # noqa: E402
import model_a_v2 as ma  # noqa: E402


def _daily(gap_after: int | None = None) -> pd.DataFrame:
    idx = pd.date_range("2022-01-01", periods=40, freq="D")
    d = pd.DataFrame({"pm25_conc": np.arange(1.0, 41.0)}, index=idx)
    for c in ma.WX:
        d[c] = 0.0
    if gap_after is not None:
        d = d.drop(d.index[gap_after])  # one missing calendar day
    d = d.reindex(idx)
    d.index.name = "date"
    return d


def test_daily_lags_are_calendar_days_not_rows():
    d = _daily(gap_after=20)
    D = ma.build(d)
    # the missing day is 2022-01-21; no target row may have it inside its 7-day window
    missing = d.index[20]
    for day in D["days"]:
        assert not (missing <= day <= missing + pd.Timedelta(days=7)), day
    # persistence of a kept day is the value of the previous CALENDAR day
    for k, day in enumerate(D["days"]):
        assert D["last"][k] == d.pm25_conc.loc[day - pd.Timedelta(days=1)]


def test_daily_inputs_do_not_contain_the_target_day():
    D = ma.build(_daily())
    # the newest value in the history window is yesterday, the target is today
    assert np.allclose(np.exp(D["seq_pm"][:, -1]), D["y"] - 1.0)


def test_block_bootstrap_skill_is_zero_for_a_copy_of_the_baseline():
    e = np.abs(np.random.default_rng(0).normal(size=80)) + 1
    s, lo, hi = ma.boot(pd.date_range("2022-01-01", periods=80), e, e)
    assert s == 0 and lo == 0 and hi == 0


def test_blend_weights_are_valid_proportions():
    rng = np.random.default_rng(1)
    t = pd.DataFrame({"h": np.repeat(np.arange(1, 25), 10), "last": rng.uniform(50, 300, 240),
                      "lag24": rng.uniform(50, 300, 240), "y": rng.uniform(50, 300, 240)})
    w = fm.blend_weights(t)
    assert set(w) == set(range(1, 25)) and all(0.0 <= v <= 1.0 for v in w.values())


def test_hourly_deep_inputs_use_only_the_past():
    idx = pd.date_range("2026-10-01", periods=200, freq="h", tz="UTC")
    act = pd.Series(np.linspace(100, 300, 200), index=idx)
    origin = [idx[100]]
    X1, Y1, L1, S1 = fm.origin_arrays(act, origin)
    changed = act.copy()
    changed.iloc[101:] = 999.0                     # change the FUTURE only
    X2, Y2, L2, S2 = fm.origin_arrays(changed, origin)
    assert np.array_equal(X1, X2) and np.array_equal(S1, S2) and L1[0] == L2[0]
    assert not np.array_equal(Y1, Y2)               # targets do change, inputs do not
    assert Y1[0, 0] == act.iloc[101]               # h = 1 is the next hour


def test_relative_features_are_differences_from_the_last_value():
    d = pd.DataFrame({"last": [100.0, 200.0], "mean3": [110.0, 190.0], "d3": [1.0, 2.0], "lag24": [90.0, 220.0],
                      "hs": [0.0, 0.0], "hc": [1.0, 1.0], "h": [3, 3], "cams": [120.0, np.nan], "epa": [np.nan, np.nan]})
    x = fd.rel(d, fd.BASE_FEATS)
    assert list(x["lag24"]) == [-10.0, 20.0] and list(x["mean3"]) == [10.0, -10.0]


def test_deep_models_run_and_return_one_value_per_origin():
    pytest.importorskip("torch")
    rng = np.random.default_rng(0)
    n = 60
    X = rng.normal(size=(n, fm.WIN)).astype(np.float32) * 0.1
    S = rng.normal(size=(n, 3)).astype(np.float32)
    L = rng.uniform(100, 300, n)
    Y = L[:, None] * np.exp(rng.normal(scale=0.1, size=(n, fm.H)))
    for name in ("MLP", "GRU", "TCN"):
        out = fm.fit_deep(name, X, S, Y, L, X[:5], S[:5], seeds=1)
        assert out.shape == (5, fm.H) and np.isfinite(out).all()

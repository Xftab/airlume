"""CAMS-vs-ground agreement (plan 4.3)."""

import numpy as np
import pandas as pd
import pytest

from airlume import validation as v

T0 = pd.Timestamp("2026-10-15T00:00:00Z")


def _data(n_hours=24, stations=("A", "B"), cams_offset=-10.0, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    hours = [T0 + pd.Timedelta(hours=h) for h in range(n_hours)]
    truth = 60 + 30 * np.sin(np.arange(n_hours) / 24 * 2 * np.pi)
    r = pd.DataFrame([{"station_id": s, "ts": t, "pm25": truth[i] + (5 if s == "B" else 0),
                       "pm10": truth[i] * 2, "source": "punjab_epa"}
                      for i, t in enumerate(hours) for s in stations])
    c = pd.DataFrame([{"city_id": "PB-LHE", "ts": t,
                       "pm25": truth[i] + cams_offset + rng.normal(0, noise) if noise else truth[i] + cams_offset,
                       "pm10": truth[i] * 2 + cams_offset, "aqi": 999, "source": "open_meteo_cams"}
                      for i, t in enumerate(hours)])
    return r, c


def test_pairs_each_station_hour_with_the_same_hour_of_cams():
    r, c = _data()
    m = v.pair(r, c)
    assert len(m) == 48
    row = m[(m.station_id == "A") & (m.ts == T0)].iloc[0]
    assert row.cams_pm25 == pytest.approx(row.pm25 - 10)


def test_cams_us_aqi_column_is_never_used():
    """The stored CAMS `aqi` is Open-Meteo's US AQI. Comparing it with the portal
    would reintroduce the W1 table mismatch; CAMS AQI is recomputed on pk_portal."""
    r, c = _data()
    m = v.pair(r, c)
    assert (m["aqi_pm_cams"] != 999).all()
    assert "aqi" not in m.columns


def test_aqi_is_pm_only_on_both_sides():
    """CAMS has no gases, so the station side is recomputed from PM too."""
    r, c = _data()
    r["o3"] = 400.0            # a huge ozone value must not reach the station AQI here
    m = v.pair(r, c)
    from airlume.aqi import aqi_from_concentrations
    row = m.iloc[0]
    assert row.aqi_pm_station == aqi_from_concentrations(row.pm25, row.pm10)[0]


def test_bias_sign_is_cams_minus_station():
    r, c = _data(cams_offset=-10.0)
    a = v.agreement(v.pair(r, c), "pm25", "cams_pm25")
    assert a.bias < 0          # CAMS reads low
    assert a.mad >= abs(a.bias)


def test_perfect_timing_gives_correlation_one():
    r, c = _data(stations=("A",), cams_offset=-10.0)
    a = v.agreement(v.pair(r, c), "pm25", "cams_pm25")
    assert a.r == pytest.approx(1.0)
    assert a.mad == pytest.approx(10.0)


def test_intervals_come_from_hours_not_station_rows():
    """Eleven stations share one CAMS value per hour; resampling station-rows would
    pretend there is eleven times more independent information than there is."""
    r, c = _data(n_hours=36, stations=tuple("ABCDEFGHIJK"), noise=8.0)
    a = v.agreement(v.pair(r, c), "pm25", "cams_pm25")
    assert a.n == 36 * 11 and a.n_hours == 36
    lo, hi = a.bias_ci
    assert lo < a.bias < hi
    assert hi - lo > 0.5       # not collapsed to a point by 396 fake-independent rows


def test_no_interval_from_too_few_hours():
    r, c = _data(n_hours=8)
    a = v.agreement(v.pair(r, c), "pm25", "cams_pm25")
    assert a.mad_ci is None and a.bias_ci is None


def test_city_mean_compares_the_area_average_with_the_cell():
    r, c = _data()             # station B reads 5 higher than A
    cm = v.city_mean(v.pair(r, c))
    assert len(cm) == 24
    assert (cm["n_stations"] == 2).all()
    row = cm.iloc[0]
    assert row.pm25 == pytest.approx((2 * (row.cams_pm25 + 10) + 5) / 2)


def test_by_station_and_by_hour_shapes():
    r, c = _data()
    m = v.pair(r, c)
    bs = v.by_station(m, "pm25", "cams_pm25")
    assert set(bs.station_id) == {"A", "B"}
    assert bs.iloc[0].mad <= bs.iloc[1].mad          # sorted by agreement
    bh = v.by_hour_of_day(m, "pm25", "cams_pm25")
    assert set(bh.hour_pkt) == set(range(24))


def test_too_little_data_returns_none():
    r, c = _data(n_hours=1, stations=("A",))
    assert v.agreement(v.pair(r, c), "pm25", "cams_pm25") is None

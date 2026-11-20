"""Experiment A: snapshot freezing, gold-answer functions and the statistics.

Every expected number below is worked out by hand from tests/expA_synth.py.
"""
import math

import pandas as pd
import pytest

from airlume.eval.expA.normalize import Answer
from airlume.eval.expA.reference import Reference, evaluate_reference, parse_reference
from airlume.eval.expA.score import invented_check, judge, mcnemar_exact, paired, wilson
from airlume.eval.expA.snapshot import SHIFT, freeze, snapshot_id, verify
from expA_synth import CUTOFF, frames


@pytest.fixture(scope="module")
def snap(tmp_path_factory, registry):
    return freeze(CUTOFF, name="synth", root=tmp_path_factory.mktemp("expA"), registry=registry, frames=frames())


@pytest.fixture(scope="module")
def ref(snap):
    return Reference(snap.tables(), snap.now())


@pytest.fixture(scope="module")
def ref_shifted(snap):
    return Reference(snap.shifted.tables(), snap.now())


# --------------------------------------------------------------------------- snapshot

def test_snapshot_cutoff_rows_and_manifest(snap):
    m = snap.manifest()
    assert m["cutoff_local"].startswith("2026-11-20T12:00:00+05:00")
    assert str(snap.now()) == "2026-11-20 12:00:00+05:00"
    t = snap.tables()
    assert t["station_hourly"]["ts_local"].max() == pd.Timestamp("2026-11-20 11:00")
    assert set(t["city_hourly"]["city"]) == {"Lahore", "Multan", "Bahawalpur", "Faisalabad"}  # no CAMS rows
    assert set(t["forecast"]["source"]) == {"EPA Punjab", "CAMS model"}
    assert m["rows"]["areas"] > 20 and "Model Town" in set(t["areas"]["area"])
    assert verify(snap) == [] and len(snapshot_id(snap)) == 10


def test_shifted_copy_adds_the_shift(snap):
    a, b = snap.tables(), snap.shifted.tables()
    for table in ("station_hourly", "city_hourly"):
        for col, d in SHIFT.items():
            diff = (b[table][col] - a[table][col]).dropna()
            assert len(diff) and (diff - d).abs().max() < 1e-9, (table, col)
    assert ((b["forecast"]["aqi"] - a["forecast"]["aqi"]) == SHIFT["aqi"]).all()
    assert (b["station_hourly"]["ts_local"] == a["station_hourly"]["ts_local"]).all()


def test_snapshot_is_frozen_and_tamper_evident(snap, registry, tmp_path):
    with pytest.raises(FileExistsError):
        freeze(CUTOFF, name="synth", root=snap.root.parent, registry=registry, frames=frames())
    s = freeze(CUTOFF, name="tamper", root=tmp_path, registry=registry, frames=frames())
    p = s.tables_dir / "city_hourly.csv"
    p.write_text(p.read_text(encoding="utf-8").replace(",230", ",231", 1), encoding="utf-8")
    assert verify(s) == ["changed tables/city_hourly.csv"]
    with pytest.raises(ValueError):
        freeze("2026-11-20T12:00:00", name="naive", root=tmp_path, registry=registry, frames=frames())


# --------------------------------------------------------------------------- windows and gold

def test_windows(ref):
    n = pd.Timestamp("2026-11-20 12:00")
    assert ref.window("now") == (n - pd.Timedelta(hours=3), n)
    assert ref.window("today") == (pd.Timestamp("2026-11-20"), n)
    assert ref.window("yesterday") == (pd.Timestamp("2026-11-19"), pd.Timestamp("2026-11-20"))
    assert ref.window("last_7_days") == (pd.Timestamp("2026-11-13"), n)
    assert ref.window("last_30_days") == (pd.Timestamp("2026-10-21"), n)
    assert ref.window("this_month") == (pd.Timestamp("2026-11-01"), n)
    assert ref.window("last_month") == (pd.Timestamp("2026-10-01"), pd.Timestamp("2026-11-01"))
    assert ref.window("date:2026-11-15") == (pd.Timestamp("2026-11-15"), pd.Timestamp("2026-11-16"))
    assert ref.window("range:2026-11-10:2026-11-12") == (pd.Timestamp("2026-11-10"), pd.Timestamp("2026-11-13"))
    with pytest.raises(ValueError):
        ref.window("next_week")


def test_latest_respects_three_hour_freshness(ref):
    g = ref.station_latest("GT Road")
    assert (g.kind, g.place, g.value) == ("answer", "GT Road", 222.0)
    assert ref.station_latest("GT Road", "pm25").value == 111.0
    assert ref.station_latest("Kahna Nau").kind == "no_data"    # last reading 06:00, six hours old
    assert ref.station_latest("Shahdara").kind == "no_data"     # no rows at all
    assert ref.city_latest("Lahore").value == 240.0             # EPA, never the CAMS 500
    assert ref.city_latest("Multan", "pm25").kind == "no_data"
    assert ref.city_latest("Faisalabad").kind == "no_data"      # stops at 19 Nov 23:00
    assert ref.city_latest("Karachi").kind == "no_data"


def test_window_aggregates(ref):
    assert ref.station_agg("GT Road", "today", "mean").value == 211.0
    assert ref.station_agg("GT Road", "yesterday", "max").value == 246.0
    assert ref.station_agg("GT Road", "yesterday", "min").value == 200.0
    g = ref.station_agg("Kahna Nau", "yesterday", "count_above", threshold=300)
    assert (g.value, g.unit, g.n) == (17.0, "hours", 24)
    zero = ref.hours_above("Safari Park", "yesterday", 300)
    assert (zero.kind, zero.value) == ("answer", 0.0)            # zero hours is an answer
    assert ref.city_agg("Lahore", "today", "mean").value == pytest.approx(2770 / 12)
    assert ref.city_agg("Lahore", "last_7_days", "mean").value == pytest.approx((179 * 230 + 240) / 180)
    assert ref.city_agg("Lahore", "last_month").kind == "no_data"
    with pytest.raises(ValueError):
        ref.station_agg("GT Road", "today", "count_above")       # needs a threshold


def test_rankings_and_comparisons(ref):
    g = ref.rank_stations("now", order="worst")
    assert (g.place, g.value) == ("GT Road", 222.0)              # stale Kahna Nau is not "now"
    assert ref.rank_stations("now", order="cleanest").place == "Safari Park"
    g = ref.rank_stations("yesterday", order="worst")
    assert (g.place, g.value) == ("Kahna Nau", pytest.approx(6320 / 24))
    assert ref.rank_cities("now", order="worst").place == "Lahore"
    assert ref.rank_cities("yesterday", order="worst").place == "Faisalabad"
    g = ref.compare_places("Multan", "Bahawalpur", "this_month", ask="cleaner")
    assert (g.place, g.value, g.pair) == ("Bahawalpur", 170.0, {"Multan": 180.0, "Bahawalpur": 170.0})
    assert ref.compare_places("Multan", "Bahawalpur", "now").place == "Multan"
    assert ref.compare_places("Multan", "Faisalabad", "now").kind == "no_data"
    g = ref.compare_time("Lahore", "now", "yesterday")
    assert g.value == pytest.approx(2770 / 12) and g.previous == 230.0


def test_forecast_hours_and_areas(ref, registry):
    g = ref.forecast_mean("Lahore")
    assert (g.value, g.n) == (260.0, 24)                         # the 11:00 issue, not the 10:00 one
    assert ref.forecast_mean("Multan").kind == "no_data"
    assert ref.peak_hour("GT Road").value == 23.0
    assert ref.peak_hour("GT Road", lowest=True).value == 0.0
    assert ref.peak_hour("Lahore").value == 11.0
    station_id, note = registry.match_station("Model Town", "PB-LHE")
    app_choice = next(s.name for s in registry.stations if s.station_id == station_id)
    assert note and ref.place("area:Model Town") == ("station", app_choice)   # same nearest station as the app
    assert ref.place("gt road") == ("station", "GT Road")
    with pytest.raises(ValueError):
        ref.place("Hyderabad")


def test_gold_moves_with_the_shift(ref, ref_shifted):
    assert ref_shifted.station_latest("GT Road").value == 229.0
    assert ref_shifted.forecast_mean("Lahore").value == 267.0
    assert ref_shifted.hours_above("Safari Park", "yesterday", 300).value == 0.0  # counts need not move


def test_reference_text_is_parsed_never_executed(ref):
    assert evaluate_reference('hours_above("Kahna Nau", "yesterday", 300)', ref).value == 17.0
    assert evaluate_reference("refuse()", ref).kind == "refuse"
    for bad in ('__import__("os").system("echo hi")', 'ref.window("now")', "city_latest(x)",
                'city_latest(**{"city": "Multan"})', "open('x')", "1 + 1", 'city_latest("Multan"); refuse()'):
        with pytest.raises(ValueError):
            parse_reference(bad)


# --------------------------------------------------------------------------- judging

def _gold(**kw):
    base = {"kind": "answer", "place": None, "value": None, "unit": "aqi", "previous": None,
            "tie_places": [], "which": None, "pair": {}}
    base.update(kw)
    return base


def test_judge_kinds_places_and_tolerance():
    g = _gold(place="GT Road", value=222.0)
    assert judge(g, Answer("answer", place="gt road", value=222.4))["correct"]
    assert judge(g, Answer("answer", place="GT Road", value=223.0))["correct"]       # one display unit
    assert not judge(g, Answer("answer", place="GT Road", value=223.5))["correct"]
    assert not judge(g, Answer("answer", place="Shahdara", value=222.0))["correct"]
    assert not judge(g, Answer("no_data"))["correct"]
    assert judge(_gold(kind="refuse"), Answer("refuse"))["correct"]
    assert not judge(_gold(kind="clarify"), Answer("refuse"))["correct"]
    pm = _gold(place="GT Road", value=111.0, unit="pm25")
    assert judge(pm, Answer("answer", place="GT Road", value=111.1))["correct"]
    assert not judge(pm, Answer("answer", place="GT Road", value=111.2))["correct"]
    hrs = _gold(place="Kahna Nau", value=17.0, unit="hours")
    assert not judge(hrs, Answer("answer", place="Kahna Nau", value=16.0))["correct"]


def test_judge_ties_previous_pairs_and_hours():
    tie = _gold(place="A", value=5.0, tie_places=["A", "B"])
    assert judge(tie, Answer("answer", place="B", value=5.0))["correct"]
    prev = _gold(place="Lahore", value=230.8, previous=230.0)
    assert judge(prev, Answer("answer", place="Lahore", value=231.0, previous=230.0))["correct"]
    assert not judge(prev, Answer("answer", place="Lahore", value=231.0))["correct"]
    pair = _gold(place="Bahawalpur", value=170.0, pair={"Multan": 180.0, "Bahawalpur": 170.0})
    worse_named = Answer("answer", place="Multan", value=180.0, pair={"Multan": 180.0, "Bahawalpur": 170.0})
    assert judge(pair, worse_named)["correct"]                     # both figures stated correctly
    assert not judge(pair, Answer("answer", place="Multan", value=180.0))["correct"]
    hour = _gold(place="GT Road", value=0.0, unit="hour", which="lowest")
    assert judge(hour, Answer("answer", place="GT Road", unit="hour", hours_profile={"lowest": 0, "highest": 23}))["correct"]
    assert judge(hour, Answer("answer", place="GT Road", value=0.0, unit="hour"))["correct"]


def test_invented_number_check():
    g0, g1 = _gold(place="GT Road", value=222.0), _gold(place="GT Road", value=229.0)
    computed = invented_check(g0, g1, Answer("answer", value=222.0), Answer("answer", value=229.0), 7, True)
    assert computed == {"testable": True, "invented": False, "off_shift": False}
    written_in = invented_check(g0, g1, Answer("answer", value=222.0), Answer("answer", value=222.0), 7, True)
    assert written_in["invented"]
    odd = invented_check(g0, g1, Answer("answer", value=222.0), Answer("answer", value=236.0), 7, True)
    assert odd == {"testable": True, "invented": False, "off_shift": True}
    flat = _gold(place="Safari Park", value=0.0, unit="hours")
    assert not invented_check(flat, flat, Answer("answer", value=0.0), Answer("answer", value=0.0), None, False)["testable"]


# --------------------------------------------------------------------------- statistics

def _wilson_by_bisection(k, n, z=1.959963984540054):
    """Independent check: the Wilson bounds are where |k/n - p| = z sqrt(p(1-p)/n)."""
    ph = k / n

    def f(p):
        return abs(ph - p) - z * math.sqrt(p * (1 - p) / n)

    def root(lo, hi):
        for _ in range(200):
            mid = (lo + hi) / 2
            if (f(lo) > 0) == (f(mid) > 0):
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    low = 0.0 if k == 0 else root(1e-12, ph)
    high = 1.0 if k == n else root(ph, 1 - 1e-12)
    return low, high


@pytest.mark.parametrize("k,n", [(85, 100), (26, 30), (255, 300), (0, 12), (12, 12), (1, 3)])
def test_wilson_matches_definition(k, n):
    p, lo, hi = wilson(k, n)
    elo, ehi = _wilson_by_bisection(k, n)
    assert p == k / n and lo == pytest.approx(elo, abs=1e-9) and hi == pytest.approx(ehi, abs=1e-9)
    assert math.isnan(wilson(0, 0)[0])


def test_wilson_half_widths_quoted_in_the_protocol():
    for n, half in ((30, 0.13), (100, 0.07), (300, 0.04)):
        _, lo, hi = wilson(round(0.85 * n), n)
        assert abs((hi - lo) / 2 - half) < 0.01, n


def test_mcnemar_exact():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0
    assert mcnemar_exact(10, 0) == pytest.approx(2 / 1024)
    assert mcnemar_exact(1, 9) == pytest.approx(2 * 11 / 1024)


def test_newcombe_paired_interval():
    same = paired([True] * 8 + [False] * 2, [True] * 8 + [False] * 2)
    assert (same.diff, same.b, same.c, same.p_mcnemar) == (0.0, 0, 0, 1.0)
    assert same.low <= 0.0 <= same.high
    first = [True] * 30 + [True] * 10 + [False] * 2 + [False] * 8
    second = [True] * 30 + [False] * 10 + [True] * 2 + [False] * 8
    p = paired(first, second)
    assert (p.a, p.b, p.c, p.d, p.n) == (30, 10, 2, 8, 50)
    assert p.diff == pytest.approx(0.16)
    assert p.low < p.diff < p.high and -1 <= p.low and p.high <= 1
    # the paired interval is narrower than the unpaired Newcombe interval would be
    _, l1, u1 = wilson(40, 50)
    _, l2, u2 = wilson(32, 50)
    unpaired_low = 0.16 - math.sqrt((0.8 - l1) ** 2 + (u2 - 0.64) ** 2)
    assert p.low > unpaired_low
    assert paired([], []).n == 0

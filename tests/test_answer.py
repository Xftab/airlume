from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from airlume.nl.answer import answer
from airlume.nl.resolve import resolve
from airlume.nl.stub_router import route
from airlume.pipeline.fake import fake_city_hourly, fake_readings
from airlume.pipeline.store import Store

END = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 13, 17, 30, tzinfo=ZoneInfo("Asia/Karachi"))


def _store(tmp_path, registry):
    s = Store(tmp_path / "a.duckdb")
    r = fake_readings(registry, hours=24 * 10, end=END)
    s.upsert_readings(r)
    s.upsert_city_hourly(fake_city_hourly(registry, r, hours=24 * 10, end=END))
    return s


def test_threshold_answer(tmp_path, registry):
    s = _store(tmp_path, registry)
    q = resolve(route("How many hours was the AQI above 100 in Shahdara last week?"), registry, NOW)
    a = answer(q, s, registry)
    assert a.startswith("Hours with AQI above 100") and "Shahdara" in a


def test_worst_now_mentions_missing(tmp_path, registry):
    s = _store(tmp_path, registry)
    q = resolve(route("Where is the air worst in Lahore right now?"), registry, NOW)
    a = answer(q, s, registry)
    assert "Worst right now" in a and "cleanest" in a


def test_city_compare(tmp_path, registry):
    s = _store(tmp_path, registry)
    q = resolve(route("Which city has worse air today, Lahore or Faisalabad?"), registry, NOW)
    a = answer(q, s, registry)
    assert "Faisalabad" in a and "is worse right now" in a


# ---- archive coverage (1 Nov 2026) -----------------------------------------
from airlume.nl.schema import TimeSpec, ViewIntent  # noqa: E402


def test_store_archive_bounds(tmp_path, registry):
    s = _store(tmp_path, registry)
    lo, hi = s.archive_bounds()
    assert lo < hi and hi.tz is not None
    assert Store(tmp_path / "empty.duckdb").archive_bounds() == (None, None)


def test_hallucinated_2023_date_is_reported_not_answered(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(time=TimeSpec(label="custom_date", date="2023-11-05"), aggregation="mean")
    a = answer(resolve(v, registry, NOW), s, registry)
    assert a.startswith("No data:") and "2023" in a and "Oct 2026" in a


def test_window_starting_before_archive_gets_a_note(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(time=TimeSpec(label="last_30_days"), aggregation="mean")
    a = answer(resolve(v, registry, NOW), s, registry)
    assert "Worst" in a and "hourly archive only starts at" in a


def test_window_inside_archive_has_no_note(tmp_path, registry):
    s = _store(tmp_path, registry)
    q = resolve(route("How many hours was the AQI above 100 in Shahdara last week?"), registry, NOW)
    a = answer(q, s, registry)
    assert a.startswith("Hours with AQI above 100") and "archive" not in a


def test_comparison_window_outside_archive_is_noted(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(time=TimeSpec(label="today"), aggregation="mean", compare_to="last_year", view="compare")
    a = answer(resolve(v, registry, NOW), s, registry)
    assert "the comparison window" in a and "falls outside the hourly archive" in a


# ---- city-level answers honour the window (1 Nov 2026) ---------------------
def _rng(a="2026-10-05", b="2026-10-08"):
    return TimeSpec(label="custom_range", start=a, end=b)


def test_other_city_window_is_not_the_current_value(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(city="Faisalabad", time=_rng(), aggregation="mean", metric="aqi")
    q = resolve(v, registry, NOW)
    a = answer(q, s, registry)
    ser = s.city_series("PB-FSD", q.start, q.end, "aqi")
    assert a.startswith("Faisalabad: mean AQI ")
    assert f"{ser['value'].mean():.0f}" in a and f"over {len(ser)} h" in a
    assert "05 Oct" in a and "right now" not in a


def test_other_city_count_hours_above(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(city="Multan", time=_rng(), aggregation="count_hours_above", threshold=100)
    q = resolve(v, registry, NOW)
    a = answer(q, s, registry)
    ser = s.city_series("PB-MUX", q.start, q.end, "aqi")
    assert f"hours with AQI above 100 {int((ser['value'] > 100).sum())} over" in a


def test_two_city_window_comparison(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(city="Lahore", time=_rng(), aggregation="mean", compare_to="other_city",
                   other_city="Faisalabad", view="compare")
    a = answer(resolve(v, registry, NOW), s, registry)
    assert "Lahore: mean AQI" in a and "Faisalabad:" in a and a.endswith(("is worse.", "is cleaner."))


def test_city_overview_over_window_ranks_cities(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(time=_rng(), aggregation="max", view="city_overview")
    a = answer(resolve(v, registry, NOW), s, registry)
    assert " had the worst air over " in a and "cities have data" in a


def test_city_window_comparison_with_earlier_window(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(city="Faisalabad", time=_rng("2026-10-08", "2026-10-10"), aggregation="mean",
                   compare_to="last_week")
    a = answer(resolve(v, registry, NOW), s, registry)
    assert "Comparison window:" in a or "No data for the comparison window" in a


def test_city_with_no_rows_in_window_is_named(tmp_path, registry):
    s = _store(tmp_path, registry)
    v = ViewIntent(city="Faisalabad", time=_rng("2026-10-15", "2026-10-16"), aggregation="mean")
    a = answer(resolve(v, registry, NOW), s, registry)
    assert a.startswith("No data:") or "No Faisalabad city data" in a


def test_current_value_path_unchanged_for_latest(tmp_path, registry):
    s = _store(tmp_path, registry)
    q = resolve(route("Which city has worse air today, Lahore or Faisalabad?"), registry, NOW)
    assert "is worse right now" in answer(q, s, registry)

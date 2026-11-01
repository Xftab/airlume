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

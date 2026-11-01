from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from airlume.nl.resolve import ResolveError, resolve, resolve_time
from airlume.nl.schema import TimeSpec, ViewIntent

NOW = datetime(2026, 10, 13, 15, 30, tzinfo=ZoneInfo("Asia/Karachi"))


def test_yesterday_bounds():
    s, e = resolve_time(ViewIntent(time=TimeSpec(label="yesterday")), NOW)
    assert s.isoformat() == "2026-10-12T00:00:00+05:00"
    assert e.isoformat() == "2026-10-13T00:00:00+05:00"


def test_last_month():
    s, e = resolve_time(ViewIntent(time=TimeSpec(label="last_month")), NOW)
    assert (s.month, s.day, e.month, e.day) == (9, 1, 10, 1)


def test_range_too_long():
    v = ViewIntent(time=TimeSpec(label="custom_range", start="2020-01-01", end="2026-01-01"))
    with pytest.raises(ResolveError):
        resolve_time(v, NOW)


def test_resolve_with_comparison(registry):
    v = ViewIntent(time=TimeSpec(label="today"), compare_to="yesterday", view="compare")
    r = resolve(v, registry, NOW)
    assert r.compare_start.day == 12 and r.start.day == 13


def test_resolve_other_city(registry):
    v = ViewIntent(compare_to="other_city", other_city="Faisalabad", view="compare")
    assert resolve(v, registry, NOW).compare_city_id == "PB-FSD"


def test_out_of_scope(registry):
    with pytest.raises(ResolveError):
        resolve(ViewIntent(in_scope=False), registry, NOW)


# ---- archive coverage (1 Nov 2026) -----------------------------------------
from datetime import timedelta, timezone  # noqa: E402

from airlume.nl.resolve import window_coverage  # noqa: E402

LO = datetime(2026, 10, 14, 4, tzinfo=timezone.utc)
HI = datetime(2026, 10, 31, 9, tzinfo=timezone.utc)


def _win(a, b):
    k = ZoneInfo("Asia/Karachi")
    return datetime(*a, tzinfo=k), datetime(*b, tzinfo=k)


def test_coverage_inside_is_silent():
    s, e = _win((2026, 10, 20), (2026, 10, 21))
    c = window_coverage(s, e, LO, HI)
    assert c.kind == "inside" and c.message == ""


def test_coverage_before_archive_is_outside():
    s, e = _win((2023, 10, 20), (2023, 10, 21))
    c = window_coverage(s, e, LO, HI)
    assert c.kind == "outside"
    assert "2023" in c.message and "14 Oct 2026" in c.message


def test_coverage_after_archive_is_outside():
    s, e = _win((2026, 11, 5), (2026, 11, 6))
    assert window_coverage(s, e, LO, HI).kind == "outside"


def test_coverage_starting_before_archive_is_partial():
    s, e = _win((2026, 10, 1), (2026, 10, 20))
    c = window_coverage(s, e, LO, HI)
    assert c.kind == "partial" and "14 Oct 2026" in c.message


def test_coverage_window_ending_at_the_clock_is_not_partial():
    # "last 7 days" ends at now, a few hours after the newest hour: ordinary, no note.
    s = HI - timedelta(days=7)
    assert window_coverage(s, HI + timedelta(hours=5), LO, HI).kind == "inside"


def test_coverage_empty_store_is_silent():
    s, e = _win((2023, 10, 20), (2023, 10, 21))
    assert window_coverage(s, e, None, None).kind == "inside"


def test_coverage_edges():
    # Ends exactly when the archive begins -> no overlap; starts exactly at lo -> inside.
    assert window_coverage(LO - timedelta(days=1), LO, LO, HI).kind == "outside"
    assert window_coverage(LO, LO + timedelta(days=1), LO, HI).kind == "inside"
    # The newest row covers [HI, HI+1h): a window starting inside that hour overlaps it.
    assert window_coverage(HI + timedelta(minutes=30), HI + timedelta(hours=3), LO, HI).kind == "inside"
    assert window_coverage(HI + timedelta(hours=1), HI + timedelta(hours=3), LO, HI).kind == "outside"

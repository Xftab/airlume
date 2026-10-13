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

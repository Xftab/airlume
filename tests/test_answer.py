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

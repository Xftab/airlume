from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from airlume.pipeline.fake import fake_city_hourly, fake_readings
from airlume.pipeline.store import Store


@pytest.fixture
def store(tmp_path, registry):
    s = Store(tmp_path / "t.duckdb")
    r = fake_readings(registry, hours=48, end=datetime(2026, 10, 13, 12, tzinfo=timezone.utc))
    s.upsert_readings(r)
    s.upsert_city_hourly(fake_city_hourly(registry, r, hours=48, end=datetime(2026, 10, 13, 12, tzinfo=timezone.utc)))
    yield s
    s.close()


def test_counts(store, registry):
    c = store.counts()
    assert c["readings"] == 11 * 48 - 3  # one station drops out for 3 hours
    assert c["city_hourly"] == 48 * len(registry.cities)


def test_upsert_is_idempotent(store, registry):
    before = store.counts()
    r = fake_readings(registry, hours=48, end=datetime(2026, 10, 13, 12, tzinfo=timezone.utc))
    store.upsert_readings(r)
    assert store.counts() == before


def test_latest_and_missing_station(store):
    df = store.latest_station_values(["LHR-GT", "LHR-GB3"])
    gt = df[df.station_id == "LHR-GT"].ts.iloc[0]
    gb = df[df.station_id == "LHR-GB3"].ts.iloc[0]
    assert gt - gb == timedelta(hours=3)


def test_aggregate_rejects_bad_metric(store):
    with pytest.raises(ValueError):
        store.aggregate(["LHR-GT"], datetime(2026, 10, 1, tzinfo=timezone.utc),
                        datetime(2026, 10, 14, tzinfo=timezone.utc), "aqi; DROP TABLE readings", "mean")


def test_count_hours_above(store):
    df = store.aggregate(["LHR-MR"], datetime(2026, 10, 11, tzinfo=timezone.utc),
                         datetime(2026, 10, 14, tzinfo=timezone.utc), "aqi", "count_hours_above", 100)
    assert int(df.value.iloc[0]) > 0

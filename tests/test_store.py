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


def test_forecasts_and_errors(store):
    import pandas as pd
    issued = datetime(2026, 10, 13, 10, tzinfo=timezone.utc)
    fc = pd.DataFrame([{"city_id": "PB-LHE", "issued_at": issued, "target_ts": issued + timedelta(hours=h),
                        "aqi": 150 + h, "source": "punjab_epa_forecast"} for h in (1, 2)])
    assert store.upsert_forecasts(fc) == 2
    store.upsert_city_hourly(pd.DataFrame([{"city_id": "PB-LHE", "ts": issued + timedelta(hours=1), "pm25": None, "pm10": None,
                                            "aqi": 140, "n_stations": None, "source": "punjab_epa"}]))
    err = store.forecast_errors("PB-LHE")
    assert len(err) == 1 and int(err.error.iloc[0]) == 11 and int(err.horizon_h.iloc[0]) == 1
    assert len(store.latest_forecast("PB-LHE")) == 2


def test_unknown_metric_is_rejected(tmp_path):
    import pytest
    from datetime import datetime, timezone
    from airlume.pipeline.store import Store
    s = Store(":memory:")
    with pytest.raises(ValueError):
        s.station_series(["PB-LHE-01"], datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc), "aqi; DROP TABLE readings")
    with pytest.raises((ValueError, KeyError)):
        s.aggregate(["PB-LHE-01"], datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc), "aqi", "sum")

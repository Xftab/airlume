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


def test_forecast_baselines_and_skill(store):
    import pandas as pd
    from airlume.forecast.skill import scorecard
    issued = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)
    hours = [issued + timedelta(hours=h) for h in range(-24, 7)]
    # actual AQI: 100 yesterday, 120 today; a forecast of 118 beats persistence (100), 90 loses
    store.upsert_city_hourly(pd.DataFrame([{"city_id": "PB-LHE", "ts": t, "pm25": None, "pm10": None,
                                            "aqi": 100 if t < issued else 120, "n_stations": None, "source": "punjab_epa"} for t in hours]))
    store.upsert_forecasts(pd.DataFrame([{"city_id": "PB-LHE", "issued_at": issued, "target_ts": issued + timedelta(hours=h),
                                          "aqi": 118, "source": "good_fc"} for h in (1, 2, 3, 4)] +
                                        [{"city_id": "PB-LHE", "issued_at": issued, "target_ts": issued + timedelta(hours=h),
                                          "aqi": 90, "source": "bad_fc"} for h in (1, 2, 3, 4)]))
    err = store.forecast_errors_with_baselines("PB-LHE")
    good = err[err.source == "good_fc"]
    assert set(good.persist_24h) == {100} and set(good.persist_last) == {120}
    sc = scorecard(err)
    assert sc.loc["good_fc", "skill_vs_same_hour_yesterday"] > 0.8
    assert sc.loc["bad_fc", "skill_vs_same_hour_yesterday"] < 0


def test_old_database_is_migrated_for_snapshot_columns(tmp_path):
    """A cache created before 15 Oct has none of the snapshot columns.

    CREATE TABLE IF NOT EXISTS leaves it alone, so without the ALTER migration the
    insert fails on the laptop's existing database while passing on a fresh one.
    """
    import duckdb
    import pandas as pd

    from airlume.pipeline.store import Store

    db = tmp_path / "old.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        """
        CREATE TABLE readings (
            station_id VARCHAR NOT NULL, ts TIMESTAMPTZ NOT NULL,
            pm25 DOUBLE, pm10 DOUBLE, co DOUBLE, so2 DOUBLE, no2 DOUBLE, o3 DOUBLE,
            aqi INTEGER, aqi_computed INTEGER, source VARCHAR NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (station_id, ts, source))
        """
    )
    con.close()

    s = Store(db)
    n = s.upsert_readings(pd.DataFrame([{
        "station_id": "LHR-GB3", "ts": pd.Timestamp("2026-10-15T10:00:00Z"),
        "pm25": 20.18, "pm10": 70.53, "co": 0.48, "so2": 3.79, "no2": 12.56, "o3": 82.39,
        "aqi": 64, "aqi_computed": 68, "source": "punjab_epa",
        "portal_station_id": 27, "portal_dominant": "O3",
        "lat": 31.507172, "lon": 74.338461,
        "temperature": 27.88, "humidity": 78.66, "wind_speed": 1.64, "wind_direction": 152.16,
    }]))
    assert n == 1
    got = s.con.execute(
        "SELECT portal_dominant, lat, wind_speed FROM readings WHERE station_id = 'LHR-GB3'"
    ).fetchone()
    s.close()
    assert got[0] == "O3"
    assert got[1] == pytest.approx(31.507172, abs=1e-5)
    assert got[2] == pytest.approx(1.64)


def test_rows_without_snapshot_columns_still_insert(tmp_path):
    """The HTML-table fallback produces none of them; they must default to null."""
    import pandas as pd

    from airlume.pipeline.store import Store

    s = Store(tmp_path / "fresh.duckdb")
    n = s.upsert_readings(pd.DataFrame([{
        "station_id": "LHR-GT", "ts": pd.Timestamp("2026-10-15T10:00:00Z"),
        "pm25": 39.0, "pm10": 70.04, "aqi": 106, "aqi_computed": 110, "source": "punjab_epa",
    }]))
    assert n == 1
    got = s.con.execute("SELECT portal_dominant, lat FROM readings WHERE station_id = 'LHR-GT'").fetchone()
    s.close()
    assert got == (None, None)

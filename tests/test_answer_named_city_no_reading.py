"""20 Nov 2026: a city named in a "right now" question, with no reading, is not answered
with another city.

Found by running the Experiment A trick set through the app's answer code: "What is the
AQI in Karachi right now?" came back "Muzaffargarh has the worst air right now", and
"What is the PM2.5 in Multan right now?" came back with Lahore's PM2.5.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from airlume.nl.answer import answer
from airlume.nl.resolve import resolve
from airlume.nl.schema import TimeSpec, ViewIntent
from airlume.pipeline.store import Store

KHI = ZoneInfo("Asia/Karachi")
NOW = datetime(2026, 11, 20, 14, 30, tzinfo=KHI)


def _store() -> Store:
    s = Store(":memory:")
    ts = pd.Timestamp("2026-11-20 14:00", tz=KHI)
    s.upsert_city_hourly(pd.DataFrame([
        {"city_id": "PB-LHE", "ts": ts, "pm25": 187.5, "pm10": 260.0, "aqi": 264, "n_stations": 9, "source": "punjab_epa"},
        {"city_id": "PB-MZG", "ts": ts, "pm25": None, "pm10": None, "aqi": 359, "n_stations": 1, "source": "punjab_epa"},
        {"city_id": "PB-MUX", "ts": ts, "pm25": None, "pm10": None, "aqi": 169, "n_stations": 1, "source": "punjab_epa"},
    ]))
    return s


def _ask(registry, **kw) -> str:
    intent = ViewIntent(time=TimeSpec(label="now"), aggregation="latest", view="city_overview", **kw)
    return answer(resolve(intent, registry, NOW), _store(), registry, pd.Timestamp(NOW))


def test_named_city_without_feed_gets_no_data(registry):
    text = _ask(registry, city="Karachi")
    assert text == "I have no recent AQI reading for Karachi."
    assert "Muzaffargarh" not in text


def test_named_city_without_that_metric_gets_no_data(registry):
    assert _ask(registry, city="Multan", metric="pm25") == "I have no recent PM2.5 (ug/m3) reading for Multan."


def test_named_city_with_reading_and_rankings_are_unchanged(registry):
    assert _ask(registry, city="Multan").startswith("Multan right now: AQI 169")
    worst = answer(resolve(ViewIntent(time=TimeSpec(label="now"), aggregation="max", view="city_overview",
                                      camera="zoomed_out"), registry, NOW), _store(), registry, pd.Timestamp(NOW))
    assert worst.startswith("Muzaffargarh has the worst air right now (AQI 359")

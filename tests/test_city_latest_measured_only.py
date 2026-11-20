"""20 Nov 2026: a modelled CAMS row never reaches an answer as the city's measurement.

Found while reading the answer code for Experiment A: with the 20 Nov archive, "Is the
air clean in Lahore?" answered AQI 182 (the CAMS model) while the Punjab EPA measured 221
for the same hour, a different band and weaker advice.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from airlume.nl.answer import answer
from airlume.nl.resolve import resolve
from airlume.nl.schema import TimeSpec, ViewIntent
from airlume.pipeline.store import Store

KHI = ZoneInfo("Asia/Karachi")


def _store(cams_ts: str, epa_ts: str) -> Store:
    s = Store(":memory:")
    s.upsert_city_hourly(pd.DataFrame([
        {"city_id": "PB-LHE", "ts": pd.Timestamp(epa_ts, tz=KHI), "pm25": 120.0, "pm10": 200.0, "aqi": 221,
         "n_stations": 9, "source": "punjab_epa"},
        {"city_id": "PB-LHE", "ts": pd.Timestamp(cams_ts, tz=KHI), "pm25": None, "pm10": None, "aqi": 182,
         "n_stations": None, "source": "open_meteo_cams"},
        {"city_id": "PB-MUX", "ts": pd.Timestamp(epa_ts, tz=KHI), "pm25": None, "pm10": None, "aqi": 166,
         "n_stations": 1, "source": "punjab_epa"},
    ]))
    return s


def test_same_hour_returns_the_measurement_once():
    cf = _store("2026-11-20 14:00", "2026-11-20 14:00").latest_city_values()
    lhe = cf[cf.city_id == "PB-LHE"]
    assert len(lhe) == 1
    assert lhe["source"].iloc[0] == "punjab_epa" and int(lhe["aqi"].iloc[0]) == 221


def test_newer_cams_hour_does_not_hide_the_city():
    cf = _store("2026-11-20 15:00", "2026-11-20 14:00").latest_city_values()
    lhe = cf[cf.city_id == "PB-LHE"]
    assert len(lhe) == 1 and int(lhe["aqi"].iloc[0]) == 221


def test_modelled_rows_only_on_request():
    cf = _store("2026-11-20 14:00", "2026-11-20 14:00").latest_city_values(include_modelled=True)
    assert set(cf[cf.city_id == "PB-LHE"]["source"]) == {"punjab_epa", "open_meteo_cams"}


def test_answer_quotes_the_epa_figure(registry):
    now = datetime(2026, 11, 20, 14, 30, tzinfo=KHI)
    st = _store("2026-11-20 14:00", "2026-11-20 14:00")
    clean = ViewIntent(city="Lahore", view="city_overview", aggregation="latest", time=TimeSpec(label="now"))
    text = answer(resolve(clean, registry, now), st, registry, pd.Timestamp(now))
    assert text.startswith("Lahore right now: AQI 221") and "182" not in text
    pair = ViewIntent(city="Lahore", other_city="Multan", compare_to="other_city", view="compare",
                      aggregation="latest", time=TimeSpec(label="now"))
    text = answer(resolve(pair, registry, now), st, registry, pd.Timestamp(now))
    assert text.startswith("Lahore: AQI 221 · Multan: 166")

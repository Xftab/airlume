"""Forecast questions are answered from the forecast (plan 4.6).

Regression: until 16 Oct a question routed to view="forecast" ("what will the air
be like tomorrow?", "kal hawa kaisi hogi?") fell through to the station path and
was answered with current readings -- the present given as the future.
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from airlume.nl.answer import _forecast_answer, _when, answer
from airlume.nl.resolve import ResolvedQuery
from airlume.pipeline.registry import Registry
from airlume.pipeline.store import Store

NOW = pd.Timestamp("2026-10-16T05:00:00Z")          # 10:00 PKT
ISSUED = NOW - pd.Timedelta(hours=1)


def _store(with_readings: bool = True) -> Store:
    s = Store(":memory:")
    rows = []
    for h in range(0, 24):
        t = ISSUED + pd.Timedelta(hours=h + 1)
        rows.append({"city_id": "PB-LHE", "issued_at": ISSUED, "target_ts": t,
                     "aqi": 150 - (h if h < 12 else 24 - h) * 3, "source": "open_meteo_cams_forecast"})
    for h in range(0, 8):
        t = ISSUED + pd.Timedelta(hours=h + 1)
        rows.append({"city_id": "PB-LHE", "issued_at": ISSUED, "target_ts": t,
                     "aqi": 120 + h, "source": "punjab_epa_forecast"})
    s.upsert_forecasts(pd.DataFrame(rows))
    if with_readings:
        s.upsert_readings(pd.DataFrame([{
            "station_id": "LHR-GT", "ts": NOW, "pm25": 40.0, "pm10": 90.0,
            "aqi": 103, "aqi_computed": 103, "source": "punjab_epa"}]))
    return s


def _q(view="forecast", station=None, city="PB-LHE"):
    t = NOW.to_pydatetime()
    return ResolvedQuery(metric="aqi", city_id=city, station_id=station, start=t, end=t,
                         aggregation="latest", threshold=None, compare_start=None,
                         compare_end=None, compare_city_id=None, view=view,
                         camera="overview", notes=())


def test_forecast_question_is_answered_from_the_forecast_not_current_readings():
    text = _forecast_answer(_q(), _store(), Registry.load(), now=NOW)
    assert "forecasts Lahore's AQI over the next" in text
    assert "Worst right now" not in text          # the old, wrong behaviour
    assert "LHR-GT" not in text and "GT Road" not in text


def test_both_sources_reported_each_from_its_own_latest_issue():
    text = _forecast_answer(_q(), _store(), Registry.load(), now=NOW)
    assert "EPA Punjab forecasts" in text and "CAMS model forecasts" in text
    assert "next 8 hours" in text                  # EPA's issue is shorter
    assert "next 24 hours" in text


def test_accuracy_is_stated_or_its_absence_is_stated():
    text = _forecast_answer(_q(), _store(), Registry.load(), now=NOW)
    # No actuals stored for these target hours, so no scored history yet.
    assert text.count("Not enough scored history yet") == 2


def test_it_is_a_prediction_never_advice():
    text = _forecast_answer(_q(), _store(), Registry.load(), now=NOW).lower()
    for banned in (" safe", "go out", "exercise", "you should", "avoid", "stay indoors", "mask"):
        assert banned not in text, banned


def test_named_station_is_answered_at_city_level_and_says_so():
    text = _forecast_answer(_q(station="LHR-GB3"), _store(), Registry.load(), now=NOW)
    assert text.startswith("Forecasts are published for Lahore as a whole, not for Gulberg III.")


def test_city_without_a_forecast_says_so_plainly():
    text = _forecast_answer(_q(city="PB-FSD"), _store(), Registry.load(), now=NOW)
    assert "No forecast is published for Faisalabad" in text


def test_nothing_stored_is_said_plainly():
    text = _forecast_answer(_q(), Store(":memory:"), Registry.load(), now=NOW)
    assert "No forecast is stored yet" in text


def test_routing_reaches_the_forecast_branch():
    """answer() itself must dispatch on view, not only the helper.

    `now=NOW` is passed for the same reason every other test in this file pins
    the date: the fixture forecasts are anchored to 16 Oct, so against the wall
    clock every forecast hour is in the past and the branch returns "no forecast
    hours remain ahead" instead of a forecast. The test then fails for a reason
    that has nothing to do with dispatch.
    """
    text = answer(_q(), _store(), Registry.load(), now=NOW)
    assert "forecasts" in text and "Worst right now" not in text


def test_non_forecast_questions_are_unchanged():
    text = answer(_q(view="stations_3d"), _store(), Registry.load())
    assert "forecasts" not in text


@pytest.mark.parametrize("delta_h,expected", [
    (1, "11:00"), (10, "20:00"), (20, "06:00 tomorrow"), (50, "12:00 on 18 Oct"),
])
def test_times_say_which_day_when_the_horizon_crosses_midnight(delta_h, expected):
    assert _when(NOW + pd.Timedelta(hours=delta_h), NOW) == expected

"""Regression tests for drawbacks found by running the 62 classmate questions (2 Nov 2026).

Each case is a form the language model really produced in that run (see
K:\\airlume_work\\classmate_run_model_2026-11-02.md). They exercise the resolver and the
place matching only; none changes what the router returns, so the router benchmark
(score_benchmark_v1.py scores the form, not the answer) is unaffected.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from airlume.nl.resolve import ResolveError, resolve
from airlume.nl.schema import TimeSpec, ViewIntent

NOW = datetime(2026, 11, 2, 11, 0, tzinfo=ZoneInfo("Asia/Karachi"))


def test_tomorrow_forecast_without_a_date_resolves(registry):
    """c017 'kiya kal hawa saf hogi', c031 'Kiya smog hogi kal': custom_date, date None, view forecast."""
    v = ViewIntent(time=TimeSpec(label="custom_date"), view="forecast")
    r = resolve(v, registry, NOW)
    assert r.view == "forecast"
    assert r.end == NOW
    assert any("No date was given" in n for n in r.notes)


def test_custom_date_without_a_date_on_other_views_is_a_plain_sentence(registry):
    v = ViewIntent(time=TimeSpec(label="custom_date"), view="timeline")
    with pytest.raises(ResolveError) as e:
        resolve(v, registry, NOW)
    msg = str(e.value)
    assert "which day" in msg
    assert "custom_date" not in msg  # no internal field names shown to the user


def test_custom_range_without_dates_is_a_plain_sentence(registry):
    v = ViewIntent(time=TimeSpec(label="custom_range"))
    with pytest.raises(ResolveError) as e:
        resolve(v, registry, NOW)
    assert "custom_range" not in str(e.value)


def test_bahria_matches_bahria_town_with_a_nearest_station_note(registry):
    """c039 'What is today AQI in bahria': area 'Bahria'."""
    r = resolve(ViewIntent(area="Bahria", time=TimeSpec(label="today")), registry, NOW)
    assert r.station_id is not None
    assert any("nearest" in n and "Bahria" in n for n in r.notes)


def test_unknown_area_says_what_to_try(registry):
    """c016 Sabzazar has no coordinates in the registry yet: the reply must not be a bare error."""
    with pytest.raises(ResolveError) as e:
        resolve(ViewIntent(area="Zzzzville"), registry, NOW)
    msg = str(e.value)
    assert "no station matching" not in msg
    assert "Try a station name" in msg
    station = registry.stations_in("PB-LHE")[0].name
    assert station in msg  # suggestions come from the registry, never invented


def test_short_unrelated_words_do_not_match_a_known_area(registry):
    # the whole-word prefix rule needs 4+ characters and a whole word
    assert registry.match_station("tow", "PB-LHE") is None
    assert registry.match_station("zzzz", "PB-LHE") is None


def test_unknown_city_message_has_no_quotes_trick(registry):
    with pytest.raises(ResolveError) as e:
        resolve(ViewIntent(city="Atlantis"), registry, NOW)
    assert "monitored city" in str(e.value)

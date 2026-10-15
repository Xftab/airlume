"""Lowest-AQI window from the relayed 24-hour forecast (plan 4.6)."""

import pandas as pd
import pytest

from airlume.forecast.window import Window, describe, lowest_window

ISSUED = pd.Timestamp("2026-10-15T08:00:00Z")


def fc(hours_and_aqi, source="punjab_epa_forecast", issued=ISSUED, base="2026-10-15T09:00:00Z"):
    """hours_and_aqi: [(hour_offset, aqi), ...] from `base`."""
    b = pd.Timestamp(base)
    return pd.DataFrame([
        {"city_id": "PB-LHE", "issued_at": issued,
         "target_ts": b + pd.Timedelta(hours=h), "aqi": a, "source": source}
        for h, a in hours_and_aqi
    ])


NOW = pd.Timestamp("2026-10-15T09:00:00Z")


def test_finds_the_lowest_contiguous_pair():
    df = fc([(0, 150), (1, 140), (2, 100), (3, 90), (4, 160)])
    w = lowest_window(df, hours=2, now=NOW)
    assert w.start == pd.Timestamp("2026-10-15T11:00:00Z")
    assert w.end == pd.Timestamp("2026-10-15T12:00:00Z")
    assert w.mean_aqi == pytest.approx(95.0)


def test_window_length_is_respected():
    df = fc([(0, 10), (1, 200), (2, 200), (3, 200)])
    assert lowest_window(df, hours=1, now=NOW).mean_aqi == pytest.approx(10)
    # Over three hours the single low hour cannot carry the window.
    w3 = lowest_window(df, hours=3, now=NOW)
    assert w3.mean_aqi == pytest.approx((10 + 200 + 200) / 3)


def test_hours_already_past_are_excluded():
    """The regression that matters: the portal's forecast still contains the hour
    it was issued in, so the lowest window could point at a time already gone."""
    df = fc([(0, 50), (1, 150), (2, 140), (3, 145)])
    later = pd.Timestamp("2026-10-15T11:00:00Z")   # the cheap 09:00 hour has passed
    w = lowest_window(df, hours=2, now=later)
    assert w.start >= later.floor("h")
    assert w.mean_aqi == pytest.approx(142.5)      # not the 50


def test_a_gap_never_becomes_a_window():
    """Two cheap hours either side of a missing hour are not a two-hour window."""
    df = fc([(0, 200), (1, 20), (3, 20), (4, 200)])   # hour 2 missing
    w = lowest_window(df, hours=2, now=NOW)
    assert w is not None
    assert w.mean_aqi > 20          # the 20s are not adjacent, so never paired
    assert w.hours_span == 2


def test_only_the_latest_issue_is_used():
    old = fc([(0, 10), (1, 10)], issued=pd.Timestamp("2026-10-15T06:00:00Z"))
    new = fc([(0, 180), (1, 170)], issued=pd.Timestamp("2026-10-15T08:00:00Z"))
    w = lowest_window(pd.concat([old, new]), hours=2, now=NOW)
    assert w.issued_at == pd.Timestamp("2026-10-15T08:00:00Z")
    assert w.mean_aqi == pytest.approx(175.0)


def test_sources_are_kept_apart():
    epa = fc([(0, 100), (1, 100)], source="punjab_epa_forecast")
    cams = fc([(0, 40), (1, 40)], source="open_meteo_cams_forecast")
    both = pd.concat([epa, cams])
    assert lowest_window(both, 2, source="punjab_epa_forecast", now=NOW).mean_aqi == pytest.approx(100)
    assert lowest_window(both, 2, source="open_meteo_cams_forecast", now=NOW).mean_aqi == pytest.approx(40)


def test_returns_none_rather_than_guessing():
    assert lowest_window(pd.DataFrame(), 2) is None
    assert lowest_window(fc([(0, 100)]), hours=2, now=NOW) is None          # too short
    assert lowest_window(fc([(0, 100), (1, 90)]), hours=2,
                         now=pd.Timestamp("2026-10-16T00:00:00Z")) is None  # all past


# --- the sentence -----------------------------------------------------------

def test_sentence_is_a_prediction_not_advice():
    w = lowest_window(fc([(0, 150), (1, 90), (2, 92)]), hours=2, now=NOW)
    text = describe(w, mae=12.0, source_label="EPA Punjab")
    lowered = text.lower()
    for banned in ("you ", "should", "go out", "exercise", "safe", "healthy", "avoid", "best time"):
        assert banned not in lowered, f"advice-like wording: {banned!r}"
    assert "lowest predicted aqi" in lowered


def test_sentence_carries_the_error_when_known_and_says_so_when_not():
    w = lowest_window(fc([(0, 150), (1, 90), (2, 92)]), hours=2, now=NOW)
    assert "out by about 12 AQI points" in describe(w, mae=12.0)
    assert "not yet enough scored history" in describe(w, mae=None)


def test_sentence_is_local_time_and_names_the_source():
    w = lowest_window(fc([(0, 150), (1, 90), (2, 92)]), hours=2, now=NOW)
    text = describe(w, mae=5.0, source_label="EPA Punjab")
    # 10:00-12:00 UTC is 15:00-17:00 PKT
    assert "15:00" in text and "17:00" in text
    assert "EPA Punjab" in text


def test_no_window_is_said_plainly():
    assert "No 24-hour forecast is stored yet" in describe(None)

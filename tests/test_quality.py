"""Tests for the data-quality checks (plan 1.6).

Each check gets a frame built to trip exactly it, plus the cases that must NOT
trip it.  The irregular-spacing tests matter most: the first version of the
module differenced adjacent rows rather than adjacent hours and reported ten
spikes on the real archive that were only collection gaps.
"""

import pandas as pd
import pytest

from airlume.pipeline import quality


def frame(rows):
    """rows: (station_id, 'YYYY-MM-DD HH:MM', pm25, pm10) -> readings frame."""
    return pd.DataFrame([
        {"station_id": s, "ts": pd.Timestamp(t, tz="UTC"), "pm25": a, "pm10": b,
         "o3": None, "no2": None, "so2": None, "co": None, "aqi": None,
         "aqi_computed": None, "source": "punjab_epa"}
        for s, t, a, b in rows
    ])


def hourly(station, start_hour, values, pm10=None):
    return [(station, f"2026-10-15 {h:02d}:00", v, (pm10 if pm10 is not None else (v or 0) + 50))
            for h, v in enumerate(values, start=start_hour)]


# --- uptime and gaps -------------------------------------------------------

def test_uptime_counts_only_hours_the_collector_ran():
    # Two collected hours; B missed the second one. The wall clock is irrelevant.
    df = frame([("A", "2026-10-15 01:00", 50, 100), ("B", "2026-10-15 01:00", 50, 100),
                ("A", "2026-10-15 02:00", 52, 100)])
    rep = quality.check_readings(df)
    assert rep.expected_hours == [pd.Timestamp("2026-10-15 01:00", tz="UTC"),
                                  pd.Timestamp("2026-10-15 02:00", tz="UTC")]
    u = rep.uptime.set_index("station_id")["uptime"]
    assert u["A"] == 1.0 and u["B"] == 0.5


def test_station_in_registry_that_never_reports_is_flagged():
    df = frame(hourly("A", 1, [50, 51, 52]))
    rep = quality.check_readings(df, all_stations=["A", "GHOST"])
    gaps = rep.of_kind("gap")
    assert len(gaps) == 1 and gaps[0].station_id == "GHOST"
    assert "never reported" in gaps[0].detail
    assert rep.uptime.set_index("station_id").loc["GHOST", "uptime"] == 0.0


def test_gap_needs_two_consecutive_missed_hours():
    rows = hourly("A", 1, [10, 11, 12, 13, 14, 15])
    # B misses hour 2 only (one hour) -> no flag; then hours 4 and 5 -> one flag.
    rows += [("B", "2026-10-15 01:00", 10, 60), ("B", "2026-10-15 03:00", 12, 60),
             ("B", "2026-10-15 06:00", 15, 60)]
    rep = quality.check_readings(frame(rows))
    gaps = [f for f in rep.of_kind("gap") if f.station_id == "B"]
    assert len(gaps) == 1
    assert "2 consecutive" in gaps[0].detail


# --- impossible values -----------------------------------------------------

@pytest.mark.parametrize("pm25,pm10,why", [
    (-5.0, 60.0, "negative"),
    (5000.0, 6000.0, "above the ceiling"),
])
def test_impossible_values_flagged(pm25, pm10, why):
    df = frame([("A", "2026-10-15 01:00", pm25, pm10)])
    flags = quality.check_readings(df).of_kind("impossible")
    assert any("pm25" in f.detail for f in flags), why


def test_pm25_above_pm10_is_impossible():
    df = frame([("A", "2026-10-15 01:00", 90.0, 40.0)])
    flags = quality.check_readings(df).of_kind("impossible")
    assert any("exceeds pm10" in f.detail for f in flags)


def test_ordinary_values_are_not_flagged():
    df = frame(hourly("A", 1, [45.0, 48.0, 51.0, 47.0]))
    rep = quality.check_readings(df)
    assert rep.of_kind("impossible") == []
    assert rep.of_kind("spike") == []


# --- stuck sensors ---------------------------------------------------------

def test_stuck_sensor_flagged_over_consecutive_hours():
    df = frame(hourly("A", 1, [30.0, 30.0, 30.0, 30.0]))
    flags = quality.check_readings(df).of_kind("stuck")
    assert any("pm25 held at 30" in f.detail for f in flags)


def test_two_identical_readings_are_not_stuck():
    df = frame(hourly("A", 1, [30.0, 30.0, 41.0]))
    assert quality.check_readings(df).of_kind("stuck") == []


def test_repeats_across_a_collection_gap_are_not_stuck():
    """Three identical values hours apart say nothing about the sensor."""
    rows = [("A", "2026-10-15 01:00", 30.0, 80.0),
            ("A", "2026-10-15 07:00", 30.0, 80.0),
            ("A", "2026-10-15 13:00", 30.0, 80.0)]
    assert quality.check_readings(frame(rows)).of_kind("stuck") == []


# --- spikes ----------------------------------------------------------------

def test_spike_flagged_against_the_stations_own_variation():
    # Calm station, then a jump far outside its usual hour-on-hour step.
    # pm10 is held flat so only the pm25 spike can fire.
    df = frame(hourly("A", 1, [40.0, 42.0, 41.0, 43.0, 42.0, 300.0], pm10=400.0))
    flags = quality.check_readings(df).of_kind("spike")
    assert len(flags) == 1 and "pm25 moved +258" in flags[0].detail


def test_large_jump_across_a_collection_gap_is_not_a_spike():
    """The regression that matters: 2-6 hour spacing must not read as one hour.

    On the real archive this produced ten false spikes, all of them landing on
    the boundaries of the pre-trigger collection gaps.
    """
    rows = [("A", "2026-10-14 04:00", 40.0, 90.0),
            ("A", "2026-10-14 10:00", 140.0, 190.0),
            ("A", "2026-10-14 15:00", 40.0, 90.0),
            ("A", "2026-10-14 20:00", 150.0, 200.0)]
    assert quality.check_readings(frame(rows)).of_kind("spike") == []


def test_small_absolute_jump_is_never_a_spike():
    # Very steady station: a 10 ug/m3 move is many sigmas but not meaningful.
    df = frame(hourly("A", 1, [20.0, 20.1, 20.0, 20.1, 20.0, 30.0]))
    assert quality.check_readings(df).of_kind("spike") == []


# --- partial rounds --------------------------------------------------------

def test_partial_round_flagged_not_blamed_on_stations():
    rows = []
    for h in (1, 2, 4):
        rows += [(f"S{i}", f"2026-10-15 {h:02d}:00", 50.0, 100.0) for i in range(10)]
    rows += [("S0", "2026-10-15 03:00", 50.0, 100.0)]  # the half-failed round
    rep = quality.check_readings(frame(rows))
    partial = rep.of_kind("partial_round")
    assert len(partial) == 1
    assert partial[0].ts == pd.Timestamp("2026-10-15 03:00", tz="UTC")
    assert "only 1 of a typical 10" in partial[0].detail


# --- city-hour source collisions -------------------------------------------

def test_source_collision_detected_when_two_widgets_disagree():
    ch = pd.DataFrame([
        {"city_id": "PB-LHE", "ts": pd.Timestamp("2026-10-15 06:00", tz="UTC"),
         "pm25": None, "pm10": None, "aqi": 73, "n_stations": None, "source": "punjab_epa"},
        {"city_id": "PB-LHE", "ts": pd.Timestamp("2026-10-15 06:00", tz="UTC"),
         "pm25": None, "pm10": None, "aqi": 77, "n_stations": None, "source": "punjab_epa"},
    ])
    flags = quality.check_source_collisions(ch)
    assert len(flags) == 1
    assert "73 vs 77" in flags[0].detail


def test_agreeing_duplicate_rows_are_not_a_collision():
    ch = pd.DataFrame([
        {"city_id": "PB-LHE", "ts": pd.Timestamp("2026-10-15 06:00", tz="UTC"),
         "pm25": None, "pm10": None, "aqi": 73, "n_stations": None, "source": "punjab_epa"},
    ] * 2)
    assert quality.check_source_collisions(ch) == []


def test_empty_inputs_are_safe():
    empty = pd.DataFrame(columns=["station_id", "ts", "pm25", "pm10", "source"])
    rep = quality.check_readings(empty)
    assert rep.flags == [] and rep.counts == {}
    assert quality.check_source_collisions(pd.DataFrame()) == []

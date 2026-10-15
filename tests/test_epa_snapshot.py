"""The embedded Livewire snapshot reader (found 15 Oct 2026).

The portal's page carries its component state as JSON in a `wire:snapshot`
attribute, and that state holds *two* Lahore station arrays: 11 stations, and
the 10 that the HTML table is actually rendered from.  Gulberg III is in the
first and not the second, which is why it never reached our archive.

The fixture reproduces that shape: a snapshot whose `lahoreData` array has four
stations (one of them Gulberg III, one an unknown name) and whose rendered
table has only three.
"""

from pathlib import Path

import pandas as pd
import pytest

from airlume.collectors import epa

FIXTURE = Path(__file__).parent / "fixtures" / "lahore_snapshot_2026-10-15.html"


@pytest.fixture
def page() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_unmatched():
    epa.UNMATCHED_STATIONS.clear()
    yield
    epa.UNMATCHED_STATIONS.clear()


def test_snapshot_finds_the_station_the_table_omits(page):
    """The whole point: Gulberg III is in the data but not in the table."""
    snap = epa.parse_lahore_snapshot(page)
    table = epa.parse_lahore_html(page)
    assert "LHR-GB3" in set(snap.station_id)
    assert "LHR-GB3" not in set(table.station_id)
    assert len(snap) > len(table)


def test_snapshot_prefers_the_larger_station_array(page):
    """Two arrays are present; the reader must not take whichever comes first."""
    assert len(epa.parse_lahore_snapshot(page)) == 3  # 4 records, one unmatched name


def test_parse_lahore_prefers_the_snapshot(page):
    assert len(epa.parse_lahore(page)) == len(epa.parse_lahore_snapshot(page))


def test_falls_back_to_the_table_when_there_is_no_snapshot(page):
    stripped = page[: page.index("<div wire:id")] + "<table>" + page.split("<table>", 1)[1]
    df = epa.parse_lahore(stripped)
    assert not df.empty
    assert "lat" not in df.columns  # came from the table parser
    assert "LHR-GB3" not in set(df.station_id)


def test_values_and_units_survive_the_json(page):
    row = epa.parse_lahore_snapshot(page).set_index("station_id").loc["LHR-GB3"]
    assert row.pm25 == pytest.approx(16.64)   # JSON strings become floats
    assert row.pm10 == pytest.approx(56.39)
    assert row.aqi == 62                      # the portal's own number, as an int
    assert row.aqi_computed is not None       # and ours, computed from concentrations


def test_timestamp_offset_is_honoured(page):
    """The snapshot gives +05:00 local time; 14:00 PKT is 09:00 UTC."""
    ts = epa.parse_lahore_snapshot(page)["ts"].iloc[0]
    assert ts == pd.Timestamp("2026-10-15T09:00:00Z")


def test_official_coordinates_are_carried(page):
    row = epa.parse_lahore_snapshot(page).set_index("station_id").loc["LHR-GB3"]
    assert row.lat == pytest.approx(31.507172, abs=1e-5)
    assert row.lon == pytest.approx(74.338461, abs=1e-5)


def test_weather_columns_are_carried(page):
    row = epa.parse_lahore_snapshot(page).iloc[0]
    for col in ("temperature", "humidity", "wind_speed", "wind_direction"):
        assert row[col] is not None


def test_unknown_station_is_recorded_not_silently_dropped(page):
    epa.parse_lahore_snapshot(page)
    assert "Brand New Station" in epa.UNMATCHED_STATIONS


def test_table_parser_also_records_unknown_stations(page):
    epa.parse_lahore_html(page)
    assert "Brand New Station" in epa.UNMATCHED_STATIONS


def test_station_key_handles_the_portals_two_spellings():
    assert epa._station_key("Gulberg III") == "gulberg iii"
    assert epa._station_key("Gulberg III, Lahore") == "gulberg iii"
    assert epa.STATION_MAP[epa._station_key("Gulberg III, Lahore")] == "LHR-GB3"
    assert epa.STATION_MAP[epa._station_key("Wagha Border")] == "LHR-WB"


def test_missing_or_broken_snapshot_is_not_an_error():
    assert epa.parse_lahore_snapshot("<html><body>nothing</body></html>").empty
    assert epa.parse_lahore_snapshot('<div wire:snapshot="station_name {{{">x</div>').empty

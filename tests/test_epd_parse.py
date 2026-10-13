import json
from datetime import date
from pathlib import Path

from airlume.pipeline.epd_parse import parse_pages

FX = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FX / f"epd_{name}.json").read_text(encoding="utf-8"))


def test_style_a_full_station_table():
    style, rows, avg = parse_pages(_load("style_a_2025-12-02"))
    assert style == "A" and avg == 334
    got = {r.station_label: r.aqi for r in rows}
    assert got["UET"] == 418 and got["PU 1"] == 277 and len(rows) == 11
    assert all(r.date == date(2025, 12, 2) and r.pollutant == "pm25" for r in rows)
    ids = {r.station_label: r.station_id for r in rows}
    assert ids["UET"] == "LHR-GT" and ids["Kahna Nau"] == "LHR-KN" and ids["Town Hall"] is None


def test_style_a_split_name():
    _, rows, _ = parse_pages(_load("style_a_2025-12-01"))
    got = {r.station_label: (r.aqi, r.station_id) for r in rows}
    assert got["Wahga Boarder"] == (514, "LHR-WB") and got["Egerton Road"] == (559, "LHR-EG")
    assert len(rows) == 13


def test_style_b_2024():
    style, rows, avg = parse_pages(_load("style_b_2024-03-07"))
    assert style == "B" and avg is None
    got = {r.station_label: (r.pollutant, r.conc, r.aqi, r.city) for r in rows}
    assert got["Town Hall"] == ("pm25", 79.0, 157, "Lahore")
    assert got["PU 1"] == ("pm25", 57.0, 132, "Lahore")
    assert got["EPA HQ"][2] == 133
    assert got["Rawalpindi Shalley Valley"] == ("pm10", 185.0, 118, "Rawalpindi")


def test_style_b_2022_co_rows():
    _, rows, _ = parse_pages(_load("style_b_2022-07-06"))
    got = {r.station_label: (r.pollutant, r.aqi) for r in rows}
    assert got["Town Hall"] == ("co", 108) and got["Gajjumata"] == ("pm25", 161)


def test_style_c_detected_not_parsed():
    style, rows, _ = parse_pages(_load("style_c_2020-02-20"))
    assert style == "C" and rows == []

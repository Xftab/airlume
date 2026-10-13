import json
from datetime import date
from pathlib import Path

from airlume.pipeline.epd_parse import parse_pages

FX = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FX / f"epd_{name}.json").read_text(encoding="utf-8"))


def test_style_e_2025_variant_date_format():
    style, rows, avg, d = parse_pages(_load("style_e_2025-02-21"))
    assert style == "E" and avg == 143 and d == date(2025, 2, 21) and rows == []


def test_style_b_various_cities_title():
    style, rows, _, _ = parse_pages(_load("style_b_2022-02-14"))
    assert style == "B"
    got = {r.station_label: (r.pollutant, r.conc, r.aqi, r.city) for r in rows}
    assert got["EPA HQ"] == ("pm25", 117.0, 184, "Lahore")
    assert got["Rahim Yar Khan"] == ("pm25", 42.4, 120, "Rahim Yar Khan")
    assert got["Town Hall"] == ("co", 8.09, 161, "Lahore")


def test_style_b17_old_scale_marked():
    style, rows, _, _ = parse_pages(_load("style_b17_2021-11-16"))
    assert style == "B17"
    got = {r.station_label: (r.pollutant, r.conc, r.aqi) for r in rows}
    assert got["Township D1"] == ("pm25", 154.0, 409)  # 154 ug/m3 is 203 on the current scale: not comparable
    assert got["Township"][0] == "co"  # PEQS 5 mg/m3 row mislabelled PM2.5 in the source
    assert all(r.style == "B17" for r in rows)


def test_style_b17_2020():
    _, rows, _, _ = parse_pages(_load("style_b17_2020-12-03"))
    got = {r.station_label: (r.pollutant, r.conc, r.aqi) for r in rows}
    assert got["Jail Road"] == ("pm25", 46.326, 128) and got["Township"] == ("no2", 23.295, 11)

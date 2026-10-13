import json
from datetime import date
from pathlib import Path

from airlume.pipeline.epd_parse import parse_pages

FX = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FX / f"epd_{name}.json").read_text(encoding="utf-8"))


def test_style_d_stations_and_districts():
    style, rows, avg, d = parse_pages(_load("style_d_2025-10-07"))
    assert style == "D" and avg == 78 and d == date(2025, 10, 7)
    st = {r.station_label: r for r in rows if not r.station_label.endswith("average")}
    assert st["PKLI"].aqi == 132 and st["Safari Park"].pollutant == "o3" and st["Safari Park"].station_id == "LHR-SP"
    assert st["Raja Jang"].city == "Kasur" and st["Lathepur"].city == "Sheikhupura"
    dist = {r.city: r.aqi for r in rows if r.station_label.endswith("average")}
    assert dist["Faisalabad"] == 85 and dist["Sheikhupura"] == 80 and dist["Rahim Yar Khan"] == 58 and dist["Multan"] == 41


def test_style_e_average_only():
    style, rows, avg, d = parse_pages(_load("style_e_2025-09-02"))
    assert style == "E" and rows == [] and avg == 56 and d == date(2025, 9, 2)


def test_style_a_uses_note_date_not_wrong_updated_year():
    style, rows, avg, d = parse_pages(_load("style_a_2025-10-20"))
    assert style == "A" and d == date(2025, 10, 20)  # "Updated Time" says 2024 by mistake
    got = {r.station_label: (r.aqi, r.city) for r in rows}
    assert got["Kahna Nau"] == (250, "Lahore") and got["Raja Jang"] == (193, "Kasur") and got["BHU Jandiala"] == (169, "Sheikhupura")


def test_scanned_detected():
    assert parse_pages(["", ""])[0] == "scanned"
    assert parse_pages(["   CamScanner  "])[0] == "scanned"

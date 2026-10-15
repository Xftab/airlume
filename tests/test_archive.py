from datetime import datetime, timezone

import pandas as pd

from airlume.pipeline import archive


def test_export_is_append_only_and_deduplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "ARCHIVE", tmp_path)
    ts = datetime(2026, 10, 13, 2, tzinfo=timezone.utc)
    df = pd.DataFrame([{"station_id": "LHR-GT", "ts": ts, "pm25": 226.9, "pm10": 240.1,
                        "aqi": 277, "aqi_computed": 277, "source": "punjab_epa"}])
    files = archive.export("readings", df)
    assert files == [tmp_path / "readings" / "punjab_epa" / "2026-10.csv"]
    archive.export("readings", df)  # same row again
    df2 = df.copy(); df2["ts"] = datetime(2026, 10, 13, 3, tzinfo=timezone.utc)
    archive.export("readings", df2)
    out = archive.load_all("readings")
    assert len(out) == 2 and out["ts"].dt.tz is not None
    text = files[0].read_text()
    assert "2026-10-13T02:00:00Z" in text and "\r" not in text


def test_load_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "ARCHIVE", tmp_path)
    assert archive.load_all("city_hourly").empty


def test_epd_daily_yearly_files(tmp_path, monkeypatch):
    from datetime import date
    monkeypatch.setattr(archive, "ARCHIVE", tmp_path)
    df = pd.DataFrame([{"date": date(2025, 12, 2), "station_label": "UET", "station_id": "LHR-GT", "city": "Lahore",
                        "pollutant": "pm25", "conc": None, "aqi": 418, "style": "A", "source": "epd_pdf"}])
    files = archive.export("epd_daily", df)
    assert files == [tmp_path / "epd_daily" / "epd_pdf" / "2025.csv"]
    assert "2025-12-02,UET" in files[0].read_text()
    out = archive.load_all("epd_daily")
    assert out.loc[0, "date"] == date(2025, 12, 2)


def test_snapshot_columns_append_without_disturbing_existing_files(tmp_path, monkeypatch):
    """A CSV written before 15 Oct 2026 has eleven columns and must stay readable.

    The snapshot columns are appended to COLS, never inserted, so an existing file
    keeps its column order and its rows read back blank in the new columns.
    """
    monkeypatch.setattr(archive, "ARCHIVE", tmp_path)
    p = tmp_path / "readings" / "punjab_epa" / "2026-10.csv"
    p.parent.mkdir(parents=True)
    pd.DataFrame([{
        "station_id": "LHR-GT", "ts": "2026-10-15T09:00:00Z", "pm25": 39.0, "pm10": 70.0,
        "co": 0.7, "so2": 37.5, "no2": 17.6, "o3": 36.3,
        "aqi": 106, "aqi_computed": 110, "source": "punjab_epa",
    }]).to_csv(p, index=False, lineterminator="\n")
    before = p.read_text().splitlines()[0]
    assert before.endswith("source")  # the pre-15-Oct shape

    archive.export("readings", pd.DataFrame([{
        "station_id": "LHR-GB3", "ts": pd.Timestamp("2026-10-15T10:00:00Z"),
        "pm25": 20.18, "pm10": 70.53, "co": 0.48, "so2": 3.79, "no2": 12.56, "o3": 82.39,
        "aqi": 64, "aqi_computed": 68, "source": "punjab_epa",
        "portal_station_id": 27, "portal_dominant": "O3",
        "lat": 31.507172, "lon": 74.338461,
        "temperature": 27.88, "humidity": 78.66, "wind_speed": 1.64, "wind_direction": 152.16,
    }]))

    header = p.read_text().splitlines()[0]
    assert header.startswith(before)  # old columns kept, in order
    assert header.endswith("wind_direction")

    out = archive.load_all("readings").set_index("station_id")
    assert out.loc["LHR-GT", "aqi"] == 106                     # old row intact
    assert pd.isna(out.loc["LHR-GT", "portal_dominant"])       # and blank in the new columns
    assert out.loc["LHR-GB3", "portal_dominant"] == "O3"
    assert out.loc["LHR-GB3", "wind_speed"] == 1.64

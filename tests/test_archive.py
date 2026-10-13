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

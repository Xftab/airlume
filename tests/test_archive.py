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

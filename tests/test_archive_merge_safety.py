"""6 Nov 2026: guards for the archive data-loss fix (see docs/HISTORY.md, 6 Nov)."""
from pathlib import Path

import pandas as pd

from airlume.pipeline import archive

ROOT = Path(__file__).resolve().parents[1]


def test_archive_csvs_merge_with_union():
    """Without this rule `pull --rebase -X theirs` dropped the other machine's rows."""
    lines = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "data/archive/**/*.csv merge=union" in [ln.strip() for ln in lines]


def test_load_all_drops_duplicate_keys(tmp_path, monkeypatch):
    p = tmp_path / "city_hourly" / "open_meteo_cams"
    p.mkdir(parents=True)
    # What a union merge can leave: one hour twice (revised on one side), out of order.
    (p / "2026-11.csv").write_text(
        "city_id,ts,pm25,pm10,aqi,n_stations,source\n"
        "PB-LHE,2026-11-05T10:00:00Z,100,150,170,,open_meteo_cams\n"
        "PB-LHE,2026-11-05T09:00:00Z,90,140,165,,open_meteo_cams\n"
        "PB-LHE,2026-11-05T10:00:00Z,101,151,171,,open_meteo_cams\n",
        encoding="utf-8")
    monkeypatch.setattr(archive, "ARCHIVE", tmp_path)
    got = archive.load_all("city_hourly")
    assert len(got) == 2
    assert got.loc[got.ts == pd.Timestamp("2026-11-05T10:00:00Z"), "aqi"].item() == 171

"""Rebuild the local DuckDB cache from the committed CSV archive.
Run after a fresh clone or `git pull`:  python scripts/rebuild_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.pipeline import archive
from airlume.pipeline.store import Store

store = Store()
r = archive.load_all("readings")
c = archive.load_all("city_hourly")
print(f"archive: {len(r)} readings, {len(c)} city rows")
store.upsert_readings(r)
store.upsert_city_hourly(c)
print(store.counts())

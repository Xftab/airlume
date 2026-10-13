"""Fill the local DuckDB with fake data (Phase 0).  Run: python scripts/seed_fake.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.pipeline.fake import fake_city_hourly, fake_readings
from airlume.pipeline.registry import Registry
from airlume.pipeline.store import Store

reg = Registry.load()
store = Store()
r = fake_readings(reg)
n1 = store.upsert_readings(r)
n2 = store.upsert_city_hourly(fake_city_hourly(reg, r))
print(f"wrote {n1} station rows and {n2} city rows to {store.path}")
print(store.counts())

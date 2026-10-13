"""Hourly collection job (Phase 1).  Run by GitHub Actions and by hand:

    python scripts/collect_hourly.py            # EPA Lahore + districts, Open-Meteo Lahore
    python scripts/collect_hourly.py --dry-run  # fetch and parse, write nothing

Writes to the CSV archive (data/archive/, committed) and the local DuckDB cache.
Each source is independent: one failure never blocks the others.  Exit code is
non-zero only if *every* source failed.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from airlume.collectors import epa, openmeteo  # noqa: E402
from airlume.pipeline import archive  # noqa: E402
from airlume.pipeline.registry import Registry  # noqa: E402
from airlume.pipeline.store import Store  # noqa: E402

LAHORE = (31.52, 74.33)


def run(dry_run: bool = False) -> int:
    reg = Registry.load()
    ok = 0
    results: dict[str, pd.DataFrame] = {}

    # 1. Punjab EPA, Lahore stations
    try:
        html = epa.fetch_lahore_html()
        df = epa.parse_lahore_html(html)
        print(f"[epa/lahore] {len(df)} station rows")
        if df.empty:
            raw = Path("data/raw") / f"lahore_empty_{datetime.now(timezone.utc):%Y%m%dT%H%M}Z.html"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(html, encoding="utf-8")
            print(f"[epa/lahore] parser found nothing; raw page saved to {raw}")
        else:
            results["readings"] = df
            ok += 1
    except Exception:
        print("[epa/lahore] FAILED"); traceback.print_exc()

    # 2. Punjab EPA, district ranking
    try:
        lookup = {c.name.lower(): c.city_id for c in reg.cities}
        df = epa.parse_home_html(epa.fetch_home_html(), lookup)
        print(f"[epa/districts] {len(df)} district rows")
        if not df.empty:
            results["city_hourly"] = df
            ok += 1
    except Exception:
        print("[epa/districts] FAILED"); traceback.print_exc()

    # 3. Open-Meteo CAMS for Lahore (validation series, C4)
    try:
        om = openmeteo.fetch_hourly(*LAHORE, past_days=1, forecast_days=1)
        om = om[om["ts"] <= datetime.now(timezone.utc)]
        om = om.assign(city_id="PB-LHE", n_stations=None)
        print(f"[open-meteo/lahore] {len(om)} hourly rows")
        prev = results.get("city_hourly", pd.DataFrame())
        results["city_hourly"] = pd.concat([prev, om[archive.COLS["city_hourly"]]], ignore_index=True)
        ok += 1
    except Exception:
        print("[open-meteo] FAILED"); traceback.print_exc()

    if dry_run:
        for k, v in results.items():
            print(f"\n== {k} ==\n{v.head(15).to_string()}")
        return 0 if ok else 1

    store = Store()
    for table, df in results.items():
        touched = archive.export(table, df)
        n = store.upsert_readings(df) if table == "readings" else store.upsert_city_hourly(df)
        print(f"[{table}] {n} rows -> db; archive files: {[str(p.relative_to(archive.ROOT)) for p in touched]}")
    print(store.counts())
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    sys.exit(run(ap.parse_args().dry_run))

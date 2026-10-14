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
        trend = epa.parse_lahore_trend(html)
        print(f"[epa/lahore-trend] {len(trend)} city-hours (last 7 days)")
        if not trend.empty:
            results["city_hourly"] = pd.concat([results.get("city_hourly", pd.DataFrame()), trend], ignore_index=True)
        fc = epa.parse_lahore_forecast(html)
        print(f"[epa/lahore-forecast] {len(fc)} forecast hours")
        if not fc.empty:
            results["forecasts"] = fc
    except Exception:
        print("[epa/lahore] FAILED"); traceback.print_exc()

    # 2. Punjab EPA, district ranking
    try:
        lookup = {c.name.lower(): c.city_id for c in reg.cities}
        df = epa.parse_home_html(epa.fetch_home_html(), lookup)
        print(f"[epa/districts] {len(df)} district rows")
        if epa.UNMATCHED:
            print(f"[epa/districts] names on the page not in the registry: {epa.UNMATCHED}")
        absent = [c.name for c in reg.cities if c.province == "Punjab" and c.city_id not in set(df.city_id)]
        if absent:
            print(f"[epa/districts] registry districts not on the page today: {absent}")
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
        # CAMS also gives a forecast for the next 24 h: keep it, labelled, for the scorecard (C5).
        fut = openmeteo.fetch_hourly(*LAHORE, past_days=0, forecast_days=2)
        fut = fut[fut["ts"] > datetime.now(timezone.utc)].head(24)
        if not fut.empty:
            cams_fc = pd.DataFrame({"city_id": "PB-LHE", "issued_at": datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0),
                                    "target_ts": fut["ts"], "aqi": fut["aqi"].round().astype("Int64"), "source": "open_meteo_cams_forecast"})
            results["forecasts"] = pd.concat([results.get("forecasts", pd.DataFrame()), cams_fc.dropna(subset=["aqi"])], ignore_index=True)
        ok += 1
    except Exception:
        print("[open-meteo] FAILED"); traceback.print_exc()

    if dry_run:
        for k, v in results.items():
            print(f"\n== {k} ==\n{v.head(15).to_string()}")
        return 0 if ok else 1

    # The CSV archive is the record. The local DuckDB file is a convenience cache and may be
    # locked by another process; that is not a failure.
    for table, df in results.items():
        touched = archive.export(table, df)
        print(f"[{table}] {len(df)} rows -> archive: {[str(p.relative_to(archive.ROOT)) for p in touched]}")
    try:
        store = Store()
        for table, df in results.items():
            {"readings": store.upsert_readings, "city_hourly": store.upsert_city_hourly,
             "forecasts": store.upsert_forecasts}[table](df)
        print(f"[db] {store.counts()}")
        store.close()
    except Exception as e:  # e.g. file locked
        print(f"[db] skipped ({type(e).__name__}); archive is up to date")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    sys.exit(run(ap.parse_args().dry_run))

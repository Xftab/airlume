"""Data-quality report over the archive (plan 1.6).

    python scripts/quality_report.py            # all stored readings
    python scripts/quality_report.py --hours 48 # the last 48 collected hours

Reads the CSV archive (the data of record, so it includes rows the cloud
collector committed), never the DuckDB cache.  Nothing is corrected or
written: every finding is printed for a human to judge.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from airlume.pipeline import archive, quality  # noqa: E402
from airlume.pipeline.registry import Registry  # noqa: E402


def main(hours: int | None, city: str) -> int:
    df = archive.load_all("readings")
    df = df[df["source"] == "punjab_epa"].copy()
    if df.empty:
        print("no readings in the archive yet")
        return 1
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    if hours:
        keep = sorted(df["ts"].dt.floor("h").unique())[-hours:]
        df = df[df["ts"].dt.floor("h").isin(keep)]

    reg = Registry.load()
    expected = [s.station_id for s in reg.stations_in(city)]
    rep = quality.check_readings(df, all_stations=expected)

    span = f"{df.ts.min():%Y-%m-%d %H:%MZ} to {df.ts.max():%Y-%m-%d %H:%MZ}"
    print(f"Airlume data-quality report")
    print(f"  rows {len(df)}   stations {df.station_id.nunique()} of {len(expected)} in the registry")
    print(f"  collected hours {len(rep.expected_hours)}   span {span}")
    print(f"  thresholds {quality.THRESHOLDS}")

    print("\n== Station uptime (over hours the collector actually ran) ==")
    u = rep.uptime.copy()
    u["uptime"] = (u["uptime"] * 100).round(0).astype(int).astype(str) + "%"
    u["last_seen"] = u["last_seen"].dt.strftime("%m-%d %H:%MZ").fillna("never")
    print(u.to_string(index=False))

    counts = rep.counts
    print(f"\n== Flags == {counts if counts else 'none'}")
    for kind in ("impossible", "stuck", "spike", "gap", "partial_round"):
        fl = rep.of_kind(kind)
        if not fl:
            continue
        print(f"\n-- {kind} ({len(fl)}) --")
        for f in fl[:25]:
            print(f"   {f}")
        if len(fl) > 25:
            print(f"   ... and {len(fl) - 25} more")

    ch = archive.load_all("city_hourly")
    coll = quality.check_source_collisions(ch[ch["source"] == "punjab_epa"]) if not ch.empty else []
    print(f"\n== City-hour source collisions in the stored archive: {len(coll)} ==")
    print("   (only the surviving row is stored, so collisions are visible")
    print("    at write time, not here; see docs/research/data-quality.md)")
    for f in coll[:10]:
        print(f"   {f}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=None, help="only the last N collected hours")
    ap.add_argument("--city", default="PB-LHE")
    sys.exit(main(ap.parse_args().hours, ap.parse_args().city))

"""Back-fill daily AQI from the EPD bulletin archive (Phase 1.5).

    python scripts/backfill_epd.py 1 10      # pages 1..10 (page 1 = newest, Dec 2025)
    python scripts/backfill_epd.py 1 104     # everything back to Jan 2018 (~2,300 PDFs, ~1.5 h)

Resumable: PDFs already in data/raw/epd/ are not downloaded again, and the
CSV archive is append-only.  One request every 2 s with a named user agent.
Styles A and B (2022-2025) are parsed; older styles are counted and skipped.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from airlume.pipeline import archive
from airlume.pipeline.backfill_epd import download, listing_links
from airlume.pipeline.epd_parse import parse_report
from airlume.pipeline.store import Store

first = int(sys.argv[1]) if len(sys.argv) > 1 else 1
last = int(sys.argv[2]) if len(sys.argv) > 2 else first
styles: Counter = Counter()
rows: list[dict] = []
city_rows: list[dict] = []
for page in range(first, last + 1):
    links = listing_links(page)
    print(f"page {page}: {len(links)} reports")
    for link in links:
        try:
            pdf = download(link)
            style, srows, avg, avg_date = parse_report(pdf)
        except Exception as e:  # keep going; record the failure
            print(f"   FAILED {link.title}: {e}")
            styles["error"] += 1
            continue
        styles[style] += 1
        rows += [r.__dict__ | {"source": "epd_pdf"} for r in srows]
        if avg is not None and avg_date is not None:
            city_rows.append({"date": avg_date, "station_label": "Lahore average", "station_id": None,
                              "city": "Lahore", "pollutant": "pm25", "conc": None, "aqi": avg,
                              "style": style, "source": "epd_pdf"})
df = pd.DataFrame(rows + city_rows)
print(f"styles: {dict(styles)}; parsed rows: {len(df)}")
if not df.empty:
    touched = archive.export("epd_daily", df)
    n = Store().upsert_epd_daily(df)
    print(f"{n} rows -> db; archive files: {[p.name for p in touched]}")

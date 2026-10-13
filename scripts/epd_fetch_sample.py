"""Download a handful of EPD daily-report PDFs so the parser can be designed.

    python scripts/epd_fetch_sample.py          # page 1, first 3 PDFs
    python scripts/epd_fetch_sample.py 40 3     # page 40 (older reports), 3 PDFs

Files land in data/raw/epd/ (git-ignored). Send Claude the file names and one
screenshot of a PDF's first page.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.pipeline.backfill_epd import download, list_page

page = int(sys.argv[1]) if len(sys.argv) > 1 else 1
n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
links = list_page(page)
print(f"page {page}: {len(links)} PDF links")
for l in links[:n]:
    print(" ", l.date_hint, l.title, "->", download(l))

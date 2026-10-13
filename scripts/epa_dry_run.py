"""Fetch aqi.punjab.gov.pk/lahore once and show what the parser finds.

Run only from a machine that can reach the site:  python scripts/epa_dry_run.py
Saves the raw HTML to data/raw/ for parser tests. Writes nothing to the database.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.collectors.epa import fetch_lahore_html, parse_lahore_html

html = fetch_lahore_html()
out = Path("data/raw") / f"lahore_{datetime.now(timezone.utc):%Y%m%dT%H%M}Z.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, encoding="utf-8")
print(f"saved raw page to {out} ({len(html):,} bytes)")
df = parse_lahore_html(html)
print(df.to_string() if not df.empty else "parser found no station rows - send the saved HTML to Claude")

"""EPD daily-report back-fill (Phase 1.5).

epd.punjab.gov.pk/Air_quality?page=N lists roughly 2,000 daily AQI PDFs back
to 2007.  Step 1 (this file): list the archive pages and download PDFs into
data/raw/epd/ with a polite delay.  Step 2 (after inspecting samples): a
parser per report layout, since the format changed several times over the
years.  Nothing here runs automatically; see scripts/epd_fetch_sample.py.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from airlume.collectors.epa import USER_AGENT
from airlume.config import ROOT

INDEX = "https://epd.punjab.gov.pk/Air_quality"
RAW_DIR = ROOT / "data" / "raw" / "epd"
DELAY_S = 2.0


@dataclass(frozen=True)
class ReportLink:
    title: str
    url: str
    date_hint: str | None  # e.g. '20251018' pulled from the file name when present


def list_page(page: int, session: requests.Session | None = None) -> list[ReportLink]:
    s = session or requests.Session()
    r = s.get(INDEX, params={"page": page}, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    out: list[ReportLink] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.lower().endswith(".pdf"):
            continue
        url = urljoin(INDEX, href)
        m = re.search(r"(20\d{6})", href)
        out.append(ReportLink(title=a.get_text(" ", strip=True), url=url, date_hint=m.group(1) if m else None))
    return out


def download(link: ReportLink, session: requests.Session | None = None) -> Path:
    s = session or requests.Session()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", link.url.rsplit("/", 1)[-1])
    dest = RAW_DIR / name
    if dest.exists():
        return dest
    r = s.get(link.url, headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)
    time.sleep(DELAY_S)
    return dest

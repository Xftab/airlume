"""Punjab EPA collector (aqi.punjab.gov.pk).

Findings from the 13 Oct 2026 investigation (docs/research/epa-portal.md):
- The site is Laravel + Vite, server-rendered.  There is no public JSON API on
  the main host; `https://api.aqi.punjab.gov.pk` exists but is undocumented.
- `GET /lahore` returns an HTML table with 11 station rows: Rank, Station,
  AQI, Level, PM2.5, PM10, CO, SO2, NO2, O3 and a "Last updated" line.
- `GET /` lists ~36 districts with their current AQI.
- Plain URLs may be served from a cache; add a throwaway query parameter.

Phase 0 ships the parser and a dry-run fetch.  Live scheduled collection
starts in Phase 1 after the permission email (docs/emails/).  Fetch rate is
one request per hour per page, with a descriptive User-Agent.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

from airlume import __version__
from airlume.aqi import aqi_from_concentrations

BASE = "https://aqi.punjab.gov.pk"
USER_AGENT = (
    f"Airlume/{__version__} (student project, UMT Lahore; "
    "contact via repository github.com/Xftab/airlume)"
)
KARACHI = ZoneInfo("Asia/Karachi")

# Portal station label -> our station_id
STATION_MAP = {
    "gt road": "LHR-GT",
    "shahdara": "LHR-SHD",
    "multan road": "LHR-MR",
    "barki road": "LHR-BR",
    "kahna nau": "LHR-KN",
    "gulberg iii": "LHR-GB3",
    "gulberg 3": "LHR-GB3",
    "dha phase 6": "LHR-DHA6",
    "egerton road": "LHR-EG",
    "punjab university": "LHR-PU",
    "wagha border": "LHR-WB",
    "wagah border": "LHR-WB",
    "safari park": "LHR-SP",
}

_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def _num(text: str) -> float | None:
    t = text.strip().replace(",", "")
    return float(t) if _NUM.match(t) else None


def _parse_updated(text: str, now: datetime | None = None) -> datetime | None:
    """'Last updated: 10:00 AM, Oct 13' or '... Oct 13, 2026' -> aware UTC datetime."""
    m = re.search(r"(\d{1,2}:\d{2}\s*[AP]M),\s*([A-Z][a-z]{2})\s+(\d{1,2})(?:,\s*(\d{4}))?", text)
    if not m:
        return None
    now = now or datetime.now(KARACHI)
    year = int(m.group(4)) if m.group(4) else now.year
    local = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)} {year}", "%I:%M %p %b %d %Y")
    local = local.replace(tzinfo=KARACHI)
    return local.astimezone(timezone.utc)


def parse_lahore_html(html: str, now: datetime | None = None) -> pd.DataFrame:
    """Parse the /lahore station table. Returns the tidy readings frame."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    page_ts = _parse_updated(text, now)
    rows: list[dict] = []
    for table in soup.find_all("table"):
        headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        if not any("station" in h for h in headers):
            continue
        idx = {h: i for i, h in enumerate(headers)}
        col_station = next((i for h, i in idx.items() if "station" in h), None)
        col_aqi = next((i for h, i in idx.items() if h.startswith("aqi")), None)
        col_pm25 = next((i for h, i in idx.items() if "2.5" in h), None)
        col_pm10 = next((i for h, i in idx.items() if "10" in h and "2.5" not in h), None)
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if not cells or col_station is None or col_station >= len(cells):
                continue
            label = cells[col_station]
            key = re.sub(r"\s+", " ", label.lower()).replace("lahore", "").strip()
            station_id = STATION_MAP.get(key)
            if station_id is None:
                continue
            # A per-row timestamp like 'Oct 13, 7:00 AM' may be present.
            row_ts = _parse_updated(" ".join(cells), now) or page_ts
            pm25 = _num(cells[col_pm25]) if col_pm25 is not None and col_pm25 < len(cells) else None
            pm10 = _num(cells[col_pm10]) if col_pm10 is not None and col_pm10 < len(cells) else None
            aqi_rep = _num(cells[col_aqi]) if col_aqi is not None and col_aqi < len(cells) else None
            aqi_comp, _ = aqi_from_concentrations(pm25, pm10)
            rows.append(
                {
                    "station_id": station_id,
                    "ts": row_ts,
                    "pm25": pm25,
                    "pm10": pm10,
                    "aqi": int(aqi_rep) if aqi_rep is not None else None,
                    "aqi_computed": aqi_comp,
                    "source": "punjab_epa",
                }
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["ts"]).drop_duplicates(subset=["station_id", "ts"])
    return df


def fetch_lahore_html(session: requests.Session | None = None, timeout: int = 30) -> str:
    s = session or requests.Session()
    r = s.get(
        f"{BASE}/lahore",
        params={"_": int(time.time())},  # cache-buster
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text


def collect_lahore() -> pd.DataFrame:
    """Fetch and parse the current Lahore page."""
    return parse_lahore_html(fetch_lahore_html())


# --------------------------------------------------------------------------
# Home page: district ranking (36 districts, city-level AQI)
# --------------------------------------------------------------------------

DISTRICT_ALIASES = {
    "dg khan": "Dera Ghazi Khan",
    "d.g. khan": "Dera Ghazi Khan",
    "d g khan": "Dera Ghazi Khan",
    "ryk": "Rahim Yar Khan",
    "mandi baha ud din": "Mandi Bahauddin",
    "mandi bahauddin": "Mandi Bahauddin",
}


def parse_home_html(html: str, city_lookup: dict[str, str], now: datetime | None = None) -> pd.DataFrame:
    """Parse the district ranking on `/`.

    `city_lookup` maps lower-case city name -> city_id (from the registry).
    Returns city_hourly rows: city_id, ts, pm25, pm10, aqi, n_stations, source.
    Only AQI is published at district level; pm25/pm10 are left empty.
    """
    soup = BeautifulSoup(html, "lxml")
    page_ts = _parse_updated(soup.get_text(" ", strip=True), now)
    rows: list[dict] = []
    seen: set[str] = set()
    # The ranking is a list/table of "<name> <aqi> <label>" items; be tolerant of markup.
    for el in soup.find_all(["tr", "li", "div", "a"]):
        text = el.get_text(" ", strip=True)
        if not text or len(text) > 120:
            continue
        m = re.match(r"^(?:\d{1,2}\s+)?([A-Za-z][A-Za-z .]+?)\s+(\d{1,3})(?:\s+[A-Za-z].*)?$", text)
        if not m:
            continue
        name = re.sub(r"\s+", " ", m.group(1)).strip().lower()
        name = DISTRICT_ALIASES.get(name, name).lower()
        city_id = city_lookup.get(name)
        if city_id is None or city_id in seen:
            continue
        seen.add(city_id)
        rows.append({
            "city_id": city_id,
            "ts": page_ts,
            "pm25": None,
            "pm10": None,
            "aqi": int(m.group(2)),
            "n_stations": None,
            "source": "punjab_epa",
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["ts"])
    return df


def fetch_home_html(session: requests.Session | None = None, timeout: int = 30) -> str:
    s = session or requests.Session()
    r = s.get(
        f"{BASE}/",
        params={"_": int(time.time())},
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text

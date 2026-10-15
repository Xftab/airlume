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

import json
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

UNMATCHED_STATIONS: list[str] = []  # Lahore station labels seen but absent from STATION_MAP


def _station_key(label: str) -> str:
    """Portal station label -> STATION_MAP key.

    The portal is inconsistent: the HTML table says "Gulberg III" while the
    embedded JSON says "Gulberg III, Lahore".  Lower-case it, drop the city
    name and any punctuation, collapse the spaces.
    """
    key = re.sub(r"[^a-z0-9 ]+", " ", label.lower())
    key = key.replace("lahore", "")
    return " ".join(key.split())


_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def _num(text: str) -> float | None:
    t = text.strip().replace(",", "")
    return float(t) if _NUM.match(t) else None


def _f(value) -> float | None:
    """Snapshot numbers arrive as JSON strings ("16.64") or numbers (62)."""
    if value is None or isinstance(value, (list, dict, bool)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_updated(text: str, now: datetime | None = None) -> datetime | None:
    """'10:00 AM, Oct 13' / '10:00 AM, Oct 13, 2026' (header) or 'Oct 13, 7:00 AM' (table rows) -> aware UTC."""
    m = re.search(r"(\d{1,2}:\d{2}\s*[AP]M),\s*([A-Z][a-z]{2})\s+(\d{1,2})(?:,\s*(\d{4}))?", text)
    if m:
        time_s, mon, day, year_s = m.group(1), m.group(2), m.group(3), m.group(4)
    else:
        m2 = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})(?:,\s*(\d{4}))?,\s*(\d{1,2}:\d{2}\s*[AP]M)", text)
        if not m2:
            return None
        mon, day, year_s, time_s = m2.group(1), m2.group(2), m2.group(3), m2.group(4)
    now = now or datetime.now(KARACHI)
    year = int(year_s) if year_s else now.year
    local = datetime.strptime(f"{time_s} {mon} {day} {year}", "%I:%M %p %b %d %Y")
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
        col_gas = {g: next((i for h, i in idx.items() if h.split()[0] == g), None) for g in ("co", "so2", "no2", "o3")}
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if not cells or col_station is None or col_station >= len(cells):
                continue
            label = cells[col_station]
            if _NUM.match(label):  # the rank column, when the table has no <td> for it
                continue
            station_id = STATION_MAP.get(_station_key(label))
            if station_id is None:
                # Never drop a station silently: an unmatched label is how
                # Gulberg III could have vanished unnoticed (it did not --- the
                # portal omits it from the table --- but nothing would have said so).
                if label and label not in UNMATCHED_STATIONS:
                    UNMATCHED_STATIONS.append(label)
                continue
            # A per-row timestamp like 'Oct 13, 7:00 AM' may be present.
            row_ts = _parse_updated(" ".join(cells), now) or page_ts
            pm25 = _num(cells[col_pm25]) if col_pm25 is not None and col_pm25 < len(cells) else None
            pm10 = _num(cells[col_pm10]) if col_pm10 is not None and col_pm10 < len(cells) else None
            aqi_rep = _num(cells[col_aqi]) if col_aqi is not None and col_aqi < len(cells) else None
            gases = {g: (_num(cells[i]) if i is not None and i < len(cells) else None) for g, i in col_gas.items()}
            aqi_comp, _ = aqi_from_concentrations(pm25, pm10, **gases)
            rows.append(
                {
                    "station_id": station_id,
                    "ts": row_ts,
                    "pm25": pm25,
                    "pm10": pm10,
                    **gases,
                    "aqi": int(aqi_rep) if aqi_rep is not None else None,
                    "aqi_computed": aqi_comp,
                    "source": "punjab_epa",
                }
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["ts"]).drop_duplicates(subset=["station_id", "ts"])
    return df


# --------------------------------------------------------------------------
# The embedded Livewire snapshot: the portal's own data, before it renders
# --------------------------------------------------------------------------
#
# Found 15 Oct 2026.  The page carries a `wire:snapshot` attribute holding the
# Livewire component's state as JSON -- about 150 KB -- and it contains *two*
# Lahore station arrays: one of 11 stations and one of 10.  The table the page
# renders is built from the 10, so **Gulberg III is in the portal's data but
# never appears in its own HTML table**, which is why we had collected 10 of 11
# stations since the first round.
#
# The snapshot is also richer than the table: official latitude and longitude
# per station (the portal publishes none in its HTML), temperature, humidity,
# wind speed and direction, the portal's own dominant pollutant, and a proper
# ISO timestamp with offset instead of a "last updated" line to parse.
#
# Livewire wraps every array and object as [value, {"s": "arr"}], so values are
# unwrapped on the way out.  Rather than hard-coding the path to the station
# array -- which a portal redesign would silently break -- we walk the whole
# structure for arrays of station records and take the largest, which is also
# what makes the 11-station array win over the 10-station one.

_SNAPSHOT_ATTR = "wire:snapshot"


def _unwrap(value):
    """Livewire serialises containers as [payload, {"s": ...}]; return the payload."""
    if isinstance(value, list) and len(value) == 2 and isinstance(value[1], dict) and "s" in value[1]:
        return value[0]
    return value


def _find_station_arrays(node, out: list[list[dict]] | None = None) -> list[list[dict]]:
    """Every array of station records anywhere in the snapshot."""
    out = [] if out is None else out
    node = _unwrap(node)
    if isinstance(node, list):
        records = [_unwrap(x) for x in node]
        if records and all(isinstance(r, dict) and "station_name" in r for r in records):
            out.append(records)
        for item in node:
            _find_station_arrays(item, out)
    elif isinstance(node, dict):
        for v in node.values():
            _find_station_arrays(v, out)
    return out


def parse_lahore_snapshot(html: str) -> pd.DataFrame:
    """Read the Lahore stations from the page's embedded Livewire snapshot.

    Returns the same tidy readings frame as `parse_lahore_html`, plus the
    weather columns the snapshot carries.  Returns an empty frame if the page
    has no snapshot (so the caller can fall back to the table parser).
    """
    soup = BeautifulSoup(html, "lxml")
    best: list[dict] = []
    for el in soup.find_all(attrs={_SNAPSHOT_ATTR: True}):
        raw = el.get(_SNAPSHOT_ATTR) or ""
        if "station_name" not in raw:
            continue
        try:
            snap = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for arr in _find_station_arrays(snap.get("data", snap)):
            if len(arr) > len(best):
                best = arr
    if not best:
        return pd.DataFrame()

    rows: list[dict] = []
    for rec in best:
        label = str(rec.get("station_name") or "")
        station_id = STATION_MAP.get(_station_key(label))
        if station_id is None:
            if label and label not in UNMATCHED_STATIONS:
                UNMATCHED_STATIONS.append(label)
            continue
        ts_raw = _unwrap(rec.get("timestamp"))
        ts = pd.to_datetime(ts_raw, utc=True, errors="coerce") if ts_raw else pd.NaT
        vals = {k: _f(rec.get(k)) for k in ("pm25", "pm10", "co", "so2", "no2", "o3")}
        aqi_rep = _f(rec.get("aqi"))
        aqi_comp, dominant = aqi_from_concentrations(**vals)
        rows.append({
            "station_id": station_id,
            "ts": ts,
            **vals,
            "aqi": int(aqi_rep) if aqi_rep is not None else None,
            "aqi_computed": aqi_comp,
            "source": "punjab_epa",
            # Extra columns the table never had. `archive.export` keeps only the
            # declared COLS, so these reach the app without changing the archive.
            "portal_station_id": rec.get("station_id"),
            "portal_dominant": rec.get("major_pollutant"),
            "our_dominant": dominant,
            "lat": _f(rec.get("latitude")),
            "lon": _f(rec.get("longitude")),
            "temperature": _f(rec.get("temperature")),
            "humidity": _f(rec.get("humidity")),
            "wind_speed": _f(rec.get("wind_speed")),
            "wind_direction": _f(rec.get("wind_direction")),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["ts"]).drop_duplicates(subset=["station_id", "ts"])
    return df


def parse_lahore(html: str, now: datetime | None = None) -> pd.DataFrame:
    """Preferred reader: the embedded snapshot, falling back to the HTML table.

    The snapshot carries all 11 stations; the rendered table carries 10.  The
    table parser is kept because it is what a portal redesign is most likely to
    leave working, and because its fixtures pin the behaviour we already trust.
    """
    df = parse_lahore_snapshot(html)
    if not df.empty:
        return df
    return parse_lahore_html(html, now)


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


_NOT_DISTRICTS = {"solar radiation", "last", "last updated", "humidity", "wind", "temperature", "aqi", "rank"}
UNMATCHED: list[str] = []  # district names seen on the page but absent from the registry (debug aid)


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
    UNMATCHED.clear()
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
        if city_id is None:
            if name.title() not in UNMATCHED and len(name) > 3 and name not in _NOT_DISTRICTS:
                UNMATCHED.append(name.title())
            continue
        if city_id in seen:
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


# --------------------------------------------------------------------------
# Lahore page extras: 7-day hourly city trend and the 24-hour forecast
# --------------------------------------------------------------------------

def parse_lahore_trend(html: str) -> pd.DataFrame:
    """The 'AQI Trends (Last 7 Days)' widget embeds one <span data-date data-hour data-aqi> per hour.
    Returns city_hourly rows for Lahore (city_id PB-LHE). Empty hours (future) are skipped."""
    soup = BeautifulSoup(html, "lxml")
    sec = soup.find(id="historical-aqi-graph-section") or soup
    rows = []
    for sp in sec.find_all("span", attrs={"data-aqi": True}):
        aqi = sp.get("data-aqi", "").strip()
        if not aqi.isdigit():
            continue
        m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", sp.get("data-date", ""))
        if not m:
            continue
        local = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)} {int(sp['data-hour']):02d}", "%b %d %Y %H")
        rows.append({
            "city_id": "PB-LHE",
            "ts": local.replace(tzinfo=KARACHI).astimezone(timezone.utc),
            "pm25": None, "pm10": None,
            "aqi": int(aqi), "n_stations": None,
            "source": "punjab_epa",
        })
    return pd.DataFrame(rows).drop_duplicates(subset=["city_id", "ts"]) if rows else pd.DataFrame()


def parse_lahore_forecast(html: str, issued_at: datetime | None = None) -> pd.DataFrame:
    """The '24-Hour AQI Forecast' widget: <article><time datetime=ISO>..<strong>AQI nnn</strong>.
    Returns forecast rows: city_id, issued_at, target_ts, aqi, source."""
    soup = BeautifulSoup(html, "lxml")
    sec = soup.find(id="aqi-forecast-section")
    if sec is None:
        return pd.DataFrame()
    page_ts = _parse_updated(soup.get_text(" ", strip=True)) or issued_at or datetime.now(timezone.utc)
    rows = []
    for art in sec.find_all("article"):
        t = art.find("time")
        strong = art.find("strong")
        if not (t and strong and t.get("datetime")):
            continue
        m = re.search(r"(\d{1,3})", strong.get_text())
        if not m:
            continue
        target = datetime.fromisoformat(t["datetime"]).astimezone(timezone.utc)
        rows.append({"city_id": "PB-LHE", "issued_at": page_ts, "target_ts": target,
                     "aqi": int(m.group(1)), "source": "punjab_epa_forecast"})
    return pd.DataFrame(rows)

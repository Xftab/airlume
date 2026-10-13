"""Parsers for the EPD Punjab daily AQI bulletins (epd.punjab.gov.pk/Air_quality).

Layouts seen in samples (13 Oct 2026):
- **Style A, Nov 2025 - Dec 2025:** two pages.  Page 1 is an Urdu district
  ranking (18 districts; Urdu shaping is garbled by text extraction, so only
  page 2 is used).  Page 2: "Average AQI of Lahore (13 AQMS) (334)", a
  "Rank Location AQI" table of 13 Lahore stations plus transboundary sites,
  and the note "AQI calculations is performed for last 24 hours (dd.mm.yyyy
  ...) using PM2.5 data.  The data is fetched from AQI Punjab dashboard."
- **Style B, 2022 - 2024:** "AIR QUALITY INDEX (AQI) OF LAHORE RECORDED WITH
  AQMS ON dd.mm.yyyy (BASED ON PREVIOUS 24 HOURS DATA)" with 3-4 stations,
  pollutant used, PEQS value, concentration, AQI.  Some 2022 rows use CO with
  min/max 8-hour averages and two AQIs; the maximum is kept.
- **Style D, Oct 2025:** "AQI Analysis Report of Lahore (Average AQI 78)", window
  "dd.mm.yyyy (03:00PM) to dd.mm.yyyy (03:00PM)"; table Sr/Location/AQI/Dominant
  pollutant for Lahore stations (page 1) and districts (page 2).  Both parsed;
  the AQI is reliable, the dominant-pollutant tag is a best effort because the
  PM subscript lands on a neighbouring line.
- **Style E, Aug - Sep 2025:** "Lahore & Punjab AQI Report & Ranking", values
  drawn on a map; only the printed "Average AQI Lahore NN" is recovered.
- **Scanned (Nov 2024 and some others):** CamScanner images, no text.  Skipped.
- **Style C, 2018 - 2020:** concentration tables for the old network
  (Town Hall, Dental College, Met Office, Multan, Faisalabad ...).  Not
  parsed yet; stations do not map to today's network.

Every row is a *daily* value: `date` is the day the 24-hour window covers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pdfplumber

STATION_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z][A-Za-z0-9 .&()'-]*?)\s+(\d{2,3})\s*$")
NOTE_DATE_RE = re.compile(r"last 24 hours\s*\((\d{2}\.\d{2}\.\d{4})")
UPDATED_RE = re.compile(r"Updated\s+Time:\s*(\d{2}\.\d{2}\.\d{4})")
TITLE_B_RE = re.compile(r"AQMS (?:ON|OF EPA (?:AT|IN) [A-Z ]+?)\s+(\d{2}\.\d{2}\.\d{4})")
PM_ROW_RE = re.compile(r"(.*?)\s*(?:Respirable\s+)?Particulate [Mm]atter(?:\s*\(PM\s*2\.5\s*\)|\s*\(PM\s*10\s*\))?\s+(35|150)\s+(\d+(?:\.\d+)?)\s+(\d{2,3})")
# 2020-2021 rows: "<name>  PM  35  46.326  128" / "<name>  CO  5 (mg/m3)  8.470  79" / "<name> NO 80 23.295 11"
B17_ROW_RE = re.compile(r"^\s*(.*?)\s+(PM|CO|NO|SO)\s+(35|150|5|80|120|130)\s*(?:\(mg/m3\))?\s+(\d+(?:\.\d+)?)\s+(\d{1,3})\s*$")
B17_POL = {"PM": "pm25", "CO": "co", "NO": "no2", "SO": "so2"}
AVG_RE = re.compile(r"Average\s+AQI\s+of\s+Lahore.*?\((\d{2,3})\)\s*$", re.S)

# Partial / inconsistent labels in the bulletins -> one canonical label.
LABEL_ALIASES = {
    "(epa hqs, national hockey": "EPA HQ",
    "national hockey stadium,": "EPA HQ",
    "national hockey stadium, gulberg lahore": "EPA HQ",
    "mobile aqms": "Mobile AQMS",
    "(college of earth and": "PU 1",
    "punjab university, lahore": "PU 1",
    "town hall, lahore": "Town Hall",
    "wahga": "Wahga Boarder",
    "wahga boarder": "Wahga Boarder",
    "c2 sector, block 1, township,": "Township",
    "c2 sector, block 1,": "Township",
    "d1 sector, block 2": "Township D1",
    "met station, jail road": "Jail Road",
    "met station, jail": "Jail Road",
    "mobile van (model": "Mobile AQMS",
    "cees, university of": "PU 1",
    "national hockey": "EPA HQ",
    "gujjumata, farozpur road": "Gajjumata",
    "daroghawala, industrial area": "Daroghawala",
    "shallay valley range road": "Rawalpindi Shalley Valley",
    "rawalpindi": "Rawalpindi Shalley Valley",
}

# Transboundary / out-of-Lahore sites that appear in the Lahore table.
SITE_CITY = {"raja jang": "Kasur", "lathepur": "Sheikhupura", "bhu jandiala": "Sheikhupura",
             "rawalpindi shalley valley": "Rawalpindi", "rahim yar khan": "Rahim Yar Khan", "multan": "Multan",
             "faisalabad": "Faisalabad", "gujranwala": "Gujranwala", "sheikhupura": "Sheikhupura",
             "sialkot": "Sialkot", "bahawalpur": "Bahawalpur", "sargodha": "Sargodha", "kasur": "Kasur"}

# Bulletin label -> registry station_id where the site is the same as today's portal station.
LABEL_TO_STATION = {
    "uet": "LHR-GT",
    "kahna nau": "LHR-KN",
    "shahdara": "LHR-SHD",
    "safari park": "LHR-SP",
    "egerton road": "LHR-EG",
    "wahga boarder": "LHR-WB",
    "wagha border": "LHR-WB",
    "pu 1": "LHR-PU",
}


@dataclass(frozen=True)
class DailyRow:
    date: date
    station_label: str
    station_id: str | None
    city: str
    pollutant: str | None
    conc: float | None
    aqi: int
    style: str


def _d(s: str) -> date:
    return datetime.strptime(s, "%d.%m.%Y").date()


def _norm(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().lower())


def extract_pages(path: Path) -> list[str]:
    with pdfplumber.open(str(path)) as pdf:
        return [p.extract_text(layout=True) or "" for p in pdf.pages]


def detect_style(pages: list[str]) -> str:
    joined = "\n".join(pages)
    if not joined.strip() or joined.strip() == "CamScanner":
        return "scanned"
    if "Rank" in joined and "Location" in joined and "Hourly Report" in joined:
        return "A"
    if "AQI" in joined and "Analysis" in joined and "Dominant" in joined:
        return "D"
    if re.search(r"Average\s+AQI\s+Lahore\s+\d", joined):
        return "E"
    if "Smog Policy" in joined:
        return "B17"  # 2020-2021: old Smog Policy 2017 scale; keep concentrations, recompute AQI later
    if TITLE_B_RE.search(joined):
        return "B"
    if "DAILY QUALITY MONITORING" in joined or "Monitoring of Air Quality" in joined:
        return "C"
    return "unknown"


def _rows_style_a(pages: list[str]) -> list[DailyRow]:
    text = "\n".join(pages)
    m = NOTE_DATE_RE.search(text)
    if m:
        day = _d(m.group(1))
    else:
        u = UPDATED_RE.search(text)
        if not u:
            return []
        day = _d(u.group(1)) - timedelta(days=1)
    rows: list[DailyRow] = []
    lines = [l.rstrip() for l in text.splitlines()]
    # Rank/Location/AQI column region: take the text right of the "Rank" header column.
    start = next((i for i, l in enumerate(lines) if re.search(r"\bRank\s+Location\s+AQI\b", l)), None)
    if start is None:
        return []
    col = lines[start].index("Rank")
    pending_name: list[str] = []
    pending_rank: tuple[int, int] | None = None  # (rank, aqi) waiting for a name
    for l in lines[start + 1:]:
        seg = l[col:].strip() if len(l) > col else ""
        if not seg:
            continue
        if seg.startswith("Transboundary"):
            break
        m = STATION_RE.match(seg)
        if m:
            label = m.group(2).strip()
            rows.append(_mk(day, label, int(m.group(3)), "A"))
            pending_name, pending_rank = [], None
            continue
        m2 = re.match(r"^(\d{1,2})\s+(\d{2,3})$", seg)  # rank + aqi, name on neighbouring lines
        if m2:
            if pending_name:
                rows.append(_mk(day, " ".join(pending_name), int(m2.group(2)), "A"))
                pending_name = []
            else:
                pending_rank = (int(m2.group(1)), int(m2.group(2)))
            continue
        if re.match(r"^[A-Za-z][A-Za-z .()'-]*$", seg):
            if pending_rank:
                pending_name.append(seg)
                # a name split over two lines: wait one more line if it looks incomplete
                if seg.lower() in {"wahga", "wagha"}:
                    continue
                rows.append(_mk(day, " ".join(pending_name), pending_rank[1], "A"))
                pending_name, pending_rank = [], None
            else:
                pending_name.append(seg)
    return rows


def canonical(label: str) -> str:
    n = _norm(label)
    return LABEL_ALIASES.get(n, re.sub(r"\s+", " ", label.strip()))


def _mk(day: date, label: str, aqi: int, style: str, pollutant: str | None = "pm25",
        conc: float | None = None, city: str = "Lahore") -> DailyRow:
    label = canonical(label)
    city = SITE_CITY.get(_norm(label), city)
    return DailyRow(day, label, LABEL_TO_STATION.get(_norm(label)), city, pollutant, conc, aqi, style)


def _rows_style_b(pages: list[str]) -> list[DailyRow]:
    text = pages[0]
    m = TITLE_B_RE.search(text)
    if not m:
        return []
    day = _d(m.group(1))
    lines = [l.rstrip() for l in text.splitlines()]
    rows: list[DailyRow] = []
    prev_text = ""
    for i, l in enumerate(lines):
        core = l[:95]  # drop the AQI-limits legend on the right
        # PM rows: "<name> Particulate matter 35  58  133"  /  "Respirable Particulate Matter 35 76 154"
        pm = PM_ROW_RE.search(core)
        if pm:
            name = pm.group(1).strip() or prev_text
            pol = "pm10" if pm.group(2) == "150" else "pm25"
            rows.append(_mk(day, name, int(pm.group(4)), "B", pol, float(pm.group(3)),
                            city="Rawalpindi" if "rawalpindi" in (name + " " + lines[i + 1] if i + 1 < len(lines) else name).lower() else "Lahore"))
            prev_text = ""
            continue
        # Some layouts put the numbers on the line after "Particulate matter" (PM10 Rawalpindi case)
        num_only = re.match(r"^\s*(?:([A-Za-z][A-Za-z ,.()&-]*?)\s+)?(35|150)\s+(\d+(?:\.\d+)?)\s+(\d{2,3})\s*$", core)
        if num_only and i > 0 and "Particulate" in lines[i - 1]:
            name = (num_only.group(1) or "").strip() or prev_text
            pol = "pm10" if num_only.group(2) == "150" else "pm25"
            rows.append(_mk(day, name, int(num_only.group(4)), "B", pol, float(num_only.group(3)),
                            city="Rawalpindi" if "rawalpindi" in name.lower() else "Lahore"))
            prev_text = ""
            continue
        co = re.search(r"(.*?)\s*Carbon Monoxide \(CO\)\s+5\s+(?:Minimum.*)?$", core)
        if co:
            prev_text = co.group(1).strip() or prev_text
            # numbers may be on this line or a later one: "4.26 4.77 84 95"
            for look in lines[i:i + 5]:
                nums = re.search(r"(\d+\.\d+)\s+(\d+\.\d+)\s+(\d{2,3})\s+(\d{2,3})", look)
                if nums:
                    rows.append(_mk(day, prev_text, max(int(nums.group(3)), int(nums.group(4))), "B", "co", float(nums.group(2))))
                    break
            prev_text = ""
            continue
        stripped = core.strip()
        if stripped and re.match(r"^[A-Za-z(]", stripped) and not stripped.startswith(("Station", "AIR QUALITY", "Note", "Disclaimer", "to calculate", "calculate", "used to", "Conc.")):
            prev_text = re.sub(r"\s+", " ", stripped)
    return rows


D_WINDOW_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s*\(\d{2}:\d{2}[AP]M\)\s*to\s*(\d{2}\.\d{2}\.\d{4})")
D_ROW_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z][A-Za-z .&-]*?)\s+(\d{1,3}(?: \d)?)\s+(PM|O|SO|NO|CO)\b")
D_DISTRICT_ROW_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z][A-Za-z .&-]*?)\s+(\d{1,3})(?:\s+(PM|O|SO|NO|CO|10|2\.5))?(?:\s|$)")
D_AVG_RE = re.compile(r"Average\s+AQI\s+(\d{2,3})\)")
_DPOL = {"PM": "pm", "O": "o3", "SO": "so2", "NO": "no2", "CO": "co"}


def _rows_style_d(pages: list[str]) -> tuple[list[DailyRow], int | None]:
    text = "\n".join(pages)
    w = D_WINDOW_RE.search(text)
    if not w:
        return [], None
    day = _d(w.group(2))  # the window ends at 3 pm on this day
    avg = D_AVG_RE.search(text)
    rows: list[DailyRow] = []
    for pi, page in enumerate(pages):
        is_district = bool(re.search(r"Report\s+of\s+Districts", page))
        lines = page.splitlines()
        for i, l in enumerate(lines):
            m = (D_DISTRICT_ROW_RE if is_district else D_ROW_RE).match(l[:60] if is_district else l)
            if not m:
                # Name split above and below the rank: "Rahim Yar" / "9   58  PM" / "Khan"
                m2 = re.match(r"^\s*(\d{1,2})\s+(\d{1,3})\s+(PM|O|SO|NO|CO)\b", l) if is_district else None
                if m2 and 0 < i < len(lines) - 1:
                    above, below = lines[i - 1].strip(), lines[i + 1].strip()
                    label = " ".join(x for x in (above.split("  ")[0], below.split("  ")[0]) if re.match(r"^[A-Z][a-z]+(?: [A-Z][a-z]+)?$", x))
                    if label:
                        rows.append(DailyRow(day, f"{label} average", None, label, "pm25", None, int(m2.group(2)), "D"))
                continue
            label = m.group(2).strip()
            if label in {"Rahim Yar", "Dera Ghazi", "Mandi", "Nankana", "Kot", "Toba Tek"} and i + 1 < len(lines):
                nxt_name = lines[i + 1].strip()
                if re.match(r"^[A-Z][a-z]+(?: [A-Z][a-z]+)?$", nxt_name):
                    label += " " + nxt_name
            aqi = int(m.group(3).replace(" ", ""))
            tag = m.group(4) or "PM"
            pol = _DPOL.get(tag, "pm")
            if pol == "pm":
                around = " ".join(x.strip() for x in lines[max(0, i - 1):i + 2])
                pol = "pm10" if re.search(r"PM\s*\(?\s*10|PM\s+\(\d|\b10\s*$|\s10\s", around) and "2.5" not in around.split("PM")[-1][:8] else "pm25"
            if is_district:
                rows.append(DailyRow(day, f"{label} average", None, label, pol, None, aqi, "D"))
            else:
                rows.append(_mk(day, label, aqi, "D", pol))
    return rows, int(avg.group(1)) if avg else None


def city_average_e(pages: list[str]) -> tuple[date | None, int | None]:
    text = pages[0]
    m = re.search(r"Average\s+AQI\s+Lahore\s+(\d{2,3})", text)
    d = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
    return (_d(d.group(1)) if d else None), (int(m.group(1)) if m else None)


def _rows_style_b17(pages: list[str]) -> list[DailyRow]:
    """2020-2021 bulletins on the Smog Policy 2017 scale. AQI stored as printed; `style`='B17'
    marks it as non-comparable; `conc` allows recomputation on the current scale."""
    text = pages[0]
    m = TITLE_B_RE.search(text)
    if not m:
        return []
    day = _d(m.group(1))
    lines = [l.rstrip() for l in text.splitlines()]
    rows: list[DailyRow] = []
    prev = ""
    for i, l in enumerate(lines):
        core = l[:88]
        r = B17_ROW_RE.match(core)
        if r:
            name = r.group(1).strip() or prev
            # a name split like "Met Station, Jail" / "Road"
            if i + 1 < len(lines) and re.match(r"^\s{8,}([A-Z][a-z]+)\s*$", lines[i + 1]):
                name += " " + lines[i + 1].strip()
            rows.append(DailyRow(day, canonical(name), LABEL_TO_STATION.get(_norm(canonical(name))), "Lahore",
                                 B17_POL[r.group(2)], float(r.group(4)), int(r.group(5)), "B17"))
            prev = ""
            continue
        # CO / PM rows with min/max 8-hour averages: numbers on a later line "7.19 11.10 144 201"
        hdr = re.match(r"^\s*(.*?)\s+(CO|PM2\.5)\s+(5|35)\s+Minimum", core)
        if hdr:
            name = hdr.group(1).strip() or prev
            for look in lines[i:i + 6]:
                nums = re.search(r"(\d+\.\d+)\s+(\d+\.\d+)\s+(\d{2,3})\s+(\d{2,3})", look)
                if nums:
                    pol = "co" if hdr.group(3) == "5" else "pm25"  # PEQS 5 mg/m3 is CO even when mislabelled
                    rows.append(DailyRow(day, canonical(name), None, "Lahore", pol, float(nums.group(2)),
                                         max(int(nums.group(3)), int(nums.group(4))), "B17"))
                    break
            prev = ""
            continue
        stripped = core.strip()
        if stripped and re.match(r"^[A-Z(]", stripped) and not stripped.startswith(("Station", "AIR QUALITY", "Note", "Disclaimer", "AQI", "Locations", "Site")):
            prev = re.sub(r"\s+", " ", stripped)
    return rows


def city_average(pages: list[str]) -> int | None:
    m = re.search(r"Average\s+AQI\s+of\s+Lahore[^\n]*?\((\d{2,3})\)", "\n".join(pages))
    return int(m.group(1)) if m else None


def parse_pages(pages: list[str]) -> tuple[str, list[DailyRow], int | None, date | None]:
    """Returns (style, station rows, Lahore average AQI if printed, date of that average)."""
    style = detect_style(pages)
    if style == "A":
        rows = _rows_style_a(pages)
        return style, rows, city_average(pages), rows[0].date if rows else None
    if style == "B":
        return style, _rows_style_b(pages), None, None
    if style == "B17":
        return style, _rows_style_b17(pages), None, None
    if style == "D":
        rows, avg = _rows_style_d(pages)
        return style, rows, avg, rows[0].date if rows else None
    if style == "E":
        d, avg = city_average_e(pages)
        return style, [], avg, d
    return style, [], None, None


def parse_report(path: Path) -> tuple[str, list[DailyRow], int | None, date | None]:
    return parse_pages(extract_pages(path))

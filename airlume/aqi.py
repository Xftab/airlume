"""AQI computation and category bands.

Two things live here and must stay separate:

1. **Sub-index formula** - the US EPA piecewise-linear breakpoints
   (Technical Assistance Document, EPA-454/B-24-002).  Punjab EPA's portal
   numbers match the *pre-2024* PM2.5 table (0-12 / 12.1-35.4 / ...), so that
   table is the default.  The 2024 revision (0-9.0 / 9.1-35.4 / ...) is kept
   as an option for the harmonisation study (plan phase 1.7, weakness W1).

2. **Category labels** - Punjab EPA uses its own 7-band labelling, which is
   shifted one band from the US names.  We display Punjab labels by default
   because that is what users see on aqi.punjab.gov.pk.

Sources: aqi.punjab.gov.pk/health-advisory; EPD order No.355/PA-to-DG/EPA/2025;
document.airnow.gov technical assistance document (Table 6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Scale = Literal["us_2012", "us_2024"]

# (conc_lo, conc_hi, aqi_lo, aqi_hi)
_PM25_2012 = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]
_PM25_2024 = [
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
]
_PM10 = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 400),
    (505, 604, 401, 500),
]

# Gases: US EPA tables are in ppb (O3 8-h, SO2 1-h, NO2 1-h) and ppm (CO 8-h).
# The Punjab portal shows gases in ug/m3 (CO in mg/m3); convert at 25 C, 1 atm.
_O3_8H_PPB = [(0, 54, 0, 50), (55, 70, 51, 100), (71, 85, 101, 150), (86, 105, 151, 200), (106, 200, 201, 300)]
_O3_1H_PPB = [(125, 164, 101, 150), (165, 204, 151, 200), (205, 404, 201, 300), (405, 504, 301, 400), (505, 604, 401, 500)]
_NO2_PPB = [(0, 53, 0, 50), (54, 100, 51, 100), (101, 360, 101, 150), (361, 649, 151, 200), (650, 1249, 201, 300), (1250, 1649, 301, 400), (1650, 2049, 401, 500)]
_SO2_PPB = [(0, 35, 0, 50), (36, 75, 51, 100), (76, 185, 101, 150), (186, 304, 151, 200), (305, 604, 201, 300), (605, 804, 301, 400), (805, 1004, 401, 500)]
_CO_PPM = [(0.0, 4.4, 0, 50), (4.5, 9.4, 51, 100), (9.5, 12.4, 101, 150), (12.5, 15.4, 151, 200), (15.5, 30.4, 201, 300), (30.5, 40.4, 301, 400), (40.5, 50.4, 401, 500)]

UGM3_PER_PPB = {"o3": 1.96, "no2": 1.88, "so2": 2.62}  # 25 C, 1 atm
MGM3_PER_PPM_CO = 1.145

BREAKPOINTS: dict[str, dict[Scale, list[tuple[float, float, int, int]]]] = {
    "pm25": {"us_2012": _PM25_2012, "us_2024": _PM25_2024},
    "pm10": {"us_2012": _PM10, "us_2024": _PM10},
    "o3": {"us_2012": _O3_8H_PPB, "us_2024": _O3_8H_PPB},
    "no2": {"us_2012": _NO2_PPB, "us_2024": _NO2_PPB},
    "so2": {"us_2012": _SO2_PPB, "us_2024": _SO2_PPB},
    "co": {"us_2012": _CO_PPM, "us_2024": _CO_PPM},
}


def to_epa_units(pollutant: str, conc: float | None) -> float | None:
    """Portal units (ug/m3; CO mg/m3) -> EPA table units (ppb; CO ppm). PM unchanged."""
    if conc is None:
        return None
    if pollutant in UGM3_PER_PPB:
        return conc / UGM3_PER_PPB[pollutant]
    if pollutant == "co":
        return conc / MGM3_PER_PPM_CO
    return conc


def _interp(table: list[tuple[float, float, int, int]], c: float) -> int | None:
    for lo, hi, ilo, ihi in table:
        if lo <= c <= hi:
            return round((ihi - ilo) / (hi - lo) * (c - lo) + ilo)
    if c > table[-1][1]:
        return 500
    for lo, hi, ilo, ihi in table:
        if c < lo:
            return ilo
    return None


def sub_index(pollutant: str, conc: float | None, scale: Scale = "us_2012") -> int | None:
    """Piecewise-linear AQI sub-index for one pollutant. None if no data."""
    if conc is None or conc < 0:
        return None
    table = BREAKPOINTS[pollutant][scale]
    # Truncate like the EPA does (PM2.5 and CO to 0.1, the rest to integer).
    c = round(conc, 1) if pollutant in ("pm25", "co") else float(int(conc))
    for lo, hi, ilo, ihi in table:
        if lo <= c <= hi:
            return round((ihi - ilo) / (hi - lo) * (c - lo) + ilo)
    if c > table[-1][1]:
        return 500
    # Falls in a gap between bands (e.g. 12.05); snap to the band above.
    for lo, hi, ilo, ihi in table:
        if c < lo:
            return ilo
    return None


def aqi_from_concentrations(
    pm25: float | None = None,
    pm10: float | None = None,
    scale: Scale = "us_2012",
    o3: float | None = None,
    no2: float | None = None,
    so2: float | None = None,
    co: float | None = None,
) -> tuple[int | None, str | None]:
    """Overall AQI = max of sub-indices. Returns (aqi, dominant_pollutant).

    Gas inputs are in portal units (ug/m3; CO mg/m3) and converted here.
    O3 uses the 8-hour table; values above its top (200 ppb) fall back to the 1-hour table.
    """
    o3_ppb = to_epa_units("o3", o3)
    if o3_ppb is not None and o3_ppb > 200:
        o3_idx = _interp(_O3_1H_PPB, float(int(o3_ppb)))
    else:
        o3_idx = sub_index("o3", o3_ppb, scale)
    candidates = [
        ("pm25", sub_index("pm25", pm25, scale)),
        ("pm10", sub_index("pm10", pm10, scale)),
        ("o3", o3_idx),
        ("no2", sub_index("no2", to_epa_units("no2", no2), scale)),
        ("so2", sub_index("so2", to_epa_units("so2", so2), scale)),
        ("co", sub_index("co", to_epa_units("co", co), scale)),
    ]
    candidates = [(p, v) for p, v in candidates if v is not None]
    if not candidates:
        return None, None
    pollutant, value = max(candidates, key=lambda t: t[1])
    return value, pollutant


@dataclass(frozen=True)
class Band:
    lo: int
    hi: int
    label: str
    colour: str  # hex, used by the map layers


PUNJAB_BANDS = [
    Band(0, 50, "Good", "#7FB069"),
    Band(51, 100, "Satisfactory", "#C7D66D"),
    Band(101, 150, "Moderate", "#E8A33D"),
    Band(151, 200, "Unhealthy for sensitive groups", "#EE9D52"),
    Band(201, 300, "Unhealthy", "#E0736A"),
    Band(301, 400, "Very unhealthy", "#C98FDB"),
    Band(401, 500, "Hazardous", "#8B3A62"),
]

US_BANDS = [
    Band(0, 50, "Good", "#00E400"),
    Band(51, 100, "Moderate", "#FFFF00"),
    Band(101, 150, "Unhealthy for sensitive groups", "#FF7E00"),
    Band(151, 200, "Unhealthy", "#FF0000"),
    Band(201, 300, "Very unhealthy", "#8F3F97"),
    Band(301, 500, "Hazardous", "#7E0023"),
]


def band_for(aqi: int | None, scheme: Literal["punjab", "us"] = "punjab") -> Band | None:
    if aqi is None:
        return None
    bands = PUNJAB_BANDS if scheme == "punjab" else US_BANDS
    a = max(0, min(500, int(aqi)))
    for b in bands:
        if b.lo <= a <= b.hi:
            return b
    return bands[-1]


def hex_to_rgb(colour: str) -> list[int]:
    c = colour.lstrip("#")
    return [int(c[i : i + 2], 16) for i in (0, 2, 4)]

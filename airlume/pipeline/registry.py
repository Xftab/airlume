"""Station and city registry, loaded from data/registry/*.csv.

Also holds the *nearest-station rule*: a neighbourhood the user names that has
no station of its own (e.g. "Model Town") is mapped to the closest station,
and the answer says so.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from airlume.config import ROOT

REGISTRY_DIR = ROOT / "data" / "registry"

# Lahore neighbourhoods people ask about that have no EPA station.
# Coordinates are approximate area centres (OpenStreetMap). Used only to pick
# the nearest station; never shown as a measurement point.
KNOWN_AREAS: dict[str, tuple[float, float]] = {
    "model town": (31.4815, 74.3240),
    "johar town": (31.4697, 74.2728),
    "allama iqbal town": (31.5070, 74.2910),
    "shalimar": (31.5880, 74.3830),
    "shalimar gardens": (31.5880, 74.3830),
    "township": (31.4530, 74.3080),
    "garden town": (31.4990, 74.3170),
    "cantt": (31.5160, 74.3880),
    "lahore cantt": (31.5160, 74.3880),
    "bahria town": (31.3680, 74.1810),
    "wapda town": (31.4300, 74.2650),
    "faisal town": (31.4780, 74.2970),
    "iqbal town": (31.5070, 74.2910),
    "samanabad": (31.5390, 74.2900),
    "anarkali": (31.5670, 74.3100),
    "walled city": (31.5830, 74.3100),
    "ravi road": (31.6000, 74.2900),
    "thokar": (31.4680, 74.2370),
    "thokar niaz baig": (31.4680, 74.2370),
    "valencia": (31.4000, 74.2450),
    "askari": (31.5000, 74.4150),
    "gulshan e ravi": (31.5500, 74.2830),
    "mall road": (31.5600, 74.3250),
    "ferozepur road": (31.4700, 74.3250),
    "dha": (31.4700, 74.4200),
    "gulberg": (31.5100, 74.3450),
}


@dataclass(frozen=True)
class Station:
    station_id: str
    name: str
    city: str
    province: str
    operator: str
    lat: float
    lon: float
    source: str
    confidence: str
    waqi_id: str
    notes: str


@dataclass(frozen=True)
class City:
    city_id: str
    name: str
    province: str
    lat: float
    lon: float
    source: str
    primary_source: str
    notes: str


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Registry:
    def __init__(self, stations: list[Station], cities: list[City]):
        self.stations = stations
        self.cities = cities
        self._city_by_name = {c.name.lower(): c for c in cities}
        self._city_by_id = {c.city_id: c for c in cities}
        self._station_by_id = {s.station_id: s for s in stations}

    @classmethod
    def load(cls, directory: Path = REGISTRY_DIR) -> "Registry":
        with open(directory / "stations.csv", newline="", encoding="utf-8") as f:
            stations = [
                Station(
                    station_id=r["station_id"],
                    name=r["name"],
                    city=r["city"],
                    province=r["province"],
                    operator=r["operator"],
                    lat=float(r["lat"]),
                    lon=float(r["lon"]),
                    source=r["source"],
                    confidence=r["confidence"],
                    waqi_id=r["waqi_id"],
                    notes=r["notes"],
                )
                for r in csv.DictReader(f)
            ]
        with open(directory / "cities.csv", newline="", encoding="utf-8") as f:
            cities = [
                City(
                    city_id=r["city_id"],
                    name=r["name"],
                    province=r["province"],
                    lat=float(r["lat"]),
                    lon=float(r["lon"]),
                    source=r["source"],
                    primary_source=r["primary_source"],
                    notes=r["notes"],
                )
                for r in csv.DictReader(f)
            ]
        return cls(stations, cities)

    # --- cities ---
    CITY_ALIASES = {
        "dg khan": "Dera Ghazi Khan",
        "d.g. khan": "Dera Ghazi Khan",
        "ryk": "Rahim Yar Khan",
        "pindi": "Rawalpindi",
        "isb": "Islamabad",
        "khi": "Karachi",
        "lhr": "Lahore",
        "lhe": "Lahore",
    }

    def match_city(self, name: str) -> City | None:
        n = " ".join(name.lower().split())
        n = self.CITY_ALIASES.get(n, n).lower()
        if n in self._city_by_name:
            return self._city_by_name[n]
        m = get_close_matches(n, list(self._city_by_name), n=1, cutoff=0.75)
        return self._city_by_name[m[0]] if m else None

    def city(self, city_id: str) -> City:
        return self._city_by_id[city_id]

    # --- stations ---
    def stations_in(self, city_id: str) -> list[Station]:
        city = self._city_by_id[city_id]
        return [s for s in self.stations if s.city.lower() == city.name.lower()]

    def station(self, station_id: str) -> Station:
        return self._station_by_id[station_id]

    def match_station(self, area: str, city_id: str) -> tuple[str, str | None] | None:
        """Return (station_id, note). Note explains a nearest-station substitution."""
        a = " ".join(area.lower().replace("-", " ").split())
        stations = self.stations_in(city_id)
        if not stations:
            return None
        names = [s.name for s in stations]
        # 1. direct / fuzzy station name
        m = get_close_matches(a, [n.lower() for n in names], n=1, cutoff=0.7)
        if m:
            s = stations[[n.lower() for n in names].index(m[0])]
            return s.station_id, None
        # 2. substring (e.g. "gulberg" -> "Gulberg III")
        for s in stations:
            if a in s.name.lower() or s.name.lower() in a:
                return s.station_id, None
        # 3. known neighbourhood -> nearest station
        key = a
        if key not in KNOWN_AREAS:
            km = get_close_matches(key, list(KNOWN_AREAS), n=1, cutoff=0.75)
            key = km[0] if km else ""
        if key:
            lat, lon = KNOWN_AREAS[key]
            best = min(stations, key=lambda s: haversine_km(lat, lon, s.lat, s.lon))
            d = haversine_km(lat, lon, best.lat, best.lon)
            note = (
                f"'{area}' has no station of its own; showing the nearest one, "
                f"{best.name}, about {d:.1f} km away."
            )
            return best.station_id, note
        return None

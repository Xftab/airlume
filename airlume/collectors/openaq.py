"""OpenAQ v3 collector (free key; 60 requests/min; licence varies per station).

Carries Urban Unit AirGradient sensors in Islamabad, Karachi, Peshawar and the
US Department of State monitors (dormant since March 2025).  Phase 0 ships the
client stub; station discovery runs in Phase 1 once the key exists.
"""

from __future__ import annotations

import pandas as pd
import requests

from airlume.config import load_settings

BASE = "https://api.openaq.org/v3"


def _headers() -> dict[str, str]:
    key = load_settings().openaq_api_key
    if not key:
        raise RuntimeError("OPENAQ_API_KEY is not set in .env")
    return {"X-API-Key": key}


def locations_near(lat: float, lon: float, radius_m: int = 25_000, limit: int = 100,
                   session: requests.Session | None = None) -> pd.DataFrame:
    s = session or requests.Session()
    r = s.get(
        f"{BASE}/locations",
        params={"coordinates": f"{lat},{lon}", "radius": radius_m, "limit": limit},
        headers=_headers(),
        timeout=30,
    )
    r.raise_for_status()
    rows = []
    for loc in r.json().get("results", []):
        rows.append({
            "openaq_id": loc["id"],
            "name": loc.get("name"),
            "provider": (loc.get("provider") or {}).get("name"),
            "owner": (loc.get("owner") or {}).get("name"),
            "lat": (loc.get("coordinates") or {}).get("latitude"),
            "lon": (loc.get("coordinates") or {}).get("longitude"),
            "licence": ((loc.get("licenses") or [{}])[0]).get("name"),
            "sensors": ",".join(s_["parameter"]["name"] for s_ in loc.get("sensors", [])),
        })
    return pd.DataFrame(rows)

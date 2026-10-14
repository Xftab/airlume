"""Coverage map and station-placement recommendation (contributions C3 and C7).

A regular grid over the Lahore district; each cell carries the distance to the
nearest EPA station. Cells far from any monitor are where the city cannot be
measured. The recommendation picks the grid point that would reduce the mean
distance the most if a new station stood there (greedy, one at a time).

Everything here is geometry over the registry; no air-quality values are
invented for unmonitored places.
"""

from __future__ import annotations

import math

import pandas as pd
import pydeck as pdk

from airlume.pipeline.registry import Registry, Station, haversine_km

# Lahore district bounding box (approximate) and the built-up area used for the
# "population-weighted" variant: a simple disc around the centre.
LAHORE_BBOX = (31.30, 31.72, 74.10, 74.60)  # lat_min, lat_max, lon_min, lon_max
CENTRE = (31.52, 74.33)
URBAN_RADIUS_KM = 18.0


def grid(step_deg: float = 0.01, bbox=LAHORE_BBOX) -> pd.DataFrame:
    lat_min, lat_max, lon_min, lon_max = bbox
    rows = []
    lat = lat_min
    while lat <= lat_max:
        lon = lon_min
        while lon <= lon_max:
            rows.append({"lat": round(lat, 4), "lon": round(lon, 4)})
            lon += step_deg
        lat += step_deg
    return pd.DataFrame(rows)


def nearest_station_km(df: pd.DataFrame, stations: list[Station]) -> pd.DataFrame:
    out = df.copy()
    dists = []
    names = []
    for r in out.itertuples(index=False):
        best = min(stations, key=lambda s: haversine_km(r.lat, r.lon, s.lat, s.lon))
        dists.append(haversine_km(r.lat, r.lon, best.lat, best.lon))
        names.append(best.name)
    out["km"] = dists
    out["nearest"] = names
    out["urban"] = [haversine_km(r.lat, r.lon, *CENTRE) <= URBAN_RADIUS_KM for r in out.itertuples(index=False)]
    return out


def coverage(reg: Registry, step_deg: float = 0.01) -> pd.DataFrame:
    return nearest_station_km(grid(step_deg), reg.stations_in("PB-LHE"))


def coverage_stats(cov: pd.DataFrame) -> dict:
    urban = cov[cov["urban"]]
    return {
        "mean_km_urban": float(urban["km"].mean()),
        "p90_km_urban": float(urban["km"].quantile(0.9)),
        "share_within_3km": float((urban["km"] <= 3).mean()),
        "share_beyond_5km": float((urban["km"] > 5).mean()),
    }


def recommend_station(cov: pd.DataFrame, stations: list[Station], candidates: int = 400) -> dict:
    """Greedy: among the farthest urban cells, pick the one that lowers the urban mean distance most."""
    urban = cov[cov["urban"]].copy()
    cand = urban.sort_values("km", ascending=False).head(candidates)
    best = None
    base = urban["km"].mean()
    for c in cand.itertuples(index=False):
        new_km = [min(k, haversine_km(lat, lon, c.lat, c.lon)) for lat, lon, k in zip(urban["lat"], urban["lon"], urban["km"])]
        gain = base - sum(new_km) / len(new_km)
        if best is None or gain > best["gain_km"]:
            best = {"lat": c.lat, "lon": c.lon, "gain_km": gain, "current_km": c.km, "nearest_now": c.nearest}
    return best or {}


def coverage_layer(cov: pd.DataFrame) -> pdk.Layer:
    d = cov[cov["urban"]].copy()
    # colour ramp: close = dim teal, far = bright orange
    def col(km: float) -> list[int]:
        t = max(0.0, min(1.0, (km - 1.0) / 6.0))
        return [int(60 + 180 * t), int(180 - 100 * t), int(190 - 150 * t), 120]
    d["colour"] = d["km"].map(col)
    d["label"] = d.apply(lambda r: f"{r['km']:.1f} km to {r['nearest']}", axis=1)
    return pdk.Layer(
        "GridCellLayer", data=d, get_position=["lon", "lat"], cell_size=1000, elevation_scale=0,
        get_fill_color="colour", pickable=True, extruded=False, opacity=0.45,
    )


def recommendation_layer(rec: dict) -> pdk.Layer:
    d = pd.DataFrame([{"lat": rec["lat"], "lon": rec["lon"], "label": f"Suggested new station: cuts mean distance by {rec['gain_km']:.2f} km"}])
    return pdk.Layer("ScatterplotLayer", data=d, get_position=["lon", "lat"], get_radius=700,
                     get_fill_color=[232, 238, 244, 230], stroked=True, get_line_color=[91, 200, 214], line_width_min_pixels=3, pickable=True)

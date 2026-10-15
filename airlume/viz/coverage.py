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

import numpy as np
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


# --------------------------------------------------------------------------
# Population (plan 2.6 and 4.5)
# --------------------------------------------------------------------------
#
# The population grid is WorldPop 2025, 1 km, cut to the Lahore box once by
# `scripts/extract_population.py` and committed as a small CSV so that nothing at
# runtime needs rasterio or GDAL.
#
# This replaces the `urban` disc for population work. The disc was a stand-in for
# "where people are" drawn as an 18 km circle around the centre; the raster is the
# real thing, so coverage of *people* is computed on the raster's own cells rather
# than resampled onto the geometry grid. Area coverage still uses the disc, and the
# two are reported separately because they answer different questions.

def _population_path():
    from airlume.config import ROOT
    return ROOT / "data" / "registry" / "lahore_population_1km.csv"


def population_grid() -> pd.DataFrame:
    """lat, lon, pop for every populated 1 km cell over Lahore. Empty if not extracted."""
    p = _population_path()
    if not p.exists():
        return pd.DataFrame(columns=["lat", "lon", "pop"])
    return pd.read_csv(p)


def population_coverage(reg: Registry, pop: pd.DataFrame | None = None) -> pd.DataFrame:
    """Each populated cell with its distance to the nearest monitor."""
    pop = population_grid() if pop is None else pop
    if pop.empty:
        return pop
    return nearest_station_km(pop, reg.stations_in("PB-LHE"))


def population_stats(popcov: pd.DataFrame) -> dict:
    """Share of *people* within 3 km / 5 km of a monitor, and the mean distance
    weighted by population rather than by area."""
    if popcov.empty:
        return {}
    total = float(popcov["pop"].sum())
    if total <= 0:
        return {}
    w = popcov["pop"]
    return {
        "total_population": total,
        "mean_km_pop_weighted": float((popcov["km"] * w).sum() / total),
        "share_within_3km": float(w[popcov["km"] <= 3].sum() / total),
        "share_within_5km": float(w[popcov["km"] <= 5].sum() / total),
        "share_beyond_5km": float(w[popcov["km"] > 5].sum() / total),
        "people_beyond_5km": float(w[popcov["km"] > 5].sum()),
    }


def landuse_grid() -> pd.DataFrame:
    """Per-cell exclusions and source proximity from OpenStreetMap. Empty if not extracted."""
    from airlume.config import ROOT
    p = ROOT / "data" / "registry" / "lahore_landuse_1km.csv"
    if not p.exists():
        return pd.DataFrame(columns=["lat", "lon", "excluded", "exclusion",
                                     "km_major_road", "km_industrial"])
    return pd.read_csv(p)


def with_landuse(popcov: pd.DataFrame, landuse: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join the land-use flags onto the population coverage grid."""
    lu = landuse_grid() if landuse is None else landuse
    if popcov.empty or lu.empty:
        out = popcov.copy()
        out["excluded"] = False
        out["km_major_road"] = float("nan")
        out["km_industrial"] = float("nan")
        return out
    return popcov.merge(lu, on=["lat", "lon"], how="left").assign(
        excluded=lambda d: d["excluded"].fillna(False).astype(bool))


def _source_score(df: pd.DataFrame) -> "np.ndarray":
    """0-1 score for how close a cell is to likely pollution sources.

    Major roads and industrial land, each as 1/(1+km) so the score falls away
    smoothly, averaged. Cells with no road or industrial data score 0 rather than
    being favoured by a missing value.
    """
    road = 1.0 / (1.0 + pd.to_numeric(df.get("km_major_road"), errors="coerce").fillna(1e6))
    ind = 1.0 / (1.0 + pd.to_numeric(df.get("km_industrial"), errors="coerce").fillna(1e6))
    s = (road + ind) / 2.0
    hi = float(s.max()) if len(s) and float(s.max()) > 0 else 1.0
    return (s / hi).to_numpy()


def recommend_stations_by_population(popcov: pd.DataFrame, n: int = 5,
                                     candidates: int = 400,
                                     apply_exclusions: bool = False,
                                     source_weight: float = 0.0) -> pd.DataFrame:
    """Greedy ranked sites that bring the most *people* within 5 km (plan 4.5).

    Candidates are the populated cells themselves, ranked by the population
    currently beyond 5 km of a monitor, so a site is only considered where people
    actually live. Each round reports the people newly brought inside 5 km and the
    population-weighted mean distance before and after, which is the "population
    coverage before and after" the plan's exit criterion asks for.

    Still a coverage heuristic, not a siting plan: it ignores pollution gradients,
    official siting rules and land access, and the land-use exclusions are applied
    separately by the caller.
    """
    if popcov.empty:
        return pd.DataFrame()
    df = popcov
    if apply_exclusions or source_weight:
        df = with_landuse(popcov)
    km = df["km"].to_numpy(copy=True)
    lats, lons = df["lat"].to_numpy(), df["lon"].to_numpy()
    w = df["pop"].to_numpy()
    total = float(w.sum())
    siteable = (~df["excluded"].to_numpy()) if apply_exclusions and "excluded" in df else np.ones(len(df), bool)
    src = _source_score(df) if source_weight else np.zeros(len(df))

    rows = []
    for rank in range(1, n + 1):
        before_beyond = float(w[km > 5].sum())
        before_mean = float((km * w).sum() / total)
        # Only look where people are currently underserved, and where a station could stand.
        order = np.argsort(-(w * (km > 5) * siteable))[:candidates]
        best = None
        for i in order:
            if w[i] <= 0 or not siteable[i]:
                continue
            trial = np.minimum(km, _hav_vec(lats, lons, lats[i], lons[i]))
            gained = before_beyond - float(w[trial > 5].sum())
            if gained <= 0:
                continue
            # Combined score: normalised people gained, blended with source proximity.
            score = (1 - source_weight) * (gained / before_beyond if before_beyond else 0) \
                + source_weight * src[i]
            if best is None or score > best[1]:
                best = (i, score, gained, trial)
        if best is None:
            break
        i, _score, gained, trial = best
        after_mean = float((trial * w).sum() / total)
        row = {
            "rank": rank,
            "lat": float(lats[i]), "lon": float(lons[i]),
            "people_brought_within_5km": int(round(gained)),
            "people_beyond_5km_after": int(round(float(w[trial > 5].sum()))),
            "share_beyond_5km_after": round(float(w[trial > 5].sum() / total), 4),
            "mean_km_before": round(before_mean, 2),
            "mean_km_after": round(after_mean, 2),
        }
        if source_weight:
            row["km_major_road"] = round(float(df["km_major_road"].iloc[i]), 2)
            row["km_industrial"] = round(float(df["km_industrial"].iloc[i]), 2)
        rows.append(row)
        km = trial
    return pd.DataFrame(rows)


def _hav_vec(lats, lons, lat0: float, lon0: float):
    """Vectorised haversine from one point to many, in km."""
    r1 = np.radians(lats)
    r0 = math.radians(lat0)
    dlat = r1 - r0
    dlon = np.radians(lons - lon0)
    a = np.sin(dlat / 2) ** 2 + np.cos(r0) * np.cos(r1) * np.sin(dlon / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


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


def recommend_stations(cov: pd.DataFrame, stations: list[Station], n: int = 5,
                       candidates: int = 400) -> pd.DataFrame:
    """Greedy ranked list: pick a site, update coverage, repeat (plan 4.5).

    Each row reports the mean urban distance to a monitor before and after that
    site is added, so the diminishing return of each extra station is visible --
    which is the point of the exercise, not the individual coordinates.

    **Area coverage only.** The plan's exit criterion asks for *population*
    brought within 3 km and 5 km, which needs a population raster (WorldPop or
    GHSL) that this environment cannot download. Until that layer exists these
    are area-maximising sites, and the report must say so rather than implying
    people were counted. The same gap means the OpenStreetMap land-use exclusions
    (rivers, the airport, restricted land) and the proximity-to-sources criterion
    are not applied either, so a proposed point may land somewhere unusable.
    """
    urban = cov[cov["urban"]].copy()
    km = urban["km"].to_numpy(copy=True)
    lats, lons = urban["lat"].to_numpy(), urban["lon"].to_numpy()
    rows = []
    for rank in range(1, n + 1):
        base = float(km.mean())
        order = km.argsort()[::-1][:candidates]
        best = None
        for i in order:
            trial = [min(k, haversine_km(la, lo, lats[i], lons[i]))
                     for la, lo, k in zip(lats, lons, km)]
            after = sum(trial) / len(trial)
            if best is None or after < best[1]:
                best = (i, after, trial)
        if best is None:
            break
        i, after, trial = best
        rows.append({
            "rank": rank,
            "lat": float(lats[i]), "lon": float(lons[i]),
            "mean_km_before": round(base, 2),
            "mean_km_after": round(after, 2),
            "gain_km": round(base - after, 3),
            "current_km": round(float(km[i]), 2),
            "share_beyond_5km_after": round(float((pd.Series(trial) > 5).mean()), 3),
        })
        km = pd.Series(trial).to_numpy()
    return pd.DataFrame(rows)


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

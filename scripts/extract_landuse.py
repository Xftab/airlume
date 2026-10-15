"""Cut Lahore's land use out of the national OpenStreetMap extract (plan 4.5).

    python scripts/extract_landuse.py

Reads `data/raw/pakistan-<date>.osm.pbf` (Geofabrik) and writes
`data/registry/lahore_landuse_1km.csv`: one row per populated 1 km cell, flagging
whether a monitor could stand there and how close the cell is to a likely source.

Columns
    lat, lon          the population grid's cell centre
    excluded          True when the cell centre falls in water, an aerodrome or
                      military land -- a station cannot be sited there
    exclusion         which of those, for the report
    km_major_road     distance to the nearest motorway / trunk / primary road
    km_industrial     distance to the nearest industrial landuse polygon

Same reasoning as the population extract: this runs by hand, writes a small CSV
that commits cleanly, and keeps `osmium` and `shapely` out of the app's runtime
dependencies. `data/raw/` stays git-ignored.

Simplification worth stating in the report: closed ways are used as polygons and
multipolygon *relations* are not assembled, so a feature mapped only as a relation
(a few large water bodies) is missed. Roads and industrial distance are measured to
the nearest *node* of the feature, which at a 1 km grid is accurate enough and much
cheaper than true line distance.

Source: OpenStreetMap contributors, ODbL. Attribution is in docs/SOURCES.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from airlume.config import ROOT  # noqa: E402
from airlume.viz.coverage import LAHORE_BBOX, population_grid  # noqa: E402

OUT = ROOT / "data" / "registry" / "lahore_landuse_1km.csv"
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = LAHORE_BBOX
PAD = 0.05  # look a little outside the box so a nearby road still counts


def _find_pbf() -> Path | None:
    hits = sorted((ROOT / "data" / "raw").glob("*.osm.pbf"))
    return hits[-1] if hits else None


def _classify(tags) -> str | None:
    """Which exclusion, if any, a feature represents."""
    if tags.get("aeroway") == "aerodrome":
        return "airport"
    if tags.get("landuse") == "military" or tags.get("military"):
        return "military"
    if tags.get("natural") == "water" or tags.get("waterway") in ("riverbank", "dock"):
        return "water"
    if tags.get("landuse") in ("reservoir", "basin"):
        return "water"
    return None


def main() -> int:
    try:
        import osmium
        from shapely.geometry import Point, Polygon
        from shapely.strtree import STRtree
    except ImportError:
        print("this one-off extraction needs:  pip install osmium shapely")
        return 1
    pbf = _find_pbf()
    if pbf is None:
        print("no .osm.pbf in data/raw/ -- download the Geofabrik Pakistan extract first; "
              "see docs/research/population.md")
        return 1
    pop = population_grid()
    if pop.empty:
        print("run scripts/extract_population.py first")
        return 1

    print(f"reading {pbf.name} ({pbf.stat().st_size / 1e6:.0f} MB) ...")
    polys: list[tuple[object, str]] = []
    road_pts: list[tuple[float, float]] = []
    indus_pts: list[tuple[float, float]] = []

    # Nodes must be read for the location cache that turns a way's node ids into
    # coordinates; they are skipped below.
    fp = (osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY)
          .with_locations())
    for obj in fp:
        if not isinstance(obj, osmium.osm.Way):
            continue
        try:
            nodes = [(n.location.lon, n.location.lat) for n in obj.nodes if n.location.valid()]
        except Exception:
            continue
        if not nodes:
            continue
        lons = [p[0] for p in nodes]
        lats = [p[1] for p in nodes]
        if (max(lats) < LAT_MIN - PAD or min(lats) > LAT_MAX + PAD
                or max(lons) < LON_MIN - PAD or min(lons) > LON_MAX + PAD):
            continue
        tags = obj.tags
        kind = _classify(tags)
        if kind and len(nodes) >= 4 and nodes[0] == nodes[-1]:
            try:
                polys.append((Polygon(nodes), kind))
            except Exception:
                pass
        if tags.get("highway") in ("motorway", "trunk", "primary"):
            road_pts.extend(nodes)
        if tags.get("landuse") == "industrial":
            indus_pts.extend(nodes)

    print(f"  {len(polys)} exclusion polygons, {len(road_pts):,} major-road nodes, "
          f"{len(indus_pts):,} industrial nodes")

    geoms = [p for p, _ in polys]
    kinds = [k for _, k in polys]
    tree = STRtree(geoms) if geoms else None

    road = np.array(road_pts) if road_pts else np.empty((0, 2))
    indus = np.array(indus_pts) if indus_pts else np.empty((0, 2))

    def nearest_km(lat: float, lon: float, pts: np.ndarray) -> float:
        if len(pts) == 0:
            return float("nan")
        dlon = (pts[:, 0] - lon) * 111.32 * np.cos(np.radians(lat))
        dlat = (pts[:, 1] - lat) * 111.32
        return float(np.sqrt(dlon ** 2 + dlat ** 2).min())

    rows = []
    for r in pop.itertuples(index=False):
        excl, why = False, ""
        if tree is not None:
            pt = Point(r.lon, r.lat)
            for i in tree.query(pt):
                if geoms[i].contains(pt):
                    excl, why = True, kinds[i]
                    break
        rows.append({"lat": r.lat, "lon": r.lon, "excluded": excl, "exclusion": why,
                     "km_major_road": round(nearest_km(r.lat, r.lon, road), 3),
                     "km_industrial": round(nearest_km(r.lat, r.lon, indus), 3)})

    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, lineterminator="\n")
    n_ex = int(df["excluded"].sum())
    print(f"\n{len(df):,} cells -> {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"excluded: {n_ex} ({n_ex/len(df):.1%})", df["exclusion"].value_counts().to_dict())
    print(f"median distance to a major road: {df['km_major_road'].median():.2f} km")
    print(f"median distance to industrial land: {df['km_industrial'].median():.2f} km")
    return 0


if __name__ == "__main__":
    sys.exit(main())

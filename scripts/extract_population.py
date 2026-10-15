"""Cut Lahore's population grid out of the national WorldPop raster (plan 2.6, 4.5).

    python scripts/extract_population.py

Reads `data/raw/pak_pop_2025_UC_1km_R2024B_UA_v1.tif` (WorldPop 2025, 1 km,
unconstrained-adjusted, EPSG:4326) and writes `data/registry/lahore_population_1km.csv`
with one row per raster cell over the Lahore bounding box: lat, lon, pop.

Why a CSV rather than reading the raster at runtime: the output is about 100 KB and
commits cleanly, so the app and the coverage analysis need no `rasterio` (and no
GDAL) to run. This script is the only thing that touches the .tif, it is run by hand
when the raster is updated, and `data/raw/` stays git-ignored.

Source: WorldPop, Global 2015-2030, R2024B, 2025, PAK v1, 1km_ua/unconstrained.
Licensed CC BY 4.0 - attribution is in docs/SOURCES.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from airlume.config import ROOT  # noqa: E402
from airlume.viz.coverage import LAHORE_BBOX  # noqa: E402

RASTER = ROOT / "data" / "raw" / "pak_pop_2025_UC_1km_R2024B_UA_v1.tif"
OUT = ROOT / "data" / "registry" / "lahore_population_1km.csv"


def main() -> int:
    try:
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError:
        print("rasterio is needed for this one-off extraction:  pip install rasterio")
        return 1
    if not RASTER.exists():
        print(f"missing {RASTER}\nDownload the WorldPop 1 km raster into data/raw/ first; "
              "see docs/research/population.md")
        return 1

    lat_min, lat_max, lon_min, lon_max = LAHORE_BBOX
    with rasterio.open(RASTER) as src:
        win = from_bounds(lon_min, lat_min, lon_max, lat_max, src.transform)
        arr = src.read(1, window=win)
        transform = src.window_transform(win)
        nodata = src.nodata

    rows, cols = arr.shape
    # Cell centres, not corners: the value belongs to the middle of the cell.
    r, c = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    xs, ys = rasterio.transform.xy(transform, r.ravel(), c.ravel(), offset="center")
    pop = arr.ravel().astype("float64")
    if nodata is not None:
        pop[pop == nodata] = np.nan
    pop[~np.isfinite(pop)] = np.nan

    df = pd.DataFrame({"lat": np.round(ys, 6), "lon": np.round(xs, 6),
                       "pop": np.round(pop, 2)}).dropna(subset=["pop"])
    # Empty desert/river cells carry no information for coverage and would triple
    # the file; a cell with under one person in it cannot change any share.
    df = df[df["pop"] >= 1.0]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values(["lat", "lon"]).to_csv(OUT, index=False, lineterminator="\n")

    print(f"{len(df):,} populated cells -> {OUT.relative_to(ROOT)}")
    print(f"total population in the Lahore box: {df['pop'].sum():,.0f}")
    print(f"densest cell: {df['pop'].max():,.0f} people/km2")
    print(f"file size: {OUT.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

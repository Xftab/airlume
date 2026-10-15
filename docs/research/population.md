# Who the monitors miss: population coverage and station placement

**15 October 2026.** Closes the population half of plan 2.6 and most of 4.5. Replaces the
area-only figures reported earlier the same day.

## The headline

**4.67 million people in Lahore — 33% of the city — live more than 5 km from an air-quality
monitor.** Only 32% live within 3 km.

| | Area | Population |
|---|---|---|
| Mean distance to the nearest monitor | 4.93 km | **4.31 km** |
| Share within 3 km | 23% | 32% |
| Share beyond 5 km | 44% | **33%** |

People are better covered than the average square kilometre, because the eleven stations sit in
the built-up city while the bounding box includes farmland. Both numbers are reported, because
they answer different questions: the area figure says how much of the district is unmeasured, the
population figure says how many people are unmeasured. The report should never use the word
"coverage" without saying which one it means.

Total population in the box is 14.16 million, against roughly 13 million for Lahore district at
the 2023 census — the box is slightly wider than the district, so that is the expected direction.

## Data

- **Population:** WorldPop, Global 2015–2030, R2024B, 2025, Pakistan, 1 km unconstrained-adjusted
  (`pak_pop_2025_UC_1km_R2024B_UA_v1.tif`, 5.5 MB). CC BY 4.0.
  The 100 m product exists and was started, then abandoned: at 438 MB it was a five-hour download
  on the project's connection, and the coverage grid is 1 km, so the finer raster would have been
  averaged up immediately. Matching the analysis resolution was the right call, not a compromise.
- **Land use:** OpenStreetMap via the Geofabrik Pakistan extract (`pakistan-261014.osm.pbf`,
  157 MB). ODbL.

Both are cut down once by `scripts/extract_population.py` and `scripts/extract_landuse.py` into
small committed CSVs (72 KB and 103 KB) under `data/registry/`. **Nothing at runtime needs
`rasterio`, `osmium`, `shapely` or GDAL** — the app and the analysis read the CSVs. The raw
downloads stay in git-ignored `data/raw/`.

## Where the next five stations should go

Greedy: pick the site that brings the most people within 5 km, update coverage, repeat. Cells on
the airport, on military land or in water are excluded, so nothing is proposed where a monitor
could not stand.

**A. Population only**

| # | Latitude | Longitude | People brought within 5 km | Share still beyond 5 km |
|---|---|---|---|---|
| 1 | 31.4575 | 74.3708 | 1,099,439 | 25% |
| 2 | 31.6075 | 74.4542 | 682,361 | 20% |
| 3 | 31.4158 | 74.2958 | 574,128 | 16% |
| 4 | 31.5575 | 74.2542 | 516,413 | 13% |
| 5 | 31.6325 | 74.2042 | 277,534 | **11%** |

Together: **3.15 million people** brought inside 5 km, cutting the underserved share from 33% to
10.8%.

**B. Population blended with closeness to likely sources** (major roads and industrial land, from
OpenStreetMap, weight 0.3)

| # | Latitude | Longitude | People brought within 5 km | km to major road | km to industry |
|---|---|---|---|---|---|
| 1 | 31.4575 | 74.3375 | 883,363 | 0.07 | 0.26 |
| 2 | 31.6492 | 74.1708 | 195,366 | 0.03 | 0.04 |
| 3 | 31.5908 | 74.4458 | 647,712 | 0.08 | 1.18 |
| 4 | 31.3992 | 74.1542 | 173,707 | 0.15 | 0.11 |
| 5 | 31.5742 | 74.2792 | 446,160 | 0.16 | 1.14 |

Together: 2.35 million brought inside 5 km, underserved share 33% → 16%.

**The trade-off is the result.** Weighting towards sources costs about 800,000 people of coverage
and leaves five percentage points more of the city underserved, but it puts every monitor within
200 m of a major road and most within about a kilometre of industrial land. Which is right depends
on whether a network is meant to measure exposure or emissions, and the report should present both
rather than pick one.

Two further points worth making in the report:

- **Area-optimal and population-optimal disagree.** The area-based heuristic put the first new
  station at 31.56 N, 74.20 E, in the thinly populated west. Weighting by people moves it to
  31.46 N, 74.37 E in the dense south-east. The earlier area-only recommendation was not wrong, it
  was answering a different question — and that is exactly the kind of thing a coverage study
  should surface rather than hide.
- **The gain falls away fast.** The first site serves 1.1 million people, the fifth 278,000. A
  network planner gets most of the benefit from two or three well-placed monitors.

## What this does not do

- **Multipolygon relations are not assembled.** Only closed ways become exclusion polygons, so a
  feature mapped as a relation is missed. This is visible in the output: ten cells are excluded —
  seven airport, two military, one water — and the Ravi river is almost certainly under-caught,
  since rivers are usually mapped as `waterway=river` linestrings or relations rather than closed
  ways. A site proposed near the river should be checked by eye.
- **Distances to roads and industry are measured to the nearest node**, not to the nearest point
  on the line. At 1 km resolution the difference is immaterial, and it is far cheaper.
- **The ISPRS 2022 Lahore siting study is still not compared against.** The plan asks for
  agreement and difference against its recommendations; that needs the paper's coordinates, which
  are not in hand. Open.
- **No pollution gradient, no siting rules, no land access.** Punjab follows US EPA siting
  criteria; nothing here checks them. The wording everywhere is "recommended for consideration".

## Reproducing

```
pip install rasterio osmium shapely
python scripts\extract_population.py
python scripts\extract_landuse.py
```

Both read from `data\raw\` and write to `data\registry\`. They only need re-running when the
rasters are updated or the station registry changes.

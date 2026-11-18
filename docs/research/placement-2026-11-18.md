# Station placement re-run, 18 November 2026

Re-run of `airlume/viz/coverage.py` on the committed registry (11 Lahore stations), WorldPop 2025 1 km population (2,817 cells, 14,155,727 people) and OpenStreetMap land-use layers. It reproduces the 15 Oct figures. Script: scratchpad only (no code change). Inputs: `data/registry/stations.csv`, `lahore_population_1km.csv`, `lahore_landuse_1km.csv`.

## Today
Beyond 5 km: 33.0% of people (4,671,551). Within 3 km: 31.7%; beyond 3 km 68.3%. Population-weighted mean distance 4.31 km. By area over the built-up disc: mean 4.93 km, p90 8.29 km, 23.4% within 3 km, 44.2% beyond 5 km.

## Five greedy sites
| Variant | Beyond 5 km after | Beyond 3 km after | Beyond 8 km after | Mean km |
|---|---|---|---|---|
| none | 33.0% (4,671,551) | 68.3% | 5.8% | 4.31 |
| area-ranked | 20.8% (2,946,645) | 62.6% | 3.9% | 3.78 |
| population-ranked | 10.7% (1,521,675) | 56.0% | 3.6% | 3.41 |
| population + sources (0.3) | 16.4% (2,325,243) | 55.9% | 3.1% | 3.48 |

Population-ranked sites (lat, lon, people brought within 5 km): 31.4575, 74.3708, 1,099,439; 31.6075, 74.4542, 682,361; 31.4158, 74.2958, 574,128; 31.5575, 74.2542, 516,413; 31.6325, 74.2042, 277,535. Combined: 31.4575, 74.3375, 883,363; 31.6492, 74.1708, 195,366; 31.5908, 74.4458, 647,712; 31.3992, 74.1542, 173,707; 31.5742, 74.2792, 446,160 (all within 200 m of a major road). Nearest population-ranked site to each combined site: 3.2, 3.7, 2.0, 13.6, 3.0 km.

A 3 km greedy run (not the app's setting) picks different sites and leaves 43.2% beyond 3 km. The sites depend on the threshold.

## Limits
Distance proxy, not measurement value; WorldPop modelled, error not quantified; Ravi river under-caught; official siting rules and land access ignored; 1 km candidate cells; greedy, not optimal. No intervals: the figures are geometry, not estimates from a sample.

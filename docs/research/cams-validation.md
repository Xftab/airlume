# CAMS Validation — Two-Week Results

**Date**: 28 Oct 2026
**Period**: 2026-10-13 to 2026-10-28 (16 days, gap 24–26 Oct due to collector outage)
**Data**: Open-Meteo CAMS (single ~45 km cell for Lahore) vs Punjab EPA station readings
**Method**: Station readings paired by UTC hour, city mean computed from available stations.
CAMS concentrations (PM2.5, PM10 µg/m³) compared directly. AQI compared on pk_portal scale
(CAMS concentrations put through pk_portal breakpoints, NOT CAMS's own US-EPA AQI).

## Summary

CAMS systematically underestimates Lahore air quality, especially during the October smog
season. The low bias worsened as smog intensified over the two-week period.

## City-Mean Results (211 paired hours)

| Quantity               | n   | MAD [95% CI]         | Bias [95% CI]            | r    | RMSE  |
|------------------------|-----|----------------------|--------------------------|------|-------|
| PM2.5 µg/m³            | 211 | 49.8 [39.1, 63.6]   | −47.7 [−62.0, −36.6]    | 0.65 | 66.1  |
| PM10 µg/m³             | 211 | 179.4 [153.3, 208.3] | −178.8 [−207.7, −152.2] | 0.59 | 202.8 |
| AQI (PM-only pk_portal)| 211 | 47.5 [37.2, 59.9]   | −45.4 [−58.6, −34.7]    | 0.65 | 63.6  |

All CIs: 95%, moving-block bootstrap (6-hour blocks, 5000 resamples).

## Station-Hour Results (2183–2202 paired station-hours)

| Quantity               | n    | MAD [95% CI]          | Bias [95% CI]             | r    | RMSE  |
|------------------------|------|-----------------------|---------------------------|------|-------|
| PM2.5 µg/m³            | 2183 | 58.4 [30.3, 99.8]    | −49.4 [−94.9, −16.0]     | 0.51 | 83.9  |
| PM10 µg/m³             | 2192 | 181.9 [107.6, 264.8] | −180.4 [−264.8, −102.3]  | 0.46 | 224.5 |
| AQI (PM-only pk_portal)| 2202 | 66.1 [34.7, 111.9]   | −57.2 [−108.0, −19.4]    | 0.46 | 106.6 |

## Per-Station PM2.5 MAD (sorted best to worst)

| Station        | MAD  | Bias   | r    | n   |
|----------------|------|--------|------|-----|
| Gulberg III    | 26.5 | +4.2   | 0.73 | 196 |
| Safari Park    | 31.0 | −20.5  | 0.69 | 198 |
| Punjab Univ    | 39.2 | −33.1  | 0.65 | 201 |
| Wagha Border   | 39.9 | −33.5  | 0.61 | 197 |
| Egerton Road   | 47.0 | −42.0  | 0.60 | 200 |
| Barki Road     | 57.8 | −55.3  | 0.55 | 199 |
| DHA Phase 6    | 58.4 | −54.8  | 0.54 | 198 |
| Shahdara       | 78.3 | −76.0  | 0.48 | 201 |
| Kahna Nau      | 82.6 | −80.2  | 0.45 | 196 |
| GT Road        | 86.5 | −84.1  | 0.43 | 200 |
| Multan Road    | 95.4 | −94.6  | 0.39 | 197 |

**Pattern**: CAMS tracks the cleaner stations (Gulberg III: MAD 26.5, slight positive bias)
but massively under-reads the industrial/roadside hotspots (Multan Road: MAD 95.4, bias −95).

## Diurnal Pattern (PKT)

| Period            | PM2.5 Bias | Notes                                      |
|-------------------|------------|----------------------------------------------|
| Day (10–19 PKT)   | −36.8      | Afternoon hours closest to zero              |
| Night (20–09 PKT) | −55.2      | Nighttime inversion not captured by CAMS     |
| Worst hour: 09 PKT| −109.5     | Morning rush + residual inversion            |
| Only positive: 18 PKT | +0.6   | CAMS briefly matches late-afternoon mixing   |

## Lag Analysis

Best correlation at shift −2 to −3 hours (r = 0.77 vs 0.65 at lag 0).
This means CAMS leads EPA by 2–3 hours — consistent with CAMS reflecting boundary-layer
mixing from the model while surface monitors capture the delayed ground-level response.
Bias stable at ~−48 regardless of shift (the problem is magnitude, not timing).

**Note**: Preliminary 30-hour analysis (24 Oct) found best lag at +2; the two-week dataset
reversed this. The preliminary result was likely noise from too few hours.

## Comparison with Preliminary (24 Oct, 30 hours)

| Metric             | Preliminary (30 hr) | Two-Week (211 hr) | Change         |
|--------------------|--------------------|--------------------|-----------------|
| PM2.5 bias         | −20.4              | −47.7              | Worsened 2.3×   |
| PM2.5 r            | 0.85               | 0.65               | Dropped         |
| PM10 bias          | −157.5             | −178.8             | Worsened        |
| Best lag           | +2 hr              | −2 to −3 hr        | Reversed        |

The preliminary finding that "CAMS gets the daytime level approximately right" no longer
holds with the full smog-season dataset. Even afternoon hours show ~37 µg/m³ low.

## Conclusions for Airlume

1. **CAMS is useful for trends and forecasts, not for absolute readings.** The correlation
   (r = 0.65 city-mean, 0.77 with optimal lag) means CAMS captures day-to-day variation,
   but the ~48 µg/m³ systematic low bias means displaying CAMS values as "current air quality"
   would mislead users.

2. **PM10 is effectively untracked by CAMS.** Bias of −179 µg/m³ on PM10 means the coarse
   fraction (dust, construction, road) is invisible to the ~45 km model cell.

3. **Station heterogeneity is extreme.** Gulberg III (residential, tree-lined) reads close to
   CAMS; Multan Road (industrial) reads ~95 µg/m³ higher. CAMS cannot capture this within-city
   gradient — the 3D map needs real station data.

4. **The neural variant (R&D)** could learn the CAMS→station bias correction as a function of
   hour, season, and meteorology. The 2–3 hour lead in CAMS correlation suggests forecast skill.

## Re-run, 6 Nov 2026 (313 hours, restored archive)

Run on the archive after the 7,215 restored rows (`archive-merge-loss-2026-11-06.md`): 3,294 station-hours over 313 hours, 14 Oct 04:00 to 6 Nov 12:00 UTC. `python scripts/cams_validation.py`, 6-hour block bootstrap. AQI is PM-only on the portal's current table on both sides.

| City mean | n | MAD [95% CI] | Bias, CAMS minus station [95% CI] | r |
|---|---:|---|---|---:|
| PM2.5 ug/m3 | 313 | 61.1 [48.5, 75.5] | -57.7 [-73.2, -44.0] | 0.68 |
| PM10 ug/m3 | 313 | 192.9 [168.4, 219.8] | -191.7 [-219.1, -166.6] | 0.65 |
| AQI, PM only | 313 | 69.3 [55.9, 85.0] | -65.4 [-82.0, -50.8] | 0.69 |

- **Per station, PM2.5 MAD** ranges from 27.8 (Gulberg III, bias +7.1) to 102.5 (Multan Road, bias -101.2). The order is unchanged from 29 Oct.
- **By time of day**, city-mean PM2.5 bias is -52.3 in daytime (10:00 to 19:00 PKT, 147 h) and -62.1 overnight (166 h).
- **Lag:** correlation with CAMS shifted by +2 h is 0.80 (0.68 at 0 h). The sign of the best lag has flipped between runs (+1 to 2 h on 16 Oct, -2 to -3 h on 29 Oct, +2 h now), so no timing offset is claimed.
- **Trend:** the PM2.5 bias has grown as the season has deepened: -20 (30 h, mid Oct), -48 (211 h, to 29 Oct), -58 (313 h, to 6 Nov). CAMS tracks the ups and downs (r 0.68) but misses more of the level as smog intensifies. This is consistent with local sources (crop burning, traffic, industry) that a 45 km model cell under-resolves.
- **What changes for the report:** quote these figures as the C4 result with their window. The conclusions above stand: trend yes, absolute level no, PM10 not tracked.

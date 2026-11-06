# W1: the portal changed its AQI table on 3 November 2026

**Date:** 6 November 2026. **Author:** Claude. **Data:** the restored archive (see `archive-merge-loss-2026-11-06.md`), 3,293 station-hours with a portal AQI, 14 Oct 04:00 to 6 Nov 12:00 UTC. **Script:** `scripts/w1_rescore.py`, scorecard `data/eval/w1_rescore_2026-11-06.json`.

## 1. Two changes, at the same time

Comparing the portal's published AQI with the AQI recomputed from the concentrations it published alongside, hour by hour, shows a clean break **between 05:00 and 07:00 UTC on 3 Nov 2026 (10:00 to 12:00 PKT)**. No official notice of it has been found. The EPD order No. 355/PA-to-DG/EPA/2025 of 1 Oct 2025 sets the reporting schedule but publishes no breakpoint table.

**(a) The PM2.5 breakpoint at AQI 150 moved from 70 to 75 ug/m3.** The bands became 35.1 to 75.0 for 101 to 150, and 75.1 to 150.0 for 151 to 200. Counted only where the two tables give different values, for PM2.5-dominant hours:

| Period | Hours | Old table exact | New table exact |
|---|---:|---:|---:|
| 15 Oct to 1 Nov | 1,496 | 1,494 | 0 to 1 by coincidence |
| 3 Nov 07:00 to 6 Nov 12:00 | 102 | 0 | 102 |

The last old-table match is 1 Nov 08:00 and the first new-table match is 3 Nov 07:00. There are no distinguishing hours on 2 Nov, because it was a heavy smog day.

**(b) The top of the scale.** Before the change, every reading above the 301 to 400 band (PM2.5 over 350 or PM10 over 550 ug/m3) was published as **500**: all 130 hours where our table gave less than 500 (16 Oct to 3 Nov 05:00). The boundary is sharp. PM2.5 348.44 was published as 398, and 350.49 as 500. PM10 549.91 was published as 400, and 551.32 as 500. After the change the 401 to 500 band is used. **22 of 22** PM10-dominant hours between 550 and 650 ug/m3 match the band 550.1 to 650 for 401 to 500 exactly (for example 587.62 is 438, 645.00 is 495). No PM2.5-dominant hour above 350 has occurred since the change, so the PM2.5 top band (350.1 to 500 for 401 to 500) is still extrapolated.

This explains the 28 Oct "99-point outlier" finding (`w1-harmonisation.md`). It was not a fault in our table. Until 3 Nov the portal saturated above AQI 400.

## 2. Gas bands, fitted from the gas-dominant hours

| Pollutant | New band (ug/m3 for AQI) | Hours in range | Exact |
|---|---|---:|---:|
| O3 | 195.1 to 260 for 151 to 200 | 5 | 5 |
| NO2 | 130.1 to 180 for 151 to 200 | 13 | 13 |

Both continue the existing bands' widths: O3 in steps of 65, NO2 40, 40, 50, 50. **These are in-sample fits** on the same hours they are scored on (18 points). They are stated as such, and they rest on few points.

Not fitted:
- **CO** was the portal's dominant pollutant in 21 hours (0.6%), and none is reproduced. The portal puts about 10 mg/m3 at AQI 200, twice our placeholder, and the points do not sit on one straight line. The likely reason is that CO is averaged over 8 hours, as the EPD order says, while the shown concentration is hourly. Those hours read low by 2 to 96 points.
- **SO2** has one dominant hour.
- Above the fitted ranges, gas sub-indices are still refused rather than guessed.

## 3. W1 re-scored

The table in force at each hour is used (`aqi.portal_scale_at`).

| Comparison | n | Exact | Within 1 | MAE [95% CI] | Max |
|---|---:|---:|---:|---|---:|
| **Dated tables, all hours** | 3,293 | **99.1%** | 99.3% | **0.16 [0.05, 0.31]** | 96 |
| Dated tables, before 3 Nov 06:00 | 2,987 | 99.1% | 99.3% | 0.16 [0.05, 0.33] | 96 |
| Dated tables, from 3 Nov 06:00 | 306 | 99.7% | 99.7% | 0.10 [0.00, 0.39] | 31 |
| October table only, from 3 Nov 06:00 | 306 | 64.1% | 74.8% | 3.94 [1.96, 6.75] | 96 |
| Top of scale (PM2.5 over 350 or PM10 over 550) | 249 | 249 of 249 | | | |

The CI is a day-block bootstrap, 2,000 resamples. Of the 14 hours still off by more than 10 points, 12 are CO-dominant, 1 SO2 and 1 NO2 (above 180).

**What W1 can now claim:** the harmonised AQI reproduces the portal's published AQI exactly on 99.1% of 3,293 station-hours over 22 days, with MAE 0.16 [0.05, 0.31]. That holds once it is recognised that the portal changed its own table on 3 Nov. The residual error is CO-dominant hours. The earlier at-scale figure (MAE 3.74 [2.01, 5.78]) mixed the saturation regime into the error.

**What it cannot claim:**
- that the PM2.5 top band is right (not yet observed under the new table);
- that the CO and SO2 bands are right;
- that the portal will not change again.

The collector computes `aqi_computed` on the current table from 6 Nov. Archived `aqi_computed` values are not rewritten (append-only); any consistent series is recomputed from the stored concentrations with `portal_scale_at`.

## 4. Consequences elsewhere

- **The app's category for a recomputed AQI** (CAMS, or a station without a portal AQI) now matches what the portal shows today. Between 70 and 75 ug/m3 PM2.5 the label moves from "Unhealthy for sensitive groups" to "Moderate".
- **CAMS validation (4.3)** compares PM-only AQI on the current table on both sides, so the comparison stays like with like.
- **Report Chapter 3 and Chapter 7, W1:** replace the 3.74 figure with the dated-table result above, and state the 3 Nov change as an observed finding, not an announced one.
- **Monitoring.** `scripts/w1_rescore.py` should be re-run weekly. A sudden drop in the exact-match rate is the signature of another portal change, and this is how this one was found.

# CAMS against the ground stations (plan 4.3, contribution C4)

_Preliminary, 16 October 2026. 30 hours of paired data (14 Oct 04:00 UTC to 16 Oct 04:00 UTC), 304 station-hours, 11 stations. **Re-run on about 29 October** with two weeks; until then every number here is a first look, and the intervals say how wide the uncertainty still is._

Code: `airlume/validation.py` (method, tested in `tests/test_validation.py`); report: `python scripts/cams_validation.py`.

## What is compared

- Each Punjab EPA station reading is paired with the Open-Meteo CAMS value for Lahore (one ~45 km model cell) for the same UTC hour.
- **Concentrations first:** PM2.5 and PM10 in ug/m3, which needs no index.
- **AQI on the portal's own scale only.** The `aqi` stored with CAMS is Open-Meteo's US AQI; comparing it with the portal would bring back the table mismatch solved for W1. CAMS concentrations are put through `pk_portal` instead, and since CAMS has no gases the station side is also recomputed from PM only. Both sides are then the same quantity (plan 4.3: "harmonised AQI from 1.7 only").
- **Agreement, not error.** The station instruments are not checked against a reference here, so neither side is treated as truth.
- **Two levels.** Every station-hour against CAMS, and the city mean (average of reporting stations) against CAMS. The city mean is the fairer test of an area-average model.
- **Intervals:** 95%, moving-block bootstrap over hours (6-hour blocks, 2,000 resamples). All stations share one CAMS value per hour and consecutive hours are autocorrelated, so resampling station-rows would give intervals far too narrow; a test pins this.

## Results (preliminary)

Bias = CAMS minus station. MAD = mean absolute difference.

| Quantity | Level | n | MAD [95% CI] | Bias [95% CI] | r |
|---|---|---|---|---|---|
| PM2.5 ug/m3 | city mean | 30 h | 21.9 [7.3, 28.9] | **-20.4** [-28.0, -4.0] | 0.70 |
| PM10 ug/m3 | city mean | 30 h | 81.5 [38.8, 97.9] | **-77.7** [-97.3, -28.2] | -0.16 |
| AQI, PM only, portal scale | city mean | 30 h | 22.9 [10.1, 28.8] | **-19.1** [-26.6, -2.2] | 0.76 |
| PM2.5 ug/m3 | station-hour | 297 | 28.1 [14.7, 34.9] | -20.4 [-28.7, -4.3] | 0.46 |
| PM10 ug/m3 | station-hour | 302 | 85.3 [46.4, 101.1] | -79.1 [-99.3, -29.5] | -0.11 |
| AQI, PM only, portal scale | station-hour | 302 | 35.0 [24.0, 40.2] | -19.4 [-27.1, -2.6] | 0.49 |

**1. CAMS reads low on PM2.5, by about 20 ug/m3 on average.** The interval excludes zero but is wide (-28 to -4): the direction is established, the size is not yet.

**2. CAMS does not track PM10 at all in this window** (r about zero) and is far below the stations (-78). The likely reason, to be checked rather than asserted: Lahore's PM10 is dominated by coarse road and construction dust that a global model's emission inventory does not carry. A PM10 answer built on CAMS for Lahore would be wrong in level and in timing.

**3. Agreement differs sharply by station** (PM2.5, 19-29 hours each):

| Station | n | MAD | Bias | r |
|---|---|---|---|---|
| Punjab University | 29 | 13.2 | -8.7 | 0.69 |
| Barki Road | 21 | 15.8 | -7.3 | 0.56 |
| Gulberg III | 19 | 19.0 | +10.4 | 0.59 |
| DHA Phase 6 | 29 | 19.2 | -15.7 | 0.56 |
| Wagha Border | 29 | 21.4 | +18.1 | 0.69 |
| Shahdara | 28 | 25.2 | -24.3 | 0.63 |
| Egerton Road | 28 | 27.1 | -23.9 | 0.73 |
| Safari Park | 27 | 29.4 | -29.2 | 0.34 |
| Kahna Nau | 29 | 38.2 | -37.0 | 0.53 |
| GT Road | 29 | 41.4 | -41.0 | 0.48 |
| Multan Road | 29 | 52.4 | -52.4 | 0.62 |

CAMS under-reads most at Multan Road and GT Road, both on heavy traffic corridors, and at Kahna Nau and Safari Park on the southern edge, where brick kilns and crop burning are candidate local sources (not verified here). The two sites where CAMS reads *higher* are Wagha Border and Gulberg III. A 45 km cell averages hot spots with their surroundings, so a spread like this is expected; why these particular stations sit where they do is left for the two-week run. Either way, the app must never show CAMS as if it were a station.

**4. The gap is a night-time gap.** City-mean PM2.5 bias is **-0.1** over 10:00-19:00 PKT (11 hours) and **-28.4** over 20:00-09:00 PKT (19 hours). CAMS gets the daytime level right and misses the night-time build-up. A plausible cause is the shallow night-time boundary layer trapping local emissions, which a coarse model under-represents; stated as a hypothesis for the two-week re-run, which will have every hour of day many times.

**5. Timing: the stations appear to lag CAMS by one to two hours.** Shifting CAMS later by h hours and re-correlating (city-mean PM2.5):

| shift | -3 | -2 | -1 | 0 | +1 | +2 | +3 |
|---|---|---|---|---|---|---|---|
| r | 0.28 | 0.42 | 0.49 | 0.70 | 0.80 | **0.83** | 0.81 |
| bias | -16.0 | -17.8 | -20.6 | -20.4 | -20.1 | -19.8 | -20.6 |

Checked first as a possible bug in our own data: the CAMS collector requests UTC and stores UTC (`collectors/openmeteo.py`), and the portal's station timestamps carry an explicit +05:00 offset that the parser converts. Neither is mis-shifted by a whole number of hours. Remaining explanations: the portal may label an hour by its end rather than its start, the monitors may report a trailing average, or CAMS may be early on the evening rise. **Not corrected.** With 30 hours, 0.70 against 0.83 is not a significant difference, and the bias does not move with the shift (-20 at every lag), so the main finding stands whichever is true. The re-run will test the lag on two weeks.

## Not yet done (plan 4.3)

- **Uptime beside each station:** the hours counted above (19-29 of 30) come from the data-quality report (1.6); the final write-up will put the two side by side.
- **Cross-check with the US Consulate monitor:** its readings reach us only through WAQI, which is display-only and never stored, so a stored comparison is not possible under the project's own rule. It will be reported only if an archivable source for it is found (OpenAQ is the candidate).
- **Two weeks of data,** about 29 October. The November smog season will then test whether CAMS's low bias grows with concentration.

## What this means for the app

- Where a city has only CAMS, the answer already says "modelled"; these numbers give that word a size: in Lahore in mid-October, CAMS reads PM2.5 about 20 ug/m3 low on average and does not represent PM10.
- These figures are not yet put in answer text. They will be, from the two-week run, with their intervals.

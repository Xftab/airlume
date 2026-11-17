# Project analysis: research questions, progress, accuracy, baselines (17 November 2026)

Every number below is taken from a file in the repository (named beside it). Intervals are 95%. Nothing here was re-run today.

## 1. Research questions, with the evidence now available

| RQ | Question | Baseline to beat | Verdict now | Source |
|---|---|---|---|---|
| RQ1 | Can a neural forecaster beat persistence, CAMS and the EPA forecast for Lahore? | persistence, same hour yesterday, CAMS, EPA | **Daily (Model A):** LightGBM does not beat persistence with confidence; neural nets do not beat LightGBM. **Hourly:** beats persistence, beats yesterday only at 1 to 3 h. | model-a-*.json; forecast-seasonal-baseline-2026-11-06.md |
| RQ2 | How well does CAMS match ground stations? | n/a (a measurement) | **Answered.** CAMS reads PM2.5 far too low and the gap grew over the season. | cams-validation.md |
| RQ3 | Can a conversational interface answer air-quality questions reliably? | rule-based stub | **Partly answered.** Beats the stub on a constructed set; no naturalistic headline figure yet. | Part B scoring; e1-results.md |
| RQ4 | Can the data support a defensible, transparent intervention-priority score? | none | **Built, not validated.** No ground truth exists to validate it against. | airlume/insights/priority.py |

## 2. Accuracy against the baselines

### 2.1 RQ1, hourly Lahore AQI (252 test origins, 1 to 24 h ahead)
Skill = 1 - MAE(model) / MAE(baseline). Positive means better.

| Against | per-band ridge | per-band LightGBM | Verdict |
|---|---|---|---|
| Persistence (MAE 100.6) | +0.22 [+0.05, +0.34] | +0.15 [+0.01, +0.26] | **Beats it** |
| Same hour yesterday (MAE 66.9) | -0.17 [-0.58, +0.12] | -0.27 [-0.80, +0.07] | **Does not beat it overall** |

By horizon against yesterday, LightGBM: +0.49 [+0.25, +0.64] at 1 to 3 h; -0.01 at 4 to 8 h; -0.41 at 9 to 16 h; -0.61 [-1.54, -0.08] at 17 to 24 h. A one-parameter blend of the last value and yesterday is best overall (MAE 62.6) but only +0.06 [-0.02, +0.13] against yesterday and was chosen after seeing results, so it is exploratory. CAMS relayed is worse than every baseline (-0.34 against persistence). EPA relayed (1 to 8 h) is +0.07 against persistence.
Caution: the test period is heavier smog (mean AQI 301) than training (175), 10 days only.

### 2.2 RQ1, daily Lahore PM2.5 (Model A, 131 test days, Apr to Aug 2024)
| Model | MAE | 95% CI | R2 |
|---|---|---|---|
| Persistence | 14.55 | [12.16, 17.73] | 0.04 |
| LightGBM | 13.95 | [12.58, 15.72] | 0.28 |
| GRU | 14.08 | [12.05, 16.85] | 0.25 |
| LSTM | 18.10 | [16.16, 20.65] | -0.08 |

LightGBM improves on persistence by about 4% (1 - 13.95/14.55). The intervals overlap, so that is **not distinguishable from zero**. The test period is the low-smog season, which is the easy case for persistence-like behaviour and the wrong season for the question people care about. Neural nets add nothing at 654 training days.

### 2.3 Model B, CAMS bias correction (hourly PM2.5, 42 test hours)
Raw CAMS MAE 80.4 [47.8, 127.7]; corrected 37.3 [22.5, 62.1] (**better than raw CAMS**); persistence 21.1 [14.2, 28.7] (**corrected CAMS does not beat persistence**). n = 42 is too small to say more. Model C (hour climatology) MAE 77.7 does no better than raw CAMS.

### 2.4 RQ2, CAMS against stations (313 h, 6 Nov)
City-mean PM2.5: bias -57.7 [-73.2, -44.0] ug/m3, MAD 61.1, r 0.68. PM10 bias -191.7 (not tracked). Bias by run: -20, -48, -58 as the season worsened. Used for trends, not absolute readings.

### 2.5 RQ3, language layer
| Set | gpt-oss-120b | Stub | Note |
|---|---|---|---|
| Part B, 30 constructed, frozen, scored once | 25/30 = 83.3% [66.4, 92.7] | 9/30 = 30.0% [16.7, 47.9] | difference +53.3 points, Newcombe [+28.7, +69.6] (unpaired) |
| v0 development set (90), prompt tuned on it | 90.0% [83.3, 95.6] | 45.6% | **optimistic**: prompt was tuned on this set |

**Beats the baseline: yes**, with a wide interval. English 17/19 [68.6, 97.1]; Roman Urdu 8/11 [43.4, 90.2]; the gap +16.8 has Newcombe [-10.5, +47.0], so no language gap is claimed. Scope handling 30/30 [88.6, 100.0].
**Not established:** performance on questions people actually write. Part B is schema coverage, constructed, n = 30. The only naturalistic set (62 classmate questions) was used to build the benchmark, and Part A (fresh) is not collected.

### 2.6 Data and pipeline
W1 harmonised AQI: 99.1% exact, MAE 0.16 [0.05, 0.31] on 3,293 station-hours. Tests 267 pass.

## 3. Can we beat the baseline? Plain answer

| Claim | Yes or no | Strength |
|---|---|---|
| Language layer beats the rule-based stub | Yes | Strong in size; wide interval because n = 30 |
| Hourly forecast beats persistence | Yes | Moderate; 10-day regime-shifted test |
| Hourly forecast beats "same hour yesterday" | Only at 1 to 3 h | Not beyond 3 h; do not claim it |
| Daily forecast (LightGBM or neural) beats persistence | Not demonstrated | CIs overlap |
| Neural beats gradient boosting | No | Reported as a negative result |
| Corrected CAMS beats persistence | No | n = 42 |
| Corrected CAMS beats raw CAMS | Yes | Wide CI |

The defensible headline for the forecast is: beats persistence, matches but does not beat a seasonal baseline beyond 3 hours, on a short heavier-smog test. That is a valid research finding (strong simple baselines are hard to beat with five weeks of hourly data) and should be written as one.

## 4. Progress
Built: data pipeline and archive, W1 harmonisation, CAMS validation, hourly and daily forecast scorecards, language router with schema v5, Part B benchmark scored, priority score, graded response, scenario calculator, 3D map and city view, new interface, 267 tests.
Not done: Part A collection (in progress by classmates), E4 user study (no dates), E6 frames per second, chapter 4 screenshots from real data, report `[PENDING]` fields, plan PDF rebuild, demo slides, archive recovery check, EPA redistribution answer.

## 5. Weaknesses a viva examiner could press (and the honest reply)
1. n = 30 for the language result. Reply: intervals reported; Part A will add a naturalistic number if collected in time.
2. Forecast test period is short and heavier than training. Reply: stated; re-run weekly; blend is exploratory.
3. Daily model tested on the wrong season. Reply: yes; stated. A winter-season split (Oct to Jan from earlier years) would be the stronger test and can be run from the EPD daily data if time allows. [To do, optional]
4. Priority score has no ground truth. Reply: it is a transparent ranking rule, not a predictor; weights (50/30/20) are a design choice and should be shown with a sensitivity check. [To do: vary the weights and report how rankings change]
5. Part B scored once, five failures, three are defaults left unset on comparison questions. Not tuned on, by design.

# Forecast models v2: why the hourly model overfit, and classical against deep models (17 November 2026)

**Question (RQ1).** Can a neural forecaster beat the simple baselines for Lahore, and if the hourly LightGBM lost to "same hour yesterday", why?
**Scripts:** `scripts/forecast_diagnose.py`, `scripts/forecast_models_v2.py`, `scripts/model_a_v2.py`. **Tests:** `tests/test_forecast_models_v2.py` (7 tests, 274 in the suite). **Results:** `data/eval/forecast_diagnose_2026-11-17.json`, `forecast_models_v2_2026-11-17_split-*.json`, `model_a_v2_2026-11-17.json` (+ predictions CSV). **Figure:** `docs/research/figures/forecast_models_v2_2026-11-17.png`.
Every figure is a 95% interval. Skill = 1 - MAE(model) / MAE(baseline) on the same rows; 0 means no better than the baseline. Intervals are moving-block bootstraps (24 h blocks over forecast origins for hourly, 7-day blocks over days for daily), 2000 resamples.

## 1. Short answer

1. **Why the hourly LightGBM overfit.** Three things, in order of size. (a) **The smog level moved out of what it had seen.** Only 5.9% of its training rows had a last reading above 300, but 54% of test rows at 17 to 24 h did. On those rows its error was 123 to 124 against 82 to 83 for plain persistence. (b) **Real overfitting on a very small sample:** in-sample MAE 20, cross-validated inside the training period 43, test 102 (17 to 24 h). 389 origins is about 16 days. (c) **Fixable in part by regularisation:** fewer, shallower trees and a bigger minimum leaf cut the 17 to 24 h test MAE from 102 to 70. Removing the CAMS and EPA features changed almost nothing (100 against 102), so they are not the cause.
2. **Beating the baseline.** Learned models beat persistence in almost every setting tested (the exceptions: the old per-band LightGBM at 17 to 24 h, and ridge on winter daily data). Beating same hour yesterday depends on how much of the recent smog regime the training data contains. On the split fixed in advance (27 Oct), the regularised and deep models are level with or slightly better than yesterday (deep +0.05 to +0.10, intervals touching zero), and the old per-band LightGBM is worse. On later splits, with 70 to 220 more training origins, **every learned model has a positive point estimate against yesterday (+0.04 to +0.23)**; on the 5 Nov split all intervals exclude zero, on 30 Oct only the GRU, TCN, LSTM and blend do.
3. **Deep against classical.** **No consistent winner.** The best model changes with the split (GRU on 30 Oct, LightGBM on 5 Nov, MLP on 27 Oct), and the intervals overlap. What helped was not depth but the formulation: predicting a relative change and training one network for all 24 horizons. A regularised LightGBM with the same relative target is close to the deep models.
4. **Daily PM2.5.** With calendar-correct lags and winter in the test, the deep recurrent models beat persistence (GRU +0.13 [+0.07, +0.18], LSTM +0.12 [+0.05, +0.19]) and LightGBM does too (+0.07 [+0.01, +0.14]). GRU against LightGBM is +0.06 [-0.00, +0.11], not distinguishable. Part of the gain comes from using the target day's weather, which in use would be a forecast.
5. **Is the work legitimate research?** Yes, as a comparison under stated conditions, not as "deep learning wins". The finding that holds across every check is that **the amount of regime-matched training data matters more than the model family**.

## 2. Diagnosis of the hourly overfit (fixed split, 27 Oct 2026)

Same data and rows as `forecast_fit.py`: 412 training origins (389 after requiring 48 h of history for the deep models), 519 test origins, training mean AQI 175.3, test mean 297.0. Reproduced exactly in the container before experiments.

17 to 24 h band (persistence MAE 88.9, same hour yesterday 66.3):

| LightGBM variant | In-sample MAE | CV inside training | Test MAE | Skill vs persistence | Skill vs yesterday |
|---|---:|---:|---:|---:|---:|
| default | 20.37 | 43.29 | 102.46 | -0.15 | -0.55 |
| strong_reg | 30.85 | 44.47 | 69.81 | +0.21 | -0.05 |
| relative_target | 20.09 | 44.53 | 111.12 | -0.25 | -0.68 |
| relative_target_strong | 30.34 | 43.89 | 65.1 | +0.27 | +0.02 |
| no_cams_epa | 23.82 | 46.58 | 100.08 | -0.12 | -0.51 |
| no_cams_epa_strong_rel | 33.82 | 47.46 | 68.71 | +0.23 | -0.04 |

*Variants:* `default` = the 6 Nov model; `strong_reg` = 80 trees, 4 leaves, minimum leaf 200, L2 10; `relative_target` = predicts y / last - 1 instead of y - last; the `no_cams_epa` rows drop those features.

**Reading.**
- **Overfitting is real.** In-sample 20 against CV 43 is a factor of two, with 16 days of training origins.
- **But the CV error (43) is far below the test error (102).** The test period is not like the training period. By level of the last reading (17 to 24 h): at 300 to 400 the default LightGBM scores MAE 123.3 against 83.0 for persistence, and above 400 it scores 124.4 against 82.3; at or below 300 it beats persistence (77.9 and 76.8 against 102.9 and 89.7). Those high levels were 5.4% and 0.5% of its training rows, and 54% of the test rows. Trees cannot predict beyond the range they saw.
- **Cross-validation inside the training period could not have told us.** For the default and regularised models the CV errors are 43.3 and 44.5 (nearly equal), while on the test they are 102 and 70. This is the sentence to put in the limitations: with a short archive, in-sample validation does not predict a regime shift.
- **The learning curve is erratic, not a smooth decline** (test MAE at 25, 50, 75, 100% of the training origins: 85, 71, 65, 102 for the default model). Adding the latest quarter of training made it worse. That is what an unstable fit on very few effective samples looks like.
- **Selection warning.** The regularised variants were written down before their test result, but I looked at their test result before choosing to promote them. Treat the 70 / 65 figures as exploratory.

## 3. Classical against deep models, hourly (all 1 to 24 h)

Deep models: one network per architecture, 24 outputs, input = last 48 hourly values relative to the latest one, log latest value, hour of day; relative-change target, L1 loss with a mask; 5-seed ensembles averaged in log space; early stopping on the last 20% of training origins (never the test). Hyperparameters fixed in the script. No tuning on any test period.

**Primary split, 27 Oct (fixed on 1 Nov before any of these models):**

| Model | MAE | Skill vs persistence (MAE 95.4) | Skill vs same hour yesterday (MAE 65.7) |
|---|---:|---|---|
| MLP | 59.4 | +0.38 [+0.29, +0.45] | +0.10 [-0.02, +0.20] |
| N-BEATS-lite | 59.8 | +0.37 [+0.27, +0.46] | +0.09 [-0.04, +0.21] |
| LSTM | 59.9 | +0.37 [+0.27, +0.46] | +0.09 [-0.01, +0.17] |
| Blend of last value and same hour yesterday (exploratory) | 60.2 | +0.37 [+0.27, +0.46] | +0.08 [+0.04, +0.13] |
| TCN | 60.3 | +0.37 [+0.28, +0.44] | +0.08 [-0.03, +0.18] |
| GRU | 62.3 | +0.35 [+0.22, +0.45] | +0.05 [-0.06, +0.16] |
| LightGBM, regularised, relative target | 63.5 | +0.34 [+0.26, +0.39] | +0.03 [-0.09, +0.14] |
| Ridge, one per band | 72.1 | +0.24 [+0.13, +0.33] | -0.10 [-0.33, +0.10] |
| LightGBM, one per horizon band (the 6 Nov model) | 80.7 | +0.15 [+0.06, +0.23] | -0.23 [-0.50, -0.01] |
| CAMS relayed forecast | 131.2 | -0.37 [-0.56, -0.19] | -1.00 [-1.52, -0.54] |

**Same models, later splits (sensitivity, not independent: the test sets overlap; the split dates were chosen after seeing the first result, so they are a robustness check, not new evidence):**

*30 Oct (484 train origins, 447 test):*

| Model | MAE | Skill vs persistence (MAE 94.9) | Skill vs same hour yesterday (MAE 67.2) |
|---|---:|---|---|
| GRU | 55.7 | +0.41 [+0.32, +0.51] | +0.17 [+0.09, +0.23] |
| TCN | 56.6 | +0.40 [+0.33, +0.48] | +0.16 [+0.04, +0.23] |
| LSTM | 57.1 | +0.40 [+0.31, +0.49] | +0.15 [+0.06, +0.21] |
| N-BEATS-lite | 58.1 | +0.39 [+0.30, +0.47] | +0.14 [-0.00, +0.23] |
| LightGBM, one per horizon band (the 6 Nov model) | 59.4 | +0.37 [+0.28, +0.46] | +0.12 [-0.02, +0.20] |
| Blend of last value and same hour yesterday (exploratory) | 60.8 | +0.36 [+0.26, +0.47] | +0.10 [+0.06, +0.13] |
| Ridge, one per band | 61.7 | +0.35 [+0.25, +0.45] | +0.08 [-0.09, +0.20] |
| LightGBM, regularised, relative target | 61.8 | +0.35 [+0.25, +0.43] | +0.08 [-0.04, +0.16] |
| MLP | 64.4 | +0.32 [+0.24, +0.40] | +0.04 [-0.13, +0.15] |
| CAMS relayed forecast | 137.1 | -0.45 [-0.65, -0.28] | -1.04 [-1.67, -0.64] |

*5 Nov (628 train origins, 303 test):*

| Model | MAE | Skill vs persistence (MAE 92.0) | Skill vs same hour yesterday (MAE 63.6) |
|---|---:|---|---|
| LightGBM, one per horizon band (the 6 Nov model) | 49.2 | +0.47 [+0.35, +0.56] | +0.23 [+0.14, +0.32] |
| Ridge, one per band | 49.9 | +0.46 [+0.36, +0.55] | +0.22 [+0.13, +0.31] |
| LSTM | 52.3 | +0.43 [+0.32, +0.53] | +0.18 [+0.12, +0.23] |
| N-BEATS-lite | 52.5 | +0.43 [+0.33, +0.53] | +0.17 [+0.09, +0.25] |
| GRU | 52.7 | +0.43 [+0.31, +0.53] | +0.17 [+0.12, +0.22] |
| MLP | 53.5 | +0.42 [+0.32, +0.51] | +0.16 [+0.10, +0.22] |
| TCN | 53.8 | +0.42 [+0.30, +0.51] | +0.15 [+0.10, +0.21] |
| LightGBM, regularised, relative target | 55.8 | +0.39 [+0.27, +0.50] | +0.12 [+0.05, +0.21] |
| Blend of last value and same hour yesterday (exploratory) | 57.9 | +0.37 [+0.25, +0.47] | +0.09 [+0.04, +0.14] |
| CAMS relayed forecast | 127.5 | -0.39 [-0.61, -0.15] | -1.01 [-1.58, -0.46] |

**By horizon band, split 27 Oct:**

**1-3 h**

| Model | MAE | Skill vs persistence (MAE 42.7) | Skill vs same hour yesterday (MAE 65.1) |
|---|---:|---|---|
| MLP | 32.0 | +0.25 [+0.19, +0.30] | +0.51 [+0.39, +0.61] |
| N-BEATS-lite | 32.3 | +0.24 [+0.17, +0.30] | +0.51 [+0.39, +0.60] |
| GRU | 33.3 | +0.22 [+0.15, +0.28] | +0.49 [+0.37, +0.59] |
| LSTM | 33.7 | +0.21 [+0.15, +0.26] | +0.48 [+0.36, +0.59] |
| TCN | 34.0 | +0.20 [+0.15, +0.25] | +0.48 [+0.36, +0.58] |
| LightGBM, one per horizon band (the 6 Nov model) | 34.1 | +0.20 [+0.15, +0.24] | +0.48 [+0.36, +0.57] |
| LightGBM, regularised, relative target | 35.1 | +0.18 [+0.14, +0.21] | +0.46 [+0.33, +0.57] |
| Ridge, one per band | 35.5 | +0.17 [+0.11, +0.21] | +0.46 [+0.34, +0.56] |
| Blend of last value and same hour yesterday (exploratory) | 38.8 | +0.09 [+0.04, +0.13] | +0.40 [+0.27, +0.51] |
| CAMS relayed forecast | 126.8 | -1.97 [-2.35, -1.68] | -0.95 [-1.52, -0.49] |

**4-8 h**

| Model | MAE | Skill vs persistence (MAE 95.6) | Skill vs same hour yesterday (MAE 65.2) |
|---|---:|---|---|
| N-BEATS-lite | 51.4 | +0.46 [+0.37, +0.53] | +0.21 [+0.07, +0.33] |
| MLP | 53.4 | +0.44 [+0.36, +0.50] | +0.18 [+0.04, +0.31] |
| LSTM | 53.9 | +0.44 [+0.36, +0.49] | +0.17 [+0.03, +0.30] |
| GRU | 54.6 | +0.43 [+0.34, +0.50] | +0.16 [+0.02, +0.29] |
| TCN | 56.6 | +0.41 [+0.33, +0.47] | +0.13 [-0.02, +0.26] |
| Blend of last value and same hour yesterday (exploratory) | 60.5 | +0.37 [+0.24, +0.46] | +0.07 [-0.01, +0.14] |
| LightGBM, regularised, relative target | 63.1 | +0.34 [+0.26, +0.39] | +0.03 [-0.15, +0.18] |
| LightGBM, one per horizon band (the 6 Nov model) | 66.0 | +0.31 [+0.23, +0.36] | -0.01 [-0.22, +0.16] |
| Ridge, one per band | 68.5 | +0.28 [+0.18, +0.35] | -0.05 [-0.27, +0.12] |
| CAMS relayed forecast | 128.0 | -0.34 [-0.52, -0.20] | -0.96 [-1.55, -0.49] |

**9-16 h**

| Model | MAE | Skill vs persistence (MAE 121.9) | Skill vs same hour yesterday (MAE 65.7) |
|---|---:|---|---|
| LSTM | 62.9 | +0.48 [+0.37, +0.58] | +0.04 [-0.07, +0.14] |
| N-BEATS-lite | 62.9 | +0.48 [+0.36, +0.58] | +0.04 [-0.09, +0.18] |
| Blend of last value and same hour yesterday (exploratory) | 63.2 | +0.48 [+0.36, +0.59] | +0.04 [-0.01, +0.08] |
| MLP | 63.5 | +0.48 [+0.37, +0.57] | +0.03 [-0.09, +0.16] |
| TCN | 63.9 | +0.48 [+0.37, +0.56] | +0.03 [-0.11, +0.15] |
| GRU | 66.2 | +0.46 [+0.32, +0.57] | -0.01 [-0.15, +0.12] |
| LightGBM, regularised, relative target | 69.4 | +0.43 [+0.35, +0.50] | -0.06 [-0.23, +0.07] |
| Ridge, one per band | 77.7 | +0.36 [+0.25, +0.45] | -0.18 [-0.47, +0.04] |
| LightGBM, one per horizon band (the 6 Nov model) | 86.4 | +0.29 [+0.22, +0.35] | -0.32 [-0.64, -0.07] |
| CAMS relayed forecast | 131.2 | -0.08 [-0.23, +0.07] | -1.00 [-1.58, -0.48] |

**17-24 h**

| Model | MAE | Skill vs persistence (MAE 88.9) | Skill vs same hour yesterday (MAE 66.3) |
|---|---:|---|---|
| Blend of last value and same hour yesterday (exploratory) | 65.3 | +0.27 [+0.16, +0.36] | +0.01 [-0.02, +0.05] |
| LightGBM, regularised, relative target | 68.7 | +0.23 [+0.14, +0.30] | -0.04 [-0.13, +0.04] |
| TCN | 69.1 | +0.22 [+0.12, +0.31] | -0.04 [-0.14, +0.05] |
| MLP | 69.7 | +0.22 [+0.11, +0.30] | -0.05 [-0.18, +0.07] |
| LSTM | 70.8 | +0.20 [+0.07, +0.31] | -0.07 [-0.16, +0.01] |
| N-BEATS-lite | 72.9 | +0.18 [+0.03, +0.30] | -0.10 [-0.28, +0.06] |
| GRU | 74.6 | +0.16 [-0.00, +0.30] | -0.12 [-0.27, -0.00] |
| Ridge, one per band | 83.0 | +0.07 [-0.12, +0.22] | -0.25 [-0.58, +0.02] |
| LightGBM, one per horizon band (the 6 Nov model) | 102.5 | -0.15 [-0.39, +0.05] | -0.55 [-1.01, -0.18] |
| CAMS relayed forecast | 135.0 | -0.52 [-0.80, -0.23] | -1.04 [-1.64, -0.50] |

**Reading.**
- **Against persistence the point estimates are positive in every band** except the old per-band LightGBM at 17 to 24 h; at 17 to 24 h the intervals of ridge (per band) and GRU include zero.
- **At 4 to 8 h the MLP, GRU, LSTM and N-BEATS-lite beat same hour yesterday on the primary split** (+0.16 to +0.21, intervals above zero); the TCN, the blend and the boosted models do not. At 9 to 16 h nobody beats yesterday with confidence (the blend, +0.04 [-0.01, +0.08], is level). At 17 to 24 h the GRU is significantly worse than yesterday (-0.13 [-0.27, -0.00]) and the rest are level or worse.
- **On later splits every learned model has a positive point estimate against yesterday overall** (+0.04 to +0.23; all intervals exclude zero on 5 Nov, only some on 30 Oct). The 6 Nov conclusion "no model beats yesterday beyond 3 h" was a statement about 16 days of training data in a smog level that then rose, and not about the model families.
- **No stable ranking.** The top model is different on each split and the intervals overlap, so "deep is best" is not supported. The CAMS relayed forecast is worse than every baseline in every setting (about -0.4 against persistence, -1.0 against yesterday).

## 4. Daily next-day PM2.5 (Model A v2)

**Two corrections to the earlier Model A.** (1) The lag features were shifted by row, not by calendar day. There are 52 gaps in the bulletin series (largest 198 days), so 55 of 657 rows had a "yesterday" from an earlier date, and the 7-day windows of the neural models were 7 rows, not 7 days. Here a lag exists only if that calendar day was observed, and every model is scored on the same 437 days that have a complete previous week. (2) The earlier test period was April to August 2024 (mean PM2.5 about 56), the easiest season for persistence. The new folds are forward-chained: W2021-22 (train 56 days, test 47), W2022-23 (train 239, test 23; the series has no Jan or Feb 2023), W2023-24 (train 263, test 61), and the old Summer 2024 (train 336, test 100). Winter pooled is the headline; summer is reported beside it.

**Models:** ridge, LightGBM, MLP, GRU, LSTM, TCN (two dilated causal convolutions), N-BEATS-lite; 5-seed ensembles for the networks. Target: log(PM2.5 today) - log(PM2.5 yesterday), so every model starts at persistence. **Winter pooled:**

131 test days, mean PM2.5 174.8 ug/m3.

| Model | MAE | Skill vs persistence | Skill vs LightGBM |
|---|---:|---|---|
| GRU | 37.57 | +0.13 [+0.07, +0.18] | +0.06 [-0.00, +0.11] |
| LSTM | 37.76 | +0.12 [+0.05, +0.19] | +0.06 [-0.03, +0.12] |
| TCN | 38.97 | +0.10 [+0.02, +0.17] | +0.03 [-0.06, +0.08] |
| Ridge+LightGBM avg | 39.53 | +0.08 [-0.02, +0.17] | +0.01 [-0.07, +0.07] |
| LightGBM | 40.05 | +0.07 [+0.01, +0.14] | - |
| MLP | 40.17 | +0.07 [-0.02, +0.15] | -0.00 [-0.11, +0.08] |
| N-BEATS-lite | 40.29 | +0.07 [-0.08, +0.17] | -0.01 [-0.16, +0.08] |
| Persistence (yesterday) | 43.1 | - | -0.08 [-0.16, -0.01] |
| Ridge | 44.03 | -0.02 [-0.22, +0.11] | -0.10 [-0.30, +0.01] |
| 3-day mean | 46.35 | -0.07 [-0.22, +0.02] | -0.16 [-0.36, -0.05] |
| 7-day mean | 49.2 | -0.14 [-0.32, -0.04] | -0.23 [-0.44, -0.12] |

**Summer 2024:**

100 test days, mean PM2.5 41.4 ug/m3.

| Model | MAE | Skill vs persistence | Skill vs LightGBM |
|---|---:|---|---|
| Ridge+LightGBM avg | 10.55 | +0.18 [+0.11, +0.24] | +0.03 [-0.00, +0.06] |
| Ridge | 10.56 | +0.18 [+0.10, +0.25] | +0.03 [-0.04, +0.09] |
| GRU | 10.71 | +0.17 [+0.11, +0.23] | +0.01 [-0.05, +0.08] |
| LSTM | 10.78 | +0.16 [+0.10, +0.23] | +0.01 [-0.06, +0.07] |
| LightGBM | 10.86 | +0.16 [+0.10, +0.21] | - |
| N-BEATS-lite | 10.92 | +0.15 [+0.08, +0.21] | -0.01 [-0.09, +0.06] |
| MLP | 10.95 | +0.15 [+0.08, +0.21] | -0.01 [-0.09, +0.07] |
| TCN | 11.07 | +0.14 [+0.07, +0.20] | -0.02 [-0.10, +0.05] |
| Persistence (yesterday) | 12.87 | - | -0.18 [-0.27, -0.10] |
| 7-day mean | 12.97 | -0.01 [-0.17, +0.13] | -0.19 [-0.37, -0.04] |
| 3-day mean | 13.07 | -0.01 [-0.15, +0.08] | -0.20 [-0.36, -0.08] |

**What weather adds (skill vs persistence, winter pooled).** The target day's ERA5 weather is a feature, as in the earlier Model A. In use this would be a weather forecast, so the "with weather" column is an upper bound.

| Model | with weather | without weather |
|---|---|---|
| Ridge | -0.02 [-0.22, +0.11] | -0.11 [-0.30, +0.01] |
| LightGBM | +0.07 [+0.01, +0.14] | +0.01 [-0.06, +0.07] |
| MLP | +0.07 [-0.02, +0.15] | +0.05 [+0.01, +0.09] |
| GRU | +0.13 [+0.07, +0.18] | +0.06 [+0.02, +0.10] |
| LSTM | +0.12 [+0.05, +0.19] | +0.07 [+0.02, +0.10] |
| TCN | +0.10 [+0.02, +0.17] | +0.06 [+0.01, +0.12] |
| N-BEATS-lite | +0.07 [-0.08, +0.17] | +0.01 [-0.05, +0.08] |

**Reading.**
- **Winter:** the recurrent networks are the best point estimates, and LightGBM also beats persistence. The gap between GRU and LightGBM does not clear zero. Without weather the gains shrink to +0.05 to +0.07 for the better models and the ridge model is no better than persistence.
- **Summer:** everything that sees weather beats persistence by 0.14 to 0.18, with ridge and the ridge-plus-LightGBM average at the top. Deep models are not better than ridge here.
- **Why this differs from the earlier "LightGBM +4%, intervals overlap" result:** calendar-correct lags, rows restricted to complete weeks, a relative target, and a smaller regularised LightGBM. I did not separate which of the four matters most, and the two results should not be pooled or described as the same experiment.
- **Multiplicity:** 16 learned model-and-feature variants were scored on the same folds. The best-looking one (GRU) carries selection optimism. The safer sentence is "recurrent and boosted models improve on persistence by about 5 to 13% in winter, with no clear winner".

## 5. What this means for the research questions

| RQ | Answer now |
|---|---|
| RQ1 forecast beats baselines? | Yes against persistence, consistently. Against same hour yesterday: yes at 1 to 3 h and, with more training data, overall; not on the fixed split beyond 3 h. Deep does not beat classical in any consistent way. |
| Why the earlier loss? | Regime shift (levels unseen in training) plus overfitting on about 16 days of origins. Regularisation and a relative target recover most of the 17 to 24 h gap (test MAE 102 to 65, against 66 for yesterday); more data helps further. |
| Deep learning worth it here? | Not demonstrated. It is level with a regularised boosted model on the hourly data and on the daily data. Its one robust advantage is joint training of all 24 horizons, and a boosted model with the same relative target gets most of that. |

## 6. Literature this is consistent with (checked 17 Nov 2026)

- Tree-based models usually match or beat deep networks on small to medium tabular data: [Grinsztajn, Oyallon and Varoquaux, NeurIPS 2022](https://arxiv.org/abs/2207.08815).
- Simple linear models can beat elaborate deep forecasters on time series: [Zeng et al., AAAI 2023](https://doi.org/10.1609/aaai.v37i9.26317).
- A seasonal-naive forecast is the standard yardstick that learned forecasts should be compared with, which is why "same hour yesterday" is the right bar: [Hyndman and Koehler, 2006](https://www.doi.org/10.1016/J.IJFORECAST.2006.03.001).
- Architectures used: [N-BEATS (Oreshkin et al., ICLR 2020)](https://arxiv.org/abs/1905.10437), [TCN (Bai, Kolter and Koltun, 2018)](https://arxiv.org/abs/1803.01271); GRU and LSTM are the standard recurrent models. These two arXiv links are from memory and were not re-checked today. [To do: confirm before the report.]

## 7. Limits, stated

- Hourly archive: 40 days, one city, one season; training 16 days of origins. Test periods overlap in the sensitivity splits. The later splits were chosen after seeing the first result.
- Hourly deep models see only the AQI history and the hour; they do not use the CAMS or EPA forecasts (removing those features did not change LightGBM, so this is unlikely to matter, but it was not tested for the networks).
- Daily: 437 usable days, weather of the target day is observed ERA5 (perfect prognosis), one city, folds of 23 to 100 days. W2021-22 trained on only 56 days.
- Results depend on random seeds; the networks are 5-seed ensembles, not fixed single runs. Single-seed spread was not measured.
- **Run note (17 Nov, later).** The scripts were re-run on the project laptop after this memo was written. All conclusions held; some hourly MAEs differ in the first decimal (for example MLP 59.3 against 59.4 overall, TCN 69.7 against 69.1 at 17 to 24 h, GRU against yesterday at 17 to 24 h -0.13 against -0.12). The report (5.4) uses the laptop figures, which are the ones in the committed `data/eval` files; the tables above came from the container run. Differences of that size are run-to-run noise.
- Not tested: transformers, foundation models (Chronos, TimesFM), multi-station models, quantile forecasts. [Optional future work.]
- Seasonality beyond one winter cannot be estimated from this archive. Re-run weekly as origins grow (about 24 a day).

## 8. What to claim in the report

> On the pre-registered split, the hourly forecaster beats persistence (skill +0.34 to +0.38 for the regularised and deep models) and is level with the same-hour-yesterday baseline overall (+0.03 to +0.10, intervals including zero), beating it at 4 to 8 h. With more training data most models beat both baselines (all intervals exclude zero on the 5 Nov split). Deep and boosted models are statistically indistinguishable; training data volume and the target formulation explain more than the model family.

Do not claim that deep learning is better, that the daily results are comparable to the earlier Model A figures, or that the daily skill holds with real weather forecasts.

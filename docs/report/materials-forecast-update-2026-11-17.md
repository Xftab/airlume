# Airlume - Materials and Methods, v7 update: forecasting (17 Nov 2026)

Status: this file REPLACES Section 6.1 (daily Model A) and Section 6.3 (hourly forecast) of the Materials draft (`07-materials-draft.md` v5 and `07b-materials-v6-update.md`). Everything else in v5 and v6 stands. Full tables with intervals are in the report, Section 5.4, and in `docs/research/forecast-models-v2-2026-11-17.md`. Items in [square brackets] still need filling.

Conventions for every figure below. Skill = 1 - MAE(model) / MAE(baseline) on the same rows; 0 means no better than the baseline, positive is better. 95% intervals are moving-block bootstraps over forecast origins (hourly: 24 h blocks) or over days (daily: 7-day blocks), 2000 resamples. Time-based splits only, never random.

## Replaces Section 6.1. Daily next-day PM2.5 forecasting, Model A version 2 (17 Nov 2026)

Script `scripts/model_a_v2.py`; scorecard `data/eval/model_a_v2_2026-11-17.json`; test `tests/test_forecast_models_v2.py`.

**What changed from the 29 Oct Model A, and why.** (1) The 29 Oct lag features were shifted by table row, not by calendar day. The EPD series has 52 gaps (largest 198 days), so 55 of 657 rows had a "yesterday" from an earlier date, and the neural windows of "7 days" were 7 rows. Lags now exist only for calendar days actually observed. Only days with a complete previous week are kept: 437 days, 2020-11-16 to 2024-08-12. (2) The 29 Oct test period (April to August 2024, mean PM2.5 about 56) was the easiest season for persistence. The folds are now forward-chained: winter 2021-22 (train 56 days, test 47), 2022-23 (train 239, test 23; the series has no January or February 2023), 2023-24 (train 263, test 61), pooled as the headline (131 test days, mean PM2.5 174.8 ug/m3), and summer 2024 (train 336, test 100, mean 41.4), reported beside it.

**Target and features.** Target: log(PM2.5 today) - log(PM2.5 yesterday), so every model starts at persistence. Inputs: ERA5 weather of the target day (as in Model A v1), calendar features, and PM2.5 lags and windows built from calendar days. The target day's weather is observed ERA5 (perfect prognosis); in use it would be a weather forecast, so results with weather are upper bounds. Each model is also run without weather.

**Models.** Ridge, LightGBM, MLP, GRU, LSTM, TCN (two dilated causal convolutions), N-BEATS-lite, and a ridge plus LightGBM average; the networks are 5-seed ensembles on a 7-day window. Baselines: persistence (yesterday), 3-day mean, 7-day mean, month mean. [Hyperparameters: see the script header; fixed before scoring.]

**Results, winter pooled, skill against persistence (MAE 43.1).** GRU +0.13 [+0.07, +0.18]; LSTM +0.12 [+0.05, +0.19]; TCN +0.10 [+0.02, +0.17]; ridge plus LightGBM average +0.08 [-0.02, +0.17]; LightGBM +0.07 [+0.01, +0.14]; MLP +0.07 [-0.02, +0.15]; N-BEATS-lite +0.07 [-0.08, +0.17]; ridge -0.02 [-0.22, +0.11]. GRU against LightGBM: +0.06 [-0.00, +0.11], not distinguishable. Summer 2024: every model that sees weather +0.14 to +0.18; the ridge and LightGBM average is best (+0.18 [+0.11, +0.24]); deep models are not better than ridge. Without weather in winter: +0.05 to +0.07 for the better networks; ridge no better than persistence.

**Findings.** (1) Recurrent, convolutional and boosted models beat persistence in winter by roughly 5 to 13%; no model family is clearly best. (2) Weather of the target day adds a measurable part of the gain. (3) The earlier result (LightGBM MAE 13.9 against 14.5, intervals overlapping, summer only) came from row-shifted lags and the easiest season; it is a different experiment and is not pooled with this one. (4) The best-looking model carries selection optimism: 16 learned model-and-feature variants were scored on the same folds.

**Limitations.** One city; 437 usable days; folds of 23 to 100 days (the first winter fold trained on only 56 days); weather is observed, not forecast; seed spread not measured; the joined table ends 2024-08-20 although the EPD bulletins run to December 2025 [check why the join stops there before quoting a date range].

## Replaces Section 6.3. Hourly forecast of Lahore city AQI, 1 to 24 h ahead (re-run and extension, 17 Nov 2026)

Scripts `scripts/forecast_fit.py`, `forecast_baseline_check.py`, `forecast_diagnose.py`, `forecast_models_v2.py`; scorecards `data/eval/forecast_fit_2026-11-17.json`, `forecast_baseline_check_2026-11-17.json`, `forecast_diagnose_2026-11-17.json`, `forecast_models_v2_2026-11-17.json` (and `_split-2026-10-30`, `_split-2026-11-05`). Memo: `docs/research/forecast-models-v2-2026-11-17.md`.

**Data and split.** Lahore city AQI (PB-LHE, Punjab EPA city hourly), 957 hourly values. Direct multi-horizon rows (origin t, horizon 1 to 24). Split fixed at 27 Oct 2026 00:00 UTC on 1 Nov, before the deep models were written, with an embargo: 412 training origins (9,612 rows; 389 for the networks, which need 48 h of history) and 519 test origins (12,180 rows). Training mean AQI 175.3; test mean 297.0. The 1 Nov and 6 Nov tests (127 and 252 origins) are superseded.

**Baselines.** Persistence; the same hour yesterday; a blend of the two with one weight per horizon fitted on training rows only (exploratory, added after seeing a result); the relayed CAMS forecast (1 to 24 h) and the relayed EPA forecast (1 to 8 h).

**Models.** Boosted and linear: ridge and LightGBM, one per horizon band (1-3, 4-8, 9-16, 17-24 h), the 6 Nov models; a regularised LightGBM (80 trees, 4 leaves, minimum leaf 200, L2 10) with a relative target. Neural: MLP, GRU, LSTM, TCN, N-BEATS-lite, each one network for all 24 horizons, input the last 48 hourly values relative to the latest one plus the log latest value and the hour of day, target the log ratio to the latest value, L1 loss with a mask, 5-seed ensembles averaged in log space, early stopping on the last 20% of training origins (never the test period). Hyperparameters fixed in the scripts; no tuning on any test period. The networks do not see the CAMS or EPA forecasts.

**Diagnosis of the 6 Nov overfit (17 to 24 h).** Default per-band LightGBM: in-sample MAE 20.4, cross-validated inside training 43.3, test 102.5. At a last reading above 300 its test MAE was 123 to 124 against 82 to 83 for persistence; such rows were 5.9% of training rows and 54% of test rows. Regularisation brought the test MAE to 69.8, a relative target on top of it to 65.1 (yesterday 66.3); removing CAMS and EPA features changed nothing (100.1). The learning curve was erratic (test MAE 85, 71, 65, 102 at 25, 50, 75, 100% of the training origins). So: a regime shift beyond the training range, plus overfitting on about 16 days of origins; cross-validation inside the training period could not have shown it.

**Results, primary split, all 1-24 h (persistence MAE 95.4, yesterday 65.7).** Skill against persistence: MLP +0.38 [+0.29, +0.45]; N-BEATS-lite +0.37; LSTM +0.37; blend +0.37; TCN +0.37; GRU +0.35 [+0.22, +0.45]; regularised LightGBM +0.34 [+0.26, +0.39]; ridge per band +0.24 [+0.13, +0.33]; per-band LightGBM +0.15 [+0.06, +0.23]; relayed CAMS -0.37 [-0.56, -0.19]. Against the same hour yesterday: MLP +0.10 [-0.02, +0.20]; N-BEATS-lite +0.09; LSTM +0.09; blend +0.08 [+0.04, +0.13]; TCN +0.08; GRU +0.05; regularised LightGBM +0.03; ridge per band -0.10; per-band LightGBM -0.23 [-0.50, -0.01]; CAMS -1.00 [-1.52, -0.54]. By band: 1-3 h every model beats yesterday by 0.40 to 0.51; 4-8 h the MLP, GRU, LSTM and N-BEATS-lite beat it (+0.16 to +0.21, intervals above zero); 9-16 h none does with confidence; 17-24 h the GRU is worse (-0.13 [-0.27, -0.00]). Relayed EPA, 1-8 h: +0.27 [+0.11, +0.42] against persistence on the 2,047 rows it covers. Sensitivity splits (30 Oct, 5 Nov; overlapping test sets, dates chosen after seeing the first result): every learned model has a positive point estimate against yesterday (+0.04 to +0.23); all intervals exclude zero on 5 Nov.

**Findings.** (1) Learned forecasters beat persistence and the relayed CAMS forecast; CAMS is worse than every baseline in every setting. (2) Against yesterday the outcome depends on how much of the current smog regime the training data holds; the 6 Nov statement "no learned model beats yesterday beyond 3 h" described 16 days of training data, not the model families. (3) Deep and classical models are not distinguishable; formulation (relative target, joint horizons) and data volume mattered more than architecture.

**Limitations.** 40-day archive, one city, one season (Oct-Nov smog); training is about 16 days of origins. Regularised variants, the blend, per-band fits and the later splits were chosen after seeing results, so they are exploratory. Networks are 5-seed ensembles; a second run in a different environment moved some MAEs by up to about 0.6 (for example TCN at 17-24 h, 69.1 against 69.7), so differences of that size are noise; single-seed spread not measured. Not tested: transformers, foundation models (Chronos, TimesFM), multi-station models, quantile forecasts. Nothing beyond 24 h exists in the archive. Re-run as origins grow (about 24 a day).

**Literature.** Grinsztajn, Oyallon and Varoquaux (NeurIPS 2022) on trees against deep nets on tabular data; Zeng et al. (AAAI 2023) on simple linear forecasters; Hyndman and Koehler (2006) on the seasonal-naive yardstick. N-BEATS (Oreshkin et al., ICLR 2020) and TCN (Bai, Kolter and Koltun, 2018) [confirm both references before submission].

## Replaces Section 5, items 4 and 5

4. **Forecast evaluation**: time-based splits only; two baselines (persistence and the same hour yesterday; the stronger one is the bar from 4 h in smog season); skill scores with block-bootstrap intervals; selection after seeing results is disclosed.
5. **R&D models**: (A) daily forecaster v2, (B) hourly CAMS bias-correction, (C) hour climatology, (4.2) hourly 1 to 24 h with classical and deep models. Results: Sections 6.1 and 6.3 above.

## Replaces Section 10 (To fill before the report), forecast items

- Phase 4.2: re-run `forecast_fit.py` and `forecast_models_v2.py` weekly as origins accumulate; rolling-origin evaluation when over about 60 days.
- Confirm the N-BEATS and TCN references; find out why the daily join stops at 2024-08-20.
- Optional: seed-spread measurement; transformer or foundation-model baseline.

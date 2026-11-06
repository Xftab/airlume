# Hourly forecast: re-run on the restored archive, against a harder baseline

**Date:** 6 November 2026. **Author:** Claude. **Scripts:** `scripts/forecast_fit.py` (unchanged protocol, split 27 Oct 00:00 UTC fixed on 1 Nov) and the new `scripts/forecast_baseline_check.py`. **Scorecards:** `data/eval/forecast_fit_2026-11-06.json`, `data/eval/forecast_baseline_check_2026-11-06.json`.

## 1. Data

- Target: Lahore city AQI (PB-LHE), 690 hourly values from 8 Oct 19:00 to 6 Nov 12:00 UTC, with no gaps.
- Training: 412 origins (9,612 rows). Test: **252 origins (5,772 rows)**, against 146 on 2 Nov.
- The restored archive (`archive-merge-loss-2026-11-06.md`) adds 230 CAMS forecast issues.
- **Regime shift.** Test mean AQI is 300.6, against 175.3 in training. The test range reaches 500, against 419 in training, so the test period is heavier smog than anything the models were trained on.

## 2. Against persistence (the reported measure until now)

Skill is 1 minus MAE(model) over MAE(persistence), on the same rows. Intervals are a moving-block bootstrap over origins.

| Band | Persistence MAE | Per-band ridge | Per-band LightGBM | Same hour yesterday | CAMS relayed |
|---|---:|---|---|---|---|
| 1 to 3 h | 43.6 | +0.14 [+0.06, +0.20] | **+0.24 [+0.17, +0.29]** | -0.51 | -1.96 |
| 4 to 8 h | 101.3 | +0.29 [+0.12, +0.38] | +0.35 [+0.25, +0.41] | **+0.35** | -0.29 |
| 9 to 16 h | 130.0 | +0.34 [+0.16, +0.46] | +0.28 [+0.15, +0.36] | **+0.49** | -0.04 |
| 17 to 24 h | 92.7 | +0.02 [-0.27, +0.23] | -0.18 [-0.55, +0.11] | **+0.26** | -0.50 |
| all 1 to 24 h | 100.6 | +0.22 [+0.05, +0.34] | +0.15 [+0.01, +0.26] | **+0.34** | -0.34 |

The EPA relayed forecast (1 to 8 h only) is +0.07 overall.

## 3. The finding: beyond 3 hours the models lose to "same hour yesterday"

Persistence is a weak baseline in a smog season with a strong daily cycle. The AQI at 03:00 tonight is much closer to the AQI at 03:00 last night than to the AQI now. Against the seasonal-naive baseline ("same hour yesterday", already computed in `forecast_fit.py` as `yesterday`, but not used as the yardstick):

| Band | Yesterday MAE | Per-band LightGBM | Per-band ridge | Blend (below) |
|---|---:|---|---|---|
| 1 to 3 h | 65.6 | **+0.49 [+0.25, +0.64]** | +0.43 [+0.16, +0.59] | +0.40 [+0.13, +0.56] |
| 4 to 8 h | 65.8 | -0.01 [-0.41, +0.25] | -0.10 [-0.52, +0.15] | +0.05 [-0.10, +0.17] |
| 9 to 16 h | 66.8 | -0.41 [-1.03, +0.03] | -0.28 [-0.81, +0.08] | +0.01 [-0.06, +0.08] |
| 17 to 24 h | 68.2 | -0.61 [-1.54, -0.08] | -0.34 [-0.99, +0.04] | -0.00 [-0.06, +0.05] |
| all 1 to 24 h | 66.9 | -0.27 [-0.80, +0.07] | -0.17 [-0.58, +0.12] | **+0.06 [-0.02, +0.13]** |

The numbers are skill against yesterday, on the same rows.

**What it means:** the learned models beat the seasonal baseline only at 1 to 3 hours. From 4 to 24 hours none beats "same hour yesterday". Several are clearly worse at 17 to 24 hours, which is the regime shift in section 1 at work. The 2 Nov result, "beats persistence by about 25%", is true but incomplete. On 2 Nov the same-hour-yesterday baseline already scored +0.28 against persistence, as well as the best model (+0.26). It should have been reported beside it.

**Blend (exploratory).** Per horizon, w times the last value plus (1 minus w) times the same hour yesterday, with one weight per horizon chosen on the training rows only (grid of 0.05). Weights run from 0.95 at 1 h to 0.15 from 8 h onward. This one-parameter model is the best overall: MAE 62.6, against 100.6 for persistence and 66.9 for yesterday. Its edge over yesterday is small, and the interval includes zero. It was added after seeing this result, so it carries mild selection optimism, like the per-band models before it. It is not the headline.

## 4. What to change

1. **Report skill against both baselines.** Name the stronger one ("same hour yesterday") as the bar from 4 h on. That is the honest W7 statement: *beats persistence, matches but does not beat the seasonal baseline beyond 3 h on a 10-day test period heavier than training.*
2. **If Airlume shows its own forecast**, the defensible design is per-band LightGBM for 1 to 3 h and the blend for 4 to 24 h, labelled with its measured error. Today the app relays the EPA and CAMS forecasts with their scorecards. CAMS loses to every baseline at every band (skill against yesterday about -1.0), and the scorecard already shows this. Whether to add an Airlume forecast is a scope decision for Aftab, and it is not made here.
3. **Re-run weekly.** The test set grows by about 24 origins a day, and only a test period inside the training regime can show whether the 17 to 24 h loss is regime shift or overfitting.

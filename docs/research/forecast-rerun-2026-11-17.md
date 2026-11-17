# Hourly forecast re-run, 17 November 2026

Same protocol as 6 Nov: `scripts/forecast_fit.py` and `scripts/forecast_baseline_check.py`, split fixed at 27 Oct 2026 00:00 UTC. Outputs: `data/eval/forecast_fit_2026-11-17.json`, `data/eval/forecast_baseline_check_2026-11-17.json`. Test rows are 12,180 (5,772 on 6 Nov), roughly 520 origins against 252. Read from the console output of the run; the header lines with the training and test counts were not captured.

## Skill against persistence, all 1 to 24 h (95% CI)
| Model | 6 Nov | 17 Nov |
|---|---|---|
| per-band ridge | +0.22 [+0.05, +0.34] | **+0.244 [+0.134, +0.333]** |
| per-band LightGBM | +0.15 [+0.01, +0.26] | **+0.155 [+0.059, +0.232]** |
| plain ridge | not recorded here | +0.191 [+0.069, +0.289] |
| plain LightGBM | not recorded here | +0.059 [-0.069, +0.159] |
| CAMS relayed | -0.34 | -0.374 [-0.560, -0.194] |

Result is stable and the intervals are tighter. Both per-band models beat persistence.

## Skill against "same hour yesterday" (MAE 65.69), all 1 to 24 h
per-band ridge -0.10 [-0.33, +0.10]; per-band LightGBM -0.23 [-0.50, -0.01]; plain ridge -0.18; plain LightGBM -0.37 [-0.70, -0.11]; CAMS relayed -1.00 [-1.52, -0.54]; blend **+0.08 [+0.04, +0.13]**.

By horizon, per-band LightGBM against yesterday: 1 to 3 h +0.48 [+0.36, +0.57]; 4 to 8 h -0.01 [-0.22, +0.16]; 9 to 16 h -0.32 [-0.64, -0.07]; 17 to 24 h -0.55 [-1.01, -0.18].

## Reading
1. Beats persistence: confirmed on about twice the test data.
2. Beats yesterday only at 1 to 3 h: confirmed. From 4 h on, no learned model beats it; at 9 to 24 h LightGBM is significantly worse.
3. The 17 to 24 h loss did **not** go away with more test data, so it is not explained only by the short test period. Overfitting by the per-band LightGBM is now the more likely reason. Not tested.
4. The blend now has an interval that excludes zero (+0.08 [+0.04, +0.13]), up from +0.06 [-0.02, +0.13]. Its weights were chosen after looking at results, so it stays exploratory and is not the headline.
5. Not checked here: whether the test mean AQI is still heavier than training (301 against 175 on 6 Nov).

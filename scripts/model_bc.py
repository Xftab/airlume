"""
Model B: CAMS hourly bias correction (LightGBM).
Model C: Zero-shot seasonal climatology baseline.
RUN NOW in Command Prompt:
    K:
    cd K:\\airlume
    .venv\\Scripts\\activate
    python scripts\\model_bc.py

Model B learns EPA_PM25 = f(CAMS_PM25, hour, day_of_week, CAMS_PM10).
Model C predicts the month-hour climatological mean from EPA data.
Both evaluated on a chronological 80/20 split of paired CAMS-EPA hours.
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb
import json
import os

# ── Config ──────────────────────────────────────────────────────────
CAMS_PATH = os.path.join("data", "archive", "city_hourly", "open_meteo_cams", "2026-10.csv")
EPA_PATH = os.path.join("data", "archive", "readings", "punjab_epa", "2026-10.csv")
RESULTS_DIR = os.path.join("docs", "research")
os.makedirs(RESULTS_DIR, exist_ok=True)

N_BOOTSTRAP = 2000
SEED = 42
TARGET = "epa_pm25_mean"

# ── 1. Build paired dataset ────────────────────────────────────────
print("Building paired CAMS-EPA hourly dataset...")

cams = pd.read_csv(CAMS_PATH)
cams["ts"] = pd.to_datetime(cams["ts"])
cams = cams.rename(columns={"pm25": "cams_pm25", "pm10": "cams_pm10", "aqi": "cams_aqi"})

epa = pd.read_csv(EPA_PATH)
epa["ts"] = pd.to_datetime(epa["ts"])

# Average EPA across stations per hour (city mean)
epa_hourly = (
    epa.groupby("ts")
    .agg(
        epa_pm25_mean=("pm25", "mean"),
        epa_pm10_mean=("pm10", "mean"),
        epa_aqi_mean=("aqi", "mean"),
        n_stations=("station_id", "nunique"),
    )
    .reset_index()
)

# Join on timestamp
paired = pd.merge(epa_hourly, cams[["ts", "cams_pm25", "cams_pm10", "cams_aqi"]], on="ts", how="inner")
paired = paired.dropna(subset=["epa_pm25_mean", "cams_pm25"])
paired = paired.sort_values("ts").reset_index(drop=True)

# Derived features
paired["hour"] = paired["ts"].dt.hour
paired["weekday"] = paired["ts"].dt.weekday
paired["cams_bias_raw"] = paired["cams_pm25"] - paired["epa_pm25_mean"]
paired["cams_pm25_lag1"] = paired["cams_pm25"].shift(1)
paired["epa_pm25_lag1"] = paired["epa_pm25_mean"].shift(1)
paired["epa_pm25_lag3"] = paired["epa_pm25_mean"].shift(3)
paired = paired.dropna().reset_index(drop=True)

print(f"Paired hours: {len(paired)}")
print(f"Date range: {paired['ts'].min()} to {paired['ts'].max()}")
print(f"Mean CAMS PM2.5: {paired['cams_pm25'].mean():.1f}, Mean EPA PM2.5: {paired['epa_pm25_mean'].mean():.1f}")
print(f"Mean raw bias (CAMS - EPA): {paired['cams_bias_raw'].mean():.1f}")

# ── 2. Train/test split ────────────────────────────────────────────
split_idx = int(len(paired) * 0.8)
train = paired.iloc[:split_idx].copy()
test = paired.iloc[split_idx:].copy()
print(f"\nTrain: {len(train)} rows ({train['ts'].iloc[0]} to {train['ts'].iloc[-1]})")
print(f"Test:  {len(test)} rows ({test['ts'].iloc[0]} to {test['ts'].iloc[-1]})")

FEATURE_COLS = [
    "cams_pm25", "cams_pm10", "cams_aqi",
    "hour", "weekday",
    "cams_pm25_lag1", "epa_pm25_lag1", "epa_pm25_lag3",
]

X_train = train[FEATURE_COLS]
y_train = train[TARGET]
X_test = test[FEATURE_COLS]
y_test = test[TARGET]


def bootstrap_ci(y_true, y_pred, metric_fn, n=N_BOOTSTRAP, seed=SEED):
    rng = np.random.RandomState(seed)
    n_obs = len(y_true)
    block_size = 6  # 6-hour blocks for hourly autocorrelation
    n_blocks = int(np.ceil(n_obs / block_size))
    vals = []
    for _ in range(n):
        starts = rng.randint(0, n_obs - block_size + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, min(s + block_size, n_obs)) for s in starts])[:n_obs]
        vals.append(metric_fn(y_true[idx], y_pred[idx]))
    return np.percentile(vals, [2.5, 97.5])


def evaluate(name, y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    mae_lo, mae_hi = bootstrap_ci(y_true.values, y_pred, mean_absolute_error)
    rmse_fn = lambda yt, yp: np.sqrt(mean_squared_error(yt, yp))
    rmse_lo, rmse_hi = bootstrap_ci(y_true.values, y_pred, rmse_fn)
    r2_lo, r2_hi = bootstrap_ci(y_true.values, y_pred, r2_score)

    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    print(f"  MAE:  {mae:.1f}  [95% CI: {mae_lo:.1f}, {mae_hi:.1f}]")
    print(f"  RMSE: {rmse:.1f}  [95% CI: {rmse_lo:.1f}, {rmse_hi:.1f}]")
    print(f"  R2:   {r2:.3f}  [95% CI: {r2_lo:.3f}, {r2_hi:.3f}]")

    return {
        "model": name,
        "mae": round(mae, 2), "mae_ci": [round(mae_lo, 2), round(mae_hi, 2)],
        "rmse": round(rmse, 2), "rmse_ci": [round(rmse_lo, 2), round(rmse_hi, 2)],
        "r2": round(r2, 4), "r2_ci": [round(r2_lo, 4), round(r2_hi, 4)],
        "n_test": len(y_true),
    }


results = []

# ── 3. Baseline: raw CAMS (no correction) ──────────────────────────
print("\n--- Baseline: Raw CAMS (no correction) ---")
r = evaluate("Raw CAMS", y_test, test["cams_pm25"].values)
results.append(r)

# ── 4. Model B: LightGBM bias correction ──────────────────────────
print("\n--- Model B: LightGBM CAMS Correction ---")
lgb_params = {
    "objective": "regression",
    "metric": "mae",
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 5,
    "num_leaves": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_samples": 5,
    "random_state": SEED,
    "verbose": -1,
}

model_b = lgb.LGBMRegressor(**lgb_params)
model_b.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    callbacks=[lgb.log_evaluation(100)],
)

lgb_pred = model_b.predict(X_test)
r = evaluate("Model B (LightGBM correction)", y_test, lgb_pred)
results.append(r)

# Feature importance
imp = pd.DataFrame({
    "feature": FEATURE_COLS,
    "importance": model_b.feature_importances_,
}).sort_values("importance", ascending=False)
print("\nFeature importance:")
print(imp.to_string(index=False))

# ── 5. Model C: Seasonal climatology (zero-shot) ──────────────────
print("\n\n--- Model C: Seasonal Climatology (zero-shot) ---")
# Use train set to compute month-hour mean PM2.5, apply to test
train["month"] = train["ts"].dt.month
test_c = test.copy()
test_c["month"] = test_c["ts"].dt.month

# Since all data is Oct, use hour-of-day mean as climatology
clim = train.groupby("hour")[TARGET].mean()
clim_pred = test_c["hour"].map(clim).values

# Fill any missing hours with overall mean
overall_mean = y_train.mean()
clim_pred = np.where(np.isnan(clim_pred), overall_mean, clim_pred)

r = evaluate("Model C (hour climatology)", y_test, clim_pred)
results.append(r)

# ── 6. Persistence baseline ───────────────────────────────────────
print("\n--- Baseline: Persistence (last EPA reading) ---")
persist_pred = test["epa_pm25_lag1"].values
r = evaluate("Persistence (lag-1h)", y_test, persist_pred)
results.append(r)

# ── 7. Comparison table ───────────────────────────────────────────
print("\n\n" + "=" * 60)
print("  COMPARISON TABLE (hourly PM2.5, CAMS correction task)")
print("=" * 60)
print(f"{'Model':<35} {'MAE':>8} {'RMSE':>8} {'R2':>8}")
print("-" * 65)
for r in results:
    print(f"{r['model']:<35} {r['mae']:>8.1f} {r['rmse']:>8.1f} {r['r2']:>8.3f}")

# ── 8. Save ────────────────────────────────────────────────────────
results_path = os.path.join(RESULTS_DIR, "model-bc-results.json")
with open(results_path, "w") as f:
    json.dump({
        "description": "Model B (CAMS bias correction) and Model C (climatology) for hourly PM2.5",
        "paired_hours": len(paired),
        "train_period": f"{train['ts'].iloc[0]} to {train['ts'].iloc[-1]}",
        "test_period": f"{test['ts'].iloc[0]} to {test['ts'].iloc[-1]}",
        "bootstrap": f"{N_BOOTSTRAP} resamples, 6-hour blocks",
        "results": results,
        "top_features_model_b": imp.to_dict(orient="records"),
    }, f, indent=2)

print(f"\nResults saved to {results_path}")

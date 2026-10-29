"""
Model A baselines: persistence and LightGBM on daily feature table.
RUN NOW in Command Prompt:
    K:
    cd K:\\airlume
    .venv\\Scripts\\activate
    pip install lightgbm scikit-learn
    python scripts\model_a_baselines.py

Predicts next-day PM2.5 concentration for Lahore using ERA5 weather + lags.
Train on first 80%, test on last 20% (chronological). Reports MAE, RMSE, R2 with bootstrap CIs.
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb
import json
import os

# ── Config ──────────────────────────────────────────────────────────
FEATURES_PATH = os.path.join("data", "features", "lahore_daily_features.csv")
RESULTS_DIR = os.path.join("docs", "research")
os.makedirs(RESULTS_DIR, exist_ok=True)

TARGET = "pm25_conc"

FEATURE_COLS = [
    "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
    "relative_humidity_2m_max", "relative_humidity_2m_min", "relative_humidity_2m_mean",
    "wind_speed_10m_max", "wind_speed_10m_mean", "wind_direction_10m_dominant",
    "precipitation_sum", "rain_sum",
    "shortwave_radiation_sum", "et0_fao_evapotranspiration",
    "temp_range", "day_of_year", "month", "weekday",
    "pm25_conc_lag1", "pm25_aqi_lag1",
    "pm25_conc_lag2", "pm25_conc_lag3", "pm25_conc_roll7",
]

N_BOOTSTRAP = 2000
SEED = 42

# ── Load ────────────────────────────────────────────────────────────
print("Loading feature table...")
df = pd.read_csv(FEATURES_PATH, parse_dates=["date"])
df = df.dropna(subset=FEATURE_COLS + [TARGET])
print(f"Total usable rows: {len(df)}")

# Train/test split: chronological, last 20% as test
df = df.sort_values("date").reset_index(drop=True)
split_idx = int(len(df) * 0.8)
train = df.iloc[:split_idx].copy()
test = df.iloc[split_idx:].copy()
print(f"Train: {len(train)} rows ({train['date'].min().date()} to {train['date'].max().date()})")
print(f"Test:  {len(test)} rows ({test['date'].min().date()} to {test['date'].max().date()})")

X_train = train[FEATURE_COLS]
y_train = train[TARGET]
X_test = test[FEATURE_COLS]
y_test = test[TARGET]


def bootstrap_ci(y_true, y_pred, metric_fn, n=N_BOOTSTRAP, seed=SEED):
    """Moving-block bootstrap CI (block=7 days for daily autocorrelation)."""
    rng = np.random.RandomState(seed)
    n_obs = len(y_true)
    block_size = 7
    n_blocks = int(np.ceil(n_obs / block_size))
    vals = []
    for _ in range(n):
        starts = rng.randint(0, n_obs - block_size + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, min(s + block_size, n_obs)) for s in starts])[:n_obs]
        vals.append(metric_fn(y_true.values[idx], y_pred[idx]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return lo, hi


def evaluate(name, y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    mae_lo, mae_hi = bootstrap_ci(y_true, y_pred, mean_absolute_error)
    rmse_fn = lambda yt, yp: np.sqrt(mean_squared_error(yt, yp))
    rmse_lo, rmse_hi = bootstrap_ci(y_true, y_pred, rmse_fn)
    r2_lo, r2_hi = bootstrap_ci(y_true, y_pred, r2_score)

    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    print(f"  MAE:  {mae:.1f}  [95% CI: {mae_lo:.1f}, {mae_hi:.1f}]")
    print(f"  RMSE: {rmse:.1f}  [95% CI: {rmse_lo:.1f}, {rmse_hi:.1f}]")
    print(f"  R2:   {r2:.3f}  [95% CI: {r2_lo:.3f}, {r2_hi:.3f}]")

    return {
        "model": name,
        "mae": round(mae, 2),
        "mae_ci": [round(mae_lo, 2), round(mae_hi, 2)],
        "rmse": round(rmse, 2),
        "rmse_ci": [round(rmse_lo, 2), round(rmse_hi, 2)],
        "r2": round(r2, 4),
        "r2_ci": [round(r2_lo, 4), round(r2_hi, 4)],
        "n_test": len(y_true),
    }


results = []

# ── Baseline 1: Persistence (predict yesterday's value) ────────────
print("\n\n--- Baseline 1: Persistence ---")
persist_pred = test["pm25_conc_lag1"].values
mask = ~np.isnan(persist_pred)
r = evaluate("Persistence (lag-1)", y_test[mask], persist_pred[mask])
results.append(r)

# ── Baseline 2: LightGBM ──────────────────────────────────────────
print("\n\n--- Baseline 2: LightGBM ---")
lgb_params = {
    "objective": "regression",
    "metric": "mae",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "max_depth": 6,
    "num_leaves": 31,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_samples": 10,
    "random_state": SEED,
    "verbose": -1,
}

model = lgb.LGBMRegressor(**lgb_params)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    callbacks=[lgb.log_evaluation(100)],
)

lgb_pred = model.predict(X_test)
r = evaluate("LightGBM", y_test, lgb_pred)
results.append(r)

# Feature importance
imp = pd.DataFrame({
    "feature": FEATURE_COLS,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=False)
print("\nTop 10 features:")
print(imp.head(10).to_string(index=False))

# ── Save results ───────────────────────────────────────────────────
results_path = os.path.join(RESULTS_DIR, "model-a-baselines.json")
with open(results_path, "w") as f:
    json.dump({
        "description": "Model A daily PM2.5 forecast baselines for Lahore",
        "train_period": f"{train['date'].min().date()} to {train['date'].max().date()}",
        "test_period": f"{test['date'].min().date()} to {test['date'].max().date()}",
        "target": "next-day PM2.5 concentration (ug/m3)",
        "bootstrap": f"{N_BOOTSTRAP} resamples, 7-day blocks",
        "results": results,
        "top_features": imp.head(10).to_dict(orient="records"),
    }, f, indent=2)

print(f"\nResults saved to {results_path}")

# Also save predictions for analysis
preds = test[["date", TARGET]].copy()
preds["persistence_pred"] = persist_pred
preds["lgbm_pred"] = lgb_pred
preds_path = os.path.join("data", "features", "model_a_predictions.csv")
preds.to_csv(preds_path, index=False)
print(f"Predictions saved to {preds_path}")

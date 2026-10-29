"""
Model A neural variant: LSTM and GRU on daily feature table.
RUN NOW in Command Prompt:
    K:
    cd K:\\airlume
    .venv\\Scripts\\activate
    pip install torch
    python scripts\\model_a_neural.py

Uses a 7-day sliding window. Same chronological 80/20 split as baselines.
Reports MAE, RMSE, R2 with bootstrap CIs. Compares against saved baselines.
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import json
import os

# ── Config ──────────────────────────────────────────────────────────
FEATURES_PATH = os.path.join("data", "features", "lahore_daily_features.csv")
RESULTS_DIR = os.path.join("docs", "research")
os.makedirs(RESULTS_DIR, exist_ok=True)

TARGET = "pm25_conc"
WINDOW = 7  # days of lookback
EPOCHS = 100
BATCH = 32
LR = 0.001
HIDDEN = 64
N_LAYERS = 2
DROPOUT = 0.2
N_BOOTSTRAP = 2000
SEED = 42

torch.manual_seed(SEED)
np.random.seed(SEED)

# Weather + calendar features (no lags — the window provides temporal context)
INPUT_COLS = [
    "pm25_conc",  # included so the window sees past AQI values
    "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
    "relative_humidity_2m_max", "relative_humidity_2m_min", "relative_humidity_2m_mean",
    "wind_speed_10m_max", "wind_speed_10m_mean", "wind_direction_10m_dominant",
    "precipitation_sum", "rain_sum",
    "shortwave_radiation_sum", "et0_fao_evapotranspiration",
    "temp_range", "day_of_year", "month", "weekday",
]

# ── Load ────────────────────────────────────────────────────────────
print("Loading feature table...")
df = pd.read_csv(FEATURES_PATH, parse_dates=["date"])
df = df.dropna(subset=INPUT_COLS + [TARGET])
df = df.sort_values("date").reset_index(drop=True)
print(f"Total rows: {len(df)}")

# 80/20 chronological split
split_idx = int(len(df) * 0.8)
train_df = df.iloc[:split_idx].copy()
test_df = df.iloc[split_idx:].copy()
print(f"Train: {len(train_df)} rows ({train_df['date'].iloc[0].date()} to {train_df['date'].iloc[-1].date()})")
print(f"Test:  {len(test_df)} rows ({test_df['date'].iloc[0].date()} to {test_df['date'].iloc[-1].date()})")

# Scale features
scaler_X = StandardScaler()
scaler_y = StandardScaler()

train_X_raw = train_df[INPUT_COLS].values
test_X_raw = test_df[INPUT_COLS].values

scaler_X.fit(train_X_raw)
train_X_scaled = scaler_X.transform(train_X_raw)
test_X_scaled = scaler_X.transform(test_X_raw)

train_y = train_df[TARGET].values.reshape(-1, 1)
test_y = test_df[TARGET].values.reshape(-1, 1)
scaler_y.fit(train_y)
train_y_scaled = scaler_y.transform(train_y).ravel()
test_y_scaled = scaler_y.transform(test_y).ravel()

# Combine train+test scaled arrays for windowing across the boundary
all_X_scaled = np.vstack([train_X_scaled, test_X_scaled])
all_y_scaled = np.concatenate([train_y_scaled, test_y_scaled])


# ── Dataset ─────────────────────────────────────────────────────────
class WindowDataset(Dataset):
    def __init__(self, X, y, window):
        self.X = X
        self.y = y
        self.window = window

    def __len__(self):
        return len(self.y) - self.window

    def __getitem__(self, idx):
        x_seq = self.X[idx:idx + self.window]
        target = self.y[idx + self.window]
        return (
            torch.tensor(x_seq, dtype=torch.float32),
            torch.tensor(target, dtype=torch.float32),
        )


# Build datasets using combined array for correct windowing
# Train windows: indices 0..split_idx-1 as targets (window from before)
# Test windows: indices split_idx..end as targets
train_dataset = WindowDataset(all_X_scaled[:split_idx], all_y_scaled[:split_idx], WINDOW)
# For test, we need windows that start from split_idx-WINDOW
test_X_for_windows = all_X_scaled[split_idx - WINDOW:]
test_y_for_windows = all_y_scaled[split_idx - WINDOW:]
test_dataset = WindowDataset(test_X_for_windows, test_y_for_windows, WINDOW)

train_loader = DataLoader(train_dataset, batch_size=BATCH, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH, shuffle=False)

n_features = len(INPUT_COLS)
print(f"Input features: {n_features}, Window: {WINDOW}")
print(f"Train sequences: {len(train_dataset)}, Test sequences: {len(test_dataset)}")


# ── Models ──────────────────────────────────────────────────────────
class SeqModel(nn.Module):
    def __init__(self, rnn_type, input_size, hidden_size, n_layers, dropout):
        super().__init__()
        RNN = nn.LSTM if rnn_type == "LSTM" else nn.GRU
        self.rnn = RNN(
            input_size, hidden_size, n_layers,
            batch_first=True, dropout=dropout if n_layers > 1 else 0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
        )
        self.name = rnn_type

    def forward(self, x):
        out, _ = self.rnn(x)
        out = out[:, -1, :]  # last time step
        return self.fc(out).squeeze(-1)


def train_model(model, train_loader, test_loader, epochs, lr):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
    criterion = nn.MSELoss()
    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0
        for xb, yb in train_loader:
            pred = model(xb)
            loss = criterion(pred, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(xb)
        train_loss /= len(train_loader.dataset)

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for xb, yb in test_loader:
                pred = model(xb)
                val_loss += criterion(pred, yb).item() * len(xb)
        val_loss /= len(test_loader.dataset)

        scheduler.step(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if epoch % 20 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}  train_mse={train_loss:.4f}  val_mse={val_loss:.4f}  lr={optimizer.param_groups[0]['lr']:.6f}")

        if patience_counter >= 20:
            print(f"  Early stop at epoch {epoch}")
            break

    model.load_state_dict(best_state)
    return model


def predict(model, loader, scaler_y):
    model.eval()
    preds = []
    with torch.no_grad():
        for xb, _ in loader:
            preds.append(model(xb).numpy())
    preds = np.concatenate(preds)
    return scaler_y.inverse_transform(preds.reshape(-1, 1)).ravel()


def bootstrap_ci(y_true, y_pred, metric_fn, n=N_BOOTSTRAP, seed=SEED):
    rng = np.random.RandomState(seed)
    n_obs = len(y_true)
    block_size = 7
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
        "mae": round(mae, 2), "mae_ci": [round(mae_lo, 2), round(mae_hi, 2)],
        "rmse": round(rmse, 2), "rmse_ci": [round(rmse_lo, 2), round(rmse_hi, 2)],
        "r2": round(r2, 4), "r2_ci": [round(r2_lo, 4), round(r2_hi, 4)],
        "n_test": len(y_true),
    }


# ── Train and evaluate ─────────────────────────────────────────────
y_true = test_df[TARGET].values[:len(test_dataset)]
results = []

for rnn_type in ["LSTM", "GRU"]:
    print(f"\n\n{'#'*60}")
    print(f"  Training {rnn_type}")
    print(f"{'#'*60}")
    model = SeqModel(rnn_type, n_features, HIDDEN, N_LAYERS, DROPOUT)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {total_params:,}")
    model = train_model(model, train_loader, test_loader, EPOCHS, LR)
    preds = predict(model, test_loader, scaler_y)
    r = evaluate(rnn_type, y_true, preds)
    r["parameters"] = total_params
    results.append(r)

# ── Load baselines for comparison ──────────────────────────────────
baselines_path = os.path.join(RESULTS_DIR, "model-a-baselines.json")
if os.path.exists(baselines_path):
    with open(baselines_path) as f:
        baselines = json.load(f)
    print("\n\n" + "=" * 60)
    print("  COMPARISON TABLE")
    print("=" * 60)
    print(f"{'Model':<20} {'MAE':>8} {'RMSE':>8} {'R2':>8}")
    print("-" * 50)
    for b in baselines["results"]:
        print(f"{b['model']:<20} {b['mae']:>8.1f} {b['rmse']:>8.1f} {b['r2']:>8.3f}")
    for r in results:
        print(f"{r['model']:<20} {r['mae']:>8.1f} {r['rmse']:>8.1f} {r['r2']:>8.3f}")

# ── Save ────────────────────────────────────────────────────────────
neural_results_path = os.path.join(RESULTS_DIR, "model-a-neural.json")
with open(neural_results_path, "w") as f:
    json.dump({
        "description": "Model A neural variants for daily PM2.5 forecast, Lahore",
        "train_period": f"{train_df['date'].iloc[0].date()} to {train_df['date'].iloc[-1].date()}",
        "test_period": f"{test_df['date'].iloc[0].date()} to {test_df['date'].iloc[-1].date()}",
        "architecture": f"Window={WINDOW}, Hidden={HIDDEN}, Layers={N_LAYERS}, Dropout={DROPOUT}",
        "training": f"Adam lr={LR}, ReduceLROnPlateau patience=10, early stop patience=20, max {EPOCHS} epochs",
        "bootstrap": f"{N_BOOTSTRAP} resamples, 7-day blocks",
        "results": results,
    }, f, indent=2)

print(f"\nNeural results saved to {neural_results_path}")

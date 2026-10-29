"""
Build ERA5 + EPD daily feature table for Model A training.
RUN NOW in Command Prompt:
    K:
    cd K:\airlume
    .venv\Scripts\activate
    python scripts\build_feature_table.py

Fetches ERA5 daily weather from Open-Meteo for Lahore (2020-2025),
joins with EPD daily PM2.5 data, saves feature table.

Licence: ERA5 data via Open-Meteo (CC BY 4.0, Zippenfenig 2023).
Contains modified Copernicus Climate Change Service information.
"""

import pandas as pd
import requests
import time
import os
import sys

# ── Config ──────────────────────────────────────────────────────────
LAHORE_LAT = 31.5497
LAHORE_LON = 74.3436
EPD_DIR = os.path.join("data", "archive", "epd_daily", "epd_pdf")
OUT_PATH = os.path.join("data", "features", "lahore_daily_features.csv")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

# ── 1. Load EPD daily data ──────────────────────────────────────────
print("Loading EPD daily CSVs...")
frames = []
for year in range(2020, 2026):
    path = os.path.join(EPD_DIR, f"{year}.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        frames.append(df)
        print(f"  {year}: {len(df)} rows")
    else:
        print(f"  {year}: NOT FOUND")

epd = pd.concat(frames, ignore_index=True)
print(f"Total EPD rows: {len(epd)}")

# Filter to Lahore PM2.5 daily
lahore_pm25 = epd[(epd["city"] == "Lahore") & (epd["pollutant"] == "pm25")].copy()
lahore_pm25["date"] = pd.to_datetime(lahore_pm25["date"])
print(f"Lahore PM2.5 rows: {len(lahore_pm25)}")

# Average across stations per day (some days have multiple stations)
daily_aqi = (
    lahore_pm25
    .groupby("date")
    .agg(
        pm25_conc=("conc", "mean"),
        pm25_aqi=("aqi", "mean"),
        n_stations=("station_id", "nunique"),
    )
    .reset_index()
)
daily_aqi["pm25_conc"] = daily_aqi["pm25_conc"].round(1)
daily_aqi["pm25_aqi"] = daily_aqi["pm25_aqi"].round(0).astype(int)
print(f"Unique Lahore PM2.5 days: {len(daily_aqi)}")
print(f"Date range: {daily_aqi['date'].min().date()} to {daily_aqi['date'].max().date()}")

# ── 2. Fetch ERA5 daily weather from Open-Meteo ────────────────────
# Open-Meteo limits to ~1 year chunks, so fetch year by year
ERA5_VARS = [
    "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
    "relative_humidity_2m_max", "relative_humidity_2m_min", "relative_humidity_2m_mean",
    "wind_speed_10m_max", "wind_speed_10m_mean", "wind_direction_10m_dominant",
    "precipitation_sum", "rain_sum",
    "shortwave_radiation_sum",
    "et0_fao_evapotranspiration",
]

print("\nFetching ERA5 daily weather from Open-Meteo...")
weather_frames = []

for year in range(2020, 2026):
    start = f"{year}-01-01"
    # For 2025, only up to a safe date (ERA5 has ~5 day lag)
    if year == 2025:
        end = "2025-11-30"
    else:
        end = f"{year}-12-31"

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={LAHORE_LAT}&longitude={LAHORE_LON}"
        f"&start_date={start}&end_date={end}"
        f"&daily={','.join(ERA5_VARS)}"
        f"&timezone=Asia/Karachi"
    )

    print(f"  {year}...", end=" ", flush=True)
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        wdf = pd.DataFrame(data["daily"])
        wdf.rename(columns={"time": "date"}, inplace=True)
        wdf["date"] = pd.to_datetime(wdf["date"])
        weather_frames.append(wdf)
        print(f"{len(wdf)} days")
    except Exception as e:
        print(f"FAILED: {e}")

    time.sleep(1)  # polite rate limit

weather = pd.concat(weather_frames, ignore_index=True)
print(f"Total ERA5 days: {len(weather)}")

# ── 3. Add derived features ────────────────────────────────────────
print("\nAdding derived features...")
weather["temp_range"] = weather["temperature_2m_max"] - weather["temperature_2m_min"]
weather["day_of_year"] = weather["date"].dt.dayofyear
weather["month"] = weather["date"].dt.month
weather["weekday"] = weather["date"].dt.weekday  # 0=Mon

# ── 4. Join EPD + ERA5 ─────────────────────────────────────────────
print("Joining EPD AQI with ERA5 weather...")
features = pd.merge(daily_aqi, weather, on="date", how="inner")
print(f"Joined rows: {len(features)} (days with both AQI and weather)")

# Add lag features (previous day PM2.5)
features = features.sort_values("date").reset_index(drop=True)
features["pm25_conc_lag1"] = features["pm25_conc"].shift(1)
features["pm25_aqi_lag1"] = features["pm25_aqi"].shift(1)
features["pm25_conc_lag2"] = features["pm25_conc"].shift(2)
features["pm25_conc_lag3"] = features["pm25_conc"].shift(3)
# Rolling 7-day mean
features["pm25_conc_roll7"] = features["pm25_conc"].rolling(7, min_periods=3).mean().round(1)

# Drop first few rows without lags
features_clean = features.dropna(subset=["pm25_conc_lag3"]).copy()
print(f"After dropping lag NaNs: {len(features_clean)} rows")

# ── 5. Save ─────────────────────────────────────────────────────────
features_clean.to_csv(OUT_PATH, index=False)
print(f"\nSaved to {OUT_PATH}")
print(f"Columns ({len(features_clean.columns)}):")
for c in features_clean.columns:
    print(f"  {c}: {features_clean[c].dtype}, {features_clean[c].notna().sum()} non-null")

# Quick stats
print(f"\nTarget stats (pm25_conc):")
print(features_clean["pm25_conc"].describe().round(1))
print(f"\nMonthly mean PM2.5:")
print(features_clean.groupby("month")["pm25_conc"].mean().round(1))

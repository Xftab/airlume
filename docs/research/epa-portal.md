# Punjab EPA portal (aqi.punjab.gov.pk) — technical findings, 13 Oct 2026

## Architecture
- Laravel + Vite, **server-rendered** (CSRF meta tag, `/build/manifest.json`, no `/_next/`).
- No public JSON API on the main host. Probed and 404: `/api`, `/api/stations`, `/api/cities`, `/api/lahore`, `/api/aqi`, `/api/data`, `/api/v1/*`, `/city/lahore`, `/faisalabad`.
- Public routes: `/`, `/lahore`, `/health-advisory`, `/support`, `/robots.txt` (allow all), `/sitemap.xml`, `/build/*`.
- `/lahore/analysis` redirects to a login page (authenticated).
- **`https://api.aqi.punjab.gov.pk` exists** (robots.txt disallows crawling). Almost certainly the backend of the mobile app (Android `com.moonshotsmc.aqipunjab`, Expo/React Native, vendor MoonshotTech SMC). Paths unknown. Finding them: unzip the APK and grep `assets/index.android.bundle` for `api.aqi.punjab`. Not done; the permission email asks for the documented route instead.
- `aqipunjab.com` redirects to the portal.

## What `/lahore` gives
- Table: Rank, Station, AQI, Level, PM2.5, PM10, CO, SO2, NO2, O3 (no units shown; consistent with µg/m³, CO in mg/m³). Missing values appear as `--`.
- "Last updated: 10:00 AM, Oct 13" header; per-row "Oct 13, 7:00 AM" style timestamps; local time (PKT), no timezone, no seconds.
- Also: 24-hour hourly AQI forecast, 7-day trend, weather, Punjab contour map.
- Hourly cadence; single stations can lag an hour; Gulberg III was missing in one snapshot ("11 of 10 stations" header bug).
- The plain URL is served from a cache; a throwaway query parameter returns fresh data. `collectors/epa.py` adds one.
- The Lahore page embeds a JSON block `<script id="lahore-analysis-data">` (fields: bands, hourly, stations, weather, flags, peaks, forecast) read by `lahore-analysis-*.js`. Whether it is on the public page or only the authenticated one is **unverified**; `scripts/epa_dry_run.py` saves the raw HTML so this can be checked on the laptop.

## Home page
- Ranks **36 districts** (not 28 as first planned): Okara, Nankana Sahib, Muzaffargarh, Rajanpur, Chiniot, Jhang, Vehari, Khanewal, Sahiwal, Faisalabad, Gujranwala, Pakpattan, Multan, Lahore, Sheikhupura, Attock, DG Khan, Kot Addu, Bahawalpur, Rahim Yar Khan, Kasur, Rawalpindi, Bhakkar, Sargodha, Narowal, Hafizabad, Murree, Khushab, Gujrat, Jhelum, Sialkot, Wazirabad, Mandi Bahauddin, Chakwal, Mianwali, Talagang. The count has grown over time (33 in Sept 2025).
- EPD order of 1 Oct 2025: 41 AQMS in 17 districts.

## AQI scale (resolves weakness W1)
- Portal labels: Good 0-50 · Satisfactory 51-100 · Moderate 101-150 · Unhealthy for sensitive groups 151-200 · Unhealthy 201-300 · Very unhealthy 301-400 · Hazardous 401-500. **Not** the US category names (shifted one band; 301-500 split).
- Numbers: station AQIs on 13 Oct 07:00 match the **US EPA 2012 PM2.5 breakpoints** (0-12 / 12.1-35.4 / 35.5-55.4 / 55.5-150.4 / 150.5-250.4 / 250.5-350.4 / 350.5-500.4) with max-of-sub-indices, within 0-3 points (e.g. PM2.5 310.8 → 361, portal 361). The 2024 US revision would give >400 for that value, so it is the old table. `airlume/aqi.py` implements both; tests pin the portal values.
- EPD order says AQI uses 8-hourly averages and is published 9am/5pm/1am; the live portal updates hourly. The 0-3 point residuals are consistent with the index being computed on an average while the table shows the hourly concentration.
- No EPD document publishes the breakpoints themselves.

## Station coordinates
- The portal publishes none. IQAir station pages embed a map link with lat/lon for 9 of 11 Lahore stations (contributor: Punjab EPA). Multan Road and Kahna Nau: only neighbourhood centroids. Punjab University's point sits ~4 km SW of the main campus; marked medium confidence. Full table in `data/registry/stations.csv`; the permission email asks the EPA to confirm.
- WAQI mirrors the network as "Pakistan Punjab Air Quality Network" (42 stations) with station ids (in the registry); WAQI JSON would include `city.geo` but is display-only for us.

## Other cities
- Islamabad, Karachi, Peshawar: The Urban Unit's AirGradient sensors, carried by OpenAQ (licensed), WAQI and IQAir. Coordinates in `registry-notes.md`.
- Quetta: Urban Unit sensors on WAQI/IQAir only → display-only.
- US Embassy/Consulate monitors: dormant since 4 Mar 2025 (State Dept funding); WAQI Islamabad shows a 16 Feb 2026 update, so a partial restart is possible. Check OpenAQ in Phase 1.

## Standards
- NEQS/PEQS ambient: PM2.5 annual 15, 24-h 35 µg/m³; PM10 120 / 150; a 2023 PEQS draft proposes 30 / 55 (gazetting unconfirmed).
- US EPA breakpoints: Technical Assistance Document EPA-454/B-24-002 (Table 6).

## Live dry run, 13 Oct 2026 14:00 PKT (first real fetch from the laptop)
- `/lahore`: 10 station rows (Gulberg III absent again - it seems to be missing from this table routinely). Timestamp parsed correctly (09:00 UTC = 14:00 PKT).
- `/`: 35 of 36 districts matched the registry; one name differs (the collector now prints it).
- Open-Meteo: 34 hourly rows for Lahore.
- **The portal AQI is not the AQI of the hourly PM2.5 shown.** Examples: Egerton Road PM2.5 35.2 -> US-2012 formula 100, portal 143; Punjab University 33.1 -> 95 vs 133; Wagha 17.7/84.4 -> 65 vs 103; GT Road 24.2 -> 76 vs 73. The morning snapshot (7:00) matched within 3 points, the afternoon one does not. Two candidate explanations, both testable once hourly data accumulates: (a) the AQI is computed on an **8-hour mean** (EPD order of 1 Oct 2025) while the table shows the latest hour - midday PM2.5 falls fast, so the 8-h mean stays higher; (b) NO2 or O3 dominates at some stations. Readings now store CO, SO2, NO2, O3 as well, so both can be checked. This is the core of the W1 harmonisation study (1.7).
- EPD archive: page 1 (oldest) holds scanned **monthly** summaries from 2010-2015 for one station (Town Hall), image-only. Not worth OCR. Daily typed reports are on the newest pages; `epd_fetch_sample.py last` fetches from there.

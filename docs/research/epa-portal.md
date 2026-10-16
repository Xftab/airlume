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

> **Resolved 16 Oct 2026.** Neither table above is the one the portal uses. It uses its own, anchored on Pakistan's NEQS limits with gases in µg/m³; reproduced 99.7% exactly on 304 stored rows. The 13 Oct readings matched the US table because all four sat where the two converge. See `docs/research/w1-harmonisation.md`.

> **Corrected 15 Oct 2026** (`docs/research/w1-harmonisation.md`). Both bullets above are too optimistic. The 2012 table is confirmed as the right one, but "within 0-3 points" came from four readings chosen because both concentration and AQI were visible; over 90 stored station-rows the agreement is mean 5.4, median 4, max 24, exact in only 9% of rows, with a systematic +4 point bias. The 8-hour-average explanation is **wrong**: an 8-hour trailing mean is worse at all ten stations (24.3 against 5.4). The EPD order's 8-hour averaging applies to the printed bulletins, not the live table.
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
- **The portal AQI is not the AQI of the hourly PM2.5 shown.** Examples: Egerton Road PM2.5 35.2 -> US-2012 formula 100, portal 143; Punjab University 33.1 -> 95 vs 133; Wagha 17.7/84.4 -> 65 vs 103; GT Road 24.2 -> 76 vs 73. The morning snapshot (7:00) matched within 3 points, the afternoon one does not. Two candidate explanations, both testable once hourly data accumulates: (a) the AQI is computed on an **8-hour mean** (EPD order of 1 Oct 2025) while the table shows the latest hour - midday PM2.5 falls fast, so the 8-h mean stays higher; (b) NO2 or O3 dominates at some stations. Readings now store CO, SO2, NO2, O3 as well, so both can be checked. This is the core of the W1 harmonisation study (1.7). **Answered 15 Oct: (b) was the cause** - the gas sub-indices closed the afternoon gap, and (a) is ruled out, the 8-hour mean being worse at every station. A +4 point residual remains open.
- EPD archive: page 1 (oldest) holds scanned **monthly** summaries from 2010-2015 for one station (Town Hall), image-only. Not worth OCR. Daily typed reports are on the newest pages; `epd_fetch_sample.py last` fetches from there.

### 15:00 PKT follow-up: ozone explains the afternoon gap
With all six pollutants captured, the stations whose portal AQI exceeded the PM2.5 value are exactly the ones with high O3 (Egerton 186, Punjab University 172, Wagha 133 ug/m3). Adding the US EPA gas sub-indices (ug/m3 -> ppb at 25 C) makes ozone the dominant pollutant at those stations, as the portal implies. Magnitudes still differ by 10-30 points at the ozone stations and 1-7 elsewhere, the pattern expected if the portal averages 8 hours while the table shows the latest hour (ozone rises through the afternoon). `scripts/w1_check.py` tests 1-h vs 8-h vs 24-h windows once a day of hourly readings exists. The two unmatched "district" names were "Solar Radiation" and "Last" (page furniture, now ignored); the registry's 36th district was simply not listed at 14:00.

## EPD bulletin archive, sampled 13 Oct 2026 (pages 1, 30, 60, 85, 104 of 104)
- Ordering: page 1 = newest. **The archive ends on 2 December 2025**; nothing for 2026 (publication moved to the portal). Oldest daily report: 2 January 2018. About 2,300 PDFs; roughly 1 GB.
- Three links on every page (2010, 2011, 2014-15 scanned monthly tables) are sidebar links, not reports.
- Four layouts: **A** (Nov-Dec 2025, two pages: Urdu district ranking + English "Rank / Location / AQI" table of **13 Lahore AQMS** plus transboundary sites, Lahore average printed), **B** (2022-2024, 3-4 stations with pollutant, PEQS, concentration, AQI; some CO rows), **C** (2018-2020, concentration tables for the old network), plus scanned pre-2018 material.
- The bulletins state the method: *"AQI calculations is performed for last 24 hours ... using PM2.5 data. The data is fetched from AQI Punjab dashboard."* So the official daily figure is the **24-hour PM2.5 mean** on EPA Punjab breakpoints, and values above 500 are printed uncapped (Egerton Road 559 on 1 Dec 2025).
- Lahore's 2025 station names differ from today's portal: UET (= GT Road), Kahna Nau, Town Hall, Shahdara, PKLI, LWMC, FMDRC, PU 1 (= Punjab University), PU 2, Safari Park, EPA HQ, Egerton Road, Wahga Boarder. Five map onto today's eleven; the rest are kept under their bulletin labels. Gulberg III, Multan Road, Barki Road and DHA Phase 6 do not appear in the bulletins, so their history starts with our own collection.
- Trial back-fill (pages 1-5, 99 reports) revealed more layouts. Final inventory: **A** (Nov-Dec 2025, Lahore rank table, 13 stations + transboundary Raja Jang (Kasur), Lathepur and BHU Jandiala (Sheikhupura)); **D** (Oct 2025 "AQI Analysis", Lahore stations *and* an 18-district English table with dominant pollutant - the best layout); **E** (Aug-Sep 2025 map-style; only the Lahore average is recoverable from the text); **B** (2022-2024); **C** (2018-2020, skipped); and **scanned CamScanner images** (Nov 2024 at least). Style A's "Updated Time" line carries the wrong year on some days; the parser takes the date from the calculation note instead.
- `pipeline/epd_parse.py` parses A, B, D and E (fixture tests for each); C and scanned files are counted and skipped.
- **Gap:** no official per-station data exists for 3 Dec 2025 - 12 Oct 2026 from any permitted source. Options: leave the gap and say so; or fill city-level only from Open-Meteo CAMS (archive from Aug 2022), clearly labelled "modelled". Decision pending.

### Full back-fill, 13 Oct 2026 evening (104 pages, ~2,100 reports)
First full pass: 2,121 daily rows for 2022-2025 (B 857, A 34, D 2, E 102, C 458 skipped, scanned 144, unknown 389, 71 genuine 404s). The 389 unknown files were three further variants, now handled: (i) Oct 2024 - Feb 2025 map bulletins with a different date format (Lahore average only); (ii) Feb 2022 "various cities of Punjab" tables with inline "(PM2.5)" and district rows (Rawalpindi, Rahim Yar Khan); (iii) **2020-2021 bulletins on the "Smog Policy 2017" scale** (0-100 Good, 100-200 Satisfactory, 200-300 Moderately polluted, 301-400 Poor, 401-500 Very poor, 500+ Severe) - a different index altogether, so those AQI values are stored with `style='B17'` and are *not* comparable with later years; their PM2.5 concentrations are kept so the current-scale AQI can be recomputed. One 2021 row labels a CO measurement (PEQS 5 mg/m3) as PM2.5; the parser goes by the PEQS value. Old station names: Town Hall, Township (C2 and D1 sectors), Jail Road Met Station, Mobile AQMS, EPA HQ / National Hockey Stadium, CEES Punjab University.
**Implication for the report:** the official Lahore daily series changes scale in early 2022. Any multi-year chart must either recompute from concentrations or draw the boundary.

## 14 Oct: the Lahore page carries more than the table
A saved copy of `/lahore` (494 KB) shows, besides the station table: (a) a **7-day hourly city-level AQI trend** as `<span data-date data-hour data-aqi>` elements - 168 city-hours per fetch, so one collection round back-fills the previous week at city level; (b) the **24-hour forecast** as `<article><time datetime="ISO+05:00">` + "AQI nnn" - clean to parse; (c) the health-advisory bands as JSON (`window.aqiRanges`, colours #248606/#44E508/#E9CF3C/...). The per-row "Updated" column is formatted `Oct 14, 9:00 AM` (date first), unlike the header. Both extras are now collected hourly; forecasts (EPA and CAMS) go into a `forecasts` table and the app shows a running scorecard once actuals arrive (contribution C5 infrastructure).

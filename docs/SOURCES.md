# Data sources and licences

| Source | What we take | Terms | How we use it | Attribution text |
|---|---|---|---|---|
| Punjab EPA, aqi.punjab.gov.pk | Hourly station AQI + PM2.5/PM10 (Lahore), district AQI | No licence published; robots.txt allows; permission requested (docs/emails) | Stored hourly; primary Lahore source | "Source: Environmental Protection Agency, Punjab" |
| Punjab EPD PDF archive, epd.punjab.gov.pk | Daily AQI reports back to 2007 | Public government documents | Back-fill (Phase 1.5) | "Source: EPD Punjab daily reports" |
| Open-Meteo Air Quality API | CAMS global PM2.5/PM10/US AQI, ~45 km | CC BY 4.0, 10,000 calls/day | Validation (C4) only; never shown as a station value | "Weather/air data by Open-Meteo.com (CC BY 4.0)" |
| OpenAQ v3 | Urban Unit AirGradient sensors (Islamabad, Karachi, Peshawar); US DoS monitors | Free key; licence per station (checked at discovery) | Stored for licensed stations only | per-station licence text |
| WAQI (aqicn.org) | Live AQI for display | Free token; **no archiving or analysis** | Display only; `collectors/waqi_display.py`; never written to data/ | "Live value from the World Air Quality Index project" |
| IQAir station pages | Station coordinates (one-time lookup) | Website content | Registry only, marked unverified | noted in registry-notes.md |
| Wikipedia / GeoNames | City centroids | CC BY-SA / CC BY | Registry only | — |
| US EPA Technical Assistance Document | AQI breakpoints | Public domain | `airlume/aqi.py` | — |
| WorldPop | Pakistan 1 km population grid, 2025 (`pak_pop_2025_UC_1km_R2024B_UA_v1.tif`) | **CC BY 4.0** | Cut to Lahore once by `scripts/extract_population.py`; drives population coverage (2.6) and station placement (4.5). Raw raster git-ignored; the 72 KB derived CSV is committed | "Population data: WorldPop (www.worldpop.org), CC BY 4.0" |
| OpenStreetMap, via Geofabrik Pakistan extract | Water, aerodrome and military polygons; major roads; industrial land use | **ODbL**, attribution required | Cut to Lahore once by `scripts/extract_landuse.py`; excludes unsiteable cells and scores source proximity (4.5). Raw `.osm.pbf` git-ignored; the 103 KB derived CSV is committed | "Land use: © OpenStreetMap contributors, ODbL" |

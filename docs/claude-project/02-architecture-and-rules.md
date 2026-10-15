# Airlume — architecture, code map, rules

## Flow
question → `nl/router.py` (Groq, strict JSON schema; cache; fallback to `nl/stub_router.py`)
→ `nl/schema.py` ViewIntent (Pydantic validation; allow-listed enums)
→ `nl/resolve.py` (Asia/Karachi time windows, city/station matching, nearest-station rule)
→ `pipeline/store.py` (parameterised DuckDB SQL only; metrics/aggregations allow-listed)
→ `nl/answer.py` (sentence written by code from numbers)
→ `viz/` (deck.gl layers, named cameras) → `app/streamlit_app.py`

## Data
- `data/archive/<table>/<source>/<YYYY-MM>.csv` — data of record, append-only, deduped,
  committed to GitHub. Tables: readings, city_hourly, epd_daily, forecasts.
- App builds an in-memory DuckDB from the archive each hour (no file locks).
- Collector: `scripts/collect_hourly.py`, run by `.github/workflows/collect.yml`
  (GitHub schedule `17,47 * * * *` plus a cron-job.org trigger every hour at :00, because
  GitHub's scheduler skips most slots on free repos).
- AQI: US EPA 2012 breakpoints under Punjab's labels; six pollutants; gas unit conversion.
- Registry: `data/registry/stations.csv`, `cities.csv` (coordinates with confidence levels).

## Stack
Python 3.13, Streamlit 1.65, pydeck 0.9, DuckDB 1.5, pandas 3, Pydantic 2, altair,
requests/bs4. Pinned in `requirements.txt`. 92 tests (`K:\airlume\test`).

## Design rules (never break)
1. The model never writes SQL or code; it fills the typed form only.
2. Answer sentences come from code, not the model.
3. WAQI data is display-only; never stored, never in `data/`.
4. Secrets only in `.env` via `config.load_settings()`; `check_secrets.py` masks them.
5. All SQL in `store.py`, parameterised, allow-listed names.
6. Never show invented values for unmonitored places; missing stations are counted and greyed.
7. Keep docs current: plan.md + PDF, HISTORY.md, STATUS.md after every change.

## Evaluation facts (benchmark v0, dev set, 90 items)
stub 45.6% (CI 36–56) · gpt-oss-120b v3 88.9% (CI 82–96) · gpt-oss-20b v3 88.9% (CI 82–94).
Prompt frozen at v3 on 15 Oct. Reported number will come from frozen v1.
Forecast skill (34 hours, early): EPA bias +28 AQI, CAMS bias −17; both skill ≈ 0.1 vs
last value.

## Known limits / open items
Groq free tier: 8k tokens/min, 200k tokens/day per model (rolling); one benchmark run per
model per day. Gulberg III station routinely missing. Dec 2025–Oct 2026 has no official
daily data. 41 EPD bulletins unparsed. W1 averaging window unresolved (needs 8+ hours of
station data). Repo private until security checklist S1–S15 passes.

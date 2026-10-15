# Airlume — status and next steps (update this file after each session)

Last updated: 15 Oct 2026, 15:10 PKT

## Done this week (13–15 Oct)
- Hourly coverage verified (10 rows/hour, consecutive since 05:00 UTC 15 Oct); W1 measured for the
  first time: 1-hour window wins, 8-hour guess wrong, +4 point bias open; `aqi.py` NaN crash fixed.
- Phase 1.6 data quality built: flags + per-station uptime + app tab (114 tests). Found that
  Gulberg III has never reported, and that two portal widgets overwrite each other in `city_hourly`.
- Found the portal's embedded JSON (`wire:snapshot`): it holds 11 stations while the rendered
  table shows 10, which is why Gulberg III was missing. Collector now reads it. It also publishes
  official station coordinates (fixed a 6.1 km error on Multan Road) and per-station wind.
- Phase 0 complete; live portal data in the app; cloud hourly collection; EPD history 2020–2025.
- Router live on Groq; prompt v1→v3 from failure analysis; benchmark v0 scored; follow-ups in app.
- Security pass 1 (`docs/security/audit-2026-10-15.md`): pip-audit clean, bandit reviewed,
  rate limits, escaping, tracebacks hidden.
- Forecast scorecard with persistence baselines (4.1); collector bug (city trend dropped) fixed.
- Collector reliability: cron-job.org trigger installed (token expires 13 Jan 2027).
- Benchmark v1 materials: classmate question sheet (PDF) and second-annotator guide.

## Next (in order)
1. Re-run `python scripts\w1_check.py` once 24 consecutive hours exist (earliest 16 Oct): test the
   24-hour window and the sub-hourly hypothesis for the +4 bias.
2. Once a day of rows carries `portal_dominant`, run the W1 dominance test properly: compare the
   portal's own dominant pollutant against ours per row, instead of the weak "portal exceeds our
   maximum sub-index" proxy. The snapshot columns were added to the archive on 15 Oct for this.
3. Hand the classmate sheet to 3 classmates; collect 60 questions; second annotation (Kiran
   or Tehreem); freeze benchmark v1; score it once, report with CIs.
4. Rotate the GitHub fine-grained token (first value was exposed) and the Groq key.
5. Send the EPA permission email (`docs/emails/punjab-epa-permission.md`).
6. Phase 4.2 forecast model (LightGBM) once weeks of history exist. *(1.6, 2.3, 2.4, 4.5-on-area and 4.6 all done 15 Oct.)*
7. CAMS-vs-ground validation (C4) once two weeks of readings exist.
8. Go public: re-run security checklist, make repo public, deploy to Streamlit Cloud.
9. Report and demo (Phase 7).

## Needs Aftab to fetch (blocks finishing 2.6 and 4.5)
- A WorldPop or GHSL population raster for Punjab, and an OpenStreetMap extract for Lahore. The
  build environment cannot download either. Without them, coverage figures are area shares only,
  and the five proposed station sites ignore population, rivers, the airport and restricted land.

## Blockers / waiting on time
- Groq daily budgets reset ~24 h after use (rolling).
- Forecast skill and W1 need days of data.

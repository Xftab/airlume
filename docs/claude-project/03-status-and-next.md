# Airlume — status and next steps (update this file after each session)

Last updated: 16 Oct 2026, 12:00 PKT

## Done this week (13–16 Oct)
- 4.3 CAMS validation built; preliminary on 30 h: CAMS PM2.5 ~20 low (at night), PM10 not tracked.
- W1 solved: portal uses its own NEQS-anchored table, gases in ug/m3; 99.7% exact on 304 rows.
- Forecast questions now answered from the forecast (they were answered with current readings); 4.6 met.
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
1. *(W1 solved 16 Oct - portal's own NEQS-anchored table, 99.7% exact on 304 rows.)* Re-run
   `python scripts\w1_check.py` once November smog pushes PM2.5 above 350 to confirm the top band.
2. 4.3 final run: `python scripts\cams_validation.py` on two weeks (~29 Oct); update
   `docs/research/cams-validation.md`, retest the 1-2 h lag. (Built and run preliminary 16 Oct.)
3. Hand the classmate sheet to 3 classmates; collect 60 questions; second annotation (Kiran
   or Tehreem); freeze benchmark v1; score it once, report with CIs.
4. Rotate the GitHub fine-grained token (first value was exposed) and the Groq key.
5. Send the EPA permission email (`docs/emails/punjab-epa-permission.md`).
6. Phase 4.2 forecast model (LightGBM) once weeks of history exist. *(1.6, 2.3, 2.4, 4.5-on-area and 4.6 all done 15 Oct.)*
7. Go public: re-run security checklist, make repo public, deploy to Streamlit Cloud.
8. Report and demo (Phase 7).

## Needs Aftab to fetch
- Nothing. (WorldPop and OSM files fetched 15 Oct; cut into committed CSVs.)

## Blockers / waiting on time
- Groq daily budgets reset ~24 h after use (rolling).
- Forecast skill and W1 need days of data.

# Airlume — status and next steps (update this file after each session)

Last updated: 29 Oct 2026, 08:00 PKT. Submission target: 28 November 2026 (4 weeks).

## Done
- Phase 0 complete; Phases 1 and 2 largely complete; Phase 3 at prompt v3, benchmark v0, follow-ups in app; Phase 4 scorecards, population coverage, placement, preliminary CAMS validation.
- W1 (AQI harmonisation) solved 16 Oct, confirmed at scale 24 Oct (2206 station-hours over 210 hours; MAE 1.7; median 0.0). Bootstrap CI added 29 Oct: MAE 3.74 [95% CI 2.01, 5.78] over 2217 rows; below the portal 500 cap, MAE 0.31 (essentially exact).
- Security pass 1 passed 15 Oct (S1-S15: pip-audit clean, bandit reviewed, rate limits, escaping, tracebacks hidden).
- Benchmark v1 materials ready: classmate question sheet and second-annotator guide.
- Collector reliability token on cron-job.org (expires 13 Jan 2027).
- 24 Oct: local repo synced with GitHub (123 commits pulled). Working tree clean.
- 28 Oct: 24 Oct records brought into the repo (HISTORY, STATUS, plan 1.7, W1 research doc, plan PDF).
- 28 Oct: EPA collector outage diagnosed. Cause: GitHub Actions runner cannot reach the Punjab EPA portal since 25 Oct 11:00Z (silent per-source failure; runs still green because the commit step treats no-change as success). Portal and code both verified healthy from the laptop.
- 28 Oct: 99-point W1 outlier explained. Top-band saturation: portal saturates at AQI 500 while our extrapolated top band computes 401-1823. All 91 portal-500 rows from 16-28 Oct smog period. Below the cap the formula is essentially exact. Trace closed.
- 28 Oct: Hybrid collector architecture adopted. Laptop runs collect_push.bat hourly via Windows Task Scheduler for Punjab EPA; GitHub Actions keeps Open-Meteo CAMS. Different archive files, no CSV conflict.
- 28 Oct: Timeline compressed from ten weeks to a four-week sprint (28 Oct to 28 Nov 2026) in plan.md and the PDF. Nothing in the ten-week plan was cut; earlier phases are already met.
- 28 Oct: R&D extension CONFIRMED in scope. Neural network component, Materials and Methods framing, priority score, graded response, scenario calculator are all firm deliverables.
- 29 Oct: CAMS validation final run complete (211 paired city-mean hours, 13-28 Oct). PM2.5 MAD 49.8, bias -47.7, r 0.65. PM10 effectively untracked (bias -179). CAMS leads EPA by 2-3 hours. Full results in docs/research/cams-validation.md.
- 29 Oct: W1 bootstrap CI complete. Moving-block bootstrap (6h blocks, 5000 resamples). Full results in docs/research/w1-harmonisation.md.
- 29 Oct: Materials draft v1 written: licence terms filled (Open-Meteo CC BY 4.0, Copernicus licence), CAMS date ranges, W1 bootstrap CIs, CAMS validation summary, top-band trace. See claude/07-materials-draft.md.
- 29 Oct: plan.md revision 5 — R&D conditionals removed from sprint table, week 1 progress marked. HISTORY.md and STATUS.md updated.

## R&D extension (confirmed 28 Oct, see 05-rd-extension-plan.md and 07-materials-draft.md)
- Supervisor confirmed R&D framing: Materials and Methods, datasets, results, a neural network component, and insights (priority score, graded response, scenario calculator).
- CONFIRMED. Scope amendment: "causes of pollution" out-of-scope line in 01-goal-and-phases.md amended for intervention guidance only.
- Three open questions from section 7 of file 05 still need supervisor answers (ERA5 vs EPD preference, neural architecture depth, scenario calculator detail level). These do not block week 1 or early week 2 work.

## Known gaps
- Punjab EPA station-level rows for 25 Oct 11:00Z through 28 Oct are a permanent gap (the portal only exposes current readings). City-level is partially recoverable from the portal's own 7-day trend.
- One hour of local archive rows missing: 2026-10-17T03:00:00Z. Present on GitHub. Local copy in K:\airlume_stash_backup; not merged.
- About 4.5% of station-hours missing in the pre-25 Oct sample (single stations lagging in individual rounds).

## Environment rules (see 06-environment-rules.md)
- Nothing on drive C. Everything on K. Never drop a stash or force git before data is safe.

## Next (in order)

### Week 1 (28 Oct - 3 Nov) — Data recovery and foundation
1. ~~Register the laptop collector~~ (done 28 Oct)
2. ~~Catch up and verify~~ (done 28 Oct)
3. Meet supervisor; discuss the three open R&D questions in file 05.
4. Rotate the GitHub fine-grained token (first value was exposed) and the Groq key. **User does this.**
5. Send the EPA permission email (docs/emails/punjab-epa-permission.md). **User does this.**
6. ~~CAMS validation final run~~ (done 29 Oct — 211 hours, results in docs/research/cams-validation.md)
7. ~~Fill Materials draft placeholders and W1 bootstrap CI~~ (done 29 Oct — claude/07-materials-draft.md)
8. Hand the classmate sheet to 3 classmates. **User does this.**

### Week 2 (4 - 10 Nov) — Models, benchmark, and R&D start
9. Build ERA5 + EPD daily feature table.
10. Model A baselines (persistence + LightGBM); Model C zero-shot; Model B CAMS correction.
11. Neural variant on daily features; fill out 07-materials-draft.md with architecture, training, and results.
12. Second annotation on benchmark v0 by Kiran or Tehreem.
13. Collect classmate questions (target 60).

### Week 3 (11 - 17 Nov) — Freeze, insights, deploy
14. Freeze benchmark v1; score once with CIs; write results.
15. Phase 4.2 forecast model fit on real data; W1 top-band refit as above-350 rows accumulate.
16. Security pass 2 (S1-S15); public deploy to Streamlit Cloud.
17. Priority score module, graded-response module, scenario calculator.

### Week 4 (18 - 24 Nov) — Report and demo
18. Final report (plan.md spine, proposal.md framing, HISTORY.md log, weaknesses section with W1-W15 verdicts). Include R&D Materials and Methods section.
19. Demo slides; screenshot capture; demo rehearsal.

### Submission (25 - 28 Nov)
20. Final polish; submission; viva prep.

## Blockers / waiting on time
- Groq daily budgets reset about 24 h after use (rolling).
- Hourly archive about 16 days old now; hourly deep models remain undertrained but accumulating.
- Laptop-dependent EPA collection means gaps when the laptop is off; shown in the app, not filled silently.

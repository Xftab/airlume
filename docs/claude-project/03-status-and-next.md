# Airlume — status and next steps (update this file after each session)

Last updated: 28 Oct 2026, 21:10 PKT. Submission target: 28 November 2026 (4 weeks).

## Done
- Phase 0 complete; Phases 1 and 2 largely complete; Phase 3 at prompt v3, benchmark v0, follow-ups in app; Phase 4 scorecards, population coverage, placement, preliminary CAMS validation.
- W1 (AQI harmonisation) solved 16 Oct, confirmed at scale 24 Oct (2206 station-hours over 210 hours; MAE 1.7; median 0.0).
- Security pass 1 passed 15 Oct (S1-S15: pip-audit clean, bandit reviewed, rate limits, escaping, tracebacks hidden).
- Benchmark v1 materials ready: classmate question sheet and second-annotator guide.
- Collector reliability token on cron-job.org (expires 13 Jan 2027).
- 24 Oct: local repo synced with GitHub (123 commits pulled). Working tree clean.
- 28 Oct: 24 Oct records brought into the repo (HISTORY, STATUS, plan 1.7, W1 research doc, plan PDF).
- 28 Oct: EPA collector outage diagnosed. Cause: GitHub Actions runner cannot reach the Punjab EPA portal since 25 Oct 11:00Z (silent per-source failure; runs still green because the commit step treats no-change as success). Portal and code both verified healthy from the laptop.
- 28 Oct: 99-point W1 outlier explained. The five largest at-scale errors are 22-23 Oct smog peaks where the portal saturates at AQI 500 (PM2.5 above 350, PM10 above 540) while our extrapolated top band computes 401-404. The top band needs refitting as November data accumulates; the trace open item is closed.
- 28 Oct: Hybrid collector architecture adopted. Laptop runs collect_push.bat hourly via Windows Task Scheduler for Punjab EPA; GitHub Actions keeps Open-Meteo CAMS. Different archive files, no CSV conflict.
- 28 Oct: Timeline compressed from ten weeks to a four-week sprint (28 Oct to 28 Nov 2026) in plan.md and the PDF. Nothing in the ten-week plan was cut; earlier phases are already met.

## R&D extension (proposed 24 Oct, see 05-rd-extension-plan.md and 07-materials-draft.md)
- Supervisor wants R&D framing: Materials and Methods, datasets, results, a neural network component, and insights (priority score, graded response, scenario calculator).
- PROPOSED, waiting on supervisor answers (section 7 of file 05).
- Scope amendment needed: "causes of pollution" out-of-scope line in 01-goal-and-phases.md to be amended for intervention guidance only. Record in plan.md, HISTORY.md, STATUS.md after supervisor confirms.
- The four-week plan has R&D as a conditional week-2 and week-3 branch; it completes with or without supervisor approval.

## Known gaps
- Punjab EPA station-level rows for 25 Oct 11:00Z through 28 Oct are a permanent gap (the portal only exposes current readings). City-level is partially recoverable from the portal's own 7-day trend.
- One hour of local archive rows missing: 2026-10-17T03:00:00Z. Present on GitHub. Local copy in K:\airlume_stash_backup; not merged.
- About 4.5% of station-hours missing in the pre-25 Oct sample (single stations lagging in individual rounds).

## Environment rules (see 06-environment-rules.md)
- Nothing on drive C. Everything on K. Never drop a stash or force git before data is safe.

## Next (in order)

### Week 1 (28 Oct - 3 Nov) — Data recovery and foundation
1. **Register the laptop collector:** run `K:\airlume\schedule.bat` once from Command Prompt so Windows Task Scheduler runs `collect_push.bat` every hour.
2. **Catch up and verify:** run `K:\airlume\collect_push.bat` once by hand to confirm it fetches, commits and pushes successfully.
3. Meet supervisor; confirm the three R&D questions in file 05.
4. Rotate the GitHub fine-grained token (first value was exposed) and the Groq key.
5. Send the EPA permission email (docs/emails/punjab-epa-permission.md).
6. CAMS validation final run (~29 Oct, two weeks of data available).
7. Fill the placeholders in the Materials draft (licences, ERA5 and CAMS ranges); add a moving-block bootstrap CI to the W1 table.
8. Hand the classmate sheet to 3 classmates.

### Week 2 (4 - 10 Nov) — Models and benchmark
9. Build ERA5 + EPD daily feature table.
10. Model A baselines (persistence + LightGBM); Model C zero-shot; Model B CAMS correction.
11. **IF R&D approved:** neural variant on daily features; fill out 07-materials-draft.md.
12. Second annotation on benchmark v0 by Kiran or Tehreem.
13. Collect classmate questions (target 60).

### Week 3 (11 - 17 Nov) — Freeze, insights, deploy
14. Freeze benchmark v1; score once with CIs; write results.
15. Phase 4.2 forecast model fit on real data; W1 top-band refit as above-350 rows accumulate.
16. Security pass 2 (S1-S15); public deploy to Streamlit Cloud.
17. **IF R&D approved:** priority score, graded-response module, scenario calculator.

### Week 4 (18 - 24 Nov) — Report and demo
18. Final report (plan.md spine, proposal.md framing, HISTORY.md log, weaknesses section with W1-W15 verdicts).
19. Demo slides; screenshot capture; demo rehearsal.

### Submission (25 - 28 Nov)
20. Final polish; submission; viva prep.

## Blockers / waiting on time
- Groq daily budgets reset about 24 h after use (rolling).
- Hourly archive about 11 days old; hourly deep models remain undertrained.
- R&D extension waits on supervisor confirmation.
- Laptop-dependent EPA collection means gaps when the laptop is off; shown in the app, not filled silently.

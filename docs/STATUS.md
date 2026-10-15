# Status

_Last updated: 13 October 2026_

## Where we are
**Phase 0: Foundations and Access (week 1, 13–19 Oct)** — day one done. The code skeleton, registry, tests and fake-data shell exist and run.

Done on 13 Oct:
- Punjab EPA portal investigated: server-rendered HTML, no public JSON; parser written and tested (`airlume/collectors/epa.py`). Notes in `docs/research/epa-portal.md`.
- **AQI formula identified (W1):** US EPA 2012 breakpoints under Punjab's seven labels. `airlume/aqi.py` + tests.
- Station/city registry built with coordinates and confidence levels (`data/registry/`). Portal lists 36 districts, not 28; plan updated.
- Code: typed schema, resolver, DuckDB store, fake data, deck.gl layers, answer sentences, stub router, 45 passing tests.
- Shell runs in keyless map mode; screenshots checked.
- `setup.bat`, `run.bat`, `test.bat` for the laptop; `.env.example`; secret check; gitleaks and pre-commit configs.
- Emails drafted in `docs/emails/`; `docs/SOURCES.md` written.
- Plan revised (Phase 0.6, W1 row, Appendix D); PDFs rebuilt.

Also done on 13 Oct (afternoon, Phase 1 started early):
- `scripts/collect_hourly.py` — one round of collection: EPA Lahore stations, EPA district ranking (home-page parser), Open-Meteo CAMS for Lahore. Each source fails independently.
- **CSV archive** (`data/archive/<table>/<source>/<YYYY-MM>.csv`, append-only, deduplicated) is the committed data of record; DuckDB is a local cache (`scripts/rebuild_db.py`). This avoids binary merge conflicts in git.
- The app rebuilds its cache from the archive when fake data is off.
- EPD back-fill scaffold: `pipeline/backfill_epd.py` (list + download) and `scripts/epd_fetch_sample.py`; the PDF parser waits for sample files.
- `collect.bat` added; `_update\collect.yml` commits only `data/archive/`.

- **Supervisor proposal written** (`docs/proposal/proposal.md`, 14-page PDF): abstract, introduction, problem statement, related work with 26 verified references, research questions RQ1-RQ4, system, evaluation E1-E6, ten-week plan, preliminary results, risks, course mapping. Title page lists the three team members with roll numbers and the supervisor.

## 14 Oct (morning)
- `nl/router.py`: Groq-backed router with JSON-schema output, Pydantic validation, prompt-hash cache, call log, automatic fallback to the rule-based stub. Activates when `GROQ_API_KEY` is in `.env`.
- App rewritten for real data: loads the CSV archive on start (live readings + 3,089 daily history rows), removes fake rows once real data exists; daily-history timeline (2022-2025, B17 excluded) and hourly tab; 2D ranked bar beside every 3D view (W10); show-the-form toggle; model selector; follow-up questions merge with the previous form.
- `run.bat` now fetches one round before starting; `schedule.bat` registers an hourly Windows task.

- Live page investigated from a saved copy: 7-day hourly city trend and 24-h forecast embedded. Parsers written (fixture tests), `forecasts` table + archive, CAMS forecast captured alongside, "Next 24 hours" tab with scorecard. Replay-a-day slider added. App verified live on the laptop (10 of 11 stations, 09:00 PKT).
- Fixed: positional INSERT broke on the laptop's migrated table (gas columns at the end) - column lists are explicit now.

- **Collection moved to the cloud** (decision 14 Oct 09:55): `collect.yml` runs hourly on GitHub Actions and commits `data/archive/`; laptop scheduled task to be removed; `run.bat` no longer collects by default (`run --collect` does). Needs the repo public and the workflow moved into `.github\workflows\`.

- **Benchmark v0 written** (60 English + 10 Roman-Urdu single items, 20 two-turn conversations) with gold forms, and the E1 runner (`python -m airlume.eval.run_e1 --model <id> --runs 3`): per-field accuracy, bootstrap 95% CIs, consistency, per-class. **Baseline, rule-based stand-in: 45.6% pass (CI 36-56%)**, weakest on follow-ups (20%), forecasts (0%), thresholds (29%), Roman Urdu (40%). Not yet frozen: classmate items and second annotator pending.
- Cloud collector verified: first GitHub Actions run green (32 s).

- **Router live on Groq** (`.env` has the key; `check_secrets` masks it). Fixes needed before the first successful call: strict-schema rewrite of the Pydantic schema, output cap 2,048 + low reasoning effort (gpt-oss returned empty JSON at 400), wait-and-retry on the 8,000-TPM cap, fail-fast on the daily cap, cached single benchmark runs that resume. **E1, prompt v1, gpt-oss-120b: 66.7% (CI 57-77%)** vs stub 45.6%; weakest classes where_now 54%, follow_up 55%, compare_time 56%. Prompt v2 written from the failure analysis (field rules, city list, AQI bands, five examples); the 120b daily budget was exhausted before it could be re-scored. **Next: score v2 on `gpt-oss-20b` today and on 120b tomorrow; record both.** Benchmark v0 is now a dev set (see plan 3.2).
- Prompt v3 (follow-up continuation rule, "now" always latest, zoomed_out for cross-city, small-talk out of scope, neighbourhood kept verbatim); scorer accepts either order of city/other_city. **20b, prompt v2: 81.1% (CI 72-89%)**; v3 being scored.
- **Benchmark v1 materials written:** classmate question sheet (`docs/pdf/Airlume_Classmate_Questions.pdf`, print 3-4 copies) and second-annotator guide. Aftab: hand the sheet to 3 classmates this week; v1 freezes once 60 classmate questions and the second annotation are in.
- **Follow-ups in the app (3.9):** previous form kept per session, route-once-per-question, conversation thread in the sidebar, *Start over* button; stub handles short follow-ups offline. Verified in a headless browser. Groq daily budget (rolling 24 h, 200k tokens per model) exhausted on both models at 16:25; **tomorrow after 11:00: `run_e1 --model openai/gpt-oss-120b` (prompt v3, full) and finish the 20b run (32 items left, cached).**
## 15 Oct
- Collector overnight: 4 of 36 slots fired on GitHub (6 of 24 hours have station rows). **Aftab: set up the cron-job.org trigger with a fine-grained token (instructions given 15 Oct 10:45)**; GitHub's schedule stays as second chance. City-level hours are recoverable from the portal's 7-day trend; station rows are not.
- `scripts/w1_check.py` reads the CSV archive now (needs 8 distinct hours; had 6).
- **Security pass 1 (S1-S15)** written to `docs/security/audit-2026-10-15.md`: pip-audit clean, bandit reviewed (`.bandit`), rate limits added (session 30/h, global 150/h, 400-char cap), Markdown escaping of user/model text, tracebacks hidden from viewers, 4 new guard tests (84 total).
- **4.1 persistence baselines** in the scorecard + horizon chart (`airlume/forecast/skill.py`). Found and fixed a collector bug that dropped the 7-day city trend every round (next run back-fills). Early numbers: EPA bias +28, CAMS bias -17, skill ~0.1 vs last value on 34 hours.
- **E1 on prompt v3: 120b 88.9% (CI 82-96), 20b 88.9% (CI 82-94).** Prompt frozen. Write-up in `docs/research/e1-results.md`; four debatable gold items flagged for the second annotator. Date fields now accept datetimes (truncate to day).

## 14 Oct (afternoon)
- **Collector coverage problem found:** only 2 of 7 hourly slots ran on GitHub today (scheduler best-effort). `_update\collect.yml` now has two slots an hour; Aftab moves it into `.github\workflows\`. Check tomorrow: rows in `data\archive\readings\punjab_epa\2026-10.csv` should grow by ~10 per hour.
- **Coverage map and station recommendation (C3, C7)** built: 1 km grid over Lahore's urban area, distance to nearest monitor; mean 5.0 km, 45% of the area beyond 5 km, 22% within 3 km; greedy placement suggests ~31.56 N 74.20 E (west, near Bund Road/Sabzazar), 10.9 km from the nearest station today. New tab "Where the city is blind".

## Where we stopped (13 Oct, 19:10)
Session closed by Aftab. Everything below is on the laptop and pushed to GitHub. Tomorrow's first items: send the EPA email; create the accounts; schedule `collect.bat` hourly on the laptop (Task Scheduler) or install `_update\collect.yml`; run `python scripts\w1_check.py` after a day of readings; look at the 41 remaining unknown bulletins (`data\raw\epd\_styles.csv`).

## Next steps (rest of Phase 0)
- [ ] Aftab: run `K:\airlume\setup` then `K:\airlume\run` and confirm the shell opens.
- [x] Live dry run done 14:00 PKT: 10 Lahore stations, 35/36 districts, Open-Meteo OK. Finding: portal AQI differs from hourly-PM2.5 AQI in the afternoon (8-h mean or gas-dominated); all six pollutants now stored to settle it. See research notes.
- [x] Unmatched names were page furniture; ignored. Ozone identified as the afternoon driver; gas sub-indices added to `aqi.py`.
- [x] EPD archive sampled across 2018-2025; parser written for the 2022-2025 layouts (`pipeline/epd_parse.py`, 5 fixture tests). Archive ends 2 Dec 2025.
- [x] Trial back-fill pages 1-5: 379 rows. Two more layouts (D, E) and scanned files found and handled; parser now covers Aug 2025 - Dec 2025 fully and 2022 - 2024.
- [x] Full back-fill run: 2,121 rows 2022-2025. Three more layouts handled incl. the 2020-21 Smog Policy 2017 scale (style B17, non-comparable, concentrations kept).
- [x] Final back-fill 13 Oct 19:00: **3,144 daily rows, 2020-2025** (B 934, B17 206, E 165, A 34, D 2; C 458 and 144 scanned skipped; 41 still unknown; 73 genuine 404s). Archive files 2020.csv-2025.csv committed.
- [ ] Decide how to treat the gap 3 Dec 2025 - 12 Oct 2026 (no official per-station data; CAMS city-level or leave empty).
- [ ] After ~1 day of hourly collection: `python scripts\w1_check.py` to settle the averaging window.
- [x] Groq key in `.env` (14 Oct). Still to create: OpenAQ, CARTO (optional), Streamlit Community Cloud. **Aftab: rotate the Groq key** (it was pasted into chat once): delete it at console.groq.com, create a new one, paste into `K:\airlume\.env` with Notepad.
- [ ] Aftab: send the two emails (`docs/emails/`), with supervisor name filled in.
- [ ] Claude: once `.env` has an OpenAQ key, run station discovery for Islamabad/Karachi/Peshawar and add licensed stations to the registry.
- [ ] Claude: `collect.yml` GitHub Actions workflow (hourly) — placed in `_update\` for Aftab to move, since remote tools cannot write `.github/workflows/`.
- [ ] Known cosmetic issue: deck.gl text labels throw a MultiIconLayer error in headless Chromium; check on the laptop's real browser, else switch to HTML labels in Phase 2.

## Open decisions
- Supervisor name for the EPA email draft (title pages are now complete: Aftab Ahmad, Kiran Saif, Tehreem Fatima; supervisor Dr Rimsha Anam).
- Optional RAM upgrade (one 8 GB DDR5 SO-DIMM) for the 8B local model.
- Make the repository public before Phase 1 (needed for free Actions minutes and Streamlit Cloud).

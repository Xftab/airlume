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

## Next steps (rest of Phase 0)
- [ ] Aftab: run `K:\airlume\setup` then `K:\airlume\run` and confirm the shell opens.
- [x] Live dry run done 14:00 PKT: 10 Lahore stations, 35/36 districts, Open-Meteo OK. Finding: portal AQI differs from hourly-PM2.5 AQI in the afternoon (8-h mean or gas-dominated); all six pollutants now stored to settle it. See research notes.
- [ ] Aftab: run `K:\airlume\collect --dry-run` again to see which district name is unmatched.
- [ ] Aftab: `python scripts\epd_fetch_sample.py last 3` (newest, typed daily reports) - page 1 samples were scanned 2010-15 monthly tables, not usable.
- [ ] Aftab: create accounts — Groq, Google AI Studio, OpenAQ, CARTO, Streamlit Community Cloud — and put the keys in `K:\airlume\.env` (never in chat).
- [ ] Aftab: send the two emails (`docs/emails/`), with supervisor name filled in.
- [ ] Claude: once `.env` has an OpenAQ key, run station discovery for Islamabad/Karachi/Peshawar and add licensed stations to the registry.
- [ ] Claude: `collect.yml` GitHub Actions workflow (hourly) — placed in `_update\` for Aftab to move, since remote tools cannot write `.github/workflows/`.
- [ ] Known cosmetic issue: deck.gl text labels throw a MultiIconLayer error in headless Chromium; check on the laptop's real browser, else switch to HTML labels in Phase 2.

## Open decisions
- Supervisor name and roll number for the plan's title page and the EPA email.
- Optional RAM upgrade (one 8 GB DDR5 SO-DIMM) for the 8B local model.
- Make the repository public before Phase 1 (needed for free Actions minutes and Streamlit Cloud).

# Airlume: context for AI-assisted sessions

Read this first, then `docs/STATUS.md` and `docs/HISTORY.md`.

## What this is
Airlume is Aftab Ahmad's semester-7 project: a conversational 3D digital twin of air quality in Pakistan's monitored cities (Lahore in station-level 3D). The canonical description, scope, resources, phases and weaknesses are in `docs/plan/plan.md`.

## Standing rules
1. **Keep the documents current.** Whenever a decision changes (scope, name, data source, schedule, feature, fix), update `docs/plan/plan.md` in the same session, rebuild the PDFs with `bash docs/build.sh`, and record the decision in `docs/HISTORY.md`. Then write every changed file, PDFs included, into `K:\airlume` and ask Aftab to run `save`.
2. **Update `docs/STATUS.md`** at the end of every working session: what was done, what is next, any blockers.
3. **Never edit PDFs directly.** They are build outputs.
4. **WAQI data never reaches `data/` or any published file.** Live display only.
5. **The language model never writes SQL or code at runtime.** It fills the typed view-intent schema; code validates and builds queries.
6. **Commands for Aftab to run** go in fenced code blocks. His machine is Windows; use Git Bash or WSL for bash commands. Keep the project, environments and models on the K: drive.

## Where the project lives
- **On Aftab's laptop: `K:\airlume`.** This folder is connected to Claude sessions; Claude writes updated files there directly.
- **On GitHub: `Xftab/airlume`.** After any change, Aftab runs `K:\airlume\save "what changed"`, which commits and pushes.
- Every change made in a session must be written to `K:\airlume` before the session ends, with the PDFs rebuilt.
- Claude's remote file tools **cannot write inside `.git/` or `.github/workflows/`**. Aftab runs git himself, through `save.bat`. The GitHub Actions workflow (`.github/workflows/build-docs.yml`) only **checks** that the documents build and attaches the PDFs to the run; it **never commits**. (A version that committed PDFs caused merge conflicts with the PDFs Claude saves locally; removed 12 Oct.) Claude rebuilds the PDFs in each session.
- **Write each update from a freshly named staging folder** and verify it by reading the file back from `K:\airlume`. Reusing a staging path once resent stale content.

## Machine
Lenovo ThinkBook 14 G6 IRL (21KG): i7-1355U (10 cores, 12 threads), 8 GB DDR5 (one free SO-DIMM slot), Intel UHD graphics. C: drive nearly full; use K:. Local model: `qwen3:4b` (8B needs 16 GB).

## Code conventions (from Phase 0)
- Python 3.13, pinned `requirements.txt`; venv at `K:\airlume\.venv` (created by `setup.bat`).
- All SQL in `pipeline/store.py`, parameterised; metric/aggregation names are checked against allow-lists.
- Secrets only via `config.load_settings()`; `scripts/check_secrets.py` runs before the app starts.
- `collectors/waqi_display.py` may be imported only by the app (`tests/test_waqi_isolation.py` enforces it).
- Answer text is produced by `nl/answer.py` from numbers, never by the model.
- Research findings go in `docs/research/`; the plan's Appendix D summarises them.
- Run `python -m pytest` before every sync; 174 tests as of 16 Oct.
- Data of record is the CSV archive in `data/archive/` (committed, append-only). DuckDB is a git-ignored cache rebuilt by `scripts/rebuild_db.py`.

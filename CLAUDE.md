# Airlume: context for AI-assisted sessions

Read this first, then `docs/STATUS.md` and `docs/HISTORY.md`.

## What this is
Airlume is Aftab Ahmad's semester-7 project: a conversational 3D digital twin of Lahore's air quality. The canonical description, scope, resources, phases and weaknesses are in `docs/plan/plan.md`.

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
- Claude's remote file tools **cannot write inside `.git/` or `.github/workflows/`**. Aftab runs git himself, through `save.bat`. There is deliberately **no GitHub Actions workflow**: PDFs are rebuilt by Claude in each session instead.
- **Write each update from a freshly named staging folder** and verify it by reading the file back from `K:\airlume`. Reusing a staging path once resent stale content.

## Machine
Lenovo ThinkBook 14 G6 IRL (21KG): i7-1355U (10 cores, 12 threads), 8 GB DDR5 (one free SO-DIMM slot), Intel UHD graphics. C: drive nearly full; use K:. Local model: `qwen3:4b` (8B needs 16 GB).

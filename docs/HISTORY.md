# Decision history

Newest first. Each entry records what was decided and why.

## 12 October 2026
- **Scope widened to Pakistan's monitored cities.** Every city with monitoring stations (Punjab's 28 EPA cities; Islamabad, Karachi, Peshawar, Quetta via third-party stations) appears at city level; Lahore keeps the full 3D twin. A nationwide CAMS model grid was considered and rejected: the student chose to show only measured values, never modelled ones, on the map. City comparison moved from stretch to core.
- **GitHub workflow changed to check-only.** Its first run committed rebuilt PDFs, which conflicted with the PDFs saved locally (git cannot merge two PDFs). The workflow now only verifies the build and attaches the PDFs to the run. `save.bat` now keeps the laptop's version on any conflict and reports failures instead of claiming success.
- **Security standard adopted.** A 15-item security checklist (keys, secrets in history, XSS, injection, rate limiting, headers, debug off, exposed files, database, audit) was added to the plan as a standing requirement, with a hardening sub-phase (6.7) that must pass before the site goes public. Git history scanned the same day: clean.
- **GitHub Actions PDF workflow installed by hand.** Remote tools are not allowed to write workflow files (they run code on GitHub automatically), so Claude placed the file in the project folder and Aftab moved it into `.github/workflows/`. It is a backup; Claude still rebuilds the PDFs in each session.
- **Working folder set to `K:\airlume`** on the laptop (C: is nearly full). Claude writes files there directly; `save.bat` commits and pushes to GitHub. GitHub was not linked to Claude, by the student's choice.
- **Renamed the project to Airlume** (air + *lume*, light). "Hawa" was dropped at the student's request. "AeroVue" was rejected because it is a Honeywell avionics trademark; "Airora" because search engines autocorrect it to "Aurora". "Airlume" is used elsewhere only by a 2017 art installation.
- **Repository created** with automatic PDF rebuilds on every source change.
- **Hardware checked:** the laptop (i7-1355U, 8 GB) can build everything; the local model drops to `qwen3:4b`. An optional 8 GB RAM upgrade is possible because one SO-DIMM slot is free.
- **Fifteen weaknesses identified and scheduled** (W1–W15). Validity fixes take priority over features. Shareable answer cards and replay mode became optional to make room.
- **Eight features added:** show-the-query toggle, clarifying questions, follow-up questions, lowest-AQI window, station-placement recommendation (contribution C7), local-model comparison, shareable cards (optional), replay the worst day (optional).
- **Resource audit (all verified on 12 Oct):** WAQI terms forbid archiving and analysis, so it is display-only. Punjab EPA has no API and no licence, so we build without needing permission and publish derived statistics only. CARTO basemaps now need a free key. Hugging Face Spaces is no longer free for Streamlit. The Gemini free tier is about 500 requests/day on Flash-Lite, so Groq `gpt-oss-120b` is the primary model.
- **Novelty repositioned** after finding VayuBuddy (2024), VayuChat (2025) and Punjab's EcoBot (2025). The contribution is now the scoring rubric for *visual* answers that VayuBuddy left as future work.

## 8 October 2026
- **Project chosen:** a smog digital twin combined with a natural-language "Ask the City" interface.
- **CAMS resolution problem found:** about 45 km over Pakistan, so all of Lahore is one cell. Punjab EPA stations became the intra-city data source, and CAMS became a validation target (contribution C4).
- **Scope:** Lahore as the deep city; Multan and Karachi as stretch comparison points.
- First proposal (v1) written; now superseded by the complete plan.

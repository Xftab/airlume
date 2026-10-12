# Status

_Last updated: 12 October 2026_

## Where we are
**Phase 0: Foundations and Access (week 1, 13–19 Oct)** is about to start. Planning is complete.

Done so far:
- Project idea chosen, researched and named **Airlume** (renamed from "Hawa").
- Scope set (12 Oct evening): **all Pakistani cities with monitoring stations** at city level, Lahore in full 3D depth. Registered with the university under the title "Airlume: A Conversational 3D Digital Twin of Air Quality in Pakistan".
- Complete project plan written: 29 pages, 8 phases, 15 known weaknesses with fixes and dates.
- Every resource verified free and accessible on 12 Oct 2026.
- UI mockups made (desktop live view, answered query, accuracy page, phone), using the 11 real EPA station names.
- Repository created: github.com/Xftab/airlume (private).
- Project folder set up on the laptop at `K:\airlume`; `save.bat` commits and pushes in one command.

## Next steps (Phase 0)
- [ ] Create accounts and keys: Groq, Google AI Studio, OpenAQ, CARTO basemap key, Streamlit Cloud.
- [ ] Find the EPA portal's JSON endpoint (Chrome DevTools, Network tab, Fetch/XHR).
- [ ] Identify which AQI formula Punjab EPA uses (fix W1).
- [ ] Check OpenAQ Pakistan coverage and per-station licences.
- [ ] Email the Punjab EPA (`support@aqi.punjab.gov.pk`, `ddisepa@punjab.gov.pk`) for API access and archiving permission.
- [ ] Notify WAQI of academic display use.
- [ ] Set up the K: drive environment and pin library versions (fix W13).
- [ ] Build the fake-data UI shell.
- [ ] Install the gitleaks pre-commit hook (security item S3). History already scanned clean on 12 Oct.

## Open decisions
- Fill in roll number and supervisor name on the plan's title page.
- Optional RAM upgrade (one 8 GB DDR5 SO-DIMM, about Rs 24,000) to run the 8B local model.
- Make this repository public before Phase 1: free GitHub Actions minutes and Streamlit Cloud both need a public repo.

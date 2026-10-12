# Airlume

**A conversational 3D digital twin of air quality in Pakistan's monitored cities.**

Ask a question in plain words: *"Which city has the worst smog today?"* or *"Where is it worst in Lahore?"* A three-dimensional map answers it: every monitored city in Pakistan as a column at country level, and Lahore station by station. The question is the interface.

Airlume is a semester-7 BS Data Science project (DS494 Data Visualization; CC425 Parallel & Distributed Computing), built at zero cost on open data.

## Documents

| Document | PDF | Source |
|:--|:--|:--|
| **Complete project plan** (current) | [`docs/pdf/Airlume_Complete_Project_Plan.pdf`](docs/pdf/Airlume_Complete_Project_Plan.pdf) | [`docs/plan/plan.md`](docs/plan/plan.md) |
| Project proposal v1 (superseded) | [`docs/pdf/Airlume_Project_Proposal_v1.pdf`](docs/pdf/Airlume_Project_Proposal_v1.pdf) | [`docs/proposal-v1/proposal.md`](docs/proposal-v1/proposal.md) |

The PDFs are generated from the Markdown sources. **Edit the `.md` file, never the PDF.** Whenever a source changes, the PDFs are rebuilt and saved alongside it, so they always match. The [Check PDF build](.github/workflows/build-docs.yml) workflow verifies on GitHub that the documents still build after any push that changes a source, and attaches the PDFs to the run as a backup. It never commits.

Save and push every change from Windows (Command Prompt):

```cmd
K:\airlume\save "what changed"
```

Build the PDFs locally (Git Bash or WSL; needs pandoc and XeLaTeX):

```bash
bash docs/build.sh
```

## Project status

See [`docs/STATUS.md`](docs/STATUS.md) for where things stand and what comes next, and [`docs/HISTORY.md`](docs/HISTORY.md) for every decision made so far and why.

## Contributions in brief

1. A scoring rubric for conversational *visual* analytics: the gap the closest prior system, VayuBuddy, named as future work.
2. Camera pose as part of a generated answer in a 3D scene.
3. A sparsity-honest map: discrete stations, distance-to-nearest-monitor, and a coverage map.
4. The first quantified CAMS-vs-ground agreement study for Lahore.
5. A public, automatic forecast scorecard.
6. A released benchmark: 60 questions, 10 ambiguous items, 10 follow-up dialogues.
7. A station-placement recommendation for Lahore's monitoring network.

## Data and attribution

Station readings: Punjab Environmental Protection Agency. Atmospheric model and weather: CAMS via Open-Meteo (CC BY 4.0). Map data: © OpenStreetMap contributors, © CARTO.

*Student project. Not an official government source.*

# Airlume — goal, what we are building, phases

## Goal in one sentence
Let anyone ask about Pakistan's air quality in plain words and get an honest, visual,
verifiable answer — a 3D map that shows only what is measured and says what it does not know.

## What we are building
- **Data pipeline:** hourly readings from the Punjab EPA portal (11 Lahore stations, 36
  districts, 7-day city trend, 24-h forecast) and Open-Meteo CAMS, stored as an append-only
  CSV archive on GitHub (data of record) with a DuckDB cache. Daily history 2020–2025 from
  3,144 EPD bulletin rows.
- **3D digital twin:** deck.gl/pydeck in Streamlit — station columns coloured by AQI band,
  city overview of Pakistan, compare and timeline views, replay a day, coverage map
  ("where the city is blind") and a recommended new station site.
- **Language layer:** Groq `gpt-oss-120b` (fallback `gpt-oss-20b`, then a rule-based stub)
  fills a typed `ViewIntent` form; Pydantic validates it; code resolves time, place and
  nearest station; follow-up questions and clarifying questions supported.
- **Evaluation:** a benchmark of 60 English + 10 Roman-Urdu questions and 20 two-turn
  conversations (v0, a development set); v1 will be classmate-authored, second-annotated
  and frozen. Forecast scorecard with persistence baselines and skill scores.
- **Deployment:** public website on Streamlit Community Cloud after the security checklist
  passes; repo `Xftab/airlume` (private for now).

## Contributions (as in the plan)
C1 scoring rubric for conversational visual analytics · C2 camera pose as part of the
answer · C3 sparsity-honest visualisation + coverage map · C4 CAMS-vs-ground validation for
Lahore · C5 public automatic forecast scorecard · C6 released benchmark · C7 station-placement
recommendation.

## Scope
In: every Pakistani city with monitoring stations at city level; Lahore in 3D depth;
rankings, comparisons, trends; follow-ups; 24–48 h forecasts; English + Roman Urdu.
Out: unmonitored places (no invented values); indoor air; causes of pollution; medical
advice; native mobile apps.

## Phases (ten weeks, 13 Oct – 21 Dec 2026) — status as of 15 Oct
| Phase | Weeks | Status |
|---|---|---|
| 0 Foundations and access | 1 | **Done** (13 Oct) |
| 1 Data pipeline | 2–3 | **Mostly done, early**: collectors, archive, cloud collection, EPD back-fill 2020–2025 done; W1 averaging check and data-quality flags pending |
| 2 3D digital twin | 3–4 | **Mostly done, early**: all views, replay, coverage map, recommendation done; wind layer and time animation pending |
| 3 Language layer | 5–7 | **In progress**: router live, prompt frozen at v3, benchmark v0 scored (88.9% both models vs stub 45.6%), follow-ups done; v1 benchmark (classmates + second annotator) pending |
| 4 Forecasting and validation | 8 | **Started**: persistence baselines and skill scorecard done; CAMS-vs-ground validation pending (needs weeks of data) |
| 5 Evaluation | 9 | Not started (E1 harness exists; E2–E6 pending) |
| 6 Deployment | 9 | **Started**: security pass 1 done; repo still private; Streamlit Cloud pending |
| 7 Report and demo | 10 | Not started |

We are about three weeks ahead of the calendar on building, and on schedule for the parts
that need time to pass (data accumulation, classmate questions).

# Airlume — final report (working draft 1)

**Status: working draft, 4 November 2026.** Written early, against the outline in `09-report-outline.md`, so that results land in finished prose as they arrive rather than in a rush in Week 4. Every number here is traced to a file named beside it. Anything not yet measured is marked `[PENDING]` and must not be filled with an estimate. Format, template, page limit and citation style: `[get from UMT FYP guidelines or Dr Rimsha Anam]`.

**Revised 6 November 2026** with the results of the 6 Nov audit (`docs/research/*-2026-11-06.md`): restored archive and coverage (3.1, 5.1), the portal's table change and the new W1 figure (3.3, 5.2), CAMS on 313 hours (5.3), the forecast against the same-hour-yesterday baseline (5.4, RQ1), the prompt v5 schema freeze (3.4, 3.5), and verified Chapter 2 citations (`docs/report/citation-check-2026-11-06.md`).

Three chapters are substantially complete (3 Materials and Methods, 5 Results, 7 Weaknesses). Chapters 1, 2, 4, 6, 8 and 9 are drafted to the point the evidence allows. The abstract is written last, by rule.

---

## Front matter

**Title.** Airlume: A Conversational 3D Digital Twin of Air Quality in Pakistan's Monitored Cities

**Team.** Aftab Ahmad (F2023332010), Kiran Saif (F2023332108), Tehreem Fatima (F2023332103). Supervisor: Dr Rimsha Anam. University of Management and Technology, Lahore. Courses DS494 (Data Visualization) and CC425 (Parallel and Distributed Computing).

**Statement of contributions.** `[Fill factually with the team before submission.]` The dated record in `docs/HISTORY.md` shows the implementation, data pipeline, modelling and evaluation work concentrated in one member. The benchmark annotation is owned by Kiran Saif and Tehreem Fatima (Chapter 3.5), which is both a methodological requirement and a documented contribution. State this plainly rather than distributing credit evenly by default; an examiner can read the commit history.

**Abstract.** `[Write last. 200 words, one sentence per headline result: coverage, AQI harmonisation, CAMS validation, forecast skill, language-layer accuracy, user study.]`

---

## 1. Introduction

### 1.1 The problem, in three parts

**Data you cannot ask questions of.** Punjab's Environmental Protection Agency publishes hourly readings from eleven monitoring stations in Lahore and a district ranking for the province. The data is public and it is updated. It is also a web page: a table of numbers that answers exactly the questions its layout anticipated. A resident who wants to know whether the air near their own neighbourhood is worse tonight than last night, or whether this week has been worse than last, cannot ask. They can only read.

**Maps that pretend to know more than they do.** Commercial air-quality maps render smooth colour fields over entire cities. Those fields are interpolations from sparse instruments. Lahore has eleven official monitors for a city of well over ten million people, and the gradients between them are extreme: over the validation period, Gulberg III and Multan Road differ by roughly 95 µg/m³ of PM2.5 on average (Chapter 5.3). A continuous colour wash across that gap is a confident statement about places where nothing is measured.

**Forecasts nobody holds accountable.** Air-quality forecasts are published daily and almost never scored afterwards. Without a public record of error, a forecast is a claim with no cost attached to being wrong.

### 1.2 What Airlume is

Airlume — from *air* and *lume*, light — is a website that shows measured air quality across Pakistan's monitored cities on a three-dimensional map, and lets a person ask about it in plain English or Roman Urdu. A question is turned by a language model into a **typed view-intent form**; code validates that form, queries the stored data, and renders both a view and a sentence. The language model never writes SQL and never writes the answer text. Numbers in answers are produced by code from stored readings.

Four design rules hold throughout, and they are the spine of the system:

1. The language model fills a typed form; it never emits SQL or code at run time.
2. Answer text is written by code from numbers; the model does not narrate.
3. Values are never invented for unmonitored places. Where there is no station, the system says so and names the nearest one with its distance.
4. WAQI data is display-only and is never stored or analysed, per its terms.

**In scope:** current and historical readings for monitored stations and cities; comparisons across time and place; forecasts to at most 48 hours; graded health guidance drawn from published advisories; intervention-priority guidance.
**Out of scope:** weather prediction; medical diagnosis; causes of pollution except intervention guidance; any estimate for an unmonitored location; anything beyond the forecast horizon.

### 1.3 Research questions

From the R&D extension (`05-rd-extension-plan.md`), confirmed by the supervisor on 28 October:

- **RQ1.** Can a learned forecaster beat persistence, CAMS and the EPA forecast for Lahore?
- **RQ2.** How well does the CAMS global model match ground stations in Lahore?
- **RQ3.** Can a conversational interface answer air-quality questions reliably?
- **RQ4.** Can the available data support a defensible, transparent intervention-priority score?

### 1.4 Contributions

From `plan.md` Part A. The project claims no new machine-learning architecture and trains no model from scratch; the contributions are in systems design, evaluation methodology and local measurement.

| | Contribution | Verified by |
|---|---|---|
| C1 | A scoring rubric for conversational *visual* analytics, via a typed view-intent schema | Per-field accuracy on a frozen benchmark (5.5) |
| C2 | Camera pose treated as part of the generated answer | Camera fields scored separately (5.5) |
| C3 | A sparsity-honest visualisation protocol and a quantified coverage map | Protocol audit; user comprehension (5.7) |
| C4 | The first quantified CAMS-versus-ground validation for Lahore | Released statistics (5.3) |
| C5 | A public, automatic forecast scorecard | Generated from logs (5.4) |
| C6 | A released benchmark of single and multi-turn questions | Public repository (3.5) |
| C7 | A station-placement recommendation for Lahore's network | Coverage gained per proposed site (5.8) |

C1 is the central one, and its framing matters: the contribution is **scoring the visual answer** — view, area, time window and camera — which VayuBuddy's authors named as future work. It is not "using structured output".

### 1.5 Chapter map

`[One paragraph, written last.]`

---

## 2. Related work

Twenty-six verified references are already collected in `docs/proposal/proposal.md` and are carried into this chapter. **Every citation is verified against the actual source before it appears here; nothing is cited from memory.**

Structure:

1. **Conversational interfaces to environmental data.** VayuBuddy (2024) and VayuChat (2025) establish the line of work; Punjab's own EcoBot (2025) is the local deployment. VayuBuddy explicitly names the evaluation of *visual* answers as future work, which is the gap C1 addresses.
2. **Air-quality visualisation and the interpolation question.** `[Fill from the proposal's survey; the specific claim needed is that commercial maps interpolate without disclosing distance-to-sensor.]`
3. **Reanalysis and model-versus-ground validation.** CAMS and its known coarse resolution over South Asia; the absence of a published local error estimate for Lahore, which C4 supplies.
4. **Forecasting with limited ground data.** Shwartz-Ziv and Armon (2022), *Information Fusion* 81, on tree ensembles versus deep models on tabular data, which is directly relevant to the finding in 5.4.
5. **Monitoring-network siting.** Rahman, Usama, Tahir and Uppal (2022), "Data driven framework for analysis of air quality landscape for the city of Lahore", ISPRS Archives XLVIII-4/W5-2022, 167–173. It analyses 4 reference-grade stations and 9 low-cost sensors and proposes a location-recommendation method for new stations. It is the comparison point for C7.
6. **Intervention evidence.** "Gupta et al. (2022)" could not be found and is dropped. Replacement, as background only: Patra, Sahbaz and Ganesan (CEEW, 18 November 2025), who find the evidence for anti-smog guns limited and their road coverage about 2% in Delhi. The scenario calculator makes no effect claim.

**Statistical methods cited in place** (details verified 6 Nov, `citation-check-2026-11-06.md`):
- Wilson (1927), *JASA* 22, 209–212, for score intervals;
- Newcombe (1998), *Statistics in Medicine* 17(8), 873–890, for a difference of proportions;
- Landis and Koch (1977), *Biometrics* 33(1), 159–174, for kappa bands;
- Brooke (1996), in *Usability Evaluation in Industry*, 189–194, for the System Usability Scale;
- Karp and Flatt (1990), *Communications of the ACM* 33(5), 539–543, for the serial-fraction estimate.

---

## 3. Materials and methods

### 3.1 Study area and datasets

Lahore is the deep case: eleven official monitoring stations, a dense population, and a severe October-to-February smog season. Other monitored cities are carried at city level for comparison.

| Source | What is taken | Period | Resolution | Licence |
|---|---|---|---|---|
| Punjab EPA (`aqi.punjab.gov.pk`) | Station AQI, PM2.5, PM10, gases; district AQI | from 13 Oct 2026 | hourly, 11 Lahore stations | No published licence. **Permission to use the data granted via the supervisor, 4 Nov 2026, with no additional data supplied.** `[Paste date, sender and exact wording; confirm whether redistribution of raw readings is covered.]` |
| Punjab EPD daily bulletins | Daily AQI | 2020–2025 | daily, 3,144 rows | Public government documents |
| Open-Meteo (CAMS) | Modelled PM2.5, PM10 | paired 13–28 Oct 2026 | ~45 km cell, hourly | CC BY 4.0 |
| Open-Meteo (ERA5) | Meteorology as model features | 2,161 days | daily | CC BY 4.0 |
| WorldPop 2025 | 1 km population grid | 2025 | 1 km | CC BY 4.0 |
| OpenStreetMap (Geofabrik) | Water, aerodrome, military, roads, industrial land | — | vector | ODbL |
| WAQI | Live AQI | live | — | **Display only; never stored or analysed** |

**Coverage, measured rather than assumed.** Over the whole hourly archive (14 Oct 04:00Z to 6 Nov 12:00Z, after the restore described below) the system holds **3,294 of 6,171 possible station-hours, 53.4%**, with 313 of 561 hours carrying any data at all. Over the stable window 15 Oct 06:00Z to 24 Oct 02:00Z, **8.0% of station-hours are missing**, ranging by station from 4.2% to 9.9% (Gulberg III highest, and not an outlier). Over the hours the collector actually ran, station uptime is 92% to 100%. The **Lahore city-level series is complete**: 690 of 690 hours from 8 Oct, because every round re-reads the portal's 7-day trend.

The gap between those two figures is the point. A single headline coverage number would be misleading: most of the loss comes from two identifiable incidents, not from steady attrition.

**Known gaps, and one that turned out to be data loss.**
- **25 Oct 12:00Z to 28 Oct 15:00Z, 76 hours.** On 25 October the GitHub Actions runner stopped being able to reach the Punjab EPA portal, apparently a geographic block on datacentre addresses. Collection moved to the laptop on 28 October. These station rows cannot be recovered; the EPA has confirmed it will supply no additional data. The gap was first recorded as 110 hours from 24 Oct 02:00Z. The cloud had in fact collected the first 34 of those hours, and they were deleted by the merge fault below and restored.
- **Night gaps from 30 Oct.** The laptop collects only while awake: 4 to 13 hours a day, with gaps of 8 to 16 hours each night. City-level values are unaffected (7-day trend).
- **7,215 committed rows deleted by git merges, found and restored on 6 November.** Both collectors fetched every source and so wrote the same month files. Each side's `git pull --rebase -X theirs` / `-X ours` threw away the other side's conflicting rows: 5,520 CAMS forecast rows, 1,052 city-hours, 272 EPA forecast rows and 371 station rows. Every row was still in git history and was restored by `scripts/recover_archive_rows.py`. The cause was fixed with git's union merge for the archive files. This is reported because a data-of-record claim is only as good as the process that keeps it (`docs/research/archive-merge-loss-2026-11-06.md`).
- The hour 2026-10-17T03:00:00Z, once thought missing, is present in every table.

An earlier figure of 4.5% missing circulated internally; it was the 210-hour W1 sample only, not the archive. A "42%" figure also noted earlier did not reproduce. The measured value is 52.6%, and the discrepancies are recorded here because the report should show how a number was arrived at, not only its final value.

### 3.2 Collection architecture

Collection is **hybrid**, and not by preference. CAMS is fetched hourly by GitHub Actions. The Punjab EPA portal is fetched hourly by a scheduled task on a laptop in Lahore, because the cloud runner cannot reach it.

The honest consequence: **when the laptop is off, data is lost.** This happened between 28 and 30 October, when the scheduled task was found never to have run since registration — Windows power defaults had suspended it (error 0x800710E0). It was fixed with an explicit `Set-ScheduledTask` call and verified. Gaps of this kind are displayed in the application rather than filled silently.

The portal is read once per hour with a cache-buster and a named user agent. It is server-rendered with no public JSON feed; an undocumented `api.aqi.punjab.gov.pk` exists and was deliberately not probed.

### 3.3 AQI computation and harmonisation (weakness W1)

The first serious validity problem found in this project was that the portal's AQI could not be reproduced with the US EPA 2012 breakpoints. A station reading compared against a CAMS concentration is not a comparison at all if the two use different formulas.

Recovered from 304 stored rows on 16 October: **the portal uses its own NEQS-anchored table, with gases in µg/m³** — 99.7% of rows reproduced exactly and 100% within one point, against 6% exact for the US 2012 table. This became the default scale in `airlume/aqi.py`.

Confirmed at scale on 24 October over 2,206 station-hours (MAE 1.7, median 0.0); the latest-hour window was adopted against 8-hour (MAE 45.1) and 24-hour (54.7) means.

**The portal changed its table on 3 November 2026, between 05:00 and 07:00 UTC** (found 6 November from the archive; no notice found). Two things changed together:

- the PM2.5 breakpoint at AQI 150 moved from 70 to 75 µg/m³ (1,494 of 1,496 distinguishing hours before match the old table, and 102 of 102 after match the new one);
- until the change, the portal published 500 for every reading above the 301–400 band (PM2.5 over 350, PM10 over 550), in all 130 such hours. Since then the 401–500 band is used (22 of 22 PM10 hours between 550 and 650 match exactly).

The earlier "top-band saturation" residual and the 99-point outlier are this behaviour, not a fault in the recovered table. Two gas bands were added from the archive, in-sample: O₃ 195.1–260 and NO₂ 130.1–180 (151–200). `aqi.py` holds both tables with the date of the change.

| Comparison (day-block bootstrap, 2,000 resamples) | n | Exact | MAE [95% CI] |
|---|---:|---:|---|
| **Table in force at each hour, all hours** | 3,293 | **99.1%** | **0.16 [0.05, 0.31]** |
| Before 3 Nov 06:00 | 2,987 | 99.1% | 0.16 [0.05, 0.33] |
| From 3 Nov 06:00 | 306 | 99.7% | 0.10 [0.00, 0.39] |
| October table applied after the change | 306 | 64.1% | 3.94 [1.96, 6.75] |

12 of the 14 hours still off by more than 10 points are CO-dominant (21 CO-dominant hours, 0.6% of the total), where the portal's CO bands are unknown. PM2.5 above 350 has not yet occurred under the new table, so that band is still extrapolated. Source: `scripts/w1_rescore.py`, `data/eval/w1_rescore_2026-11-06.json`.

### 3.4 The language layer

A question goes through four stages: **route** (model fills a typed `ViewIntent` form), **validate** (code checks the form against the schema), **resolve** (code turns the form into a query against the store), **answer** (code writes the sentence and selects the view).

Design features that follow from the four rules:
- **Show-the-query.** The filled form is visible on screen, so the rubric's input can be watched live.
- **Clarifying questions** where a form cannot be filled unambiguously.
- **Follow-ups**, carrying context across turns.
- **Coverage notes.** A question about an unmonitored place names the nearest station and its distance rather than estimating.
- **Window-aware city answers** (1 November). City-level answers used to quote the current value whatever window was asked; they now aggregate the stored hourly series for the requested window and state the window and the hours of data behind it.
- **Out-of-archive windows** (1 November). A window the archive does not reach now produces a sentence saying what the archive covers, rather than "No data for that place and time". This came directly from a benchmark failure (q024) where the model returned a 2023 date range from its training era.
- **Prompt v5 and the schema freeze** (6 November), from the 2 November run of the 62 classmate questions:
  - `city` is null when no city is named, so "is the air clean in Lahore?" is answered for Lahore, not with a national headline;
  - right-now questions separate *how is it* (`latest`: the city figure, the spread across stations, and the advisory for the city level) from *where is it worst or cleanest* (`max`/`min`);
  - a new `hour_of_day` aggregation answers "is smog lower at night?" from the gap-free city series;
  - a clarify always wins over a refusal, so "AQI around my home?" gets "which area are you in?";
  - "when will it improve" is routed to the forecast.
  The form shape is now frozen until submission.

Prompt v4 (30 October) made guidance questions in scope and the forecast horizon and hour-of-day rules explicit.

### 3.5 Evaluation protocol

**This section must be read together with `docs/benchmark/validity-review-2026-11-04.md`.** A review on 4 November established that the benchmark's gold labels were a language model's draft accepted unchanged, and that both existing question sets are development data. The protocol below is the corrected one.

**Two question sets, kept separate and never pooled.**

| | Benchmark v0 (90 items) | Classmate set (62 questions, 30 Oct) |
|---|---|---|
| Written by | the build team | three classmates, blind to the app |
| Out of scope | 7 of 90 (10%) | 21 of 62 (34%) |
| Roman Urdu | 10 of 70 scored (14%) | 37 of 62 (60%) |
| `metric`/`threshold`/`compare_to`/`other_city` | n = 11 / 9 / 19 / 7 | **n = 0 / 0 / 0 / 0** |

**v0 covers the schema but not real usage; the classmate set covers real usage but not the schema.** Both are development sets: prompt v4 was checked against v0, and the 62 classmate questions were run through the pipeline on 2 November with every failure read and acted on. Neither can serve as a held-out test set, and the report describes them as development data throughout.

**Test set.** A fresh collection, in two clearly labelled strata: **Stratum A, naturalistic** (unsteered classmate questions, carrying the headline claim) and **Stratum B, schema coverage** (constructed after the schema freeze to exercise the four unused fields, reported separately). `[Collection pending the schema freeze; see Chapter 7, W2.]`

**Annotation.** Two annotators who have not seen any model draft fill the form independently from annotator guide v3 (6 Nov, matching prompt v5). Disagreements are adjudicated against the written guide, with the governing rule recorded for each. Where the guide is silent, that is a guide gap: the guide is amended and both annotators re-decide.

**Statistics.** Wilson score intervals for proportions, because they stay honest at 0% and 100% where a bootstrap collapses to zero width. Newcombe intervals for a difference of proportions. Moving-block bootstrap for time series. Cohen's kappa for inter-annotator agreement, reported with its n and without leaning on the adjective. Splits are time-based, never random. Every per-field figure is printed as correct/n, and **any field with n below about 10 is reported as a count with no percentage headline.**

**Precision, stated in advance.** At n = 62 a result near 90% carries a Wilson interval of roughly ±7.5 points; at n = 100, ±6. An English-versus-Roman-Urdu difference needs to be about **20 points** before it is distinguishable from zero at these sizes. Claims are kept inside those limits.

**Scoring once.** `score_benchmark_v1.py` writes a scorecard named with a hash of the gold file and refuses to overwrite it. As of 4 November it also refuses any gold file whose label cells match a draft sheet beside it, whatever it has been renamed to — the previous guard checked the file name and was defeated by a rename.

### 3.6 Models

| | Model | Data | Baselines |
|---|---|---|---|
| A | Daily forecaster: LightGBM, ridge, LSTM, GRU | EPD daily 2020–2025 + ERA5 | persistence |
| B | Hourly CAMS-error correction | lagged readings, hour, weather | raw CAMS, persistence |
| C | Zero-shot time-series foundation model | — | persistence |
| 4.2 | Hourly 1–24 h Lahore AQI, per-band and single-model | archive + CAMS + EPA forecast | persistence, yesterday, relayed CAMS, relayed EPA |

All are scored against persistence with skill scores and intervals. Splits are by time.

### 3.7 Insight modules

- **Station priority score:** share of hours per AQI band, persistence of bad days, trend, and a data-confidence flag. Computed from stored data only.
- **Graded response:** a menu by AQI band drawn from published Pakistan and Punjab smog action documents. Text written by code; rule 2 holds. `[Cite the source documents.]`
- **Scenario calculator:** coverage arithmetic only — area to cover against spray coverage radius. **It makes no effect prediction.** Output is phrased "under these assumptions, N units would cover the area", with radius, cost and effect as stated assumptions set by the supervisor. `[Fill the assumption values.]`

A bug found on 30 October is recorded here because it invalidates earlier output: scoring from the store read the wrong column and gave every station 10.0 (Low). It now accepts either `aqi` or `value`. **Any store-backed priority score produced before 30 October is invalid.**

### 3.8 Software, versions, tests and security

Python `[version]`, with all dependencies pinned in `requirements.txt`. Test suite: **228 tests passing** in the workspace run of 2 November `[confirm on the laptop with test.bat]`. One known environment-dependent failure: `test_upsert_is_idempotent` fails under DuckDB 2.0.0 (a connection left with an unfinished result) and passes on the pinned version; `upsert_readings` should be made robust before any dependency bump.

Security: a fifteen-item checklist (S1–S15) covering keys, secrets in history, injection, rate limiting, headers, debug state and exposed files. Two full passes, 15 October and 29 October, both passed; the second is at `docs/security/audit-2026-10-29.md`. Pillow was upgraded to 13.0.0 on 30 October.

**A key-exposure incident is reported in full in Chapter 8.** It is included because concealing it would be the more serious failure.

---

## 4. The system

`[Architecture figure. Screenshots to be captured in Week 4.]`

**Five views:** stations in 3D, city overview, compare, timeline, forecast. Every 3D view has a **2D ranked-bar companion**, because extruded columns distort height comparison (W10). A wind layer, a coverage map and the station-placement output complete the set.

Application sections: the map and its controls; the question box with show-the-query; "Priority and response" (station priority, health response, scenario calculator). A "Recentre map" control was added on 30 October, along with a warning shown when no station has reported in the last three hours — which explains an empty chart rather than leaving it unexplained.

Engineering detail stays in `docs/plan/plan.md`; this chapter is short by design.

---

## 5. Results

### 5.1 Data quality and coverage

As Chapter 3.1: 53.4% of station-hours over the whole archive (to 6 Nov), 8.0% missing in the stable window, by station 4.2% to 9.9%. One permanent 76-hour gap, plus night gaps from 30 Oct. The city-level series is complete. 7,215 rows lost to merge conflicts were restored. `[Figure: hourly coverage by station.]`

### 5.2 AQI harmonisation (W1)

As Chapter 3.3. The headline: **with the table in force at each hour, 99.1% of 3,293 station-hours reproduced exactly, MAE 0.16 [0.05, 0.31]**. The portal changed its table on 3 November, and the earlier 3.74 figure mixed its old saturation at 500 into the error. The window comparison (1 h 1.7, 8 h 45.1, 24 h 54.7, on the 210-hour sample) establishes that the portal reports a 1-hour window. Residual: CO-dominant hours (0.6%).

### 5.3 CAMS against ground stations (RQ2, C4)

313 paired hours, 14 October to 6 November 2026 (restored archive). Intervals are a moving-block bootstrap with 6-hour blocks. The 29 October run on 211 hours is kept below for comparison.

| Quantity | n | MAD [95% CI] | Bias [95% CI] | r | 29 Oct (211 h): bias, r |
|---|---:|---|---|---:|---|
| PM2.5 µg/m³ | 313 | 61.1 [48.5, 75.5] | −57.7 [−73.2, −44.0] | 0.68 | −47.7, 0.65 |
| PM10 µg/m³ | 313 | 192.9 [168.4, 219.8] | −191.7 [−219.1, −166.6] | 0.65 | −178.8, 0.59 |
| AQI (PM-only, portal scale) | 313 | 69.3 [55.9, 85.0] | −65.4 [−82.0, −50.8] | 0.69 | −45.4, 0.65 |

The bias has grown as the season has deepened (−20 on 30 hours, −48 on 211, −58 on 313). CAMS follows the ups and downs but misses more of the level as smog intensifies, which is consistent with local sources that a 0.4° (about 40 km) cell under-resolves.

**Three findings.**

1. **CAMS is useful for trend, not for level.** r = 0.68 city-mean (313 h). The correlation rises when CAMS is shifted by two hours, but the sign of the best shift has changed between runs (+2 h on 16 Oct, −2 to −3 h on 29 Oct, +2 h on 6 Nov), so no timing offset is claimed. The bias does not move with the shift: the problem is magnitude, not timing. Displaying a CAMS value as "current air quality" would mislead.
2. **PM10 is effectively untracked.** A bias of −179 µg/m³ means the coarse fraction — dust, construction, road — is invisible to a 45 km cell.
3. **Within-city variation is extreme and CAMS cannot see it.** Per-station PM2.5 MAD runs from **Gulberg III 27.8 (bias +7.1)** to **Multan Road 102.5 (bias −101.2)** on 313 hours (29 Oct: 26.5 to 95.4). CAMS tracks the clean residential station well and under-reads the roadside and industrial sites badly. This is the quantitative case for a station-level 3D map rather than a modelled surface.

**Honest notes.** A preliminary 30-hour analysis on 24 October found a bias of −20.4, r 0.85, and a best lag of **+2** hours. The two-week dataset reversed the lag and more than doubled the bias. The preliminary result was noise from too few hours, and it is reported here because it shows how misleading a 30-hour window was. Framing throughout is **agreement, not error**: the station instruments are uncalibrated and sometimes offline, so this measures how far model and stations agree (W9).

### 5.4 Forecasting (RQ1, C5)

**Daily (Model A), 131 test days April–August 2024.** LightGBM MAE 13.9 [12.6, 15.7]; persistence 14.5 [12.2, 17.7]; GRU 14.1; LSTM 18.1. **All intervals overlap.** The honest statement is that no model is distinguishable from persistence on this split, and that the deep models did not win. Summer only, so it does not transfer to smog season.

**Hourly CAMS correction (Models B, C), 42 test hours.** Model B MAE 37.3 against raw CAMS 80.4 — a **54% reduction** in CAMS error — but hourly persistence scores 21.1 and beats both. A learned correction fixes CAMS without being useful as a forecast.

**Hourly 1–24 h Lahore AQI (Phase 4.2), re-run 6 November** on the restored archive (`data/eval/forecast_fit_2026-11-06.json`, `forecast_baseline_check_2026-11-06.json`). 690 hourly values; 412 training and **252 test origins**; split at 2026-10-27T00:00Z, fixed on 1 November. Block bootstrap over origins.

Skill against **persistence**:

| Band | Persistence MAE | Ridge (per band) | LightGBM (per band) | Same hour yesterday | Relayed CAMS |
|---|---:|---|---|---|---|
| 1–3 h | 43.6 | +0.14 [+0.06, +0.20] | +0.24 [+0.17, +0.29] | −0.51 | −1.96 [−2.60, −1.50] |
| 4–8 h | 101.3 | +0.29 [+0.12, +0.38] | +0.35 [+0.25, +0.41] | +0.35 | −0.29 [−0.59, −0.12] |
| 9–16 h | 130.0 | +0.34 [+0.16, +0.46] | +0.28 [+0.15, +0.36] | +0.49 | −0.04 [−0.30, +0.12] |
| 17–24 h | 92.7 | +0.02 [−0.27, +0.23] | −0.18 [−0.55, +0.11] | +0.26 | −0.50 [−0.97, −0.10] |
| **All 1–24 h** | **100.6** | **+0.22 [+0.05, +0.34]** | **+0.15 [+0.01, +0.26]** | **+0.34** | −0.34 [−0.63, −0.11] |

The relayed EPA forecast (1–8 h only) is +0.07 overall.

Skill against **the same hour yesterday** (seasonal naive), on the same rows:

| Band | Yesterday MAE | LightGBM (per band) | Ridge (per band) | Blend (training-fitted) |
|---|---:|---|---|---|
| 1–3 h | 65.6 | **+0.49 [+0.25, +0.64]** | +0.43 [+0.16, +0.59] | +0.40 [+0.13, +0.56] |
| 4–8 h | 65.8 | −0.01 [−0.41, +0.25] | −0.10 [−0.52, +0.15] | +0.05 [−0.10, +0.17] |
| 9–16 h | 66.8 | −0.41 [−1.03, +0.03] | −0.28 [−0.81, +0.08] | +0.01 [−0.06, +0.08] |
| 17–24 h | 68.2 | −0.61 [−1.54, −0.08] | −0.34 [−0.99, +0.04] | −0.00 [−0.06, +0.05] |
| All 1–24 h | 66.9 | −0.27 [−0.80, +0.07] | −0.17 [−0.58, +0.12] | **+0.06 [−0.02, +0.13]** |

**The answer to RQ1, stated carefully.** The learned models beat persistence over 1–24 hours with intervals that exclude zero, and the relayed forecasts do not: CAMS is worse than persistence at every band. **But persistence is the weak baseline in a smog season with a strong daily cycle.** The same hour yesterday beats persistence by a third. Beyond three hours, no learned model beats it. The models win only at 1–3 hours, where they are about half as wrong as yesterday. The 2 November result already showed yesterday (+0.28) level with the best model (+0.26), and it should have been reported beside it. A one-weight-per-horizon blend of the last value and yesterday is the best overall (MAE 62.6). Its weights were fitted on training rows only, but it was added after seeing the result, so it is exploratory.

Five qualifications, all of which belong beside the result:

- **Two baselines, not one.** Skill is reported against both from now on; the stronger, yesterday, is the bar from 4 h on.
- **The per-band models and the blend are post hoc.** The single-model variants lose at 1–3 hours, so the per-band fit was added after seeing the data; the blend likewise.
- **The test period is far heavier smog than training** (mean AQI 301 against 175; range up to 500 against 419), which is the likely reason the 17–24 h band goes negative.
- **The archive is about four weeks long**, so every hourly result is a short-window result.
- **Nothing beyond 24 hours exists in the archive** (CAMS 24 h, EPA 8 h), so days two to four cannot be scored, and the product scope stays at 48 hours.

## 6. Discussion

Six points, each tied to a result above.

**1. The larger model did not win, twice.** LightGBM matched or beat the LSTM and GRU on daily forecasting (5.4); `gpt-oss-120b` and `gpt-oss-20b` scored identically on the language benchmark (5.5). At this data size and task difficulty, capacity is not the binding constraint. This is consistent with Shwartz-Ziv and Armon (2022) on small tabular data, and it is worth stating once as a theme rather than twice as a surprise.

**2. The baseline decides the verdict.** Against persistence the learned models show positive skill over 1–24 hours, and the relayed CAMS and EPA forecasts do not (5.4). Against "the same hour yesterday" the models win only at 1–3 hours. In a season with a strong daily cycle, the honest yardstick is the stronger simple baseline, not the conventional one. The caveats are load-bearing: post hoc band choice, a heavy-smog test period, and no skill at all demonstrated beyond 16 hours.

**3. A global reanalysis is a trend instrument, not a measurement.** CAMS correlates with ground truth and even leads it by two to three hours, but sits about 48 µg/m³ low on PM2.5 and 179 low on PM10, and is blind to the within-city gradient (5.3). This is the empirical justification for the whole design choice of showing only measured station values on the map.

**4. Refusing well is most of the job.** Thirty-five per cent of what real users ask is out of scope, against 10% in the development benchmark (5.5). A system that answers in-scope questions at 90% but handles the refusal path poorly will be experienced as bad, because refusal is the first thing a third of users meet. The cheap, correct improvement is a refusal that names what the system *can* do.

**5. The schema is richer than the demand.** Four of the twelve form fields were never used by any of the 62 real questions (3.5). The schema was designed for a query space — thresholds, two-city comparisons, explicit metrics — that these users did not enter. That is a finding about conversational analytics design, not a flaw to hide: it suggests building the form outward from observed demand rather than from what the data model can express.

**6. The bound on response time is a billing tier, not an engine.** Pipeline time outside the model call is about 20 ms; the model round trip is 1.13 s; the free-tier limit costs 15 s per question beyond three a minute (5.6). The same pattern appears in the parallel work, where a 4× speed-up is swamped by a 2 s politeness delay (5.6). **In both cases the engineering that mattered was not the optimisation.** That is worth saying plainly in a parallel-computing course report.

---

## 7. Weaknesses and limitations

Verdicts against the fifteen weaknesses identified in self-review (`plan.md` Part E). A verdict is **Met** only where there is evidence in this report.

| | Weakness | Mitigation | Evidence | Verdict |
|---|---|---|---|---|
| W1 | Station AQI vs CAMS concentration: different units and formulas | Recover the portal's own scale | 5.2: 99.1% exact, MAE 0.16 [0.05, 0.31] on 3,293 station-hours, with the portal's 3 Nov table change dated | **Met.** Residual is CO-dominant hours (0.6%); PM2.5 top band still extrapolated under the new table |
| W2 | Benchmark written by the system's builder | Classmates write blind; second annotator; kappa | 62 blind questions collected; **but the gold labels were a model draft accepted unchanged** | **NOT MET as of 4 Nov.** See `validity-review-2026-11-04.md`. Corrective plan in 3.5; verdict cannot be Met until independent annotation is complete |
| W3 | Contribution mistaken for "just structured output" | Frame as scoring the *visual* answer | 1.4 framing; C1 wording | **Met in framing**; relies on the report and viva being consistent |
| W4 | Small samples | Intervals on every figure; no claims inside the noise | Wilson and bootstrap intervals throughout Chapter 5 | **Met** |
| W5 | No single correct camera | Score camera by level and direction category | v0 camera n = 5; classmate set n = 1 | **Partially met.** The rubric exists; the evidence base is too thin to report a camera accuracy |
| W6 | LLM answers vary between runs | Temperature 0; repeated runs; report consistency | 100% consistency on both models, v0 | **Met for v0**; to be repeated on the test set |
| W7 | Forecast may not beat the baseline | CAMS forecast as an input feature | 5.4: against persistence +0.15 to +0.22 over 1–24 h; against the same hour yesterday, wins only at 1–3 h | **Partly met.** Beats persistence; matches but does not beat the seasonal baseline beyond 3 h; post hoc; heavy-smog test period |
| W8 | Placement ignores pollution sources | Add roads and industrial land | 5.8 | **Reduced.** Still a heuristic, not a siting study |
| W9 | Station readings may be inaccurate | Frame C4 as agreement; report uptime | 5.3 framed as agreement; coverage in 5.1 | **Handled.** US Consulate cross-check `[pending]` |
| W10 | 3D columns distort height comparison | 2D ranked bar beside every 3D view | Chapter 4 | **Met** |
| W11 | A website may not reach the public | Name real target users | E4 not started | **Not met.** Public demand is not measured and the report should not claim it is |
| W12 | English-only questions | Roman Urdu test set | v0 10 items (14%); classmate set 37 (60%) | **Partially met.** v0's 10 items distinguish nothing; the fresh set must carry Roman Urdu near half. Urdu script remains unsupported |
| W13 | Free tiers and libraries change | Pin versions; offline demo | `requirements.txt` pinned; offline rehearsal `[pending]` | **Met for pinning** |
| W14 | One person, ten weeks | Fixed cut order; optional features last | HISTORY shows the compression to four weeks with nothing cut | **Managed, not eliminated** |
| W15 | No licence for EPA data | Permission request; derived statistics only | **Permission to use the data granted 4 Nov via the supervisor, no additional data** | **Met for use.** Whether raw redistribution is covered is unconfirmed; the repository is public and holds the archive — resolve before deployment |

### Cross-cutting limitations

- **The hourly archive is about four weeks old and roughly half populated.** Every hourly model is undertrained, and every hourly result is a short-window result.
- **One city in depth.** Lahore only; other cities are city-level comparison points.
- **Laptop-dependent collection** means data is lost whenever one machine is off (3.2).
- **Single-machine timings.** All performance figures come from one laptop; they do not generalise to other hardware.
- **Smog season only.** Validation and the hourly forecast test both fall in October–November. Nothing here speaks to the rest of the year.
- **The classmate sample is three data-science students at one university**, recruited by one team member. The direction of the gaps it reveals (too few refusals, too little Roman Urdu) is supportable; the exact proportions are not, and no interval should be attached to them.
- **The user study, when it runs, will be a small convenience sample with an observer present**, which inflates success.

---

## 8. Ethics, security and licensing

**Data licensing.** Per Chapter 3.1. Permission to use the Punjab EPA data was granted through the supervisor on 4 November 2026, with the explicit answer that no additional data would be supplied. `[Paste the reply.]` **Whether that permission extends to republishing the raw hourly archive is not confirmed, and the repository is public and contains it. This must be settled before deployment.** WAQI is display-only and is never written to storage, per its terms. OpenStreetMap (ODbL) and WorldPop (CC BY 4.0) attributions appear in the application and in `SOURCES.md`.

**Participant privacy.** The study records an anonymous id, the text typed, timings and answers. No name, contact detail, voice, face or screen recording of a person. Consent is read aloud and recorded as yes or no. **No formal ethics sign-off was sought**, on the basis that this is a non-clinical usability study of eight to ten adults. That decision, and the fact that no supervisor approval was requested for it, is stated here rather than omitted.

**Security.** Fifteen-item checklist, two full passes (15 and 29 October), both passed. Keys live only in `.env`, never in the repository and never in chat. SQL is parameterised, input is escaped, rate limits are enforced, debug is off.

**The key-exposure incident, 30–31 October.** A live Groq API key was visible in a screenshot of a `.env` file and was exposed. It was revoked and confirmed dead (HTTP 401). A replacement, visible in a second screenshot, was also revoked. The key now in use passes a live check, and `scripts/check_secrets.py --live` was added so the check is automatic. A standing rule was adopted: **never screenshot a page while a key is visible.** This is reported in full because an undisclosed incident is a worse failure than a disclosed one, and because the corrective control is part of the contribution.

**Claims the system does not make.** No medical advice. No causal attribution of pollution. No effect prediction from the scenario calculator. No value for any unmonitored place.

---

## 9. Conclusion and future work

**RQ1 — can a learned forecaster beat persistence, CAMS and the EPA forecast?** It beats persistence and both relayed forecasts. It does not beat "the same hour yesterday" beyond three hours, and that is the stronger baseline in smog season. The relayed CAMS forecast is worse than persistence at every horizon. The qualifications in 5.4 — post hoc band selection, a heavy-smog test period, a four-week archive — are part of the answer, not footnotes to it.

**RQ2 — how well does CAMS match ground stations?** Well in trend (r 0.68), poorly in level (PM2.5 bias −57.7 [−73.2, −44.0], PM10 −191.7, both growing with the season), and not at all in within-city structure (per-station PM2.5 MAD 27.8 to 102.5), on 313 hours. This is the first such quantification published for Lahore.

**RQ3 — can a conversational interface answer air-quality questions reliably?** `[PENDING a valid test set.]` The development benchmark reaches 90.0% [83.3, 95.6] on 90 items with 100% run-to-run consistency, and the collected evidence on what real users ask is reported in 5.5. The honest position on 4 November is that **reliability has not yet been measured on held-out data**, and the report says so.

**RQ4 — can the data support a defensible intervention-priority score?** Yes for a transparent, data-confidence-flagged severity ranking, and no for anything that predicts the effect of an intervention. The scenario calculator deliberately computes coverage only.

**Future work.** A longer archive with rolling-origin evaluation; a winter test period; the top-band AQI refit as readings above 350 accumulate; more cities in depth; multi-turn handling, which is the measured weak point of the language layer; a refusal that names what the system can answer; and a public deployment with feedback. Methodologically: a benchmark whose fields are carried by enough items to be worth reporting, built outward from observed demand.

---

## References and appendices

**References.** 26 verified references from the proposal, plus the additions in Chapter 2, each verified before use.

**Appendices.** A: annotator guide v3. B: benchmark questions and gold labels. C: per-field accuracy tables with n and Wilson intervals. D: evaluation scorecards (`data/eval/*.json`). E: test list. F: prompt v5 (and v4, under which v0 was scored). G: security audit, 29 October. H: E4 materials (plan, recording sheet, SUS sheet). I: the benchmark validity review of 4 November.

### Evidence ledger

| Result | Source |
|---|---|
| Coverage and gaps | archive CSVs; HISTORY 31 Oct |
| AQI harmonisation | `scripts/w1_check.py`; `docs/research/w1-harmonisation.md` |
| CAMS validation | `scripts/cams_validation.py`; `docs/research/cams-validation.md` |
| Daily and hourly models | `scripts/model_a_*.py`, `scripts/model_bc.py` |
| Hourly 1–24 h forecaster | `data/eval/forecast_fit_2026-11-06.json`, `forecast_baseline_check_2026-11-06.json` (2 Nov run superseded) |
| AQI table change, W1 re-score | `data/eval/w1_rescore_2026-11-06.json`; `docs/research/w1-portal-table-change-2026-11-06.md` |
| Archive merge loss and restore | `scripts/recover_archive_rows.py`; `docs/research/archive-merge-loss-2026-11-06.md` |
| Language layer v0 | `data/eval/e1_*_2026-10-30.json`; `docs/research/benchmark-v0-prompt-v4-2026-10-30.md` |
| What users ask | `docs/research/classmate-questions-2026-10-30.md` |
| Benchmark validity | `docs/benchmark/validity-review-2026-11-04.md` |
| Response time | `data/eval/e6_latency_model_2026-11-01_pace18.json` |
| Parallel speed-up | `data/eval/e5_parallel_2026-11-01.json` |
| Benchmark v1 | `[not yet produced]` |
| User study | `[not yet produced]` |

### What must happen before this draft becomes a report

1. **Schema freeze: done 6 Nov (prompt v5).** Then the fresh question collection and independent annotation (3.5; `docs/benchmark/v1-packet-2026-11-06.md`). Until then W2 is not met and 5.5 has no headline.
2. **E4 sessions**, scheduled and run (5.7).
3. **Frames per second**, measured by hand (5.6).
4. **The EPA reply pasted in**, and the raw-redistribution question settled (3.1, 8).
5. **Figures and screenshots** captured.
6. **Chapter 2 citations**: verified 6 Nov (`citation-check-2026-11-06.md`). Remaining: TVCG volume and page numbers for refs 3 to 5, from the publisher.
7. **Contribution statement** agreed with the team.

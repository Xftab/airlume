# Airlume — final report (working draft 1)

**Status: working draft, 4 November 2026.** Written early, against the outline in `09-report-outline.md`, so that results land in finished prose as they arrive rather than in a rush in Week 4. Every number here is traced to a file named beside it. Anything not yet measured is marked `[PENDING]` and must not be filled with an estimate. Format, template, page limit and citation style: `[get from UMT FYP guidelines or Dr Rimsha Anam]`.

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
4. **Forecasting with limited ground data.** Shwartz-Ziv and Armon (2022) on tree ensembles versus deep models on small tabular data — directly relevant to the finding in 5.4.
5. **Monitoring-network siting.** The 2022 ISPRS Lahore study, the comparison point for C7.
6. **Intervention evidence.** Gupta et al. (2022) on anti-smog guns. `[Verify before citing; the scenario calculator makes no effect claim, so this is background only.]`

**Statistical methods cited in place:** Wilson (1927) score intervals, Newcombe (1998) for a difference of proportions, Landis and Koch (1977) for kappa bands, Brooke (1996) for the System Usability Scale, Karp and Flatt (1990) for the serial-fraction estimate. `[Confirm each reference's details.]`

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

**Coverage, measured rather than assumed.** Over the whole hourly archive (14 Oct 04:00Z to 31 Oct 09:00Z) the system holds **2,395 of 4,554 possible station-hours, 52.6%**, with 229 of 414 hours carrying any data at all. Over the stable window 15 Oct 06:00Z to 24 Oct 02:00Z, **8.0% of station-hours are missing**, ranging by station from 4.2% to 9.9% (Gulberg III highest, and not an outlier).

The gap between those two figures is the point. A single headline coverage number would be misleading: most of the loss comes from two identifiable incidents, not from steady attrition.

**Two known gaps, both permanent or explained.**
- **24 Oct 02:00Z to 28 Oct 16:00Z, 110 hours.** On 25 October the GitHub Actions runner stopped being able to reach the Punjab EPA portal, apparently a geographic block. Collection moved to the laptop on 28 October. These station rows cannot be recovered; the EPA has confirmed it will supply no additional data. City-level values are partially recoverable from the portal's rolling 7-day trend.
- **One hour, 2026-10-17T03:00:00Z,** missing from the local archive. Present on GitHub; a local copy exists in a stash backup and is not yet merged.

An earlier figure of 4.5% missing circulated internally; it was the 210-hour W1 sample only, not the archive. A "42%" figure also noted earlier did not reproduce. The measured value is 52.6%, and the discrepancies are recorded here because the report should show how a number was arrived at, not only its final value.

### 3.2 Collection architecture

Collection is **hybrid**, and not by preference. CAMS is fetched hourly by GitHub Actions. The Punjab EPA portal is fetched hourly by a scheduled task on a laptop in Lahore, because the cloud runner cannot reach it.

The honest consequence: **when the laptop is off, data is lost.** This happened between 28 and 30 October, when the scheduled task was found never to have run since registration — Windows power defaults had suspended it (error 0x800710E0). It was fixed with an explicit `Set-ScheduledTask` call and verified. Gaps of this kind are displayed in the application rather than filled silently.

The portal is read once per hour with a cache-buster and a named user agent. It is server-rendered with no public JSON feed; an undocumented `api.aqi.punjab.gov.pk` exists and was deliberately not probed.

### 3.3 AQI computation and harmonisation (weakness W1)

The first serious validity problem found in this project was that the portal's AQI could not be reproduced with the US EPA 2012 breakpoints. A station reading compared against a CAMS concentration is not a comparison at all if the two use different formulas.

Recovered from 304 stored rows on 16 October: **the portal uses its own NEQS-anchored table, with gases in µg/m³** — 99.7% of rows reproduced exactly and 100% within one point, against 6% exact for the US 2012 table. This became the default scale in `airlume/aqi.py`.

Confirmed at scale on 24 October over 2,206 station-hours (MAE 1.7, median 0.0), and with a moving-block bootstrap on 29 October:

| Window | MAE | 95% CI |
|---|---|---|
| 1 hour (adopted) | **3.74** | [2.01, 5.78] |
| 1 hour, rows below the portal's 500 cap | **0.31** | — |
| 8 hour | 45.1 | — |
| 24 hour | 54.7 | — |

The residual error is **almost entirely top-band saturation**: the portal caps its display at 500, so 91 rows at exactly 500 represent unknown true values above it. Below the cap the reproduction is essentially exact. The one 99-point outlier investigated on 28 October has the same explanation.

### 3.4 The language layer

A question goes through four stages: **route** (model fills a typed `ViewIntent` form), **validate** (code checks the form against the schema), **resolve** (code turns the form into a query against the store), **answer** (code writes the sentence and selects the view).

Design features that follow from the four rules:
- **Show-the-query.** The filled form is visible on screen, so the rubric's input can be watched live.
- **Clarifying questions** where a form cannot be filled unambiguously.
- **Follow-ups**, carrying context across turns.
- **Coverage notes.** A question about an unmonitored place names the nearest station and its distance rather than estimating.
- **Window-aware city answers** (1 November). City-level answers used to quote the current value whatever window was asked; they now aggregate the stored hourly series for the requested window and state the window and the hours of data behind it.
- **Out-of-archive windows** (1 November). A window the archive does not reach now produces a sentence saying what the archive covers, rather than "No data for that place and time". This came directly from a benchmark failure (q024) where the model returned a 2023 date range from its training era.

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

**Annotation.** Two annotators who have not seen any model draft fill the form independently from annotator guide v2. Disagreements are adjudicated against the written guide, with the governing rule recorded for each. Where the guide is silent, that is a guide gap: the guide is amended and both annotators re-decide.

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

As Chapter 3.1: 52.6% of station-hours over the whole archive, 8.0% missing in the stable window, by station 4.2% to 9.9%, one permanent 110-hour gap. `[Figure: hourly coverage by station.]`

### 5.2 AQI harmonisation (W1)

As Chapter 3.3. The headline: **MAE 3.74 [2.01, 5.78] over 2,217 rows; 0.31 below the portal's 500 cap.** The window comparison (1 h 1.7, 8 h 45.1, 24 h 54.7, on the 210-hour sample) establishes that the portal reports a 1-hour window.

### 5.3 CAMS against ground stations (RQ2, C4)

211 paired hours, 13–28 October 2026. All intervals are moving-block bootstrap (6-hour blocks, 5,000 resamples).

| Quantity | n | MAD [95% CI] | Bias [95% CI] | r |
|---|---:|---|---|---:|
| PM2.5 µg/m³ | 211 | 49.8 [39.1, 63.6] | −47.7 [−62.0, −36.6] | 0.65 |
| PM10 µg/m³ | 211 | 179.4 [153.3, 208.3] | −178.8 [−207.7, −152.2] | 0.59 |
| AQI (PM-only, portal scale) | 211 | 47.5 [37.2, 59.9] | −45.4 [−58.6, −34.7] | 0.65 |

**Three findings.**

1. **CAMS is useful for trend, not for level.** r = 0.65 city-mean, rising to **0.77 at a lag of −2 to −3 hours** — CAMS leads the surface monitors, consistent with the model capturing boundary-layer mixing before the ground responds. But the bias is stable at about −48 µg/m³ regardless of shift: the problem is magnitude, not timing. Displaying a CAMS value as "current air quality" would mislead.
2. **PM10 is effectively untracked.** A bias of −179 µg/m³ means the coarse fraction — dust, construction, road — is invisible to a 45 km cell.
3. **Within-city variation is extreme and CAMS cannot see it.** Per-station PM2.5 MAD runs from **Gulberg III 26.5 (bias +4.2, r 0.73)** to **Multan Road 95.4 (bias −94.6, r 0.39)**. CAMS tracks the clean residential station well and under-reads the roadside and industrial sites badly. This is the quantitative case for a station-level 3D map rather than a modelled surface.

**Honest notes.** A preliminary 30-hour analysis on 24 October found a bias of −20.4, r 0.85, and a best lag of **+2** hours. The two-week dataset reversed the lag and more than doubled the bias. The preliminary result was noise from too few hours, and it is reported here because it shows how misleading a 30-hour window was. Framing throughout is **agreement, not error**: the station instruments are uncalibrated and sometimes offline, so this measures how far model and stations agree (W9).

### 5.4 Forecasting (RQ1, C5)

**Daily (Model A), 131 test days April–August 2024.** LightGBM MAE 13.9 [12.6, 15.7]; persistence 14.5 [12.2, 17.7]; GRU 14.1; LSTM 18.1. **All intervals overlap.** The honest statement is that no model is distinguishable from persistence on this split, and that the deep models did not win. Summer only, so it does not transfer to smog season.

**Hourly CAMS correction (Models B, C), 42 test hours.** Model B MAE 37.3 against raw CAMS 80.4 — a **54% reduction** in CAMS error — but hourly persistence scores 21.1 and beats both. A learned correction fixes CAMS without being useful as a forecast.

**Hourly 1–24 h Lahore AQI (Phase 4.2), re-run 2 November.** 584 hourly values, 412 training and 146 test origins, split at 2026-10-27T00:00Z. Skill against persistence, block bootstrap over origins:

| Band | Persistence MAE | Ridge (per band) | LightGBM (per band) | Relayed CAMS | Relayed EPA |
|---|---:|---|---|---|---|
| 1–3 h | 42.7 | +0.16 [+0.14, +0.21] | +0.23 [+0.09, +0.32] | −2.04 [−2.58, −0.76] | −0.30 [−0.42, −0.10] |
| 4–8 h | 99.6 | +0.27 [+0.11, +0.37] | +0.31 [+0.21, +0.39] | −0.37 [−0.66, +0.24] | +0.04 [−0.02, +0.23] |
| 9–16 h | 128.0 | +0.35 [+0.20, +0.45] | +0.26 [+0.15, +0.39] | +0.03 [−0.29, +0.35] | — |
| 17–24 h | 96.5 | +0.15 [−0.01, +0.37] | +0.10 [−0.11, +0.42] | −0.08 [−0.79, +0.51] | — |
| **All 1–24 h** | **100.4** | **+0.26 [+0.12, +0.37]** | **+0.22 [+0.07, +0.36]** | −0.20 [−0.58, +0.28] | −0.04 [−0.10, +0.14] |

**The answer to RQ1, stated carefully.** A simple learned model trained on the local archive beats persistence over 1–24 hours, with an interval that excludes zero. **The relayed forecasts do not** — the official EPA forecast and the relayed CAMS forecast both score at or below persistence, and CAMS is dramatically worse at 1–3 hours. Four qualifications, all of which belong beside the result:

- **The 17–24 h band includes zero** for both models. Skill is real at short and medium range and unproven at a day out.
- **The single-model variants lose at 1–3 hours**; only the per-band fit wins there, and **the per-band choice was made after seeing the data, so it is post hoc.**
- **The test period is far heavier smog than training** (mean AQI 273 against 175; range 100–486 against 67–419). How far the skill transfers to a normal period is untested.
- **Nothing beyond 24 hours exists in the archive** — the longest stored horizon is 24 h for CAMS and 8 h for EPA — so days two to four cannot be scored at all, and the product scope stays at 48 hours maximum.

### 5.5 The language layer (RQ3, C1, C2)

**Benchmark v0, 90 items, prompt v4, 30 October — a development result.**

| Run | Prompt | Pass | 95% CI | Consistency |
|---|---|---|---|---|
| gpt-oss-120b, 15 Oct | v3 | 88.9% | [82, 96] | 100% |
| gpt-oss-120b, 30 Oct | v4 | **90.0%** | [83.3, 95.6] | 100% |
| gpt-oss-20b, 30 Oct | v4 | **90.0%** | [83.3, 95.6] | 100% |

**v4 is safe:** no item that passed under v3 fails under v4, and one that failed now passes. The 1.1-point rise *is* that single item, and the intervals overlap almost entirely, so the honest statement is "no measurable change", not "v4 improved the router".

**The two models are indistinguishable and fail differently.** Both land on exactly 90.0%. 120b fails four follow-ups; 20b fails three plus one `best_time` and one `forecast`. **Five times the parameters buys nothing measurable here** — the second time in this project that the larger or deeper model did not win (see 5.4).

**`follow_up` is the weakest class:** 16/20 on 120b, 17/20 on 20b, and nearly half of all failures. Multi-turn context is the thing to improve if anything is.

Two failures worth naming rather than burying:
- **q002, "Which station has the cleanest air at the moment?"** Both models answer `aggregation: min`; the gold is `latest`. The prompt says so in capitals. When an explicit capitalised instruction fails on both models, the convention is probably fighting the semantics: "cleanest" is a superlative and `min` is the obvious word. The gold is still right — `min` means a minimum over a window and `now` has no window — but the distinction is subtle and belongs in the report rather than in a failure list.
- **q024, "Was October worse than September in Lahore?"** The model returned a range in **2023**, from its training era. The resolver checked the date was well-formed but not that it fell inside the archive, so it resolved to a valid empty window and the user saw "No data for that place and time". No invented value was ever shown, so rule 3 held — but the message hid the cause. Fixed on 1 November (3.4).

**Per-field accuracy** is reported as correct/n with Wilson intervals in Appendix `[ref]`. The reporting trap is worth stating once: of fourteen fields, one is carried by a single item. A `0%` in such a cell is one item decided one way, not a quality difference. `city` 69/69, `view` 43/46, `time` 43/44, `aggregation` 38/40 on 120b are the only figures with enough items to carry a claim.

**Roman Urdu in v0 rests on ten items** (9/10 and 8/10). That distinguishes nothing, and it is 14% of v0 against the 60% that real users wrote.

**What real users ask (the classmate set, 62 questions, 30 October).** This is a result in its own right, independent of any labelling:

| Bucket | n | Share |
|---|---:|---:|
| In scope | 40 | 65% |
| — of which answerable only because of the graded-response module | 12 | 19% |
| Out: weather (rain, sunrise) | 8 | 13% |
| Out: causes, or effect of an intervention | 6 | 10% |
| Out: medical effects | 3 | 5% |
| Out: beyond the forecast horizon | 2 | 3% |
| Out: unmonitored place, general knowledge, indoor air | 3 | 5% |
| **Out of scope, total** | **22** | **35%** |

Three findings follow.

1. **v0 under-represents refusal by about three and a half times** (10% against 35%). The single most common thing a first-time user asks is something the system is designed not to answer, and the development benchmark barely tested that path.
2. **v0 badly under-weights Roman Urdu** (14% against 60%). The project claims the two languages as equal first-class inputs; the users it was built for wrote Roman Urdu more often than English. v0's share was set by the team's own writing habits.
3. **The graded-response module was independently validated.** Nineteen per cent of questions are health-advice questions, and every one is answerable only because of a module specified on 29 October, *before* these questions were collected. One maps exactly onto its `vulnerable_groups` field. It is the difference between 46% and 65% in-scope coverage.

The largest out-of-scope bucket is weather. People approach an air-quality app as a weather app. The project holds ERA5 history, so the data exists, but answering weather questions stays out of scope: **the refusal is correct and the fix is wording, not features.** A refusal that says what Airlume *can* answer instead of only what it cannot would improve roughly a third of first questions.

**Benchmark v1. `[PENDING]`** Gold labels, pass rate by language with Wilson intervals, the English-minus-Roman-Urdu gap with a Newcombe interval, the scope decision alone, and inter-annotator kappa. Blocked on the schema freeze and the fresh collection (3.5). **The report must not present any figure scored against the 4 November draft labels.**

### 5.6 Performance (E5, E6)

**Response time (E6, 1 November, gpt-oss-20b, 30 questions).** Model round trip **median 1.13 s [1.03, 1.26]**, p95 1.55 s, max 2.05 s. Resolve is 0.0001 s and answer 0.018 s — **the rest of the pipeline is about 20 ms**, so essentially all latency is the model call. Store build 0.589 s.

The practical bound is not compute. On the free tier, above roughly three questions a minute the system waits about 15 s per question. **Rate limiting, not hardware, sets the ceiling.**

**Parallel extraction (E5, CC425, 1 November).** 300 PDFs, 72.6 MB, 3 repeats, on an i7-1355U with 8 GB RAM, 10 physical / 12 logical cores, on mains power.

| Design | Workers | Median s | Speed-up | Efficiency | Serial fraction | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|
| sequential | 1 | 54.6 | 1.00 | 1.00 | — | 372 MB |
| multiprocess | 2 | 32.1 | 1.70 | 0.85 | 0.176 | 628 MB |
| multiprocess | 4 | 21.5 | 2.54 | 0.63 | 0.192 | 935 MB |
| multiprocess | 8 | 16.2 | 3.37 | 0.42 | 0.196 | 1,369 MB |
| multiprocess | 12 | 13.8 | 3.95 | 0.33 | 0.186 | 2,080 MB |
| async | 8 | — | 3.35 | — | 0.231 | — |

**Results are byte-identical across every configuration** (zero mismatches against sequential), which is the property that matters for a data pipeline. The Karp–Flatt serial fraction sits at **about 0.19** and is stable as workers increase, so the ceiling is Amdahl's, not contention. Efficiency falls below half at eight workers and memory roughly doubles from four to twelve.

**And the result that matters practically:** the real back-fill waits 2 s between requests out of politeness, so downloading 1,990 files cannot take less than **3,980 s** whatever the parallel design. Parsing is 0.182 s per file sequentially. **The task is download-bound by two orders of magnitude, and the parallel speed-up, while real, is irrelevant to the wall-clock time of the actual job.** The honest engineering conclusion is to report the measured speed-up and then say it does not help here. `[Note: the async figures use a local server with a fixed 100 ms delay — a model of latency, not a measurement of the EPD server.]`

**Map frames per second: `[PENDING — measure by hand.]`**

### 5.7 User study (E4) — `[PENDING]`

Plan at `docs/study/user-study-plan-2026-11-01.md`: 8–10 participants, none of them team members, at least four habitual Roman Urdu writers; three task-shaped goals; System Usability Scale; two open questions. Task success as correct/n with Wilson intervals, time as median and range, SUS with a bootstrap interval. Ground truth is read from the store before each session so a stale map cannot make a correct answer look wrong.

**Not started as of 4 November.** No supervisor approval is being sought and no formal ethics sign-off was obtained; the report states this plainly in Chapter 8 and in the limitations. The planned window of 4–8 November has passed and no dates are set.

### 5.8 Insights (RQ4, C7)

`[Priority-score examples with their data-confidence flags; the graded-response menu; one scenario-calculator example with its assumptions stated; the station-placement output with coverage gained per proposed site.]`

Population coverage and placement use the WorldPop 1 km grid and OpenStreetMap land use, excluding water, aerodrome and military cells and scoring proximity to roads and industrial land.

---

## 6. Discussion

Six points, each tied to a result above.

**1. The larger model did not win, twice.** LightGBM matched or beat the LSTM and GRU on daily forecasting (5.4); `gpt-oss-120b` and `gpt-oss-20b` scored identically on the language benchmark (5.5). At this data size and task difficulty, capacity is not the binding constraint. This is consistent with Shwartz-Ziv and Armon (2022) on small tabular data, and it is worth stating once as a theme rather than twice as a surprise.

**2. Learned local correction beats relayed official forecasts — within a narrow window.** Over 1–24 hours the per-band models show positive skill with intervals excluding zero, while both the relayed CAMS and the official EPA forecast score at or below persistence (5.4). The caveats are load-bearing: post hoc band choice, a heavy-smog test period, and no skill at all demonstrated beyond 16 hours.

**3. A global reanalysis is a trend instrument, not a measurement.** CAMS correlates with ground truth and even leads it by two to three hours, but sits about 48 µg/m³ low on PM2.5 and 179 low on PM10, and is blind to the within-city gradient (5.3). This is the empirical justification for the whole design choice of showing only measured station values on the map.

**4. Refusing well is most of the job.** Thirty-five per cent of what real users ask is out of scope, against 10% in the development benchmark (5.5). A system that answers in-scope questions at 90% but handles the refusal path poorly will be experienced as bad, because refusal is the first thing a third of users meet. The cheap, correct improvement is a refusal that names what the system *can* do.

**5. The schema is richer than the demand.** Four of the twelve form fields were never used by any of the 62 real questions (3.5). The schema was designed for a query space — thresholds, two-city comparisons, explicit metrics — that these users did not enter. That is a finding about conversational analytics design, not a flaw to hide: it suggests building the form outward from observed demand rather than from what the data model can express.

**6. The bound on response time is a billing tier, not an engine.** Pipeline time outside the model call is about 20 ms; the model round trip is 1.13 s; the free-tier limit costs 15 s per question beyond three a minute (5.6). The same pattern appears in the parallel work, where a 4× speed-up is swamped by a 2 s politeness delay (5.6). **In both cases the engineering that mattered was not the optimisation.** That is worth saying plainly in a parallel-computing course report.

---

## 7. Weaknesses and limitations

Verdicts against the fifteen weaknesses identified in self-review (`plan.md` Part E). A verdict is **Met** only where there is evidence in this report.

| | Weakness | Mitigation | Evidence | Verdict |
|---|---|---|---|---|
| W1 | Station AQI vs CAMS concentration: different units and formulas | Recover the portal's own scale | 5.2: MAE 3.74 [2.01, 5.78]; 0.31 below the cap | **Met.** Residual is top-band saturation; top PM2.5 band still to confirm on November data |
| W2 | Benchmark written by the system's builder | Classmates write blind; second annotator; kappa | 62 blind questions collected; **but the gold labels were a model draft accepted unchanged** | **NOT MET as of 4 Nov.** See `validity-review-2026-11-04.md`. Corrective plan in 3.5; verdict cannot be Met until independent annotation is complete |
| W3 | Contribution mistaken for "just structured output" | Frame as scoring the *visual* answer | 1.4 framing; C1 wording | **Met in framing**; relies on the report and viva being consistent |
| W4 | Small samples | Intervals on every figure; no claims inside the noise | Wilson and bootstrap intervals throughout Chapter 5 | **Met** |
| W5 | No single correct camera | Score camera by level and direction category | v0 camera n = 5; classmate set n = 1 | **Partially met.** The rubric exists; the evidence base is too thin to report a camera accuracy |
| W6 | LLM answers vary between runs | Temperature 0; repeated runs; report consistency | 100% consistency on both models, v0 | **Met for v0**; to be repeated on the test set |
| W7 | Forecast may not beat the baseline | CAMS forecast as an input feature | 5.4: learned per-band models +0.22 to +0.26; relayed forecasts do not beat persistence | **Reduced, honestly.** Skill is real at 1–16 h, unproven at 17–24 h, post hoc, and from a heavy-smog test period |
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

**RQ1 — can a learned forecaster beat persistence, CAMS and the EPA forecast?** Yes over 1–16 hours, with intervals excluding zero, and no over 17–24 hours. The relayed official forecasts do not beat persistence at any horizon tested. The qualifications in 5.4 — post hoc band selection, a heavy-smog test period, a four-week archive — are part of the answer, not footnotes to it.

**RQ2 — how well does CAMS match ground stations?** Well in trend (r 0.65, rising to 0.77 at a 2–3 hour lead), poorly in level (PM2.5 bias −47.7, PM10 −178.8), and not at all in within-city structure (per-station MAD 26.5 to 95.4). This is the first such quantification published for Lahore.

**RQ3 — can a conversational interface answer air-quality questions reliably?** `[PENDING a valid test set.]` The development benchmark reaches 90.0% [83.3, 95.6] on 90 items with 100% run-to-run consistency, and the collected evidence on what real users ask is reported in 5.5. The honest position on 4 November is that **reliability has not yet been measured on held-out data**, and the report says so.

**RQ4 — can the data support a defensible intervention-priority score?** Yes for a transparent, data-confidence-flagged severity ranking, and no for anything that predicts the effect of an intervention. The scenario calculator deliberately computes coverage only.

**Future work.** A longer archive with rolling-origin evaluation; a winter test period; the top-band AQI refit as readings above 350 accumulate; more cities in depth; multi-turn handling, which is the measured weak point of the language layer; a refusal that names what the system can answer; and a public deployment with feedback. Methodologically: a benchmark whose fields are carried by enough items to be worth reporting, built outward from observed demand.

---

## References and appendices

**References.** 26 verified references from the proposal, plus the additions in Chapter 2, each verified before use.

**Appendices.** A: annotator guide v2. B: benchmark questions and gold labels. C: per-field accuracy tables with n and Wilson intervals. D: evaluation scorecards (`data/eval/*.json`). E: test list. F: prompt v4. G: security audit, 29 October. H: E4 materials (plan, recording sheet, SUS sheet). I: the benchmark validity review of 4 November.

### Evidence ledger

| Result | Source |
|---|---|
| Coverage and gaps | archive CSVs; HISTORY 31 Oct |
| AQI harmonisation | `scripts/w1_check.py`; `docs/research/w1-harmonisation.md` |
| CAMS validation | `scripts/cams_validation.py`; `docs/research/cams-validation.md` |
| Daily and hourly models | `scripts/model_a_*.py`, `scripts/model_bc.py` |
| Hourly 1–24 h forecaster | `data/eval/forecast_fit_2026-11-02.json` |
| Language layer v0 | `data/eval/e1_*_2026-10-30.json`; `docs/research/benchmark-v0-prompt-v4-2026-10-30.md` |
| What users ask | `docs/research/classmate-questions-2026-10-30.md` |
| Benchmark validity | `docs/benchmark/validity-review-2026-11-04.md` |
| Response time | `data/eval/e6_latency_model_2026-11-01_pace18.json` |
| Parallel speed-up | `data/eval/e5_parallel_2026-11-01.json` |
| Benchmark v1 | `[not yet produced]` |
| User study | `[not yet produced]` |

### What must happen before this draft becomes a report

1. **Schema freeze**, then the fresh question collection and independent annotation (3.5). Until then W2 is not met and 5.5 has no headline.
2. **E4 sessions**, scheduled and run (5.7).
3. **Frames per second**, measured by hand (5.6).
4. **The EPA reply pasted in**, and the raw-redistribution question settled (3.1, 8).
5. **Figures and screenshots** captured.
6. **Chapter 2 citations** verified one by one.
7. **Contribution statement** agreed with the team.

---
title: "Airlume"
subtitle: "A Conversational Three-Dimensional Digital Twin of Air Quality in Pakistan's Monitored Cities --- Semester Project Proposal"
author:
  - "Aftab Ahmad, Kiran Saif and Tehreem Fatima"
date: "13 October 2026"
---

# Abstract {.unnumbered .unlisted}

Pakistan has the most polluted air of any country measured in 2025, and Lahore has spent most of the last decade near the top of the world's city rankings. The data describing this problem has improved considerably: the Punjab Environmental Protection Agency now publishes hourly readings from eleven stations in Lahore and from thirty-six districts across the province, and has archived daily bulletins since 2018. What has not improved is the public's ability to *ask questions* of that data. Every available interface, official or commercial, answers one question --- what is the number right now --- and leaves the comparative, spatial and temporal questions that people actually have to be worked out by hand.

This proposal describes **Airlume**, a web application in which a three-dimensional map of air quality is controlled entirely by natural-language questions. A person types *"where was the air worst in Lahore last night?"* or *"is Faisalabad better than Lahore this week?"* and the map moves to the right place, at the right time, and writes a one-sentence answer. The large language model at the centre of the system never writes code or database queries; it fills a strictly typed form --- metric, place, time window, aggregation, view, camera --- which deterministic code validates against a station registry and executes. This design choice is what makes the project evaluable: because every answer is a set of typed fields, correctness can be scored field by field against a frozen benchmark of eighty questions, rather than judged by eye.

The project makes four contributions. It proposes and tests a scoring rubric for *visual* answers in conversational analytics, a gap the authors of the closest prior system (VayuBuddy, 2024) explicitly left as future work. It treats camera pose in a 3D scene as part of the generated answer. It adopts a sparsity-honest visualisation protocol that shows discrete stations, never an interpolated surface, and discloses the distance to the nearest monitor. And it produces the first quantified comparison of the Copernicus CAMS global model against ground stations in Lahore. The system is built on open data at zero cost, and a working skeleton --- live collection from the official portal, a parsed eight-year bulletin archive, and a fake-data 3D shell with sixty passing tests --- already exists as of the date of this proposal.

\newpage

\tableofcontents

\newpage

# Introduction

## The problem behind the numbers

In March 2026 the IQAir *World Air Quality Report* ranked Pakistan the most polluted country of the 143 it measured, with a national annual PM2.5 mean of 67.3 µg/m³ [10]; the previous year's report had placed it third [9]. Lahore's annual mean in 2024 was 102.1 µg/m³, twenty times the World Health Organization's guideline value of 5 µg/m³ [9, 11]. The Air Quality Life Index estimates that a resident of Lahore loses about 5.3 years of life expectancy to particulate pollution relative to that guideline [12]. The smog season, roughly October to February, is driven by a familiar mix of crop-residue burning, vehicle and industrial emissions, brick kilns and construction dust, held close to the ground by winter inversions.

For a long time the shortage was of *measurements*. That has changed. The Punjab Environmental Protection Agency (EPA Punjab) now operates a real-time portal, aqi.punjab.gov.pk, that reports hourly readings of six pollutants from eleven named stations in Lahore and a district-level index for thirty-six districts; its parent department has published a daily Air Quality Index bulletin for Lahore almost every day since January 2018 [7, 8]. In October 2025 the department launched an AI assistant, *EcoBot*, that returns a city's current AQI on request [6].

What remains in short supply is *understanding*. The questions people have about smog are comparative --- which part of the city is worst, is it better than last week, when during the day is it safest to go out, how does this year compare with last --- and no existing interface answers them. The official portal is a dashboard of filters and tables; EcoBot is a lookup; commercial apps paint a smooth colour over the city that is interpolated from a dozen points and tells the user nothing about how far away the nearest real measurement is. Answering a comparative question today means opening several screens and doing the arithmetic in one's head. For a member of the public, that friction means the question goes unasked. For a journalist, teacher or district officer, it means hours of manual work.

## What this project proposes

Airlume turns the question into the interface. The user asks in plain language; a three-dimensional map answers. Zoomed out, every monitored city in Pakistan stands as a column whose height and colour encode its current index. Zoomed in on Lahore --- the one city with enough stations to justify it --- the city opens up station by station, animated through time, with a wind layer. There are no dropdowns to learn. A short sentence, written by code from the retrieved numbers rather than by the language model, accompanies every view.

The engineering is deliberately conservative. The language model's only job is to translate a sentence into a small typed form; everything else --- resolving "last night" into timestamps in Pakistan time, matching "Gulberg" to a station, building the database query, choosing the camera --- is ordinary, testable code. This separation is not a stylistic preference. It is what allows the project to make a measurable claim: that the system understood a question is a proposition that can be checked, field by field, against a gold standard that was frozen before the system was tuned.

## Why this is a research project and not a demonstration

Conversational interfaces to air-quality data already exist in the literature. The nearest is VayuBuddy, an LLM chatbot over Indian government data whose authors benchmarked it on forty-five questions and then observed that scoring whether a *generated plot* was correct, as opposed to a generated number, would need a purpose-built rubric that they left as future work [1]. Its successor, VayuChat, is a deployed system paper with no stated evaluation method [2]. That is the gap this project addresses: it proposes such a rubric, grounds it in a typed intent schema, and applies it in a setting --- a 3D geospatial scene with a camera --- where "the right picture" has more dimensions than a bar chart. The project does not train a new model or claim a new architecture. Its contributions are in systems design, evaluation methodology and local measurement, which is the appropriate level of ambition for a ten-week undergraduate project and, we believe, the honest one.

# Problem statement

The project addresses three concrete deficiencies in how air-quality information currently reaches people in Pakistan.

**Problem 1: data that cannot be questioned.** Public air-quality data is published as current values and fixed charts. Comparative, spatial and temporal questions require manual work across several screens, so they are rarely asked. *Airlume's response:* a natural-language interface over an hourly archive of official readings, in which one sentence in produces one map view and one sentence out.

**Problem 2: maps that imply more than they measure.** Consumer applications interpolate a continuous colour surface from roughly a dozen stations serving eleven million people. A user reasonably reads the colour over their street as a measurement of their street; it is not, and nothing on screen says so. *Airlume's response:* discrete stations only, never an invented surface; when a neighbourhood has no monitor, the system says so and reports the distance to the nearest one; a coverage map shows where the city cannot presently be measured.

**Problem 3: forecasts without accountability.** Several platforms publish forecasts; almost none publish how wrong those forecasts turned out to be, so a user has no basis for calibrating trust. *Airlume's response:* a public accuracy page, generated automatically from logs, that scores every forecast against what the stations recorded.

# Related work

## Natural-language interfaces for visualisation

The idea of generating a visualisation from a sentence has a substantial literature. Shen et al. survey the field and identify the recurring structure: parse the utterance, infer the analytic task and data attributes, and map them to a visual specification [4]. NL4DV implements this as a toolkit that converts a query into a Vega-Lite specification, with explicit handling of ambiguity [3]. With large language models the emphasis shifted to code generation: Chat2VIS prompts a model to write plotting code directly [14], and LIDA structures the problem into summarisation, goal exploration and code generation stages [13]. These systems produce two-dimensional charts over tabular data and are evaluated, when they are evaluated, by whether the chart renders and looks plausible.

The question of *how to score* generated visualisations was addressed by VisEval, which contributes a benchmark of over two thousand natural-language-to-visualisation pairs and an automated checker for validity, legality and readability [5]. VisEval is the methodological precedent for this project: it demonstrates that visual answers can be scored systematically, and it is confined to 2D charts. Airlume extends the idea to a 3D geospatial scene in which the area, the time window, the aggregation and the camera pose are all part of what must be right.

## Conversational interfaces to air-quality data

VayuBuddy [1] is the closest system in spirit and in domain. It lets a user query seven years of Indian monitoring data in natural language; the model writes Python that produces a number, a line chart, a bar chart or a map. On a forty-five-question benchmark its best model answered thirty-nine correctly, and the paper's limitations section notes that plot correctness was not scored because doing so would require a rubric the authors did not build. VayuChat [2] succeeds it as a deployed conversational interface with interactive visualisations; as a system paper it states no benchmark. In Pakistan, the Punjab government's EcoBot [6] provides a current AQI for four cities with health advice, in English and Urdu, and is a lookup rather than an analytic tool. None of these systems is three-dimensional, treats viewpoint as part of the answer, or discloses the distance from the user's named place to the nearest measurement.

## City digital twins

Batty's short editorial on digital twins [15] and Shahat, Hyun and Yeom's review [16] both make the point that a city twin earns the name only when it is coupled to live data and used to answer questions, not when it is merely a 3D model. Airlume is a narrow twin in that sense: one phenomenon, air quality, with live hourly coupling, a historical archive, and a question-answering layer. The 3D rendering is a means of making a spatial and temporal pattern legible, not an end in itself; the proposal includes a two-dimensional companion view beside every 3D view precisely because perspective distorts height comparisons.

## Sparse monitoring and low-cost sensors

The honesty requirements in this proposal come from the monitoring literature. Shabbir et al. review the sparse regulatory network in Pakistan and analyse sixty-one low-cost PM2.5 sensors across the country, arguing for a hybrid network [17]; Saeed et al. document the practical difficulty of sustaining low-cost networks in South Asia [18]. The lesson for a visualisation system is that the dozen regulatory monitors in Lahore are precious and sparse, and that a map should make the sparsity visible rather than paint over it.

## Why the model does not write the query

Text-to-SQL and text-to-code systems are brittle under small perturbations of the question, the schema or the data. Dr.Spider demonstrates this systematically with a diagnostic benchmark of seventeen perturbation types, under which state-of-the-art models lose a large fraction of their accuracy [19]. Program-of-Thoughts prompting shows, from the other direction, that separating what the model decides from what an interpreter executes improves reliability on numerical tasks [20]. Airlume takes the separation one step further: the model produces not a program but a *form*, with every field drawn from a closed vocabulary or validated against a registry, and all computation lives in code that is unit-tested independently of any model. Structured-output facilities in current model APIs make this practical [21, 22].

## The gap

Across these threads, no existing work combines (a) a conversational interface over official air-quality data in Pakistan, (b) a three-dimensional geospatial scene in which camera pose is a generated output, (c) a field-level scoring rubric for the visual answer, and (d) explicit disclosure of monitoring sparsity and forecast error. The remainder of this proposal describes how Airlume fills it.

# Research questions and objectives

**RQ1.** Can a typed view-intent schema serve as a reliable scoring rubric for conversational visual analytics --- that is, can two annotators agree on the correct form for a question, and can the resulting per-field accuracy discriminate between language models of different sizes?

**RQ2.** How accurately do current open-weight and free-tier language models fill that schema for air-quality questions in English and Roman Urdu, including ambiguous and follow-up questions?

**RQ3.** How well does the Copernicus CAMS global model, which is widely consumed over Pakistan through consumer apps, agree with EPA Punjab's ground stations in Lahore, and how does that agreement vary by station and by time of day?

**RQ4.** Does disclosing the distance to the nearest monitor change how users interpret a value for a place that has no monitor?

The corresponding objectives are to (O1) build an hourly archive of official readings for Lahore's stations and Pakistan's monitored cities, with an eight-year daily back-fill from government bulletins; (O2) implement the typed intent schema, resolver and query layer, and a 3D map that renders every view type; (O3) construct and freeze an eighty-item benchmark before tuning, with a second annotator on a subset and inter-annotator agreement reported; (O4) evaluate at least three language models on the benchmark with bootstrap confidence intervals and run-to-run consistency; (O5) publish the CAMS-versus-ground statistics and the forecast scorecard; and (O6) deploy a public, installable web application with a documented security review.

# Proposed system

## Data sources and their standing

Every source was checked for availability, cost and licence on 12 and 13 October 2026. The project costs nothing to run.

| Source | What it provides | Terms | Role |
|:-------------------------|:----------------------------------------|:-------------------------------|:------------------------|
| EPA Punjab portal (aqi.punjab.gov.pk) | Hourly AQI, PM2.5, PM10, CO, SO2, NO2, O3 for 11 Lahore stations; hourly district AQI for 36 districts | Public, no licence stated; permission requested in writing | Primary live source |
| EPD Punjab bulletin archive | Daily Lahore AQI reports, Jan 2018 -- Dec 2025 (~2,300 PDFs) | Public government documents | Historical back-fill |
| Open-Meteo Air Quality API | CAMS global PM2.5/PM10, 0.4 degrees (about 45 km), 3-hourly, archive from 2022 | CC BY 4.0; 10,000 calls/day | Validation target only (RQ3); never displayed as a station value |
| OpenAQ v3 | Urban Unit AirGradient sensors in Islamabad, Karachi, Peshawar | Free key; licence per station | City-level values outside Punjab |
| WAQI (aqicn.org) | Live index for display | Terms forbid archiving and analysis | Live display only, isolated by code and test; never stored |

Two findings from the first live fetches, made on 13 October, shape the design. First, the portal publishes no documented API; its pages are server-rendered HTML, and the project reads them once an hour with an identified user agent, which the portal's robots policy permits. A written request for a documented feed, station coordinates and archiving permission has been prepared for the EPA, and the system is designed to function whether or not a reply arrives. Second, the AQI formula is not documented anywhere, and reproducing it is itself a small piece of research: the portal's numbers match the US EPA breakpoints of 2012 under Punjab's own seven category labels, with ozone --- not particulate matter --- dominating at several stations on a clear October afternoon. That finding, and the remaining question of the averaging window the portal uses, is now part of the evaluation plan (Section 7.3).

## Architecture

The system has four layers, each of which can be tested without the others.

1. **Collection.** Scheduled jobs (GitHub Actions, hourly) fetch the portal, Open-Meteo and OpenAQ, parse them, and append rows to a plain-text CSV archive committed to the repository --- one file per source per month, so that version control records every hour of data and never has to merge a binary file. A local DuckDB database [23] is rebuilt from the archive and serves all queries. A separate, resumable job has already parsed the bulletin archive.
2. **Language.** A question goes to a language model with a JSON schema describing the *view intent*: metric (AQI, PM2.5, PM10), city, area, time label, aggregation, threshold, comparison target, view type, camera name, and three flags --- out of scope, needs clarification, refers to previous answer. The model returns only this form. A validator rejects anything outside the enumerations; a resolver turns time labels into timestamps in Asia/Karachi, matches place names to the station registry, and applies the *nearest-station rule* for neighbourhoods without a monitor. The primary model is an open-weight model on a free tier, with a smaller local model on a team member's laptop as an offline fallback; temperature is fixed at zero and every call is logged with its model identifier.
3. **Query and answer.** Code builds a parameterised SQL query from the resolved form; the metric and aggregation names are checked against allow-lists so that no string from the model ever reaches the database unchecked. The answer sentence is also written by code from the returned numbers, so the text can never contradict the map.
4. **Visualisation.** deck.gl, through pydeck [24], renders stations as extruded columns coloured by official band, cities as scaled discs at national scale, and a time slider for animation. Camera positions are named --- overview, station, north, zoomed-out --- so that the model chooses a name and code supplies the numbers. Every 3D view has a two-dimensional ranked bar chart beside it and a top-down toggle, because perspective hides and shrinks distant columns.

The language model is thus the only non-deterministic component, and it touches only the form. Everything that could leak data, run arbitrary code or mislead a user is deterministic and covered by the test suite.

## The honesty layer

Three features exist specifically to prevent the system from implying more than it knows. The nearest-station rule attaches a note --- *"Model Town has no station of its own; showing Punjab University, about 2.8 km away"* --- whenever a named place is substituted. The coverage map shows the distance from every point in the city to its nearest monitor and, as a derived output, recommends where an additional station would gain the most coverage. The station registry records a confidence level for every coordinate, because the EPA does not publish them and nine of the eleven Lahore positions were recovered from third-party pages; the map displays that uncertainty until the EPA confirms the positions. Where data is missing the display says so --- *"10 of 11 stations reporting"* --- and the missing station is drawn grey, never omitted.

## Forecasting

A 24- to 48-hour per-station forecast is included because users expect one, but it is treated with suspicion. Every model must beat a persistence baseline (tomorrow at this hour equals today at this hour) on a frozen test window or it is not used, and the public accuracy page scores whatever is deployed against what the stations later recorded. Forecasting is not a contribution of the project; the *accountability* of the forecast is.

## Security and operations

The application is public, so it is built to a written fifteen-item security checklist: secrets only in environment variables with a start-up check that refuses placeholders; a secret scanner in the commit hook and a clean scan of the repository history; parameterised queries and allow-listed identifiers; rate limiting and security headers at the edge; the server bound to localhost in development; no user accounts and therefore no passwords; and a full audit with `gitleaks`, `pip-audit` and `bandit` before the site goes public and again before submission. All library versions are pinned from day one so that a change in a free tier or a package cannot break the demonstration.

# Evaluation methodology

The evaluation is designed so that every claim in the final report carries a number and an interval.

## The benchmark (E1)

Sixty single questions and twenty conversation items (clarification and follow-up cases) are written *before* the language layer is tuned and then frozen. Half the questions are written blind by classmates outside the team, to reduce the bias of the system's authors writing their own test. Each item carries a gold view-intent form. A second annotator labels twenty items independently and Cohen's kappa is reported, which answers the first half of RQ1. Each field is scored by exact match; a question passes when every field that matters for its class matches. The question classes are: where-now, how-much, compare-time, compare-place, threshold-count, best-time, forecast, ambiguous, follow-up, and out-of-scope. Twenty items are in Roman Urdu.

At least three models are evaluated: a large open-weight model on a free API tier, a small open-weight model on the same tier, and a 4-billion-parameter model running locally on a team member's laptop. Each question is run three times at temperature zero and the consistency rate is reported alongside accuracy. All accuracy figures carry 95% bootstrap confidence intervals; with sixty items the interval is wide, and the report will not claim differences that fall inside it.

## The visual rubric (E2)

For a subset of forty answered questions, two raters score the rendered view on five criteria --- right place, right time, right metric and aggregation, view matches the question, honesty about missing data --- each from 0 to 2. This is the rubric VayuBuddy's authors left unbuilt. Agreement between raters and between the rubric and the field-level score (E1) is reported; a rubric that disagrees with the field scores would be a finding, not a failure.

## AQI harmonisation and CAMS validation (E3)

Before any comparison between stations and the global model is meaningful, the two must be on the same scale. The project's converter reproduces the portal's AQI from its published concentrations approximately but not exactly: over the first ninety stored station-readings it agrees to a mean 5.4 index points using the US EPA 2012 breakpoints on the latest hour, and reads systematically about four points high. The eight-hour window that the provincial order prescribes for printed bulletins fits the live table far worse, and the twenty-four-hour window cannot yet be tested. Settling the window over a week of hourly data, and either explaining that residual bias or reporting it as a stated interval on every station-to-model comparison, is the substance of E3; a converter presented as exact when it is not would make RQ3's error figures meaningless. The CAMS comparison then reports mean absolute error, bias and correlation per station and by hour of day over the collection period, which answers RQ3.

## Forecast scorecard (E4) and user check (E5)

The forecast page is generated from logs, not curated, and reports error by horizon and by station, with the baseline beside it. A small comprehension study with ten to fifteen students shows each participant a value for a neighbourhood without a monitor, with and without the nearest-station disclosure, and asks what they believe it measures; the difference answers RQ4. This is a pilot, and will be described as one.

## Parallel and distributed computing (E6)

Extracting roughly 2,300 bulletin PDFs is benchmarked across a sequential, a multiprocessing and an asynchronous design, with wall-clock time and CPU utilisation reported on the same machine. The deployed system is itself distributed: collection runs in a cloud scheduler and writes to a shared repository, while the application reads from it on a separate host.

# Work plan

The project runs for ten weeks, from 13 October to 21 December 2026.

| Week | Dates | Work | Milestone |
|:-----|:-------------|:---------------------------------------------------|:-------------------------------------|
| 1 | 13--19 Oct | Foundations: accounts, skeleton, registry, fake-data shell, permission requests | Shell runs; parsers verified against live site |
| 2 | 20--26 Oct | Data pipeline: hourly collection in the cloud; bulletin back-fill complete | Live archive growing; versions pinned |
| 3 | 27 Oct -- 2 Nov | AQI harmonisation study; 3D twin begins | Averaging window settled (E3) |
| 4 | 3--9 Nov | Digital twin: all view types, 2D companions, time animation; benchmark questions collected from classmates | All views live |
| 5 | 10--16 Nov | Language layer: schema, resolver, clarifying and follow-up questions; benchmark frozen; kappa reported | Benchmark frozen (E1 design) |
| 6 | 17--23 Nov | Model evaluation across three models; Roman-Urdu set | E1 results with intervals |
| 7 | 24--30 Nov | Visual rubric study (E2); coverage map and station recommendation | E2 results |
| 8 | 1--7 Dec | Forecast baseline and model; CAMS validation; PDC benchmark | E3, E4, E6 results |
| 9 | 8--14 Dec | User check (E5); deployment; security audit | Public site; audit passed |
| 10 | 15--21 Dec | Report, demo rehearsal, repository release | Submission |

If the schedule slips, features are cut in a pre-agreed order --- satellite layer, non-Punjab cities, shareable cards, replay mode, voice input --- and the benchmark, the 3D map, the language layer and the honesty features are never cut.

# Feasibility and preliminary results

The proposal is not speculative. On 13 October 2026, the first day of the plan, the following was completed and committed to the project repository.

- The official portal was investigated and found to be server-rendered with no public API; a parser for the Lahore station table and the district ranking was written, tested against fixtures, and then verified against the live site, returning ten station rows with all six pollutants and thirty-five district values.
- The AQI formula was identified (US EPA 2012 breakpoints, Punjab labels) and implemented with the gas sub-indices and unit conversions; the ozone finding described in Section 6.1 came from that first live fetch.
- The bulletin archive was sampled across its full range, four distinct layouts were characterised, parsers were written for the three that contain extractable text, and a resumable back-fill produced 1,495 daily station rows for 2022--2025 in its first full pass, with the remaining layouts queued.
- A station registry with coordinates and confidence levels, the typed intent schema, the resolver with the nearest-station rule, the DuckDB store with parameterised queries, the code-written answer sentences, and a fake-data 3D shell were built, with sixty passing tests. The shell runs on a team member's laptop.

Two facts about the data were learned that a desk study would have missed and that now shape the plan: the bulletin archive stops on 2 December 2025, leaving a ten-month gap before the project's own collection begins, which will be stated on every timeline and never filled at station level; and the portal computes its index as a maximum over six pollutants, so that ozone dominates on sunny afternoons --- a result that will be documented in the report because it is not, to our knowledge, recorded anywhere.

Hardware is adequate: the development machine is a ten-core laptop with 8 GB of memory, on which the local 4-billion-parameter model runs; the heavier models are reached through free API tiers whose quotas (around 200,000 tokens per day on the primary provider) exceed the benchmark's needs by an order of magnitude. Hosting uses a public repository's scheduled jobs and a free application host; both have been checked for current terms.

# Risks, limitations and ethics

The main risks are external. The EPA may ask that automated reading stop, in which case collection halts, the project proceeds on the bulletin archive and the other sources, and the request is documented. Free tiers may change, which is why versions are pinned and the demonstration is rehearsed offline on cached data. The station coordinates may be wrong by hundreds of metres, which is why they are labelled and why the EPA has been asked to confirm them.

The limitations are stated plainly. Lahore has eleven regulatory monitors for eleven million people, and no visualisation can manufacture resolution the network does not have; the system's honesty features exist to make that limit visible, not to overcome it. The benchmark is small, and the report will not claim differences that its confidence intervals cannot support. The user study is a pilot. Target users are named as students, journalists and analysts; public-health impact is not claimed because it will not be measured. The system never offers causal attribution or medical advice.

Ethically, every source is attributed in the form its licence requires; WAQI data is displayed live and never stored, enforced by a test; the site carries a clear "student project, not an official source" notice; permission is sought in writing and any refusal is respected; and no personal data is collected.

# Contribution to course outcomes

**DS494 Data Visualization.** The project exercises three-dimensional spatial encoding, temporal animation, an externally standardised colour scale, comparative and small-multiple views, and the explicit communication of uncertainty and data sparsity --- and it tests, in E2 and E5, whether those choices actually help a reader.

**CC425 Parallel and Distributed Computing.** The bulletin extraction is a measured comparison of sequential, multiprocess and asynchronous designs on a real workload of about 2,300 documents (E6), and the deployed system separates a scheduled collector from the serving application across two hosts with a version-controlled data interface between them.

# Deliverables

1. A public web application, installable on a phone, at a stable address.
2. A public repository containing the code, the frozen benchmark with gold labels, the evaluation scripts, the CSV data archive, and the written data-source and security documentation.
3. The CAMS-versus-ground validation statistics for Lahore and the forecast scorecard, both generated by the system.
4. A final report and a seven-minute demonstration, opening with a replay of the worst smog day in the archive.

\newpage

# References {.unnumbered}

1. Patel, Z. B., Bachwana, Y., Sharma, N., Guttikunda, S., & Batra, N. (2024). *VayuBuddy: An LLM-powered chatbot to democratize air quality insights.* arXiv:2411.12760. <https://arxiv.org/abs/2411.12760>
2. Acharya, V., Pisharodi, A., Mondal, R., Rafiuddin, M., & Batra, N. (2025). *VayuChat: An LLM-powered conversational interface for air quality data analytics.* arXiv:2511.01046. <https://arxiv.org/abs/2511.01046>
3. Narechania, A., Srinivasan, A., & Stasko, J. (2021). NL4DV: A toolkit for generating analytic specifications for data visualization from natural language queries. *IEEE Transactions on Visualization and Computer Graphics, 27*(2), 369--379. <https://doi.org/10.1109/TVCG.2020.3030378>
4. Shen, L., Shen, E., Luo, Y., Yang, X., Hu, X., Zhang, X., Tai, Z., & Wang, J. (2023). Towards natural language interfaces for data visualization: A survey. *IEEE Transactions on Visualization and Computer Graphics, 29*(6), 3121--3144. <https://doi.org/10.1109/TVCG.2022.3148007>
5. Chen, N., Zhang, Y., Xu, J., Ren, K., & Yang, Y. (2025). VisEval: A benchmark for data visualization in the era of large language models. *IEEE Transactions on Visualization and Computer Graphics, 31*(1), 1301--1311. <https://doi.org/10.1109/TVCG.2024.3456320>
6. TechJuice. (2025, October 10). *Punjab launches Pakistan's first AI EcoBot for real-time air quality monitoring.* <https://www.techjuice.pk/punjab-launches-pakistans-first-ai-ecobot-for-real-time-air-quality-monitoring/>
7. Environmental Protection Agency, Punjab. (2026). *Air Quality Index Punjab* [real-time portal]. <https://aqi.punjab.gov.pk>
8. Environment Protection Department, Punjab. (2018--2025). *Daily Air Quality Index reports* [archive]. <https://epd.punjab.gov.pk/Air_quality>
9. IQAir. (2025). *2024 World Air Quality Report.* <https://www.iqair.com/world-air-quality-report>
10. IQAir. (2026). *2025 World Air Quality Report.* Reported in Al Jazeera, 24 March 2026, *Pakistan world's most polluted country in 2025: report.* <https://www.aljazeera.com/news/2026/3/24/pakistan-worlds-most-polluted-country-in-2025-report>
11. World Health Organization. (2021). *WHO global air quality guidelines: Particulate matter (PM2.5 and PM10), ozone, nitrogen dioxide, sulfur dioxide and carbon monoxide.* <https://www.who.int/publications/i/item/9789240034228>
12. Air Quality Life Index. (2024). *Pakistan fact sheet 2024.* Energy Policy Institute at the University of Chicago. <https://aqli.epic.uchicago.edu/wp-content/uploads/2024/08/Pakistan-FactSheet_2024.pdf>
13. Dibia, V. (2023). LIDA: A tool for automatic generation of grammar-agnostic visualizations and infographics using large language models. *Proceedings of the 61st Annual Meeting of the ACL (System Demonstrations)*, 113--126. <https://doi.org/10.18653/v1/2023.acl-demo.11>
14. Maddigan, P., & Susnjak, T. (2023). Chat2VIS: Generating data visualisations via natural language using ChatGPT, Codex and GPT-3 large language models. *IEEE Access, 11*, 45181--45193. <https://arxiv.org/abs/2302.02094>
15. Batty, M. (2018). Digital twins. *Environment and Planning B: Urban Analytics and City Science, 45*(5), 817--820. <https://doi.org/10.1177/2399808318796416>
16. Shahat, E., Hyun, C. T., & Yeom, C. (2021). City digital twin potentials: A review and research agenda. *Sustainability, 13*(6), 3386. <https://doi.org/10.3390/su13063386>
17. Shabbir, M., Saeed, T., Saleem, A., Bhave, P., Bergin, M., & Khokhar, M. F. (2025). A paradigm shift: Low-cost sensors for effective air quality monitoring and management in developing countries. *Environment International, 200*, 109521. <https://doi.org/10.1016/j.envint.2025.109521>
18. Saeed, T., Khaliq, M. M., Bergin, M. H., Bhave, P. V., et al. (2024). *Sustaining low-cost PM2.5 monitoring networks in South Asia: Technical challenges and solutions.* EGUsphere preprint. <https://doi.org/10.5194/egusphere-2024-1932>
19. Chang, S., Wang, J., Dong, M., Pan, L., Zhu, H., Li, A. H., et al. (2023). Dr.Spider: A diagnostic evaluation benchmark towards text-to-SQL robustness. *International Conference on Learning Representations.* <https://arxiv.org/abs/2301.08881>
20. Chen, W., Ma, X., Wang, X., & Cohen, W. W. (2023). Program of Thoughts prompting: Disentangling computation from reasoning for numerical reasoning tasks. *Transactions on Machine Learning Research.* <https://arxiv.org/abs/2211.12588>
21. OpenAI. (2024, August 6). *Introducing Structured Outputs in the API.* <https://openai.com/index/introducing-structured-outputs-in-the-api/>
22. Pydantic. (2026). *JSON Schema* [documentation, Pydantic v2]. <https://docs.pydantic.dev/latest/concepts/json_schema/>
23. Raasveldt, M., & Muehleisen, H. (2019). DuckDB: An embeddable analytical database. *Proceedings of the 2019 ACM SIGMOD International Conference on Management of Data*, 1981--1984. <https://doi.org/10.1145/3299869.3320212>
24. vis.gl / OpenJS Foundation. (2026). *deck.gl documentation* and *pydeck documentation.* <https://deck.gl/docs>, <https://pydeck.gl/>
25. Copernicus Atmosphere Monitoring Service. (n.d.). *CAMS global atmospheric composition forecasts* [data set]. ECMWF Atmosphere Data Store. <https://doi.org/10.24381/04a0b097>; Open-Meteo. *Air Quality API* [documentation]. <https://open-meteo.com/en/docs/air-quality-api>
26. U.S. Environmental Protection Agency. (2024, updated 2026). *Technical assistance document for the reporting of daily air quality --- the Air Quality Index (AQI).* Office of Air Quality Planning and Standards. <https://www.airnow.gov/publications/air-quality-index/technical-assistance-document-for-reporting-the-daily-aqi/>

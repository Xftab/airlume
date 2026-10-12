---
title: "Airlume: A Conversational Digital Twin of Lahore's Air Quality"
subtitle: "Semester Project Proposal --- Semester 7"
author:
  - "Aftab Ahmad"
date: "8 October 2026"
---



> **Version 1 --- 8 October 2026. Superseded.** This first proposal predates later research. In particular, its related-work section does not yet cover VayuBuddy, VayuChat or EcoBot, and its data, licensing and scope sections were revised afterwards. The current, authoritative document is the *Airlume Complete Project Plan*.

# Executive Summary

This project proposes **Airlume** (from *air* and *lume*, light) --- a conversational, three-dimensional digital twin of air quality across Lahore. The system renders live and historical air quality data as an interactive 3D map of the city, and is controlled entirely through natural-language questions typed or spoken by the user, in place of conventional dropdown filters and control panels.

A user asks *"where is smog worst today?"* or *"is this worse than last October?"* The system interprets the question into a validated structured query, retrieves the relevant data, selects an appropriate visual encoding, moves the map camera, and renders the answer.

The project is **not** proposed as another air quality dashboard. Its substantive contributions are methodological and local:

1. A **typed view-intent schema** that converts natural language into a validated, executable specification covering not only the data query but also the visual encoding and the spatial camera pose --- making the language layer measurable rather than anecdotal.
2. A **60-question gold-standard benchmark** for evaluating that layer, with per-field error attribution.
3. The first **quantified comparison**, to the author's knowledge, between the globally available CAMS atmospheric model at its Pakistan resolution and the Punjab Environmental Protection Agency's ground station network in Lahore.
4. A **sparsity-honest visualization protocol** that refuses to imply spatial precision the underlying ten-station network cannot support.
5. A **publicly visible forecast scorecard** in which the system continuously reports its own prediction error against a stated baseline.

The project requires no budget, no GPU, and no paid services. All data sources are open and free. A working interactive prototype, a deployed public web application, a reproducible evaluation harness, and a written report are proposed as deliverables.

\vspace{1em}

> **Why this is not just another dashboard.** Air quality dashboards already exist, including an official one for Punjab. This project does not compete with them on data collection. It asks a different research question: *can a natural-language layer control a three-dimensional geospatial scene accurately enough to replace conventional filter-based interfaces, and how do we measure whether it does?* The air quality data is the testbed; the interface and its evaluation are the contribution. The honesty mechanisms --- disclosed station distance, published forecast error --- are the second contribution, and they address a documented weakness of the commercial alternatives.

\newpage

# Problem Statement

## Context

Lahore is among the most polluted major cities in the world. Analysis of community low-cost sensor data has placed the city's annual average PM2.5 concentration at approximately 105 µg/m³, with hourly peak episodes reaching 900 µg/m³ [1]. The city's smog season runs from approximately October to February, driven by crop residue burning, vehicle and industrial emissions, brick kiln smoke, and construction dust [2].

Despite the severity of the problem, Lahore has historically been characterised as a data gap: monitoring has been sporadic, and public availability of reliable air quality data has been limited [1]. A 2022 assessment of the city's monitoring capacity documented only four publicly available reference-grade continuous monitoring stations alongside nine low-cost sensors, and concluded that there was an urgent need both for expanded sensor coverage and for public availability of reliable data [3]. The Lahore smog commission recommended increasing active reference-grade stations from three to twelve [4].

The situation has since improved. The Punjab Environmental Protection Agency now operates a real-time platform reporting Lahore's air quality index from **ten government-certified monitoring stations** across the city, including Multan Road, Shahdara, DHA and Gulberg, updated hourly, covering PM2.5, PM10, SO~2~, NO~2~, CO and O~3~ [2].

## The remaining gap

Data availability has improved; **data interpretability has not**. Three specific problems motivate this project.

**First, the interface problem.** Existing air quality interfaces present a number and a colour. Answering a comparative or spatial question --- *which part of the city is worst, how does this week compare to last month, when during the day is it worst* --- requires the user to operate filters, switch views, and mentally assemble the comparison. For a non-expert public, and for policy users who need to ask ad-hoc questions quickly, this friction is substantial.

**Second, the false-precision problem.** Consumer air quality applications routinely render smooth, continuous colour surfaces across entire cities. For Lahore, that surface is interpolated from ten stations serving a population exceeding eleven million. The visual implies a spatial resolution the underlying data does not possess, and users reasonably but incorrectly infer street-level accuracy.

**Third, the accountability problem.** Air quality platforms publish forecasts. They very rarely publish how wrong those forecasts turned out to be. A user has no basis on which to calibrate their trust.

# Related Work and Current Landscape

## Air quality monitoring and modelling

Two classes of data source are relevant and both are freely available.

*Ground monitoring.* The Punjab EPA network provides hourly, station-level readings at ten named locations in Lahore [2]. These are direct measurements and constitute ground truth for this project. Additional historical context exists in published low-cost sensor networks covering Karachi, Lahore, Islamabad and Peshawar over a seven-year period [1].

*Atmospheric modelling.* The Copernicus Atmosphere Monitoring Service (CAMS) produces modelled atmospheric composition forecasts, redistributed openly via the Open-Meteo API with no authentication required. Critically for this project, Open-Meteo documents that forecasts are based on the 11 km CAMS European air quality forecast and the 45 km CAMS global atmospheric composition forecast, with the European and global domains uncoupled [5]. Pakistan falls under the global domain, at 0.4° (approximately 40--45 km) resolution and three-hourly timesteps [5].

**This resolution fact is decisive for the project design and is discussed in Section 4.**

## Natural-language interfaces to data

Natural-language querying of structured data is an established research area. Text-to-SQL systems translate questions into database queries and are conventionally evaluated by execution accuracy against gold queries. Natural-language-to-visualization systems extend this to selecting a chart type and encoding. Both lines of work are overwhelmingly evaluated on tabular, non-spatial data, and produce a static chart as output.

Contemporary large language models make the generation step substantially easier than it was. They do not, however, make it *reliable*, and the dominant failure mode in deployed systems is the silent production of a plausible but incorrect query. The engineering response adopted in this proposal --- constraining generation to a validated typed schema rather than free-form query text --- is discussed in Section 7.3.

## Geospatial digital twins

Three-dimensional urban visualization using WebGL frameworks is mature; rendering hundreds of thousands of geolocated data points in a browser is a solved problem. Urban digital twins for environmental monitoring exist for several cities in the Global North. What is conventionally absent is a language-driven control layer: these systems are navigated by mouse, filter panel and timeline.

## Prior work on Lahore specifically

Published work on Lahore's air quality has concentrated on *measurement capacity* rather than *interpretation interfaces*. The 2022 ISPRS study analysed the city's air quality data landscape and proposed a context-aware algorithm for recommending locations for new monitoring stations [3]. Community-sensor work has focused on data collection and public awareness [1]. The author is not aware of published work providing a conversational interface over Lahore air quality data, nor of a published validation of the CAMS global model against the Punjab EPA station network.

\newpage

# Gap Analysis

The following table sets out what exists, what is missing, and what this project adds.

| Area | Current state | Gap |
|:--|:--|:--|
| Lahore AQ data | Ten EPA stations, hourly, public [2] | Presented as numbers and lists; no spatial-temporal exploration |
| AQ interfaces | Filter-driven dashboards, 2D maps | No natural-language control; no camera-aware response |
| NL-to-data research | Mature for tables and charts | Rarely spatial; camera state never part of the output; seldom evaluated in deployment |
| Consumer AQ maps | Smooth interpolated surfaces | Imply precision ten stations cannot support |
| Forecast publication | Forecasts published widely | Forecast error almost never published |
| CAMS model in Pakistan | Freely available at approx. 45 km [5] | No published validation against Lahore ground stations |

## The resolution constraint, stated explicitly

An important design constraint was identified during the planning phase and is stated here because it determines the system architecture.

Lahore's metropolitan area spans roughly 25--30 km. The CAMS global model available for Pakistan operates at approximately 40--45 km resolution [5]. **The entire city therefore falls within approximately one model grid cell.** Any attempt to build a neighbourhood-resolution map of Lahore from this model alone would produce near-identical values at every location --- a visually convincing map carrying no real spatial information.

This constraint is the reason the project adopts a **two-source architecture**: Punjab EPA station readings as the authoritative intra-city signal, and CAMS as a coarse regional and meteorological context layer. It is also what makes contribution N4 (Section 5) possible and worthwhile.

# Novelty and Contributions

This section states the project's claims to novelty explicitly, each with its prior art, its gap, the proposed contribution, and the method by which the contribution will be verified.

## N1 --- Camera-aware natural-language control of a 3D geospatial scene

**Prior art.** Natural-language-to-SQL; natural-language-to-chart. Output is a table or a 2D chart.

**Gap.** In a three-dimensional geospatial scene, the *viewpoint* is part of the answer. "Where is smog worst in the west of the city?" is answered not only by a number but by looking west, at an appropriate zoom and pitch. No widely reported system treats camera pose as a component of the generated response.

**Contribution.** A view-intent schema in which the language model specifies metric, spatial extent, time window, aggregation, comparison mode, visual encoding **and camera pose** as a single validated object.

**Verification.** Per-field accuracy against the gold benchmark (Section 8), reported separately for data fields and view fields.

## N2 --- An evaluable language layer via constrained structured intent

**Prior art.** Free-form SQL or code generation from natural language, typically evaluated offline on academic benchmarks.

**Gap.** Deployed LLM dashboard features are rarely evaluated at all; when generation is free-form, failures are difficult to attribute and can crash or compromise the runtime.

**Contribution.** The language model is permitted only to populate a strongly typed schema, validated before execution. Query construction is performed by deterministic application code. This (a) eliminates injection risk, (b) eliminates malformed-query runtime failure, and (c) renders the layer *measurable*, because a predicted object can be compared field-by-field against a gold object.

**Verification.** Exact-match and per-field accuracy over 60 questions; failure analysis by question type and by field.

## N3 --- Sparsity-honest geospatial visualization

**Prior art.** Commercial air quality maps interpolate aggressively across sparse networks.

**Gap.** The resulting visual encodes confidence that is not present in the data, and users cannot tell where real measurements end.

**Contribution.** A stated visualization protocol: discrete station columns rather than a continuous surface; where interpolation is shown, station locations are always overlaid; and for any queried location without a nearby station, the system returns the nearest station reading **together with its distance in kilometres**, rather than an imputed local value.

**Verification.** Protocol compliance audit across all query types, plus a small user comprehension check (Section 8.4).

## N4 --- Quantified model-versus-ground divergence for Lahore

**Prior art.** CAMS global is openly available and widely consumed; its stated resolution for the region is approximately 45 km [5].

**Gap.** The author is not aware of a published quantification of how far this model departs from Punjab EPA's station readings in Lahore. Applications and users consume the modelled values without a local error estimate.

**Contribution.** A paired dataset of modelled versus measured values across all ten stations over the project period, reporting mean absolute error, bias, correlation and per-station breakdown.

**Verification.** The dataset and analysis script are released; results are reported whatever they show, including an unfavourable outcome.

## N5 --- Published self-assessment of forecast accuracy

**Prior art.** Forecasts are published; error is not.

**Gap.** Users have no calibration signal.

**Contribution.** Forecast accuracy is a first-class, continuously updated page of the application, reporting error against a persistence baseline ("tomorrow equals today"), by station and by hour of day.

**Verification.** The page is generated automatically from logged predictions and subsequent observations; it is not hand-curated.

## Secondary contributions

- **A released time-series dataset** of Lahore station readings logged at hourly resolution over the project period, published openly.
- **A released natural-language benchmark** of 60 annotated questions for air quality spatial querying, reusable by other researchers.

## Honest positioning of the novelty claim

The contribution of this project lies in **systems design, evaluation methodology and applied local measurement**. It does not claim a novel machine learning architecture, and no new model is trained from scratch. This positioning is deliberate and is argued to be appropriate: a semester project that proposes a new model architecture will almost certainly fail to produce a defensible result in ten weeks, whereas the contributions above are achievable, measurable, and individually publishable at a workshop level. Claims N2, N3 and N4 in particular are, in the author's assessment, genuinely unaddressed in the published literature for this city and this data environment.

\newpage

# Aim and Objectives

## Aim

To design, build, deploy and evaluate a conversational three-dimensional visualization system for Lahore's air quality that answers natural-language spatial and temporal questions accurately, and that communicates the limits of its own data honestly.

## Objectives

**O1.** Construct an automated collection pipeline that ingests Punjab EPA station readings hourly and CAMS regional and meteorological data, and stores them in a queryable local store.

**O2.** Design a typed view-intent schema sufficient to express the six identified question classes (lookup, ranking, comparison, trend, aggregate, conditional) together with visual encoding and camera pose.

**O3.** Implement a language layer that populates the schema from natural-language input, with validation that rejects malformed or out-of-scope intents and produces an informative refusal.

**O4.** Implement a 3D geospatial rendering layer with temporal animation, camera control, comparison views and a wind overlay.

**O5.** Implement a short-horizon forecasting module and evaluate it against a persistence baseline.

**O6.** Construct a 60-question gold benchmark and evaluate O3 against it, reporting per-field and per-type accuracy.

**O7.** Quantify divergence between CAMS modelled values and EPA station measurements for Lahore.

**O8.** Deploy the system publicly with a continuously updated accuracy page, correct data attribution and a clear non-official disclaimer.

\newpage

# Methodology

## System architecture

The system is organised into four layers with strict separation of concerns.

```
   User question (typed or spoken)
              |
              v
   +--------------------------------+
   |  LANGUAGE LAYER                |
   |  LLM populates a typed         |
   |  view-intent object            |
   +----------------+---------------+
                    |
                    v
   +--------------------------------+
   |  VALIDATION LAYER              |
   |  Schema validation; relative   |
   |  dates resolved in code;       |
   |  deterministic SQL assembly    |
   +----------------+---------------+
                    |
                    v
   +--------------------------------+
   |  DATA LAYER                    |
   |  Local analytical store:       |
   |  EPA readings, CAMS context,   |
   |  wind, forecasts, geometries   |
   +----------------+---------------+
                    |
                    v
   +--------------------------------+
   |  RENDER LAYER                  |
   |  3D columns, time animation,   |
   |  camera flight, comparison     |
   +--------------------------------+
```

A deliberate architectural decision is that **the language model never emits executable query text**. It emits data. Application code emits queries. This single decision delivers the security, robustness and measurability properties claimed in N2.

## Data layer

| Source | Role | Resolution | Access |
|:--|:--|:--|:--|
| Punjab EPA network [2] | Authoritative intra-city signal | 10 discrete stations, hourly | Public platform |
| CAMS via Open-Meteo [5] | Regional background, pollutant context | approx. 45 km, 3-hourly | Free, no API key |
| Open-Meteo weather [5] | Wind, temperature, rainfall | Grid, hourly | Free, no API key |
| OpenStreetMap | District boundaries, road geometry | Vector | Open |

Collection runs on a scheduled job independent of the web application, so that data freshness does not depend on the application being awake. Records are appended to a columnar store. Volume is modest --- ten stations at hourly resolution produce approximately 88,000 rows per year --- so a single file-based analytical database is sufficient and no database server is required.

**Data freshness is surfaced in the interface itself**, as an explicit "data as of" timestamp, which doubles as a monitoring signal for pipeline failure.

## Semantic query layer

This is the project's principal technical component. Rather than generating SQL, the model fills a schema of the following shape:

```json
{
  "metric":      "pm2_5",
  "area":        "lahore_west",
  "time":        "today",
  "aggregation": "mean",
  "compare_to":  null,
  "viz":         "columns_3d",
  "camera":      { "zoom": 11, "pitch": 55, "bearing": 45 }
}
```

Three safeguards apply:

1. **Validation before execution.** The object is parsed into a typed model. A field outside its permitted domain causes rejection with a user-facing explanation rather than a failed query.
2. **Relative dates resolved in application code.** The model emits a *label* ("today", "last week", "last November"); resolution to absolute timestamps in the Asia/Karachi timezone is performed deterministically in code. Language models are unreliable at date arithmetic, and date errors fail silently --- the user receives a plausible map of the wrong period.
3. **Explicit out-of-scope handling.** Questions the data cannot support (street-level readings, source attribution, personal health advice, multi-year history preceding the logging period) return a structured refusal that states why.

## Visualization layer

Station readings are rendered as discrete vertical columns positioned at true station coordinates, with height and colour encoding the index value. The colour scale is the **official US AQI banding**, adopted rather than invented so that the encoding is externally standardised and immediately legible to anyone familiar with air quality reporting.

Supported views correspond to the six question classes: single-station focus, ranked city view, split-screen comparison, animated time series, aggregate summary and filtered conditional view. A wind vector overlay provides meteorological context for "why" questions, presented explicitly as correlation and never as causation.

## Forecasting module

A short-horizon (24--48 hour) per-station forecast is produced. The methodology is deliberately conservative: a persistence baseline is established first, and any model is adopted only if it demonstrably improves on that baseline on held-out data. Candidate approaches are classical time-series methods and gradient-boosted regression on lagged and meteorological features. **A negative result --- that the baseline is not beaten --- will be reported as a finding rather than concealed.**

\newpage

# Evaluation Plan

Evaluation is treated as a first-class deliverable rather than a concluding activity. Four independent evaluations are proposed.

## E1 --- Language layer accuracy

A benchmark of **60 questions** is constructed by hand, annotated with gold view-intent objects, and frozen before the language layer is implemented. Questions are stratified across the six question classes and include deliberately out-of-scope items.

Metrics: exact-object match; per-field accuracy; accuracy by question class; refusal precision and recall on out-of-scope items.

Target: at least 85% per-field accuracy, with error analysis identifying the weakest field.

## E2 --- Forecast accuracy

Metrics: mean absolute error versus a persistence baseline; correct AQI band classification rate; error decomposed by station and by hour of day.

Target: improvement over persistence baseline, reported with the magnitude of improvement.

## E3 --- Model-versus-ground divergence (contribution N4)

Paired comparison of CAMS modelled values against EPA station readings over the project period.

Metrics: mean absolute error, signed bias, Pearson correlation, per-station breakdown.

This evaluation has no target. Its purpose is measurement, and the result is reported as found.

## E4 --- Interface comprehension and performance

A small comprehension check with 8--10 participants, each asked to answer three factual questions using the interface, recording success rate and time to answer. Participants are additionally asked to state how precise they believe the map to be --- directly testing whether the sparsity-honest protocol (N3) achieves its stated purpose.

Rendering performance is recorded as frames per second and time to first paint.

## Guard against evaluation error

The benchmark is frozen before implementation; a separate small development set is used for tuning. Automated scoring of the language layer is validated by manually checking a 30-item sample and reporting agreement. Class balance is reported for all classification metrics, and plain accuracy is not reported in isolation.

\newpage

# Technology Stack and Budget

| Component | Technology | Cost |
|:--|:--|:--|
| Language | Python | Free |
| Data store | Columnar file-based analytical database | Free |
| Schema validation | Typed validation library | Free |
| Language model | Free-tier hosted LLM API | Free |
| Rendering | WebGL geospatial library | Free, open source |
| Application | Python web application framework | Free |
| Scheduled collection | Hosted CI scheduler | Free on public repositories |
| Hosting | Free-tier application hosting | Free |
| Version control | Git / GitHub | Free |

**Total project cost: PKR 0.** No GPU is required; all computation runs on a standard laptop. A custom domain name, if desired for presentation purposes, would cost approximately PKR 300--3,500 per year and is entirely optional.

# Project Timeline

| Week | Activity | Milestone |
|:--|:--|:--|
| 1 | Literature review; architecture shell built with synthetic data | Runnable interface skeleton |
| 2 | EPA collection pipeline; scheduled job; store schema | Live data flowing |
| 3 | CAMS and meteorological ingestion; 3D render with real data | Working digital twin |
| 4 | Temporal animation; wind overlay; camera control | Interactive twin |
| 5 | View-intent schema designed; 60-question benchmark written and frozen | Benchmark locked |
| 6 | Language layer; validator; refusal handling | Language control working |
| 7 | Integration of language layer with camera and encoding selection | **System complete end to end** |
| 8 | Forecasting module; comparison views | Feature complete |
| 9 | All four evaluations executed; deployment; accuracy page | Results obtained |
| 10 | User comprehension study; report writing; presentation rehearsal | Submission |

Weeks 1 and 7 are identified as critical. Week 1 removes integration risk at the earliest possible point by building the interface shell before any real data exists. Week 7 is the point at which the two halves of the system --- language and visualization --- become a single product.

# Deliverables

1. Deployed, publicly accessible web application with a live URL.
2. Complete source code in a public repository with documentation.
3. Released dataset of logged Lahore station readings.
4. Released 60-question natural-language benchmark with gold annotations.
5. Reproducible evaluation harness producing all reported figures.
6. Written project report including full methodology, results and limitations.
7. Presentation and live demonstration.

\newpage

# Risk Register

+------+----------------------------+-------------+----------+------------------------------------------------------+
| ID   | Risk                       | Likelihood  | Impact   | Mitigation                                           |
+======+============================+=============+==========+======================================================+
| R1   | EPA platform provides no   | Medium      | High     | Week 1 investigation task. Fallback: scheduled       |
|      | structured data endpoint   |             |          | scraping with a defensive parser; begin logging      |
|      |                            |             |          | immediately so a proprietary time series accumulates |
|      |                            |             |          | regardless                                           |
+------+----------------------------+-------------+----------+------------------------------------------------------+
| R2   | Station history            | Medium      | Medium   | Begin logging in week 1. Ten weeks of self-collected |
|      | unavailable; only current  |             |          | data spanning peak smog season becomes a project     |
|      | readings                   |             |          | contribution in itself                               |
+------+----------------------------+-------------+----------+------------------------------------------------------+
| R3   | Scheduled collection job   | Medium      | Medium   | Freshness timestamp displayed in the interface;      |
|      | fails silently             |             |          | 48-hour unattended soak test before reliance; logged |
|      |                            |             |          | run history                                          |
+------+----------------------------+-------------+----------+------------------------------------------------------+
| R4   | Language layer accuracy    | Low         | Medium   | Reported as a finding with error analysis.           |
|      | below target               |             |          | Constrained schema guarantees graceful failure       |
|      |                            |             |          | rather than system failure                           |
+------+----------------------------+-------------+----------+------------------------------------------------------+
| R5   | Forecast fails to beat     | Medium      | Low      | Reported as a negative result. The comparison itself |
|      | persistence baseline       |             |          | is the deliverable                                   |
+------+----------------------------+-------------+----------+------------------------------------------------------+
| R6   | Deployment platform        | Low         | Low      | Collection decoupled from application; local         |
|      | limitations                |             |          | demonstration retained as primary presentation path  |
+------+----------------------------+-------------+----------+------------------------------------------------------+
| R7   | Scope creep                | Medium      | High     | Scope cut order fixed in advance (Section 13)        |
+------+----------------------------+-------------+----------+------------------------------------------------------+
| R8   | Examiner compares          | **High**    | Medium   | Pre-emptively addressed: E3 quantifies model-versus- |
|      | displayed values to a      |             |          | ground divergence, and differing AQI formulations    |
|      | third-party application    |             |          | are documented in the report                         |
+------+----------------------------+-------------+----------+------------------------------------------------------+

Risk R8 deserves particular comment. Different providers use different stations, averaging windows and index formulations; the US AQI and European AQI produce different numbers from identical PM2.5 concentrations. A discrepancy between this system and a consumer application is therefore expected rather than anomalous, and the project explicitly measures and documents it.

# Limitations and Scope Boundaries

The following are stated as explicit limitations and will appear in both the application interface and the final report.

1. **Spatial resolution.** Ten stations serve a city of over eleven million people. The system reports the nearest station and its distance; it does not impute street-level values.
2. **Temporal depth.** Station-level history begins when logging begins. Multi-year retrospective analysis at station level is outside scope.
3. **Causal attribution.** Meteorological correlates are displayed. Source apportionment requires chemical analysis and is outside scope.
4. **Health guidance.** The system displays the official AQI band and its standard associated wording. It does not generate personalised health advice.
5. **Single city.** Lahore only. The architecture generalises, but no claim of generalisation is tested.
6. **Regional model error.** CAMS values at approximately 45 km resolution are regional estimates, not local measurements [5]. This is measured in E3 rather than assumed away.

**Pre-committed scope cut order**, should the schedule slip: (i) satellite overlay, (ii) voice input, (iii) split-screen comparison, (iv) forecasting module. The 3D rendering, temporal animation, language layer and evaluation harness are not subject to cutting; they constitute the project.

# Ethical and Legal Considerations

**Attribution.** CAMS data redistributed via Open-Meteo is licensed CC BY 4.0 and requires clear attribution to both CAMS and Open-Meteo [5]. Punjab EPA is credited as the source of station readings. Attribution appears on every page of the deployed application.

**Non-impersonation.** The application displays official air quality readings. Because it must not be mistaken for a government service, every page and the About section carry an explicit statement that it is a student project and not an official source.

**Responsible communication.** Air quality is a public health matter. The system therefore (a) displays only the standard wording associated with each official AQI band and generates no personalised medical advice, (b) presents meteorological factors as correlates and never as proven causes, and (c) publishes its own forecast error so that users can calibrate their trust.

**Data collection conduct.** Collection is rate-limited and respects the fair-use terms of the sources. No personal data is collected, stored or processed at any point in the system.

# Mapping to Course Learning Outcomes

**DS494 Data Visualization.** The project exercises 3D spatial encoding, temporal animation, colour scale selection against an external standard, comparative view design, and --- unusually for a student project --- the explicit visual communication of uncertainty and data sparsity (N3), supported by an empirical comprehension check (E4).

**CC425 Parallel & Distributed Computing.** The ingestion and backfill pipeline processes a large number of independent station-hour and grid-point retrievals. A sequential implementation is benchmarked against parallel and asynchronous implementations, with speed-up measured across worker counts and the scaling limit analysed. The collection scheduler and web application are additionally deployed as decoupled distributed components with independent lifecycles.

# Expected Outcomes and Success Criteria

The project is considered successful if:

1. A publicly deployed system answers the six question classes correctly from natural language.
2. Language layer per-field accuracy of at least 85% is achieved and reported with error analysis.
3. The forecast is evaluated against a persistence baseline, with the result reported in either direction.
4. Model-versus-ground divergence for Lahore is quantified and published.
5. The dataset and benchmark are released openly.
6. All limitations are documented in both the interface and the report.

Criteria 3 and 4 are satisfied by *measurement*, not by a favourable outcome. This is deliberate: it ensures the project cannot fail for reasons outside the author's control, while leaving the quality of the engineering and analysis as the true basis of assessment.

\newpage

# References

[1] Omar, A. and Rosales, C. (2024). *Open Air Quality Community Data in Pakistan.* EGU General Assembly 2024, Vienna, EGU24-453. https://doi.org/10.5194/egusphere-egu24-453

[2] Punjab Environmental Protection Agency. *Lahore Air Quality Index --- real-time monitoring platform.* Government of the Punjab. https://aqi.punjab.gov.pk/lahore

[3] *Data Driven Framework for Analysis of Air Quality Landscape for the City of Lahore.* The International Archives of the Photogrammetry, Remote Sensing and Spatial Information Sciences, Vol. XLVIII-4/W5-2022, pp. 167 et seq. https://isprs-archives.copernicus.org/articles/XLVIII-4-W5-2022/167/2022/

[4] *Finding the Blue Skies: Lahore's Air Apocalypse.* Lahore University of Management Sciences, City Knowledge and Policy. https://city.lums.edu.pk

[5] Open-Meteo. *Air Quality API documentation --- CAMS European and CAMS global model resolutions.* https://open-meteo.com/en/docs/air-quality-api

[6] Copernicus Atmosphere Monitoring Service (CAMS), European Centre for Medium-Range Weather Forecasts. Licensed CC BY 4.0.

[7] United States Environmental Protection Agency. *Technical Assistance Document for the Reporting of Daily Air Quality --- the Air Quality Index (AQI).*

\newpage

# Appendix A --- View-Intent Schema (Draft)

| Field | Type | Permitted values | Source |
|:--|:--|:--|:--|
| `metric` | enum | pm2_5, pm10, no2, so2, co, o3, us_aqi | Model |
| `area` | enum | station id, district, named region, all_lahore | Model |
| `time` | enum label | now, today, yesterday, this_week, last_week, this_month, named month, past_24h | Model |
| `time_start` | timestamp | resolved absolute value | **Code** |
| `time_end` | timestamp | resolved absolute value | **Code** |
| `aggregation` | enum | mean, max, min, count_above_threshold | Model |
| `compare_to` | object or null | a second time or area specification | Model |
| `viz` | enum | columns_3d, ranked_list, split_view, time_series, calendar | Model |
| `camera` | object | zoom, pitch, bearing, centre | Model |
| `confidence` | float | model self-reported; low values trigger clarification | Model |

Fields marked **Code** are never produced by the language model.

# Appendix B --- Sample Benchmark Questions

| ID | Question | Class | Expected behaviour |
|:--|:--|:--|:--|
| 1 | Where is smog worst right now? | Ranking | All stations ranked; city camera |
| 2 | What is the AQI in Gulberg? | Lookup | Single station; zoomed camera |
| 3 | Is today worse than yesterday? | Comparison | Split view, two time windows |
| 4 | Show me the last thirty days | Trend | Animated time series |
| 5 | How many days this month exceeded 150? | Conditional | Filtered count with calendar |
| 6 | When during the day is pollution worst? | Aggregate | Mean by hour of day |
| 7 | Which area improved most this week? | Comparison | Change computation across windows |
| 8 | What is the AQI on my street? | **Out of scope** | Structured refusal with explanation |
| 9 | What was the AQI in 2019? | **Out of scope** | Refusal; history begins at logging start |
| 10 | Is it safe for my child to play outside? | **Out of scope** | Official band wording only; no medical advice |

# Appendix C --- Interface Design

Interactive design mockups of four screens --- the live desktop view, an answered query state, the public accuracy page, and the installed mobile view --- have been prepared and are available for review alongside this proposal. They illustrate the sparsity-honest visualization protocol (N3), the nearest-station distance disclosure, and the public forecast scorecard (N5) as implemented interface elements rather than as report appendices.

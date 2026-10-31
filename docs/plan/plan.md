---
title: "Airlume: Complete Project Plan"
subtitle: "A Conversational 3D Digital Twin of Air Quality in Pakistan's Monitored Cities --- Problem, Product, Resources and Phased Build Plan"
author:
  - "Aftab Ahmad, Kiran Saif and Tehreem Fatima"
date: "13 October 2026 (revision 6, updated 31 October 2026: coverage measured, key rotation, insight modules wired and benchmark prompt v4)"
---

# Part A --- The Project

## The project in one paragraph

**Airlume** --- from *air* and *lume*, light --- is a website that shows air pollution across Pakistan's monitored cities on a three-dimensional map, and that you control by asking questions in plain language. Zoomed out, every city with monitoring stations stands as a glowing column --- taller and more purple where the air is worse. Zoom into Lahore and the city opens up station by station. You type or say *"which city has the worst smog today?"* or *"where is it worst in Lahore?"* and the map turns to the right place and writes a short answer. You ask *"is today worse than yesterday?"* and the screen splits into two maps side by side. There are no filters, dropdowns or menus to learn: the question is the interface.

Behind that simple surface sit three engineering pieces --- a data pipeline that collects official readings every hour, a 3D visualisation engine, and a language layer that turns a sentence into a precise, checked instruction --- plus the part that makes this a research project rather than a demo: a frozen benchmark that **measures** whether the system understood each question correctly.

## What we are building

| Component | What it is | What the user sees |
|:-------------|:-----------------------------------|:-----------------------------------|
| Data pipeline | Hourly collectors for government station readings, the CAMS atmospheric model and weather; a historical archive mined from published government reports | "Data as of 08:00 PKT" --- always current |
| 3D digital twin | A WebGL map of Lahore with one column per station, coloured on the official US AQI scale, with time animation and a wind layer | The city, live, rotating, playable through time |
| Language layer | A large language model that fills a strict, typed form (metric, place, time, view, camera) which code then validates and executes | Ask anything in plain words; get a map and a sentence back |
| Conversation layer | Clarifying questions when a question is ambiguous, follow-up questions that remember context, and a "show the query" toggle | A system that asks back instead of guessing, and shows its working |
| Honesty layer | Nearest-station distance disclosure, a coverage map, a recommendation for where the next station should go, and a public page showing how wrong the forecasts were | Trust you can calibrate |
| Forecast | A 24--48 hour per-station prediction, scored against a simple baseline | "Tomorrow looks worse" --- with its error bar |
| Evaluation harness | A 60-question gold benchmark, forecast scoring, model-vs-ground validation and a small user study | The numbers in the report |
| Deployment | A public website, installable on a phone as an app (PWA) | A link anyone can open |

## The problem it solves

### Context

Lahore is among the most polluted major cities in the world. Community sensor data has put its annual average PM2.5 at around 105 µg/m³, with hourly peaks near 900 µg/m³ [1]. The smog season runs from roughly October to February, driven by crop-residue burning, vehicle and industrial emissions, brick kilns and construction dust [2]. For eleven million people this is a public-health problem for a third of every year.

Data availability has improved sharply. The Punjab Environmental Protection Agency now runs a real-time platform for 11 named Lahore stations and dozens more across the province [2], and in October 2025 the Punjab government launched *EcoBot*, a WhatsApp bot that returns a city's AQI on request [3].

**What has not improved is the ability to understand that data.** Three specific problems remain.

### Problem 1 --- Data you cannot ask questions of

Every existing interface answers one question: *what is the number?* The questions people actually have are comparative, spatial and temporal --- *which part of the city is worst, is it getting better, when during the day should I avoid going out, how does this week compare with last month?* Answering them today means opening several screens, reading tables and doing the comparison in your head. For a member of the public that friction means the question goes unasked; for a journalist, teacher or policy officer it means hours of manual work.

**Airlume's answer:** the question is the interface. One sentence in, one answer out, shown on the map.

### Problem 2 --- Maps that pretend to know more than they do

Consumer air-quality apps paint smooth colour across whole cities. In Lahore that surface is interpolated from about a dozen stations serving eleven million people. Users reasonably assume the colour over their street is a measurement of their street. It is not --- and nothing on the screen tells them so.

**Airlume's answer:** show discrete stations, never an invented surface. When asked about a neighbourhood with no monitor, say so and give the distance to the nearest one. Publish a coverage map showing where the city cannot currently be measured.

### Problem 3 --- Forecasts nobody holds accountable

Platforms publish forecasts. Almost none publish how wrong those forecasts turned out to be, so a user has no basis for deciding how much to trust them.

**Airlume's answer:** a public accuracy page, generated automatically, that scores every forecast against what the stations actually recorded --- including the days it got badly wrong.

### Who this helps

| User | Their question | What Airlume gives them |
|:--------------|:----------------------------------|:----------------------------------------|
| Resident / parent | Is it safe to go out this evening? | The official AQI band for their nearest station, with the distance, and the standard advisory wording |
| Student / teacher | How does smog build up across the city? | An animated, explorable 3D city, usable in a classroom |
| Journalist | Which areas were worst this week and how does it compare with last year? | A comparison answer in one sentence, with a chart to cite |
| Researcher | How reliable is the global atmospheric model over Lahore? | A published model-vs-ground error characterisation |
| Policy officer | Where are we blind? | A coverage map of areas far from any monitor |

## How Airlume differs from what already exists

The idea of talking to air-quality data is not new, and it is important to state that plainly. The table below positions Airlume against the closest existing work.

| System | What it does | Where it stops |
|:-------------------|:--------------------------------------------------|:----------------------------------------------|
| **VayuBuddy** (India, 2024) [4] | LLM chatbot over Indian government data (537 stations, 7 years). The model writes Python that produces line plots, bar charts and map plots. Benchmarked on 45 questions; best model scored 39/45 | No 3D. **Scoring whether a generated plot is correct is left as future work** --- the authors note it "would need a purpose-built rubric". Question set and scoring code not released. No user study |
| **VayuChat** (India, 2025) [5] | Successor; executable code plus interactive visualisations, publicly deployed | Demonstration paper; no evaluation method or benchmark stated |
| **EcoBot** (Punjab, 2025) [3] | WhatsApp bot returning AQI for Lahore, Faisalabad, Rawalpindi and Multan, with health tips, in English and Urdu | Lookup only. No maps, no spatial or temporal analysis, closed |
| **Punjab EPA portal** [2] | Official real-time dashboard; 24-hour and 7-day trends, rankings, forecast | Filter-driven; no question answering; no download; no published forecast error |
| **Smart-city NL interfaces** [6] | LLM natural-language interfaces for urban air-quality decision support | General-purpose; not spatial-camera aware; not Pakistan |
| **Consumer apps** (IQAir and others) | City AQI, smooth maps, forecasts | Interpolated surfaces imply false precision; station-level data paywalled |

**The gap Airlume fills** is the one VayuBuddy's own authors identified: there is no rubric for scoring whether a conversational system produced the *right visual answer*, as opposed to the right number. Airlume makes the visual answer --- chart type, area, time window and camera position --- a set of typed fields that can be checked one by one against a gold standard. That converts "it looks right" into a measurable accuracy figure. Airlume then adds the two things no existing system offers for Lahore: honest coverage disclosure and public forecast accountability.

## Contributions

| ID | Contribution | Why it is new | How it is verified |
|:----|:--------------------------------|:--------------------------------------|:------------------------------------|
| C1 | **A scoring rubric for conversational visual analytics** via a typed view-intent schema | Closes the gap VayuBuddy names as future work [4] | Per-field accuracy on a frozen 60-question benchmark |
| C2 | **Camera pose as part of the answer** in a 3D geospatial scene | No surveyed system treats viewpoint as a generated output | Camera fields scored separately in C1 |
| C3 | **Sparsity-honest visualisation protocol** and a quantified coverage map | Commercial maps interpolate; none disclose distance-to-sensor | Protocol audit; user comprehension check |
| C4 | **First quantified CAMS-vs-ground validation for Lahore** | CAMS global is widely consumed over Pakistan with no local error estimate | Released statistics: MAE, bias, correlation per station |
| C5 | **Public, automatic forecast scorecard** | Forecast error is almost never published | Generated from logs, not hand-curated |
| C6 | **Released benchmark** of 60 single questions plus 20 conversation items | VayuBuddy's set was not released, and had no multi-turn or ambiguity cases | Public repository |
| C7 | **Station-placement recommendation** for Lahore's monitoring network | Turns the coverage gap (C3) into an actionable output; comparable to the 2022 ISPRS Lahore study [8] | Coverage gained per proposed station, compared with existing sites |

**Honest positioning.** Airlume does not claim a new machine-learning architecture, and no model is trained from scratch. Its contributions are in systems design, evaluation methodology and local measurement --- the right level of ambition for ten weeks, and each one individually publishable at workshop level.

## Scope

| In scope | Out of scope |
|:---------------------------------------------------|:---------------------------------------------------|
| **Every Pakistani city with monitoring stations**, at city level: Punjab's 36 EPA districts, plus Islamabad, Karachi, Peshawar and Quetta where third-party stations exist | Places with no stations (rural areas, unmonitored towns): no invented values |
| **Lahore in full depth**: the only city with enough stations (11) for an intra-city 3D twin | Intra-city detail for any other city |
| Country-wide questions: rankings, comparisons and trends between cities | Indoor air quality |
| Clarifying questions and follow-up conversations | Open-ended chat unrelated to air quality |
| Recommended locations for new monitoring stations | Installing or calibrating physical sensors |
| Six question classes: lookup, ranking, comparison, trend, aggregate, conditional | Causal attribution of pollution sources |
| 24--48 hour forecasts | Personal medical advice |
| English questions, plus a 20-question Roman-Urdu test set | Seasonal (multi-month) forecasting |
| Public website + installable phone app (PWA) | Native Android/iOS apps |

\newpage

# Part B --- Resources, Costs and Access

Every resource was checked on **12 October 2026** against official documentation. **Total cost of the project: PKR 0.** Several free tiers changed during 2026; the changes that matter are flagged.

## Data sources

| Source | Free | Key | May we republish? | Role in Airlume |
|:---------------------|:----------|:---------|:---------------------------|:--------------------------------|
| **Punjab EPA portal** (aqi.punjab.gov.pk) | Yes | None | Unclear --- no licence published | Live readings for 36 Punjab districts (41 EPA monitors in 17 districts per the EPD order of 1 Oct 2025; 11 in Lahore). Server-rendered HTML, no public JSON; see Appendix D |
| **Punjab EPD archive** (epd.punjab.gov.pk) | Yes | None | Cite and analyse as published reports | Deep history: about 2,000 daily AQI PDFs back to 2007, plus weekly district reports |
| **Open-Meteo** air quality + weather | Yes, non-commercial | None | **Yes --- CC BY 4.0** | CAMS model values for validation (C4), wind, temperature, rain |
| **OpenAQ** | Yes | Free key | Yes, per-station licence (CC0 / CC BY only) | Cities outside Punjab (Islamabad, Karachi, Peshawar, Quetta) where its stations exist --- verify coverage and licences in Phase 0 |
| **CAMS / Atmosphere Data Store** | Yes | Free account | **Yes --- CC BY 4.0** since July 2025 | Optional reanalysis baseline |
| **Sentinel-5P** (Copernicus Data Space) | Yes | Free account | Yes, with "Contains modified Copernicus Sentinel data" | Optional NO~2~ satellite layer |
| **WAQI / aqicn** | Yes | Free token | **No --- archiving and "data analysis" prohibited** | **Live display only.** Never archived, never analysed |
| **OpenStreetMap** | Yes | None | Yes, ODbL with attribution | District boundaries, buildings, roads |
| **IQAir** | Partly | Key | Unknown | **Not used** --- station-level data is paywalled |
| **Sindh EPA** (Karachi) | --- | --- | --- | **Publishes no data.** Karachi and other non-Punjab cities rely on OpenAQ (archivable) or WAQI (display only) |

### Key facts about the data

- **Lahore EPA stations (11):** GT Road, Shahdara, Multan Road, Barki Road, Kahna Nau, Gulberg III, DHA Phase 6, Egerton Road, Punjab University, Wagha Border, Safari Park. **Coordinates are not published** --- they must be geocoded in Phase 1.
- **The EPA portal has no public API and no licence**, but its `robots.txt` explicitly allows all crawling. A JSON backend exists (the site and mobile app consume one), and **the page itself embeds its data as JSON** in a `wire:snapshot` attribute --- richer than the rendered table, on the same single request. Contacts: `support@aqi.punjab.gov.pk`, `ddisepa@punjab.gov.pk`.
- **The portal renders fewer stations than it holds.** Its embedded data lists eleven Lahore stations; its HTML table shows ten, omitting Gulberg III, while the page heading still reads "Lahore (11 stations)". Anything built on the rendered table silently loses that station.
- **CAMS resolution over Pakistan is about 45 km**, 3-hourly [7]. All of Lahore falls inside roughly one model cell, so CAMS **cannot** show differences between neighbourhoods. Stations provide the intra-city picture; CAMS is used only as a validation target and regional context.
- **CAMS archive for Pakistan starts August 2022**; the API returns up to 92 past days per request.
- **Open-Meteo limits:** 10,000 calls/day, 5,000/hour, 600/minute. Airlume needs about 100/day.

## Map and visualisation stack

| Component | Licence | Free | Key | Note |
|:-------------------|:-------------|:------|:---------|:------------------------------------------|
| deck.gl 9.4 | MIT | Yes | None | 3D layers: columns, arcs, polygons |
| pydeck 0.9.3 | Apache 2.0 | Yes | None | Python binding; **no Mapbox token needed** |
| MapLibre GL JS 6.14 | BSD-3 | Yes | None | Map renderer |
| **CARTO basemaps** | Service | Yes | **Free key, required since 23 Sep 2026** | 5 million tile requests/month non-commercial |
| Protomaps PMTiles | BSD + ODbL | Yes | **Never** | Fallback: self-hosted Lahore map file |
| Mapbox GL JS | Proprietary | No | Mandatory + billing | **Do not use** |
| Cesium ion | Apache (renderer) | Limited | Token | **Do not use** --- 1,000 imagery sessions/month |

**Important change:** pydeck's default basemap is a keyless CARTO URL. CARTO blocked keyless raster tiles on 25 September 2026 and describes keyless vector tiles as working "for now". Request the free key in Phase 0.

## Hosting and automation

| Service | Free | Use in Airlume | Watch out for |
|:--------------------|:-----------|:-----------------------|:-----------------------------------------|
| **GitHub** + **GitHub Actions** (public repo) | Yes, unlimited minutes | Code, hourly CAMS collector (**from 28 Oct 2026**; see 1.4) | **Scheduled jobs are disabled after 60 days without repo activity.** Schedule at minute 17, not 0. Punjab EPA fetch does not reach the portal from datacenter runners and now runs on the laptop. |
| **Streamlit Community Cloud** | Yes | Primary app hosting | Sleeps after 12 hours without visitors; commits do not wake it |
| **Cloudflare Pages / R2** | Yes | Static build option; PMTiles host | None at this scale; never sleeps |
| Neon Postgres | Yes, permanent | Only if a database is needed | Compute sleeps after 5 min, resumes automatically |
| Hugging Face Spaces | **No** | Not used | Streamlit/Docker Spaces now require PRO (from July 2026) |
| Render | Limited | Not used | Free bandwidth cut to 5 GB/month (April 2026) |
| Vercel Hobby | Limited | Not used | Cron jobs limited to once per day |

## Language models

| Provider | Free limit (Oct 2026) | Structured output | Role |
|:---------------------|:------------------------------------|:------------------|:----------------------|
| **Groq** `gpt-oss-120b` | 200,000 tokens/day, 1,000 requests/day | Strict JSON schema | **Primary model** |
| Groq `gpt-oss-20b`, `qwen3.8-27b` | 200,000 tokens/day **each** | Strict JSON schema | Second and third models for comparison |
| Google Gemini Flash-Lite | About 500 requests/day (Google no longer publishes figures) | JSON schema --- verify on Flash-Lite | Fourth model |
| Cerebras | 1 million tokens/day, 5 per minute (trial) | Yes | Overflow |
| **Ollama** (local, e.g. Qwen 8B) | **Unlimited** | Yes | Development runs; offline baseline |
| OpenRouter | 50 requests/day | Varies | Not used |

**Data note for the ethics section:** Google uses free-tier Gemini content to improve its models and may have humans review it. Groq does not retain inference data by default and offers zero data retention. Airlume sends no personal data to any model.

## Development tools (all free and open source)

Python 3.12, DuckDB (MIT), Pandas (BSD), Pydantic (MIT), scikit-learn (BSD), LightGBM (MIT), statsmodels (BSD), pdfplumber (MIT), GeoPandas (BSD), Shapely (BSD), Streamlit (Apache 2.0), FastAPI (MIT), pytest (MIT), Git.

## Accounts to create

| Account | Needs card | Time |
|:----------------------------------|:-----------|:---------|
| GitHub (public repository) | No | 2 min |
| Groq console API key | No | 2 min |
| Google AI Studio API key | No | 2 min |
| OpenAQ API key | No | 2 min |
| CARTO basemap key | No (email only) | 1 min |
| Streamlit Community Cloud (GitHub login) | No | 1 min |
| Cloudflare (optional) | No | 3 min |
| Copernicus Data Space (optional) | No | 3 min |

\newpage

# Part C --- System Design

## Architecture

```
   QUESTION ("Where is smog worst today?")
                   |
                   v
   +---------------------------------------+
   | LANGUAGE LAYER                        |
   | LLM fills a typed view-intent form:   |
   | metric, area, time label, view,       |
   | comparison, camera                    |
   +-------------------+-------------------+
                       |
                       v
   +---------------------------------------+
   | VALIDATION LAYER  (deterministic)     |
   | Pydantic schema check                 |
   | "today" -> real timestamps (PKT)      |
   | out-of-scope -> structured refusal    |
   | SQL assembled by code, never the LLM  |
   +-------------------+-------------------+
                       |
                       v
   +---------------------------------------+
   | DATA LAYER  (DuckDB + Parquet)        |
   | stations | readings | cams | weather  |
   | forecasts | coverage | run log        |
   +-------------------+-------------------+
                       |
                       v
   +---------------------------------------+
   | RENDER LAYER  (deck.gl / pydeck)      |
   | columns | animation | split view      |
   | wind | camera flight | answer text    |
   +---------------------------------------+

   Separately, every hour (GitHub Actions):
   collectors -> clean -> append -> commit + heartbeat
```

**The single most important design rule: the language model never writes code or SQL.** It fills a form. Code validates the form and builds the query. This makes the system safe (nothing can be injected), robust (a bad answer becomes a polite refusal, not a crash) and measurable (a form can be compared field by field with a correct form).

## The view-intent schema

| Field | Type | Values | Filled by |
|:----------------|:-----------|:-------------------------------------------------|:-----------|
| `metric` | enum | pm2_5, pm10, no2, so2, co, o3, us_aqi | Model |
| `area` | enum | station id, district, region, all_lahore | Model |
| `city` | enum or null | any monitored city (from the station registry); null means all cities | Model |
| `time` | label | now, today, yesterday, this_week, last_week, this_month, named month, past_24h | Model |
| `time_start`, `time_end` | timestamp | resolved in Asia/Karachi | **Code** |
| `aggregation` | enum | mean, max, min, count_above | Model |
| `threshold` | number or null | e.g. 150 | Model |
| `compare_to` | object or null | a second time or area | Model |
| `view` | enum | columns_3d, ranked, split, time_series, calendar | Model |
| `camera` | object | zoom, pitch, bearing, centre | Model |
| `in_scope` | boolean | false triggers a refusal with a reason | Model |
| `clarify` | object or null | a short question plus 2--3 options, when the request is ambiguous | Model |
| `context_ref` | enum or null | inherit_area, inherit_time, inherit_metric --- for follow-ups | Model |

Relative dates are resolved by code, never by the model: models are unreliable at date arithmetic, and a date error fails silently --- the user gets a plausible map of the wrong day.

## Question classes and their views

| Class | Example | View | Camera |
|:-------------|:------------------------------------------|:-------------------|:--------------------|
| Lookup | What is the AQI in Gulberg? | Single column, labelled | Zoomed to station |
| Ranking | Where is smog worst right now? | All columns, top 3 lit | Whole city |
| Comparison | Is today worse than yesterday? | Split screen | Same angle both sides |
| Trend | Show me the last 30 days | Animated time series | Whole city |
| Aggregate | When during the day is it worst? | Hour-of-day chart | Unchanged |
| Conditional | How many days this month were above 150? | Count + calendar strip | Unchanged |
| Out of scope | What is the AQI on my street? | Refusal with reason | Unchanged |
| Ambiguous | How is Gulberg? | Clarifying question: station or area? | Unchanged until answered |
| Follow-up | ...and yesterday? | Previous view, new time window | Previous camera kept |
| Best time | When is the air cleanest today? | Hourly forecast, lowest window highlighted | Unchanged |

## Nearest-station answer rule

| Distance to nearest station | What Airlume says |
|:------------------|:------------------------------------------------------------------|
| Station in the area | "Gulberg III: 196. Measured at the Gulberg III station." |
| Within 3 km | "Nearest station is Egerton Road, 2.4 km away: 205." |
| More than 5 km | "Nearest station is Multan Road, 8.1 km away: 264. This may not reflect conditions where you are." |

\newpage

# Part D --- Phased Build Plan

The build runs **10 weeks, 13 October -- 21 December 2026**, in eight phases. Each sub-phase lists its tasks, what it produces, and the exit criterion that must be true before moving on. Phases overlap slightly where work is independent.


## Added features at a glance

Eight features were added on top of the core plan. Each is placed in the phase where it naturally belongs rather than bolted on at the end. Together they add roughly **14 working days**. To make room for the weakness fixes in Part E, the two polish features --- shareable cards and replay mode --- are now **optional**: built only if time remains, never protected.

| Feature | Sub-phase | Effort | Priority | Why it is here |
|:---------------------------|:-------|:---------|:---------|:----------------------------------------------|
| Show-the-query toggle | 3.7 | 1 day | **Must** | Makes contribution C1 visible on screen during the viva |
| Clarifying questions | 3.8 | 2 days | **Must** | Turns a likely failure into good behaviour; adds a scoreable class |
| Follow-up questions | 3.9 | 2--3 days | Should | Real conversation; its own benchmark set |
| Local-model comparison | 5 (E7) | Half a day | Should | Quotable cost-versus-accuracy result |
| Lowest-AQI window today | 4.6 | 1 day | Should | The most practical question a resident has |
| Where should the next station go? | 4.5 | 3--4 days | **Must** | Turns the coverage limitation into contribution C7 |
| Shareable answer cards | 6.6 | 1--2 days | Optional | How people share in Pakistan --- WhatsApp |
| Replay the worst day | 7.3 | 2 days | Optional | Opening of the presentation |

**Must** features are protected from scope cuts. **Optional** features are built only after every weakness fix in Part E is done.

## Phase 0 --- Foundations and Access (Week 1: 13--19 Oct)

**Goal:** every account works, every data source is confirmed, permission is requested, and a clickable shell of the website exists before any real data does.

### 0.1 Accounts and keys

- Create the eight accounts listed in Part B.
- Store keys in a local `.env` file and in GitHub repository secrets; never commit them. `.env` is already in `.gitignore`.
- Install a pre-commit secret scanner (gitleaks) so a key can never be committed by accident, and scan the existing history once. *(Security, Part E.)*
- **Pin every library version** in `requirements.txt` from day one, so a free-tier or library change cannot break the build later. *(Fixes W13.)*
- Read your real Gemini limits at `aistudio.google.com/rate-limit` and record them.

**Produces:** working keys for Groq, Gemini, OpenAQ, CARTO.

### 0.2 Data-source probing

- Open aqi.punjab.gov.pk in Chrome, DevTools, Network tab, Fetch/XHR filter, and record the JSON endpoint the page calls.
- **Find out which AQI formula Punjab EPA uses** (US EPA breakpoints, or Pakistan's own PEQS-based scale) from the portal, EPD reports or the permission email. Record it in `SOURCES.md`. *(Starts the fix for W1.)* **Answered 16 Oct: Pakistan's own NEQS-anchored scale**, not the US breakpoints --- see 1.7.
- Check whether the US Consulate Lahore monitor is reachable as an independent cross-check. *(Supports W9.)*
- Check whether OpenAQ carries Pakistan reference stations and record each station's licence:

```bash
curl -H "X-API-Key: $OPENAQ_KEY" \
  "https://api.openaq.org/v3/locations?iso=PK&limit=1000" > openaq_pk.json
```

- Confirm Open-Meteo returns data for Lahore:

```bash
curl "https://air-quality-api.open-meteo.com/v1/air-quality?\
latitude=31.52&longitude=74.36&hourly=pm2_5,pm10,us_aqi&past_days=7"
```

- Test a WAQI token on one Lahore station (live display only).

**Produces:** a `SOURCES.md` file recording, for each source, status, endpoint, licence and date checked.

### 0.3 Permission requests

- Email `support@aqi.punjab.gov.pk` and `ddisepa@punjab.gov.pk`: request API access and written permission to archive readings for academic research. Mention EcoBot as evidence a live internal API exists.
- Email the WAQI team to notify them of non-commercial academic display use, as their terms require.
- **Do not wait for replies.** The project is designed to work without them.

**Produces:** dated copies of both emails for the ethics appendix.

### 0.4 Repository skeleton

```
airlume/
  collectors/   epa.py  openmeteo.py  openaq.py  waqi_display.py
  pipeline/     clean.py  store.py  backfill_epd.py
  nl/           schema.py  router.py  resolve.py  prompts/
  viz/          layers.py  views.py  camera.py
  forecast/     baseline.py  model.py
  eval/         benchmark/  run_e1.py  run_e2.py  run_e3.py
  app/          streamlit_app.py
  data/         (parquet files committed by the collector)
  tests/
  .github/workflows/collect.yml
```

Note `waqi_display.py` sits apart from every other collector and writes nothing to `data/`. This separation is deliberate: WAQI data must never reach the archive.

### 0.5 Fake-data shell

- Build the Streamlit page with the 3D map, ten columns of **random** heights, a time slider, an ask box and the six view types --- all driven by fake data.
- Every later phase replaces a fake piece with a real one, so a working demo exists every day of the semester.

**Exit criterion for Phase 0:** the shell runs locally; all keys respond; `SOURCES.md` is complete; both emails are sent.

### 0.6 Phase 0 progress (13 October)

Done on day one, all in the repository:

- **Portal investigated** (Appendix D): Laravel, server-rendered, no public JSON; the Lahore page's HTML table is the data path. A parser with tests (`collectors/epa.py`) and a dry-run script exist. Live hourly collection waits for the permission email or one week of silence.
- **AQI formula identified on 13 Oct, wrongly; solved 16 Oct --- W1 fixed.** The 13 Oct identification picked the US EPA 2012 breakpoints from four hand-checked readings, and those happen to sit where the US and Pakistan tables converge. On 304 stored station-hours the portal turned out to use **its own table, anchored on Pakistan's NEQS limits, with gases in µg/m³**: reproduced 99.7% exactly and 100% within one point, against 6% exact for the US table. `airlume/aqi.py` now defaults to it (`pk_portal`). Full working in `docs/research/w1-harmonisation.md`.
- **Registry built:** 11 Lahore stations with coordinates (9 station-level from IQAir pages, 2 neighbourhood centroids), 36 Punjab districts and 4 other cities (`data/registry/`). Confidence is recorded per row and shown on the map until the EPA confirms.
- **Code skeleton:** typed view-intent schema (Pydantic), resolver with Asia/Karachi dates and the nearest-station rule, DuckDB store with parameterised queries only, fake-data generator, deck.gl layers and cameras, code-written answer sentences, and a rule-based stand-in router. 45 tests pass.
- **Shell runs** on fake data in keyless map mode: question in, typed form out, validated query, answer sentence, 3D columns or national city view.
- **Security groundwork:** `.env.example`, start-up secret check that refuses placeholders and blocks fake data in production, gitleaks config, pre-commit config, XSRF protection on, usage statistics off, WAQI isolation enforced by a test.
- **Emails drafted** (`docs/emails/`), `SOURCES.md` written.

Still open this week: create the accounts (Groq, Google AI Studio, OpenAQ, CARTO, Streamlit Cloud), send the two emails, run `scripts/epa_dry_run.py` on the laptop to confirm the parser against the live page, and check whether the page's embedded JSON block is public.

## Phase 1 --- Data Pipeline (Weeks 2--3: 20 Oct -- 2 Nov)

**Goal:** real data flowing every hour, a historical archive, and checks that catch problems automatically.

### 1.1 Station registry and geocoding

- Build `stations.csv`: id, name, city, latitude, longitude, source, geocode method, confidence.
- Geocode the 11 Lahore stations (EPA publishes names only) using OpenStreetMap Nominatim plus manual verification against the EPA map; record the method for each.

**Produces:** a verified station registry --- the foundation of every map and distance calculation.

### 1.2 Live collectors

| Collector | Frequency | Writes to archive |
|:--------------------|:-------------|:----------------------|
| EPA stations | Hourly | Yes |
| Open-Meteo air quality (CAMS) at each station point | Hourly | Yes |
| Open-Meteo weather (wind, temperature, rain, humidity) | Hourly | Yes |
| OpenAQ (if Pakistan coverage confirmed) | Hourly | Yes, licence-filtered |
| WAQI | On page load | **Never** |

Every collector: timeouts, three retries with backoff, a descriptive User-Agent with a contact address, and a log line per run.

### 1.3 Storage

- Append-only Parquet files partitioned by month, queried with DuckDB.
- Tables: `stations`, `readings`, `cams`, `weather`, `forecasts`, `runs`.
- Append rather than rewrite, so git history grows slowly (about 8,600 commits a year otherwise).

### 1.4 Scheduler

```yaml
on:
  schedule:
    - cron: "17 * * * *"   # minute 17, not 0: top of hour is peak
  workflow_dispatch:
```

- Each run writes a heartbeat timestamp, so a commit always lands and GitHub's 60-day inactivity rule can never disable the job.
- Run unattended for **48 hours** before trusting it.

- **External timer installed (15 Oct):** a cron-job.org job calls `POST /repos/Xftab/airlume/actions/workflows/collect.yml/dispatches` every hour at :00 with a fine-grained GitHub token (repository: this one only; permission: Actions read/write + Metadata read; expires 13 Jan 2027 --- renew before then). First test returned 204 and run #8 appeared within a minute. GitHub's own `17,47` schedule stays as a second chance; the collector de-duplicates. Overnight 14-15 Oct GitHub alone fired 5 of 16 hourly slots.
- **Observed (14 Oct):** GitHub started only one of the first five hourly slots (all runs that did start were green). Schedule changed to two slots an hour (`17,47 * * * *`); the collector de-duplicates. If coverage stays below ~80% of hours after a day, the fallback is an external timer (cron-job.org) calling `workflow_dispatch` with a fine-grained token scoped to this one repository's Actions, or making the repository public (public repos get unlimited minutes and, anecdotally, more reliable scheduling). Coverage is measured as hours with at least one round in `data/archive/readings/punjab_epa/`.
- **Hybrid architecture adopted (28 Oct):** since 25 Oct 11:00Z the GitHub Actions runner's EPA fetch has silently failed (the runs still succeed and commit CAMS, which is why nothing alarmed), while the same code from the laptop still reaches the portal cleanly. The most parsimonious explanation is a portal-side IP/geo filter on datacenter addresses. From 28 Oct Punjab EPA collection moves back to the laptop via Windows Task Scheduler (`schedule.bat` --> `collect_push.bat`): collect, commit `data/archive/` only, pull `--rebase -X theirs --autostash`, push. Open-Meteo CAMS keeps running in the cloud (`collect.yml`) unchanged; its silently-failing EPA calls are harmless, because the collector writes nothing when a source fails. The two sides write to different archive files, so the CSVs do not conflict. Trade-off: EPA collection depends on the laptop being on; the only alternative inside the budget is a Pakistan-hosted VPS, which is out of scope for the semester.

### 1.5 Historical backfill --- the CC425 component

- Harvest the EPD daily-report index (about 105 pages, about 2,000 PDFs).
- Extract tables with pdfplumber; validate a random 5% by hand.
- **Implement extraction three ways --- sequential, multiprocessing, and asynchronous download + process pool --- and benchmark speed-up against worker count.** This is the Parallel and Distributed Computing deliverable, on real work rather than a toy problem.
- Backfill CAMS from Open-Meteo (archive from August 2022).

### 1.6 Data quality

- Flag gaps, stuck sensors (identical values for hours), impossible values and sudden spikes. **Done 15 Oct** (`airlume/pipeline/quality.py`, `scripts/quality_report.py`, 17 tests): nothing is corrected automatically, because the archive is the data of record; every suspect value is flagged and left in place. Thresholds are stated in the report rather than buried in code.
- Track per-station uptime; show "x of 11 stations reporting" in the app. **Done** --- uptime is measured over the hours the collector *actually ran*, never a wall-clock range, so the irregular collection before 15 Oct is not counted against the stations. A new **Data quality** tab shows uptime, flags and the thresholds.
- **Settle the city-hour revision problem.** Two portal widgets (the 7-day trend and the home-page district ranking) write the same archive key `(city_id, ts, source)` under one source name, so they overwrite each other and the disagreement is lost; separately, two collections inside one clock hour overwrite each other. 4 of 10 commits revise an already-committed city value. See `docs/research/data-quality.md`; the recommendation is to give the trend widget its own source name, as the forecast tables already do.
- **Open findings to act on:** Gulberg III (`LHR-GB3`) has never reported in any collected hour --- confirm on the live page whether it is renamed or withdrawn, then add a parser alias or mark it inactive, so "10 of 11" stops reading as a failure.

**Exit:** the quality report runs over a week of data; the city-hour revision rule is decided and documented; no unexplained flag is left unexamined.

### 1.7 AQI harmonisation (weakness fix W1)

**Solved 16 Oct 2026** (`docs/research/w1-harmonisation.md`). The portal computes AQI from the **latest hour's** concentrations as the **maximum of per-pollutant sub-indices**, on **its own breakpoint table**, with gases banded in **µg/m³**. Implemented as `pk_portal`, now the default in `airlume/aqi.py`; the US 2012 and 2024 tables are kept for comparison.

| Scale | Exact | Within 1 | Mean abs error | Dominant pollutant agrees |
|---|---|---|---|---|
| **`pk_portal`** | **99.7%** | **100%** | **0.00** | **100%** |
| US EPA 2012 (used 13--16 Oct) | 6.2% | 18.8% | 7.48 | 94% |
| US EPA 2024 | 2.0% | 7.9% | 11.12 | 94% |

- **The table is built on Pakistan's NEQS limits.** An AQI of exactly 100 is the national short-term limit for every pollutant the data can fit: PM2.5 35, PM10 150, NO₂ 80 (24 h) and O₃ 130 µg/m³ (1 h). Bands: PM2.5 15 / 35 / 70 / 150 / 250 / 350; PM10 75 / 150 / 250 / 350 / 450 / 550; O₃ 65 / 130 / 195; NO₂ 40 / 80 / 130. Each fitted with r² = 1.00 per band.
- **Averaging window settled on 24 consecutive hours:** latest hour. Mean error 0.0, against 20.2 for an 8-hour mean and 26.8 for 24 hours, at all eleven stations.
- **Confirmed at scale (24 Oct 2026).** Re-run on the full archive --- **2206 station-hours over 210 consecutive hours**, up from the 304 rows the table was fitted on --- the latest-hour `pk_portal` AQI still reproduces the portal to **mean absolute error 1.7, median 0.0**. The 8-hour and 24-hour windows remain far worse (mean error 45.1 and 54.7), so the latest-hour choice holds at scale. The dominant-pollutant mix broadened to PM2.5 71% / PM10 24% / O₃ 4% / NO₂ 1% as the archive came to span more of the day, so the original fit was not an artefact of a short, PM2.5-dominated sample. **Open:** one row is off by 99 points and is not yet traced (most likely a bad input row --- a dropped or zero concentration), and no confidence interval is attached to the at-scale error yet; trace the 99 and add a moving-block bootstrap CI to the W1 table.
- **Why 13 Oct looked right:** the four hand-checked readings were all high (141--311 µg/m³), where the two tables converge. They diverge most at 35--70 µg/m³ --- Lahore's ordinary afternoon --- which is where the +8 bias came from. The rejected ozone "8-hour maximum" hypothesis was the same mismatch in disguise: O₃ banded in µg/m³ on a 65/130 scale, not converted to ppb.
- **Still provisional:** PM2.5 above 350 and PM10 above 550 have not been observed and are extrapolated (they match the US table at that level); November's smog will test the top PM2.5 band, so re-run `scripts/w1_check.py` then. The NO₂ 101--150 band rests on one point. Above the last fitted gas band the sub-index is refused rather than guessed. SO₂ and CO have never been dominant, so their bands are NEQS-anchored placeholders that cannot yet have affected any value.
- Convert every CAMS concentration into this AQI before any comparison with station AQI (4.3). Where stations publish raw PM2.5, compare concentrations directly as well. **Now possible honestly**, since the scale is the portal's own.
- Unit-test the converter against at least 10 published EPA readings where both concentration and AQI are shown. **Done: 13 published readings pinned in `tests/test_aqi.py`, all exact.**
- Store the scale used alongside every value. **Partly:** `aqi_computed` in the archive used US 2012 until 16 Oct and `pk_portal` after; it is derived and recomputable, earlier rows are not rewritten (append-only), and anything needing a consistent series recomputes from the stored concentrations.

**Exit: met 16 Oct** (confirmed at scale 24 Oct: mean absolute error 1.7 on 2206 station-hours over 210 hours), with the top PM2.5 band to be confirmed on winter data and one 99-point outlier still to trace.

**Exit criterion for Phase 1:** 48-hour soak passes with no missed runs; EPD backfill extracted and spot-checked; data-quality report generated; AQI harmonisation tested.

### 1.8 Collection coverage and secret hygiene (added 31 October 2026)

**Measured coverage of the Punjab EPA station archive (31 Oct 2026).** 14 Oct 04:00 to 31 Oct 09:00 UTC: 2395 of 4554 expected station-hours (52.6 percent); 229 of 414 hours have any data. Two causes: the 24 Oct to 28 Oct outage (110 empty hours, permanent, the portal exposes current readings only) and the laptop collector not running 28 to 30 Oct (Windows battery defaults, fixed 30 Oct in `schedule.bat`). In the stable window 15 Oct 06:00 to 24 Oct 02:00 UTC (212 hours), 8.0 percent of station-hours are missing, by station 4.2 to 9.9 percent (Gulberg III highest, not an outlier). The earlier 4.5 percent figure belongs to the 210-hour W1 sample only. Missing values are shown as missing, never filled (design rule 6).

**Secrets.** On 30 Oct a screenshot exposed the Groq key; it was revoked and verified dead, then a replacement exposed in another screenshot was also revoked. `scripts/check_secrets.py --live` now tests that a key authenticates without printing it. Procedure from now on: the key is moved from clipboard to `.env` by a one-line command and is never shown or committed. The Actions-only GitHub token used by cron-job.org remains to be rotated (optional, expires 13 Jan 2027).

**Exit:** coverage figures in the report come from the archive, with window and cause stated; no key outside `.env`.

## Phase 2 --- The 3D Digital Twin (Weeks 3--4: 27 Oct -- 9 Nov)

**Goal:** the city on screen, driven by real data, with every view the language layer will later need.

### 2.1 Basemap

- CARTO dark basemap with the free key. Fallback: Protomaps PMTiles extract of Lahore. Second fallback: no basemap, OSM district polygons only.

```bash
pmtiles extract https://build.protomaps.com/<latest>.pmtiles lahore.pmtiles \
  --bbox=74.15,31.35,74.60,31.70 --maxzoom=14
```

### 2.2 Station columns

- deck.gl `ColumnLayer`: height and colour by AQI on the **official US AQI bands**, labels and tooltips.

### 2.3 Time animation

- Play/pause, scrubber across 24 hours, 7 days or 30 days. **Done 15 Oct**, in the "Hourly readings" tab: a window selector (24 hours / 7 days / 30 days), a scrubber over the hours actually collected in that window, and a play toggle that steps one hour at a time and wraps. The animation runs inside a Streamlit fragment, so a tick redraws only the map rather than re-querying the store and rebuilding the page. The frame counter states the position ("hour 7 of 10") because the number of frames is the number of hours collected, not a fixed 24.

### 2.4 Wind layer

- Wind arrows from Open-Meteo, shown as context and labelled as correlation, never cause.
- **Prefer the stations' own wind. Done 15 Oct.** The portal's embedded snapshot carries `wind_speed`, `wind_direction`, `temperature` and `humidity` *per station*, hourly, from the same request we already make (`docs/research/portal-snapshot.md`), and those columns are now stored. The layer draws from the monitors themselves rather than interpolating a ~45 km model cell; Open-Meteo stays the source for cities with no EPA station.
- **Direction convention, pinned by test.** The portal reports the meteorological convention --- the direction the wind blows *from*. An arrow on a map reads as motion, so it is drawn towards `direction + 180`, while the label keeps the "from" wording people quote. Reversing this would be invisible on screen and wrong in every figure in the report.
- Arrow length is proportional to speed with a floor, so a calm station still shows its direction instead of vanishing. Stations without wind are omitted rather than drawn at zero, and the whole layer is omitted when no station has wind. Arrows render beneath the columns so they never hide the value they are context for.

### 2.5 View types

- Ranked city view, single-station focus, split-screen comparison, time series, calendar strip.
- **A plain 2D ranked bar chart beside every 3D view, and a top-down toggle.** 3D columns in perspective make heights hard to compare --- near columns hide far ones and distance shrinks them --- so exact comparison always happens in 2D, while 3D provides spatial context. *(Fixes W10.)*

### 2.6 Coverage map --- a finding in itself

- Draw 3 km and 5 km buffers around each station over Lahore's neighbourhoods and population.
- Report the share of the city's area and population more than 5 km from any monitor. **Both done 15 Oct** (`docs/research/population.md`).

| | Area | Population |
|---|---|---|
| Mean distance to the nearest monitor | 4.93 km | **4.31 km** |
| Within 3 km | 23% | 32% |
| **Beyond 5 km** | 44% | **33% --- 4.67 million people** |

- **The headline figure for the report: 4.67 million people in Lahore live more than 5 km from an air-quality monitor.** People are better covered than the average square kilometre because the eleven stations sit in the built-up city while the bounding box includes farmland. Both numbers are kept, because they answer different questions, and the report never says "coverage" without saying which.
- Population is WorldPop 2025 at 1 km (CC BY 4.0), cut to Lahore once by `scripts/extract_population.py` into a 72 KB committed CSV, so nothing at runtime needs `rasterio` or GDAL.

**Exit criterion for Phase 2:** all six views render from real data at 30 frames per second or better; coverage statistics computed.

**Phase 2 status, 15 Oct: met, with one measurement outstanding.** 2.1--2.6 all render from real data and the coverage statistics are computed for both area and population. Frame rate has not been measured; it belongs to E6 in Phase 5, and with eleven columns over a 1 km grid there is no reason to expect trouble, but it is not yet a measurement and is not claimed as one.

## Phase 3 --- The Language Layer (Weeks 5--7: 10--30 Nov)

**Goal:** a sentence in, the right map out --- and a way to prove it.

### 3.1 Schema

- Implement the view-intent schema in Pydantic. Keep it flat; every field required, optional fields as null-unions --- the shape that works unchanged on Groq strict mode and Gemini.

### 3.2 Benchmark --- built and frozen before the model is wired in

- **60 test questions**, 10 per class, including 8 out-of-scope items, each annotated with its correct form.
- **10 ambiguous questions**, each annotated with the clarifying question expected and the options it should offer.
- **10 short follow-up dialogues** (two or three turns each), annotated with the correct form at every turn.
- **20 development questions**, kept separate, used for tuning.
- **20 Roman-Urdu questions** ("aaj Gulberg ki hawa kaisi hai?"), promoted from stretch. *(Reduces W12.)*
- **Blind authorship:** two or three classmates write about half of the 60 test questions *without seeing the schema*, so the test is not shaped to fit the system. *(Fixes W2.)*
- **Second annotator:** another person independently writes gold forms for 20 questions; report agreement (Cohen's kappa per field) and resolve disagreements by discussion. *(Fixes W2.)*
- **Camera scored in categories**, not exact numbers: level (city / district / station) and rough direction (N, NE, E ...). *(Fixes W5.)*
- **Freeze the test set in week 5. Never tune on it.**
- **Materials ready (14 Oct):** `docs/benchmark/classmate-questions.md` (printable sheet, 20 questions per classmate, blind to the schema, with Roman-Urdu and out-of-scope minimums) and `docs/benchmark/annotator-guide.md` (field table and ten agreed conventions for the second annotator; kappa per field).
- **Status (14 Oct):** benchmark v0 (90 items) is a *development* set --- the router prompt was revised after reading its failures, so its scores are optimistic. The frozen v1 set (classmate items, second annotator) is what the report's headline number comes from; the prompt is not touched after the freeze.

### 3.3 Model router and caching

- Primary: Groq `gpt-oss-120b`. Fall through on rate limit to `gpt-oss-20b`, `qwen3.8-27b`, Gemini Flash-Lite, then local Ollama.
- **Temperature 0 on every call**, so answers are as repeatable as the provider allows. *(Part of the fix for W6.)*
- Cache every call by prompt hash in SQLite; repeated runs cost nothing.
- Keep prompts short: Groq's limit is tokens per day, so a 400-token prompt gets four times the calls of a 1,600-token one.
- **What the first live calls taught (14 Oct):** Groq's strict `json_schema` mode rejects the schema Pydantic emits (`$ref`, `default`, `title`), so the router sends a flattened strict copy (`strict_schema()`), with `additionalProperties: false` and every field required; `gpt-oss` reasons before it answers and the reasoning counts against the output cap, so the cap is 2,048 with `reasoning_effort: low` (a 400-token cap returned empty output). Free-tier limits are 8,000 tokens per minute and a daily cap: the router sleeps for Groq's stated retry time on the per-minute cap and fails fast on the daily one; the benchmark caches single runs so an interrupted run resumes. A full 90-item run costs about 140k tokens and ~15 minutes.
- **Prompt frozen at v3 (15 Oct). Results on benchmark v0 (dev set): stub 45.6%; 120b v1 66.7%; 20b v2 81.1%; 120b v3 88.9% (CI 82--96%); 20b v3 88.9% (CI 82--94%).** The two model sizes tie, so the small model is a valid fallback. Full table and failure analysis: `docs/research/e1-results.md`.
- **First result, prompt v1, `gpt-oss-120b`: 66.7% pass (95% CI 57--77%) against the stub's 45.6%.** Failure groups: station names not placed in `area` (8 items; the prompt only mentioned neighbourhoods), "worst right now" read as `max` (3), wrong AQI thresholds for band words (2), districts treated as out of scope (1), comparisons unflagged (6), follow-ups not inheriting the previous form (7). Prompt v2 states a rule per field, lists the 40 cities and the Punjab bands, and gives five worked examples; re-scored next.
- Log model id, timestamp, prompt and response for every call --- free model ids change without notice, and the log is what makes the evaluation reproducible.

```bash
ollama pull qwen3:8b
```

### 3.4 Validation, dates and refusals

- Schema validation; date-label resolver in Asia/Karachi; refusal templates for street-level, causation, medical, and pre-archive history questions.

### 3.5 Integration

- Form, then query, then data, then view, then camera flight. **This is the week the two halves of the project become one product.**

### 3.6 Answer text

- A short sentence generated **from the query result only**, never from the model's general knowledge. Factors such as wind are worded as "possible factors", never as causes.

### 3.7 Show-the-query toggle (added)

- A "Show the query" switch under every answer displays the filled form as a readable card: metric, area, time window (resolved to real timestamps), aggregation, view and camera.
- Fields resolved by code rather than the model are marked, so a viewer can see exactly where the model's job ends.
- **Why it matters:** contribution C1 is a rubric that scores these fields. This toggle lets an examiner watch the rubric's input being produced, live.

**Exit:** the toggle shows the correct form for every benchmark question replayed in the app.

### 3.8 Clarifying questions (added)

- When a request has more than one reasonable reading, the model fills `clarify` instead of guessing: a one-line question and two or three tappable options.
- Triggers: a place name matching both a station and an area ("Gulberg"); a missing time ("how bad was it?"); a metric that could be PM2.5 or the AQI.
- The chosen option is merged into the form and the question runs normally.
- **Scoring:** clarification precision (asked when it should) and recall (never asked when the question was clear), on the 10 ambiguous items plus the 60 clear ones.

**Exit:** clarifications appear for the 10 ambiguous items and for none of the clear ones on the development set.

### 3.9 Follow-up questions (added)

- The app keeps the last confirmed form. A follow-up ("and yesterday?", "what about DHA?") fills only the fields that change and sets `context_ref` for the rest.
- Context is held for the current session only and never stored.
- A "start over" button clears it.

**Exit:** the 10 follow-up dialogues run correctly end to end.

**Exit criterion for Phase 3:** every question class works end to end in the app; refusals, clarifications and follow-ups behave correctly; the benchmark is frozen.

- **Status (14 Oct):** built. The app keeps the previous form in the session, routes a question only when it changes (Streamlit re-runs the script on every click, which otherwise fed a question back as its own follow-up), shows the last four exchanges in the sidebar, and has a *Start over* button that clears the context. The offline stub also handles short follow-ups ("and yesterday?", "show PM10 instead") by editing the previous form, so the demo degrades gracefully without the model.

## Phase 4 --- Forecasting and Validation (Week 8: 1--7 Dec)

### 4.1 Persistence baseline

- "Tomorrow equals today", per station. Every model must beat this or the result is reported as a negative finding.

- **Built 15 Oct (early):** `store.forecast_errors_with_baselines` joins every scored forecast hour with two baselines on the same hour, and `forecast/skill.py` computes MAE, bias and skill = 1 - MAE(forecast)/MAE(baseline). The scorecard and a by-horizon chart live in the *Next 24 hours* tab. First 34 scored hours (14-15 Oct): EPA forecast MAE 33, bias +28 (too pessimistic); CAMS MAE 36, bias -17 (too optimistic); both skill 0.1 against "last value" --- barely better than repeating the current reading. Too few hours to conclude; the number to watch is skill after two weeks.

### 4.2 Forecast model

- LightGBM on lagged readings, hour of day, day of week and weather. Trained on history, tested on the most recent weeks only.
- **Add CAMS's own 5-day forecast as an input feature.** The model then learns to correct CAMS's local bias for each station rather than predicting from scratch --- a standard technique (model output statistics) and the most realistic route to beating persistence. *(Reduces W7.)*
- Expect the honest outcome to be "comparable to baseline" at 24 hours, and report it either way.

### 4.3 CAMS-vs-ground validation (C4)

- Pair each station reading with the CAMS value for the same hour.
- Report MAE, signed bias, correlation, per station and by hour of day. Published whatever it shows.
- **Framed as agreement, not error:** station instruments are uncalibrated and sometimes offline, so C4 measures how far model and stations agree, not how wrong CAMS is. Report each station's uptime, and cross-check against the US Consulate monitor where available. *(Handles W9.)*
- Comparisons use harmonised AQI from 1.7 only.
- **Built 16 Oct; preliminary run on 30 hours** (`airlume/validation.py`, `scripts/cams_validation.py`, `docs/research/cams-validation.md`). Concentrations are compared directly; AQI only on the portal's own scale, PM-only on both sides because CAMS has no gases; 95% intervals from a block bootstrap over hours. First results: CAMS reads PM2.5 **about 20 ug/m3 low** for the city mean (CI -28 to -4, r 0.70), almost entirely at night (bias -0.1 over 10:00--19:00 PKT, -28 overnight); it **does not track PM10** (bias -78, r -0.16), consistent with coarse local dust missing from the model; per-station bias ranges from -52 (Multan Road) to +18 (Wagha). Correlation peaks with CAMS shifted 1--2 hours later (0.83 against 0.70); our timestamps were checked and are not the cause; not corrected, since the difference is not significant on 30 hours and the bias does not move with the shift. **Final run on two weeks, about 29 October.** The US Consulate cross-check needs an archivable source (WAQI is display-only).

### 4.4 City-level comparison across Pakistan (core)

- Every monitored city appears on the country view as one column: its city-level AQI, with a per-city time series and ranking.
- Punjab cities come from the EPA portal; Islamabad, Karachi, Peshawar and Quetta from OpenAQ where Phase 0 confirmed archivable coverage, otherwise shown from WAQI for display only and excluded from every analysis and published file.
- Country-level question classes: *"which city is worst today?"*, *"compare Lahore and Faisalabad this week"*, *"which city improved most this month?"*
- Each city card states its data source and station count, so a one-station city is never read as precisely as Lahore.
- Lahore remains the only city with intra-city 3D detail; clicking any other city shows its city-level record, not an invented neighbourhood map.

### 4.5 Where should the next station go? (added --- contribution C7)

- Build a grid of candidate sites over Lahore, using OpenStreetMap land use to exclude rivers, the airport and restricted areas. **Done 15 Oct** at 1 km spacing, matching the population raster rather than the 500 m first planned: candidates are the populated cells themselves, so no site is proposed where nobody lives. Ten cells are excluded (seven airport, two military, one water). **Caveat recorded:** only closed ways become exclusion polygons, multipolygon relations are not assembled, so the Ravi river is under-caught and a site proposed near it should be checked by eye.
- For each candidate, compute the population brought within 3 km and 5 km of a monitor that is not covered today, using WorldPop or census population layers (both free). **Done 15 Oct** with WorldPop 2025 at 1 km.
- **Second criterion: proximity to likely sources** --- major roads and industrial land use from OpenStreetMap --- combined with population in a weighted score. Report results for both the population-only and combined versions. **Done 15 Oct**, and the comparison is itself the finding: population-only brings **3.15 million** people within 5 km (underserved share 33% -> 11%); blending in source proximity at weight 0.3 brings 2.35 million (33% -> 16%) but puts every proposed monitor within 200 m of a major road. Weighting towards sources costs roughly 800,000 people of coverage. Which is right depends on whether the network is meant to measure *exposure* or *emissions*, so both are reported and neither is picked. *(Reduces W8.)*
- Describe it in the report as a **coverage-maximising heuristic** and state what it ignores: pollution gradients, official siting rules (Punjab follows US EPA siting criteria) and land access.
- Greedy selection: choose the best site, update coverage, repeat --- giving a ranked list of the next five stations and the coverage each adds. **Done 15 Oct on area coverage** (`recommend_stations`, shown in the app): the five together cut the mean distance from 4.93 km to 3.54 km and the share of the built-up area beyond 5 km from 44% to 18%, with the gain per station falling from 0.57 km to 0.13 km. That falling curve is the result worth reporting; the coordinates themselves are provisional, because the population, land-use and proximity-to-sources criteria below are not yet applied.
- Show the proposals on the map as hollow columns, distinct from real stations.
- Compare the ranking with the locations recommended in the 2022 ISPRS Lahore study [8] and discuss agreement and difference. **Done 15 Oct as a method comparison** (`docs/research/population.md`). **A numeric overlap is not possible from the published record:** the paper gives no coordinates, its nine sites appearing only as markers on a map, and digitising them would be accurate to no better than 1--2 km. Method, criteria and count are compared instead. The substantive finding is that their criteria (commercial hubs, industry, traffic, drainage) are source-led while ours are exposure-led, which makes their work the closer analogue of our *combined* variant than of the population-only one; and that the three-station network which motivated their nine recommendations has since grown to the eleven we collect from, moving the question from "how many" to "are they in the right places".
- Wording: "recommended for consideration", never presented as an official siting plan.

**Exit:** a ranked list of five sites, with population coverage before and after, shown on the map. **Met 15 Oct** --- both rankings, with population before and after, exclusions applied, shown in the app. The ISPRS comparison is done as a method comparison; a numeric overlap would need coordinates the paper does not publish, and asking its authors is the honest route to those.

### 4.6 Lowest-AQI window today (added)

- From the 24-hour forecast, find the contiguous two-hour window with the lowest predicted AQI. **Done 15 Oct** (`airlume/forecast/window.py`, shown in the "Next 24 hours" tab for both relayed sources).
- **City-level, not per-station.** The original wording ("for the nearest station") assumed a per-station forecast. Neither source has one: the portal publishes its 24-hour forecast for Lahore as a whole, and CAMS resolves to roughly one 45 km cell over the city. Naming a neighbourhood would imply a spatial precision that does not exist, so the answer names Lahore.
- Answer form: *"Lowest predicted AQI in Lahore over the next 24 hours: 16:00--18:00 on 15 Oct (around 119), from the EPA Punjab forecast."* Always with that source's own mean error beside it, or a plain statement that there is not yet enough scored history to know it.
- **Hours already past are excluded.** The portal's forecast still contains the hour it was issued in, so without this filter the "lowest window in the next 24 hours" can point at a time that has already gone --- which it did on the first live run. Pinned by test.
- A gap in the forecast series never becomes a window: only genuinely consecutive hours are considered, so a mean is never reported over times that were not adjacent.
- Never phrased as advice about going out, exercising or health --- only as a prediction. A test asserts the sentence contains no advice-like wording.

**Exit:** the "best time" question class answers from the forecast with its error shown. **Met 16 Oct, with the wording corrected.** In the benchmark the `best_time` class is *retrospective* ("cleanest time of day this week", "worst hour yesterday") and correctly answers from history; questions about the future are the `forecast` class. That is the class this exit really meant, and it was broken: a question routed to `view="forecast"` fell through to the station path and was answered with **current readings**. `nl/answer.py` now answers it from the stored forecasts --- each source's own latest issue, the mean, the peak and the lowest two-hour window, each source's measured error (or a plain statement that there is not yet enough history), city-level with the caveat stated when a station is named, and never phrased as advice. **Limitation surfaced:** the EPA forecast covers only 8 hours ahead because the HTML parser reads 8 points while the portal's snapshot carries 23 --- a concrete reason to do the deferred snapshot migration of the forecast reader when 4.1 is next worked on.

**Exit criterion for Phase 4:** forecast and baseline scored; validation statistics computed; station recommendations and lowest-AQI windows produced.

## Phase 5 --- Evaluation (Week 9: 8--14 Dec)

| ID | Evaluation | Metric | Target |
|:----|:--------------------------|:---------------------------------------------------|:------------------|
| E1 | Language layer | Exact match; per-field accuracy; accuracy by class; refusal precision/recall; across 4--5 models; **three runs per question with consistency reported; bootstrap 95% confidence intervals** | 85% per-field on best model |
| E2 | Forecast | MAE vs persistence; correct AQI band rate; by station and hour | Beat baseline (reported either way) |
| E3 | CAMS vs ground | MAE, bias, correlation per station | None --- a measurement |
| E4 | Users | 8--10 people, 3 tasks each: success rate, time, and "how precise do you think this map is?" | Tests C3 directly |
| E5 | Parallel speed-up (CC425) | Speed-up vs workers; scaling limit analysed | None --- a measurement |
| E6 | Performance | Frames per second, time to first answer | 30 fps, under 4 s |
| E7 | Local vs cloud model (added) | E1 rerun on the offline Ollama model; accuracy as a share of the best cloud model, and seconds per answer | None --- a measurement |
| E8 | Conversation (added) | Clarification precision and recall; per-turn accuracy on follow-up dialogues | 80% clarification recall |
| E9 | Station placement (added) | Population coverage gained by the top five proposed sites; overlap with the ISPRS recommendations | None --- a measurement |

**Rigour rules:** the test set is never used for tuning; automated E1 scoring is checked by hand on 30 items and the agreement reported; class balance is stated; plain accuracy is never reported alone.

**Exit criterion for Phase 5:** all nine evaluations complete, with figures generated by script.

## Phase 6 --- Deployment (Week 9: 8--14 Dec, in parallel)

### 6.1 Hosting

- Streamlit Community Cloud from the public repository. Collector stays on GitHub Actions, independent of the app.

### 6.2 Installable app (PWA)

- Web manifest and service worker: home-screen icon, full-screen launch, cached last data for offline viewing.

### 6.3 Accuracy page

- Generated automatically from forecast logs each day.

### 6.4 Attribution and disclaimers

- Footer on every page: Punjab EPA; CAMS ENSEMBLE and Open-Meteo (CC BY 4.0); OpenStreetMap and CARTO; WAQI and the originating EPA where WAQI data is displayed.
- "Student project --- not an official government source" on every page.

### 6.5 Monitoring

- Freshness label in the header; a GitHub Actions failure email; a weekly check that the collector is still enabled.

### 6.6 Shareable answer cards (optional)

- A "Share" button renders the current answer as a portrait image: the question, the answer sentence, a small map or chart, the data time, the source credit and the site address.
- Sized for WhatsApp; generated in the browser so no server is needed.
- Every card carries the attribution line and "student project --- not an official source", so a forwarded image can never be mistaken for a government notice.

**Exit:** cards generate for every view type and read clearly on a phone.

### 6.7 Security hardening (required before the URL goes public)

Airlume is a public, read-only site with one user input: the question box. That keeps the attack surface small, and the design keeps it that way. The full checklist is in Part E; the items below are the ones that need building.

- **Secrets:** every key lives in `.env` locally and in the host's secrets store when deployed; never in code, never in `data/`, never in a commit. A startup check refuses to run if a key is missing from the environment or found in a file.
- **Input handling:** the question is treated as untrusted text. It is passed to the model as data inside a fixed system prompt; the model's only output is the typed form; the form is validated by Pydantic; SQL is built by code with parameters only. No user text is ever interpolated into a query, a shell command or HTML.
- **Output handling:** the answer sentence and every station name are rendered as text, never as HTML. `unsafe_allow_html` is banned in the codebase (enforced by a test that greps for it).
- **Rate limiting:** per-visitor limit on the question box (for example 20 questions per 10 minutes) and a global daily cap sized to the free model quota, with cached answers served without a model call. This protects the free-tier budget, which is the asset an attacker would actually burn.
- **No accounts, no admin routes:** the public site has no login and no write path. Collection runs separately on GitHub Actions. If an operator page is ever added, it is protected by authentication and is not reachable from the public app.
- **Security headers and settings:** debug mode off; no stack traces to visitors; Content-Security-Policy, X-Content-Type-Options, X-Frame-Options and Referrer-Policy set wherever the host allows (a FastAPI layer adds them if Streamlit alone cannot).
- **Dependencies:** versions pinned; `pip-audit` run before each release; unused packages removed.
- **Data store:** DuckDB file opened read-only by the web app; collectors are the only writers, and they run outside the app.
- **Exposed-file check:** before going public, list every file served or committed and confirm none is a secret, a key, a database with private data, or a config file.
- **Logs:** never log the raw key, the full environment, or visitor IP addresses beyond what rate limiting needs (hashed, short retention).

**Exit:** the security checklist in Part E passes with zero open items; `gitleaks` and `pip-audit` report clean.

**Exit criterion for Phase 6:** public URL works on a phone; 72 hours of unattended operation; security hardening complete. (Share cards, if built.)

## Phase 7 --- Report and Demo (Week 10: 15--21 Dec)

### 7.1 Report

Introduction and problem; related work with VayuBuddy as the direct predecessor; system design; data and licensing; evaluation results; limitations; **known weaknesses and how each was handled**; ethics; conclusion and future work.

Two framing rules for the whole report:

- **The contribution is scoring the visual answer** --- view, area, time window and camera --- which VayuBuddy's authors named as an unsolved need. Never describe it as "using structured output". *(Fixes W3.)*
- **Target users are named honestly:** students, journalists and analysts. Public impact is not claimed, because it was not measured. *(Handles W11.)*

### 7.2 Releases

- Benchmark (60 questions and gold forms), evaluation code, derived statistics (C4, coverage, forecast error), and the source code. **Raw EPA readings are released only if permission was granted.**

### 7.3 Replay the worst day (optional)

- Find the day with the highest city-average AQI in the archive.
- Animate it hour by hour at about 10 seconds per hour of data, with captions drawn from the data: when the rise began, which station peaked first, the wind direction at the time.
- Captions describe what happened, never why --- consistent with the no-causation rule.
- Used as the opening of the presentation and available to any visitor from a "Replay" button.

### 7.4 Demo rehearsal

See Part F.

**Exit criterion:** report submitted; repository public; demo rehearsed twice.

\newpage

# Part E --- Timeline, Risks, Limitations and Ethics

## Timeline

The project was planned over ten weeks (13 October 2026 to 21 December 2026). On 28 October the submission date was brought in to **28 November 2026** --- four weeks from today --- because most of the ten-week plan is already built: Phase 0 is complete, Phases 1 and 2 are largely complete, Phase 3 is at prompt v3 and benchmark v0 with follow-ups in the app, and Phase 4 has the forecast scorecard, persistence baselines, population coverage, placement candidates and a preliminary CAMS validation. The remaining work is a final CAMS run, benchmark v1 (classmate questions and a second annotator), the forecast model, the public deploy with a security re-check, and the report and demo. Nothing in the ten-week plan has been cut; the earlier phases are already met.

### The ten weeks as originally planned (13 Oct -- 21 Dec)

| Week | Dates | Phase | Milestone | Status |
|:--|:--|:--|:--|:--|
| 1 | 13--19 Oct | 0 Foundations | Shell runs, keys work, emails sent | **Done** |
| 2 | 20--26 Oct | 1 Data pipeline; AQI formula identified | Live collection running; versions pinned | **Done** |
| 3 | 27 Oct -- 2 Nov | 1 Backfill, AQI harmonisation + 2 Twin begins | Soak passed; EPD extracted; **W1 fixed** | **Done** (W1 solved 16 Oct, confirmed at scale 24 Oct) |
| 4 | 3--9 Nov | 2 Digital twin, 2D companion views; recruit classmates | All views live; **W10 fixed** | **Done** (2D companion, time animation and wind layer all delivered 15 Oct) |
| 5--10 | 10 Nov -- 21 Dec | 3 Schema + benchmark; language; 4 Forecast + validation; 5 Evaluation; 6 Deployment; 7 Report | — | **Compressed into the four-week sprint below** |

### Four-week sprint to submission (28 Oct -- 28 Nov)

| Week | Dates | Focus | Deliverable |
|:--|:--|:--|:--|
| **1** | 28 Oct -- 3 Nov | Data recovery and foundation | Hybrid collector live from the laptop (28 Oct, done); R&D confirmed (28 Oct, done); CAMS validation final run (29 Oct, done); W1 bootstrap CI (29 Oct, done); Materials draft v1 (29 Oct, done); GitHub fine-grained token and Groq key rotated; EPA permission email sent; classmate question sheets handed to three classmates |
| **2** | 4 Nov -- 10 Nov | Models and benchmark build | ERA5 + EPD daily feature table; Model A baselines (persistence + LightGBM) for Phase 4.2; second-annotator pass on benchmark v0; classmate questions collected; Model A neural variant on daily features; Materials-and-Methods draft (07) placeholders filled |
| **3** | 11 Nov -- 17 Nov | Freeze and insights | Benchmark v1 frozen; one scored run with 95% CIs; results written up; W1 top-band refit as above-350 rows accumulate; security pass 2 (S1--S15); Streamlit Cloud deploy from the public repo; priority score, graded response, scenario calculator |
| **4** | 18 Nov -- 24 Nov | Report and demo | Final report (plan.md is the engineering spine, proposal.md the research framing, HISTORY.md the decision log); weaknesses section with W1--W15 verdicts and R&D results; demo slides; screenshot capture; demo rehearsal |
| **Submit** | 25 Nov -- 28 Nov | Polish and submit | Final pass; submission; viva prep |

**Critical weeks:** week 1 (final CAMS run and foundation), week 3 (freezing the benchmark protects the honesty of every reported number), and week 4 (the report either reads as one argument or it does not).

**R&D extension confirmed (28 Oct 2026).** The neural variant, Materials-and-Methods draft, priority score, graded response and scenario calculator are firm deliverables in weeks 2--3, not conditional on further approval.

**Scope cuts, in this order if behind:** (1) non-Punjab cities (keep the 36 Punjab EPA districts), (2) shareable answer cards, (3) replay-the-worst-day mode, (4) split-screen view, (5) voice input, (6) local-model comparison (keep only if a hour is free), (7) satellite layer, (8) Roman-Urdu test set expansion beyond what is already in v0. **Never cut:** the 3D map, time animation, the language layer, the evaluation, the show-the-query toggle, clarifying questions, station placement, **or any of the fully-solvable weakness fixes W1--W6, W10, W13.** The follow-ups and lowest-AQI window are already shipped and stay.

**Honest capacity note.** The sprint is tight. Four weeks allows the final CAMS run, Benchmark v1 with CIs, one trained forecast model with a neural variant, the R&D insight modules (priority score, graded response, scenario calculator), the public deploy and the report. It does not allow a second training round if the first forecast model underperforms --- a negative result is reported honestly rather than iterated. The laptop-dependent collector means EPA data gaps during weekends away or extended laptop-off hours; those gaps are shown in the app rather than filled silently. **Validity fixes come before every feature:** a polished demo with an unsound number fails a viva; a plain demo with sound numbers passes it.

## Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|:----|:----------------------------|:-----------|:---------|:---------------------------------------------|
| R1 | EPA has no usable endpoint | Medium | High | Find it in DevTools in week 1; fall back to polite page scraping; EPD PDF history independent of it |
| R2 | EPA never replies or refuses | High | Medium | Built to work without permission; release derived statistics only; respect any refusal and switch ground truth to EPD PDFs or OpenAQ |
| R3 | WAQI data leaks into analysis | Low | High | Separate module that writes nothing to disk |
| R4 | Collector stops silently | Medium | Medium | Heartbeat commits, minute-17 schedule, freshness label, failure emails |
| R5 | Free LLM limits too tight | Medium | Low | Router across 5 models, caching, short prompts, unlimited local model |
| R6 | Free model ids retired mid-project | Medium | Medium | Log exact ids; open-weight `gpt-oss` models can be re-run locally |
| R7 | CARTO basemap changes again | Medium | Low | Protomaps fallback ready; no-basemap mode works |
| R8 | Stations offline during smog season | High | Medium | Uptime shown in app; gaps reported, never filled silently |
| R9 | Language accuracy below target | Low | Medium | Reported as a finding with error analysis |
| R10 | Forecast fails to beat baseline | Medium | Low | Reported as a negative result |
| R11 | Examiner's phone app shows a different number | High | Medium | Different stations, averaging windows and AQI formulas explain it; C4 quantifies it in advance |
| R12 | Scope creep | **High** | High | Cut order fixed above; Could-priority features dropped at the first slip |
| R13 | Station recommendations read as official advice | Low | Medium | Labelled "recommended for consideration"; method and limits stated beside the map |
| R14 | Shared cards circulate as if official | Medium | Medium | Attribution and "not an official source" baked into every image |
| R16 | Ten-month gap (Dec 2025 -- Oct 2026) in official history before our own collection starts | Medium | Medium | State the gap on every timeline; optionally fill city level from CAMS, clearly labelled modelled; never fill station level |
| R15 | Leaked API key or abused question box burns the free quota or exposes the site | Medium | High | Secret scanning from day one; keys only in environment; rate limits and daily cap; read-only app with no write path; security checklist (Part E) must pass before going public |

## Known weaknesses and mitigations

A self-review identified fifteen weaknesses. They fall into three kinds: **solvable** (the fix removes the problem), **reducible** (the fix makes it much smaller) and **handled** (outside the project's control, managed openly). Each is resolved at a specific point in the build.

### Solvable --- fixed completely

| ID | Weakness | Fix | Phase | Resolved by | Exit check |
|:----|:-------------------------|:-------------------------------------|:------|:----------|:---------------------------|
| W1 | Station AQI compared with CAMS concentration --- different units and formulas | **Solved 16 Oct.** The portal uses its own NEQS-anchored table with gases in µg/m³, recovered from 304 stored rows: 99.7% exact, 100% within one point (US 2012 table: 6% exact). Default scale in `aqi.py`. **Confirmed at scale 24 Oct** (2206 station-hours / 210 h: MAE 1.7, median 0.0) | 0.2, 1.7 | Week 1 (planned week 3) | **Met**; top PM2.5 band to be confirmed on November data; one 99-point outlier still to trace |
| W2 | Benchmark written by the same person who built the system | Classmates write half the questions blind; second annotator on 20 items; report kappa | 3.2 | Week 5 | Kappa reported; benchmark frozen |
| W3 | Contribution mistaken for "just structured output" | Frame as scoring the visual answer; cite VayuBuddy's stated gap | 7.1 | Week 10 | Framing used in report and viva slides |
| W4 | 60 questions is a small sample | Bootstrap 95% confidence intervals; no claims inside the noise | 5 (E1) | Week 9 | Every accuracy figure carries an interval |
| W5 | No single "correct" camera | Score camera by level and direction categories | 3.2 | Week 5 | Camera rubric in the frozen benchmark |
| W6 | LLM answers vary between runs | Temperature 0; three runs per question; consistency reported | 3.3, 5 | Week 9 | Consistency figure in E1 |
| W10 | 3D columns distort height comparisons | 2D ranked bar beside every 3D view; top-down toggle | 2.5 | Week 4 | Every view has its 2D companion |
| W13 | Free tiers and libraries change without notice | Pin all versions; demo from laptop on cached data | 0.1, 7.4 | Week 1 | `requirements.txt` pinned; offline demo rehearsed |

### Reducible --- made much smaller

| ID | Weakness | Reduction | Phase | Resolved by | What remains |
|:----|:-------------------------|:-------------------------------------|:------|:----------|:---------------------------|
| W7 | Forecast may not beat the baseline | CAMS forecast as an input feature (bias correction) | 4.2 | Week 8 | It may still only match the baseline --- reported either way |
| W8 | Station placement ignores pollution sources | Add roads and industrial land as a second criterion | 4.5 | Week 8 | Still a heuristic, not a siting study |
| W12 | English-only questions | 20-question Roman-Urdu test set | 3.2 | Week 5 | Urdu script not supported |
| W11 | A website may not reach the public | Name real target users; share cards bridge to WhatsApp if built | 7.1 | Week 10 | Public demand not measured |
| W14 | One person, ten weeks | Fixed cut order; optional features last | All | Ongoing | Schedule risk never reaches zero |

### Handled --- outside the project's control

| ID | Weakness | Why it cannot be fixed | How it is handled | When |
|:----|:-------------------------|:------------------------------|:-----------------------------------|:----------|
| W9 | Station readings may be inaccurate | Only the EPA can calibrate its instruments | C4 framed as agreement; uptime reported; US Consulate cross-check | Week 8 |
| W15 | No licence for EPA data | Only the EPA can grant permission | Permission email; build without reply; publish derived statistics only | Week 1, then ongoing |

### Resolution schedule

| Week | Weaknesses resolved |
|:------|:------------------------------------------------------------|
| 1 | W13 (versions pinned), W15 (permission requested) |
| 3 | W1 (AQI harmonised) |
| 4 | W10 (2D companion views) |
| 5 | W2 (blind benchmark, second annotator), W5 (camera categories), W12 (Roman-Urdu set) |
| 8 | W7 (CAMS-input forecast), W8 (source criterion), W9 (agreement framing) |
| 9 | W4 (confidence intervals), W6 (three-run consistency) |
| 10 | W3 (contribution framing), W11 (target users) |
| Ongoing | W14 (scope discipline) |

## Limitations

1. **Spatial coverage:** about a dozen stations for eleven million people; between them Airlume reports the nearest reading and its distance, never an invented value.
2. **History:** station-level history is limited to the EPD published reports and Airlume's own logging period.
3. **Model resolution:** CAMS over Pakistan is about 45 km --- a regional estimate, measured in C4 rather than assumed accurate.
4. **No causation:** wind and rain are shown as correlates; source attribution needs chemical analysis.
5. **No medical advice:** only the official AQI band and its standard wording.
6. **One city in depth:** only Lahore has enough stations for intra-city detail; every other city is a single value. Places with no stations are not shown as having a value at all.
7. **Free-tier dependence:** model availability and limits can change without notice.

## Security checklist

A standing requirement for this project: it must not be an easy target. The list below is run in full before the site goes public (Phase 6.7) and again before submission. Items marked *N/A by design* are not skipped: they are true because of a design choice, and the choice is stated.

| # | Item | How Airlume meets it | When |
|:---|:-----------------------------|:-------------------------------------------------------------|:---------|
| S1 | API keys hidden | `.env` locally, host secrets store when deployed; never committed; `.gitignore` covers `.env` | Phase 0 |
| S2 | Environment variables checked | Startup check: required keys present, no key in any tracked file | Phase 0 |
| S3 | Git history free of secrets | `gitleaks` pre-commit hook plus a one-time full-history scan. **History checked 12 Oct 2026: 15 files, all documents, no secrets.** | Phase 0, then every commit |
| S4 | Admin routes protected | *N/A by design:* the public app has no admin route. Any future operator page requires authentication | Phase 6 |
| S5 | Authentication and authorisation | *N/A by design:* no user accounts; the site is read-only for everyone. If accounts are ever added: passwords hashed with Argon2id, sessions server-side | Phase 6 |
| S6 | Forms sanitised, XSS prevented | One input (the question). Treated as data; never rendered as HTML; `unsafe_allow_html` banned by a test | Phase 3 |
| S7 | Injection prevented | Model fills a typed form only; code builds SQL with parameters; no shell calls with user text | Phase 3 |
| S8 | Rate limiting | Per-visitor and global daily caps on the question box; cache serves repeats. **Done 15 Oct:** 30 calls/session/hour, 150/hour global, 400-character input cap | Phase 6 |
| S9 | API endpoints secured | Only the question endpoint is public; it accepts a bounded string, returns JSON, has the rate limit above | Phase 6 |
| S10 | Core settings and security headers | Debug off; no stack traces; CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy | Phase 6 |
| S11 | Unneeded things removed | Unused packages, routes and files deleted; `pip-audit` clean | Phase 6 |
| S12 | Exposed files checked | Review of every served and committed file before going public | Phase 6 |
| S13 | Database secured | DuckDB opened read-only by the app; writers run outside it; no network database unless needed, then least-privilege role over TLS | Phase 1, 6 |
| S14 | Passwords hashed properly | *N/A by design* (no passwords). Argon2id if ever added | --- |
| S15 | Full security audit | Whole checklist re-run, plus `gitleaks`, `pip-audit` and `bandit`, before going public and before submission. **First pass 15 Oct:** `docs/security/audit-2026-10-15.md` | Phase 6, 7 |

## Ethics and licensing

- **Attribution** on every page for every source, in the form each licence requires.
- **Non-impersonation:** clearly labelled as a student project, not an official source.
- **Permission:** sought in writing in week 1 and documented; any refusal is respected.
- **WAQI** used for live display only, as its terms allow; never archived or analysed.
- **No personal data** is collected, stored, or sent to any language model.
- **Polite collection:** hourly at most, descriptive User-Agent, timeouts and backoff.
- **Free-tier model data use** disclosed in the report.

## Mapping to course outcomes

**DS494 Data Visualization:** 3D spatial encoding, temporal animation, an externally standardised colour scale, comparative views, and the explicit communication of data sparsity --- tested empirically in E4.

**CC425 Parallel and Distributed Computing:** parallel extraction of about 2,000 historical PDFs benchmarked across sequential, multiprocessing and asynchronous designs (E5); decoupled distributed deployment of collector and application.

# Part F --- Demo Day

## Demo script (about seven minutes)

1. **Open with "Replay the worst day"** if it was built --- thirty seconds of the worst day in the data, captions only. Otherwise open with the city already rotating. Say nothing.
2. Ask **"Where is smog worst right now?"** --- live, about today. Let the camera fly.
3. Ask **"Is today worse than yesterday?"** --- the split screen.
4. Ask **"How is Gulberg?"** --- Airlume asks back: *the Gulberg III station or the whole area?* Tap one. *This is clarification.*
5. Follow up with **"and yesterday?"** --- it remembers Gulberg. Switch on **Show the query** and point at the fields. *This is C1, visible.*
6. Ask **"What's the AQI in Ali Town?"** --- no station there; Airlume names the nearest one and its distance. *This is C3 working.*
7. Ask **"What's the AQI on my street?"** --- a graceful refusal. *Proving the system knows its limits earns more credit than any success.*
8. Show the coverage map and the five recommended new stations. *This is C7.*
9. Show the accuracy page --- yesterday's forecast against reality.
10. One slide of results: E1 accuracy by class, E7 local-versus-cloud, E3 CAMS error.
11. Close on the known-weaknesses slide: what you found, and when and how you fixed each one. *(If cards were built, share one to your phone as the last click.)*

## Before walking in

- Open the app once to wake it (it sleeps after 12 hours).
- Check the freshness label shows today's date.
- Present from **localhost on cached data**; keep the public URL open in a second tab as proof it is live.
- Have a screen recording on the laptop in case the network fails.

## Deliverables

1. Public website and installable phone app.
2. Complete source code in a public repository.
3. Frozen benchmark: 60 questions, 10 ambiguous items and 10 follow-up dialogues, with gold annotations.
4. Evaluation code reproducing every figure.
5. Derived statistics: CAMS-vs-ground validation, coverage analysis, forecast scorecard.
6. Station-placement recommendation: ranked sites with coverage gained (C7).
7. Local-versus-cloud model comparison (E7).
8. Parallel-extraction benchmark (CC425).
9. Written report and presentation.

\newpage

# Appendix A --- Benchmark Samples

| ID | Question | Class | Expected behaviour |
|:----|:------------------------------------------|:-------------|:---------------------------------------|
| 1 | Where is smog worst right now? | Ranking | All stations ranked; city camera |
| 2 | What is the AQI in Gulberg? | Lookup | Gulberg III station; zoomed camera |
| 3 | Is today worse than yesterday? | Comparison | Split view, two days |
| 4 | Show me the last thirty days | Trend | Animated 30-day series |
| 5 | How many days this month were above 150? | Conditional | Count + calendar strip |
| 6 | When during the day is pollution worst? | Aggregate | Mean by hour of day |
| 7 | Which station improved most this week? | Comparison | Change across two windows, ranked |
| 8 | Compare Shahdara and DHA today | Comparison | Two stations side by side |
| 9 | What is the AQI on my street? | Out of scope | Refusal: stations kilometres apart |
| 10 | What was the AQI in 2015? | Out of scope / history | Answer from EPD archive if present, else refusal |
| 11 | Is it safe for my child to play outside? | Out of scope | Official band wording only |
| 12 | Who is causing the smog? | Out of scope | Refusal: needs source apportionment |
| 13 | How is Gulberg? | Ambiguous | Clarify: Gulberg III station or the Gulberg area? |
| 14 | How bad was it? | Ambiguous | Clarify: today, this week or this month? |
| 15 | (after Q2) ...and yesterday? | Follow-up | Same station, yesterday; camera kept |
| 16 | (after Q1) What about DHA? | Follow-up | Same view and time, DHA Phase 6 |
| 17 | When is the air cleanest today? | Best time | Lowest predicted two-hour window, with error |
| 18 | Where should a new monitor go? | Placement | Show the five recommended sites |

# Appendix B --- Week-1 Command Checklist

Create the project environment:

```bash
python -m venv venv && source venv/bin/activate
```

Install the core libraries:

```bash
pip install duckdb pandas pyarrow pydantic requests streamlit pydeck \
  geopandas shapely pdfplumber scikit-learn lightgbm statsmodels pytest
```

Check OpenAQ's Pakistan coverage:

```bash
curl -H "X-API-Key: $OPENAQ_KEY" \
  "https://api.openaq.org/v3/locations?iso=PK&limit=1000" > openaq_pk.json
```

Test Open-Meteo for Lahore:

```bash
curl "https://air-quality-api.open-meteo.com/v1/air-quality?\
latitude=31.52&longitude=74.36&hourly=pm2_5,us_aqi&past_days=7"
```

Enumerate the EPD archive index:

```bash
for p in $(seq 0 104); do
  curl -s "https://epd.punjab.gov.pk/Air_quality?page=$p" > epd_index_$p.html
  sleep 2
done
```

Install the local model for development:

```bash
ollama pull qwen3:8b
```

Re-enable the collector if GitHub ever disables it:

```bash
gh workflow enable collect.yml
```

# Appendix C --- Sources

[1] Omar, A. and Rosales, C. (2024). *Open Air Quality Community Data in Pakistan.* EGU General Assembly, EGU24-453. <https://doi.org/10.5194/egusphere-egu24-453>

[2] Punjab Environmental Protection Agency. *Lahore AQI real-time platform.* <https://aqi.punjab.gov.pk/lahore> ; Punjab EPD air-quality archive, <https://epd.punjab.gov.pk/air_quality>

[3] *Punjab introduces EcoBot for real-time air quality monitoring.* Digital Pakistan, October 2025. <https://digitalpakistan.pk/punjab-introduces-ecobot-for-real-time-air-quality-monitoring/>

[4] *VayuBuddy: an LLM-Powered Chatbot to Democratize Air Quality Insights* (2024). <https://arxiv.org/html/2411.12760v1> ; review: <https://pith.science/paper/2411.12760>

[5] *VayuChat: An LLM-Powered Conversational Interface for Air Quality Data Analytics* (2025). <https://awesomepapers.io/ai-agents/papers/2511.01046>

[6] *Towards Democratising Urban Sustainability Data: An LLM-Enabled Natural Language Interface for Smart-City Air-Quality Decision Support.* Sustainability 18(11), 5506. <https://www.mdpi.com/2071-1050/18/11/5506>

[7] Open-Meteo. *Air Quality API documentation.* <https://open-meteo.com/en/docs/air-quality-api> ; licence: <https://open-meteo.com/en/licence> ; terms: <https://open-meteo.com/en/terms>

[8] *Data Driven Framework for Analysis of Air Quality Landscape for the City of Lahore.* ISPRS Archives XLVIII-4/W5-2022. <https://isprs-archives.copernicus.org/articles/XLVIII-4-W5-2022/167/2022/>

[9] World Air Quality Index Project. *API terms of service.* <https://aqicn.org/api/tos> ; Punjab network feed: <https://aqicn.org/network/aqipunjab/>

[10] OpenAQ. *Terms of use and rate limits.* <https://docs.openaq.org/about/terms> ; <https://docs.openaq.org/using-the-api/rate-limits>

[11] CARTO. *Basemaps FAQ and terms.* <https://docs.carto.com/faqs/carto-basemaps> ; <https://carto.com/legal/basemap-terms/>

[12] Protomaps documentation. <https://docs.protomaps.com/>

[13] GitHub. *Actions billing and scheduled workflows.* <https://docs.github.com/en/billing/concepts/product-billing/github-actions> ; <https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows>

[14] Streamlit. *Community Cloud app management.* <https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app>

[15] Hugging Face. *Spaces overview.* <https://huggingface.co/docs/hub/spaces-overview>

[16] Groq. *Rate limits and structured outputs.* <https://console.groq.com/docs/rate-limits> ; <https://console.groq.com/docs/structured-outputs>

[17] Google. *Gemini API pricing, rate limits and terms.* <https://ai.google.dev/gemini-api/docs/pricing> ; <https://ai.google.dev/gemini-api/terms>

[18] Copernicus. *CC BY licence for CDS/ADS (from 2 July 2025).* <https://forum.ecmwf.int/t/cc-by-licence-to-replace-licence-to-use-copernicus-products-on-02-july-2025/13464> ; Data Space quotas: <https://documentation.dataspace.copernicus.eu/Quotas.html>

[19] United States EPA. *Technical Assistance Document for the Reporting of Daily Air Quality --- the AQI.*

# Appendix D --- Punjab EPA portal findings (13 October 2026)

Full notes: `docs/research/epa-portal.md` and `docs/research/registry-notes.md`.

- **Site:** Laravel + Vite, server-rendered. Public routes: `/`, `/lahore`, `/health-advisory`, `/support`. `/lahore/analysis` needs a login. No public JSON on the main host; `api.aqi.punjab.gov.pk` exists but is undocumented (it serves the Android app `com.moonshotsmc.aqipunjab`).
- **Data path:** `GET /lahore` returns an HTML table (Rank, Station, AQI, Level, PM2.5, PM10, CO, SO2, NO2, O3) with a "Last updated" line in Pakistan time. Plain URLs can be served stale from a cache; a throwaway query parameter fetches fresh data. Hourly cadence; single stations can lag or drop out (Gulberg III was absent in one snapshot).
- **AQI scale:** labels Good 0--50, Satisfactory 51--100, Moderate 101--150, Unhealthy for sensitive groups 151--200, Unhealthy 201--300, Very unhealthy 301--400, Hazardous 401--500. Numbers come from the portal's own NEQS-anchored breakpoint table with max-of-sub-indices and gases in µg/m³ (solved 16 Oct; the 13 Oct reading of 'US EPA 2012' was wrong --- see 1.7). The EPD order of 1 October 2025 says official bulletins use 8-hour averages at 9 am, 5 pm and 1 am.
- **Districts on the home page:** 36 (Okara, Nankana Sahib, Muzaffargarh, Rajanpur, Chiniot, Jhang, Vehari, Khanewal, Sahiwal, Faisalabad, Gujranwala, Pakpattan, Multan, Lahore, Sheikhupura, Attock, DG Khan, Kot Addu, Bahawalpur, Rahim Yar Khan, Kasur, Rawalpindi, Bhakkar, Sargodha, Narowal, Hafizabad, Murree, Khushab, Gujrat, Jhelum, Sialkot, Wazirabad, Mandi Bahauddin, Chakwal, Mianwali, Talagang). The plan's earlier figure of 28 was out of date.
- **Coordinates:** **published by the portal after all** --- inside the page's embedded Livewire snapshot, found 15 Oct 2026. (This plan previously recorded them as unpublished.) The registry now carries the EPA's own latitude and longitude for all eleven Lahore stations, `confidence: official`. The earlier IQAir-derived values were right to within 130 m for nine of eleven; Multan Road was 6.13 km out and Kahna Nau 0.58 km, both neighbourhood-centroid guesses, and both are corrected. The permission email still goes --- a published attribute is not a licence --- but it no longer needs to ask for coordinates. See `docs/research/portal-snapshot.md`.
- **Other cities:** Islamabad, Karachi and Peshawar have The Urban Unit's AirGradient sensors on OpenAQ (licensed, storable). Quetta's sensors are on WAQI/IQAir only, so Quetta is display-only. The US Embassy and Consulate monitors have been dormant since March 2025.
- **Standards:** NEQS ambient limits (2012 values): PM2.5 15 annual / 35 24-hour; PM10 120 / 150; NO₂ 40 / 80; O₃ 130 one-hour; SO₂ 80 / 120 µg/m³; CO 5 (8 h) / 10 (1 h) mg/m³. **The portal's AQI puts 100 exactly at the short-term limit** for every pollutant we can fit.
- **Afternoon ozone (13 Oct, 14:00):** the live portal's AQI is a maximum over six pollutants; at Egerton Road, Punjab University and Wagha the ozone sub-index dominated. The converter now includes O3, NO2, SO2 and CO with unit conversion.
- **Averaging window tested (15 Oct, 90 stored station-rows, `scripts/w1_check.py`):** the 8-hour window hypothesis above is **wrong**. The latest-hour values reproduce the portal to a mean 5.4 AQI points; an 8-hour trailing mean gives 24.3 and is worse at all ten stations. The 24-hour window cannot be tested until a full day of consecutive hours is stored. The 2012 PM2.5 table beats the 2024 one (5.4 against 10.4), confirming the 13 Oct identification. PM2.5 dominates 93% of station-hours. A **systematic +4 point bias remains** (we read higher than the portal in 83% of rows); a ±1 hour publication lag, integer truncation and dropping the gases are each ruled out. Note that the EPD order's 8-hour averaging applies to the printed 9 am / 5 pm / 1 am bulletins, not to the live portal table. Full working: `docs/research/w1-harmonisation.md`. **Superseded 16 Oct:** the +4 bias was the wrong breakpoint table, not an averaging effect; the portal's own NEQS-anchored table reproduces every stored row to within one point (see 1.7).
- **EPD bulletin archive:** daily reports from 2 January 2018 to **2 December 2025** (about 2,300 PDFs; nothing for 2026). Bulletins compute AQI from the **24-hour PM2.5 mean**, uncapped above 500. Layouts 2022--2025 are parsed; the 2018--2020 layout covers the old station network and is skipped. Lahore had 13 monitors in late 2025 under different names (UET = GT Road, PU 1 = Punjab University; Town Hall, PKLI, LWMC, FMDRC, PU 2, EPA HQ have no portal counterpart). There is **no permitted official per-station data for 3 December 2025 -- 12 October 2026**; whether to fill that gap at city level from CAMS (labelled "modelled") or leave it empty is an open decision (risk R16).

# W1: which formula does the Punjab EPA portal use for its AQI?

**Status: solved, 16 Oct 2026.** The portal computes AQI from the **latest hour's**
concentrations, as the **maximum of per-pollutant sub-indices**, on **its own breakpoint table
anchored on Pakistan's NEQS limits**, with gases banded in **µg/m³** rather than ppb. Implemented
as the `pk_portal` scale in `airlume/aqi.py`, now the default.

Checked against every stored station-hour (304, over 30 hours, 24 of them consecutive, 14–16 Oct):

| Scale | Exact | Within 1 | Mean abs error | Bias | Max | Dominant pollutant agrees |
|---|---|---|---|---|---|---|
| **`pk_portal` (fitted)** | **99.7%** | **100%** | **0.00** | **+0.00** | **1** | **100%** |
| US EPA 2012 (used until today) | 6.2% | 18.8% | 7.48 | +5.87 | 50 | 94% |
| US EPA 2024 | 2.0% | 7.9% | 11.12 | +9.62 | 50 | 94% |

The single non-exact row is off by one, which is rounding. Every one of the portal readings
published on 13 Oct and pinned in our tests is reproduced exactly.

## Confirmed at scale (24 October 2026)

Re-running `scripts\w1_check.py` against the full archive --- **2206 station-hours over 210
consecutive hours**, up from the 304 rows and 30 hours the table was fitted on --- the latest-hour
`pk_portal` AQI still reproduces the portal's published value almost exactly:

| Averaging window | Mean abs error | Median | Max | n |
|---|---|---|---|---|
| **1 hour (latest reading)** | **1.7** | **0.0** | 99 | 2206 |
| 8-hour trailing mean | 45.1 | — | — | 2206 |
| 24-hour trailing mean | 54.7 | — | — | 2206 |

The latest-hour window still wins by a wide margin. The dominant-pollutant mix has broadened to
**PM2.5 71%, PM10 24%, O₃ 4%, NO₂ 1%** (against 93% PM2.5 on the first 30 hours) as the archive came
to span more of the day and more weather, so the 16 Oct fit is not an artefact of a short,
PM2.5-dominated sample.

**The 99-point outlier is top-band saturation (closed 28 Oct 2026).** Re-run against the archive on
GitHub, the five largest errors are all **22--23 October smog peaks where the portal saturates at
AQI 500** --- PM2.5 above 350 ug/m3 and PM10 above 540 --- while the extrapolated top band computes
401--404. Four of the five are PM-dominated; one row at `LHR-GT 2026-10-16 15:00` is marked
CO-dominant by the portal and our CO band is a NEQS-anchored placeholder, so the 96-point error
there is from the placeholder rather than the data. This exercises the caveat recorded on 16 Oct
("PM2.5 above 350 and PM10 above 550 are extrapolated"): November smog has already arrived, so the
top band now needs **refitting**, not extrapolating. The open work is a top-band refit once more
above-350 rows accumulate, and a proper CO band if CO ever dominates again.

**One open item: no confidence interval on the at-scale error yet.** A moving-block bootstrap over
hours (as used for the CAMS validation) is the next step.

## The table

Concentrations in the units the portal shows: µg/m³, CO in mg/m³.

| AQI | PM2.5 | PM10 | O₃ | NO₂ |
|---|---|---|---|---|
| 0–50 | 0–15 | 0–75 | 0–65 | 0–40 |
| 51–100 | 15.1–**35** | 75.1–**150** | 65.1–**130** | 40.1–**80** |
| 101–150 | 35.1–70 | 150.1–250 | 130.1–195 | 80.1–130 ‡ |
| 151–200 | 70.1–150 | 250.1–350 | — | — |
| 201–300 | 150.1–250 | 350.1–450 | — | — |
| 301–400 | 250.1–350 | 450.1–550 | — | — |
| 401–500 | 350.1–500 † | 550.1–650 † | — | — |

**Bold = the NEQS short-term limit.** For every pollutant the data can fit, an AQI of exactly 100
on the portal *is* the national legal limit: PM2.5 35 (24 h), PM10 150 (24 h), O₃ 130 (1 h), NO₂ 80
(24 h). The lower edges are the NEQS annual limits for PM2.5 (15) and NO₂ (40), and half the
short-term limit for PM10 and O₃. The scale was built so that "Satisfactory" ends where the law
does — which is a better story for the report than "it is the US scale".

† **Not yet observed** — extrapolated from the pattern, and identical to the US table at that
level. Lahore's November smog routinely passes 350 µg/m³ PM2.5, so the top band gets its first
real test within weeks. Re-run `scripts\w1_check.py` then.
‡ One point (87.2 → 108). Plausible, not confirmed.

Above the last fitted gas band the sub-index is **refused, not extrapolated**, so a guess can never
set a reported AQI. SO₂ and CO have never been the dominant pollutant in our data; their bands are
NEQS-anchored placeholders (SO₂ 80 / 120 µg/m³, CO 5 / 10 mg/m³) that cannot have affected any
value so far.

## How it was found

1. **Dominance test.** The snapshot carries the portal's own `major_pollutant`. Against ours on 204
   rows it agreed 94% — and on the rows where both said PM2.5, our PM2.5 sub-index exceeded the
   portal's AQI on essentially *every* row (mean +8.3, mean absolute 8.3). The bias was inside the
   PM2.5 calculation, not in which pollutant won.
2. **Inverting it.** The concentration the portal's AQI implies, divided by the concentration it
   displays, varied by band (0.80, 0.98, 0.91, 0.84, 1.00). Not a scale factor, not an offset —
   the signature of different breakpoints.
3. **NowCast ruled out.** The US 12-hour weighted average cut the bias (+8.3 → +3.5) but made the
   error worse (8.4 → 9.7).
4. **Fitting each band.** Regressing concentration on AQI inside each band gave r² = 1.00 for
   every PM2.5 and PM10 band and recovered the edges directly: 15 / 35 / 70 / 150 / 250, and
   75 / 150 / 250 / 350 / 450 / 550. Gases fell out the same way.

## Why the first identification looked right and was not

On 13 Oct the US 2012 table was chosen because four hand-checked readings matched "within 0–3
points". They did — and under the true table they match exactly too. All four were smog-morning
values (141, 190, 227, 311 µg/m³) sitting where the two tables converge: both agree at 150–350.

**The tables part most at 35–70 µg/m³**, where the US table ends its 101–150 band at 55.4 and the
portal ends it at 70. That is Lahore's ordinary October afternoon. A reading of 60 µg/m³ is
"Moderate" on the portal and "Unhealthy for sensitive groups" on the US table. Four readings chosen
because they were easy to check all came from the one region that could not tell the tables
apart; ninety stored rows exposed the bias, three hundred settled it.

## What this resolves

- **The +4/+8 bias** recorded on 15 Oct — it was the wrong table, nothing else.
- **The rejected ozone hypothesis.** The two rows that suggested an 8-hour maximum were the portal
  banding O₃ in µg/m³ on a 65/130 scale while we converted to ppb for the US table. Gulberg III,
  82.39 µg/m³ → 64 (portal 64); Wagha, 91.97 → 71 (portal 71). There never was an averaging effect.
- **The averaging window**, now on 24 consecutive hours: latest hour, unambiguously. Mean error
  0.0 against 20.2 for an 8-hour mean and 26.8 for a 24-hour one, at all eleven stations.
- **Plan 1.7's first bullet** — "implementing exactly the breakpoint table Punjab EPA uses" — is
  now literally met.
- **4.3 (CAMS vs ground) can now be done honestly**: CAMS concentrations can be put on the portal's
  own scale, so the comparison measures model agreement rather than a table mismatch.

## Data-of-record note

`aqi_computed` in `data/archive/readings/` was written with the US 2012 table until 16 Oct 2026 and
with `pk_portal` from then on. It is a derived column, fully recomputable from the stored
concentrations, and earlier rows are **not** rewritten — the archive is append-only. Anything that
needs a consistent series recomputes from concentrations rather than reading that column.

## Reproducing

```
python scripts\w1_check.py
```

---

# Earlier record (14–16 Oct), kept for the history of the finding


## What the data allows

| | |
|---|---|
| Rows | 90 Punjab EPA station-readings with a published AQI |
| Stations | 10 of 11 (Gulberg III has not appeared in a collected round yet) |
| Distinct hours | 10, of which 4 consecutive (05:00–08:00 UTC, 15 Oct) |
| Window testable | 1-hour: yes. 8-hour: one hour per station only. 24-hour: **not at all** |

The 24-hour window produced no rows: its rolling mean needs 12 hours of history and the archive's
longest consecutive run is 4 hours. The 8-hour figures below rest on a single station-hour each
and should not be quoted in the report.

## Result 1 — the portal is not publishing a trailing 8-hour mean

Mean absolute error against the portal's published AQI, US EPA 2012 table, max of sub-indices:

| Averaging window | Mean abs error | Median | Max | n |
|---|---|---|---|---|
| **1 hour (latest reading)** | **5.4** | 4.0 | 24 | 90 |
| 8-hour trailing mean | 24.3 | 20.5 | 69 | 10 |
| 24-hour trailing mean | — | — | — | 0 |

The 8-hour window is worse at every one of the ten stations, by 2 to 33 AQI points. This
contradicts the 13 October note in `docs/HISTORY.md`, which guessed an 8-hour window from
afternoon ozone behaviour. The guess was wrong: adding the gas sub-indices was what fixed those
afternoon rows, not averaging.

## Result 2 — the 2012 PM2.5 table is the right one

Instantaneous values, all six pollutants, both tables:

| Table | Mean abs error | Median | Exact match | Within 5 | Bias (ours − portal) |
|---|---|---|---|---|---|
| **US EPA 2012** | **5.4** | 4.0 | 9% | 64% | +4.0 |
| US EPA 2024 | 10.4 | 11.0 | 2% | 30% | — |

This confirms the Phase 0 finding. PM2.5 dominates 93% of station-hours, PM10 4%, NO~2~ and O~3~
1% each, so the choice of PM2.5 table is what the agreement turns on.

## Result 3 — a +4 point bias remains unexplained

The 1-hour 2012 configuration is the best of those tested, but it is **not** the portal's exact
formula. It matches exactly in only 9% of rows and reads **higher** than the portal in 83% of
them, mean +4.0 AQI points (sd 6.5). A systematic bias is not rounding noise.

Four candidate explanations were tested and none accounts for it:

| Hypothesis | Mean abs error | Exact | Bias |
|---|---|---|---|
| Baseline (round PM2.5 to 0.1) | 5.4 | 9% | +4.0 |
| Floor PM2.5 to 0.1 | 5.4 | 9% | +4.0 |
| Truncate PM2.5 to integer | 5.1 | 13% | +3.5 |
| PM2.5 and PM10 only (drop gases) | 5.4 | 9% | +4.1 |
| Portal AQI lagged one hour behind concentrations | 10.4 | — | +1.4 |
| Portal AQI one hour ahead | 11.8 | — | +2.4 |

Truncating to an integer helps slightly and is what the EPA document specifies, but it closes
about an eighth of the gap. A ±1 hour lag between the concentrations shown and the AQI published
is ruled out: lag 0 is clearly best.

### A concrete lead, 15 Oct 16:00 PKT: ozone may use a maximum 8-hour average

The snapshot parser (`docs/research/portal-snapshot.md`) gave us the portal's own
`major_pollutant` per station, which is a free per-row check on the sub-index logic. On the first
live round, 9 of 11 stations agree with us. The two that disagree both point the same way:

| Station | Portal | Ours | O3 the portal's number implies | O3 displayed |
|---|---|---|---|---|
| Gulberg III | 64, **O3** | 68, PM2.5 | ~59 ppb (116 µg/m³) | 82.4 µg/m³ (42 ppb) |
| Wagha Border | 71, **O3** | 57, PM10 | ~61 ppb (120 µg/m³) | 92.0 µg/m³ (47 ppb) |

In both the portal's ozone sub-index implies roughly **1.3–1.4× the ozone concentration the same
page displays**. The obvious candidate is that the portal computes ozone on a **maximum 8-hour
average** — which is exactly what the US EPA specifies for O3, and is not what it does for PM —
while the table shows the latest hour. Feeding µg/m³ straight into the ppb table is ruled out: that
would give 140 and 164, far above the portal's 64 and 71.

This partially rehabilitates the 13 October instinct. That note guessed an 8-hour window for
*everything* and was wrong — Result 1 above rules that out decisively for the overall index. But
ozone alone on an 8-hour maximum is both standard practice and consistent with every afternoon row
that first prompted the guess.

#### First test against stored data: not supported

Checked the same hour against all 100 stored station-rows before writing this up further. The lead
does **not** survive its first contact with the archive:

- The portal exceeds *every* sub-index we can compute in only **3 of 100 rows**. If its ozone were
  systematically inflated relative to what it displays, this should be common in the afternoon, not
  rare.
- On those 3 rows the implied O3 multiplier is 1.49, 2.85 and 3.51 — scattered, not the consistent
  ~1.4× the two dry-run rows suggested.
- The dominant pattern is the opposite one: **we read higher than the portal in 81 of 100 rows**.

The one thing that does survive is a time-of-day shape. Mean (portal − ours) by Pakistan hour is
negative everywhere — between −1 and −7 — except at 13:00 and 14:00 PKT, where it turns slightly
positive (+1.0, +0.6). Ozone peaks in exactly those hours, so *something* ozone-shaped is moving
the portal's number relative to ours. That is a weak signal on ten stations across one day, and it
is not evidence for the 8-hour-maximum mechanism specifically.

**What the clean test needs is `portal_dominant`, which we do not store.** The archive drops it,
because `archive.COLS["readings"]` does not declare it, so the test above had to use the much
weaker proxy "portal exceeds our maximum sub-index". With the portal's own dominant pollutant on
every row, each row becomes a direct check. This turns the pending schema decision in
`portal-snapshot.md` from a convenience into the thing blocking W1.

Note also that this does **not** explain the +4 PM-dominated bias — Shahdara on the live round read
124 to the portal's 115 with both of us agreeing PM2.5 dominates — so there remain at least two
separate things here.

Still untested, in the order worth trying: a sub-hourly averaging window (the portal may publish
a 15- or 30-minute mean while showing one instantaneous concentration); a PM2.5 breakpoint table
of Punjab's own that happens to sit near the 2012 one; the portal rounding each sub-index down
rather than to nearest. Each needs more consecutive hours than exist now.

## What this means for the plan

- The 1-hour window is what the comparison code should use, and 1.7's "exactly the breakpoint
  table Punjab EPA uses" is not yet achievable — we have the right family of tables, not the
  formula. Comparisons must therefore carry the residual as a stated uncertainty, not be
  presented as harmonised.
- **The claim "within 0–3 points" in the plan's Phase 0 section is too strong** and has been
  corrected. It came from four readings chosen because both concentration and AQI were visible;
  over 90 stored rows the spread is mean 5.4, max 24.
- The honest statement for the report, until more data arrives: *the portal's AQI is reproduced
  from the latest hour's concentrations using the US EPA 2012 breakpoints with max-of-sub-indices
  to within a mean 5.4 points (median 4), with a systematic +4 point bias whose source is not yet
  identified.* The 1.7 exit criterion should be the bias explained or bounded, not "tests pass".

## Reproducing

```
python scripts\w1_check.py
```

Reads `data/archive/readings/` (the CSV data of record, so it includes rows the cloud collector
committed), not the local DuckDB cache.

## Incidental findings, 15 Oct

- **`aqi.py` crashed on NaN.** `sub_index` guarded `None` but not NaN, and NaN fails every
  comparison silently, so a gap in a rolling mean reached `int()` and raised. This is why the
  check had never been run. Fixed; regression test in `tests/test_aqi.py`.
- **City rows are upserted, not appended.** Lahore's city AQI for 15 Oct 06:00 UTC was 73 in one
  commit and 77 in a later one. `data/archive/city_hourly/` therefore is not append-only, unlike
  `readings/`. *(First explanation here — that a later round recomputed the city mean from more
  stations — was wrong: nothing in the pipeline computes a city value from our station rows, and
  `n_stations` is always empty. The measured causes are in `docs/research/data-quality.md`.)*
- **Hourly collection is live.** 05:00–08:00 UTC on 15 Oct are consecutive with 10 rows each.
  Earlier rows are 2–6 hours apart, from before the cron-job.org trigger was installed.

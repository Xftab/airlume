# W1: which averaging window and breakpoint table reproduces the portal's AQI?

**Status: interim. 90 station-rows over 10 distinct hours (14–15 Oct 2026).** Enough to rule two
things out, not enough to settle the question. Re-run `python scripts\w1_check.py` once 24
consecutive hours exist; this file is replaced then.

W1 is the weakness that station AQI and CAMS concentrations cannot be compared until we know the
formula the portal publishes. Phase 0 identified the breakpoint table from four hand-checked
readings. This is the first test against stored data.

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

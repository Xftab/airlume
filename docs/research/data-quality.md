# Data quality in our own collection (plan 1.6)

**First report, 15 Oct 2026.** 90 station-rows over 10 collected hours (14–15 Oct). Produced by
`python scripts\quality_report.py`, shown in the app's **Data quality** tab, implemented in
`airlume/pipeline/quality.py`. Nothing here is corrected automatically: the archive is the data of
record, so a suspect value is flagged and left in place.

## What the checks are, and why

| Check | Fires when | Why that threshold |
|---|---|---|
| `gap` | a station misses 2+ consecutive **collected** hours | collection is hourly; one missed hour is a blip |
| `stuck` | 3 identical readings of one pollutant in consecutive hours | real PM2.5 moves hourly; this is AirNow's QA rule. Zero is excluded and reported as `impossible` |
| `impossible` | negative, above a physical ceiling, or PM2.5 > PM10 | PM10 includes the PM2.5 fraction by definition |
| `spike` | a one-hour move over 50 µg/m³ **and** over 5× that station's own usual hourly step | a fixed number would fit Gulberg or Shahdara but not both |
| `partial_round` | a round catches under 60% of the usual station count | a fault in the round, not in the stations |

"Collected hours" means hours in which *some* station reported, never a wall-clock range. Before
the hourly trigger was installed on 15 Oct the collector fired every 2–6 hours; counting those as
missed would make every station look broken.

## The methodological mistake worth recording

The first version of these checks differenced **adjacent rows** instead of adjacent **hours**, and
reported ten spikes and one stuck sensor on the real archive. Every one was an artefact: the
flagged timestamps landed exactly on the boundaries of the pre-trigger collection gaps, so a
five-hour change was being read as a one-hour jump. After restricting both checks to pairs exactly
one hour apart, all eleven disappeared and the two genuine findings below remained.

This is worth a line in the report. A quality check that fires on its own sampling irregularity
would have put eleven false "sensor faults" into the dissertation, and the numbers looked
plausible enough to survive a casual read. The regression is pinned in
`tests/test_quality.py::test_large_jump_across_a_collection_gap_is_not_a_spike`.

## Findings

**1. Gulberg III has never reported.** `LHR-GB3` is in the registry as one of Lahore's eleven
stations, and in 10 collected hours it has produced zero rows — not an intermittent dropout. The
13 Oct portal note recorded it as "absent in one snapshot"; it is absent in all of them. Every
"10 of 11 stations" figure in the app is this station, consistently. Either the portal has stopped
publishing it or it has a different name on the page that the parser does not match. **To check on
the laptop:** open `aqi.punjab.gov.pk/lahore` and look for Gulberg in the table. If it is there
under another spelling, the parser needs an alias; if it is not, the registry should mark it
inactive so "10 of 11" stops reading as a failure.

**2. One round in ten was partial.** 15 Oct 05:00 UTC collected 1 station of the usual 10; 06:00
collected 9. The portal serves an incomplete table briefly while it updates, and the collector
takes whatever is there. Not harmful — the next round fills in — but it is why the ten reporting
stations show 90% uptime rather than 100%, and why a city value computed from a partial round
would be wrong if we ever computed one.

**3. No stuck sensors, impossible values or spikes** in the 90 stored rows once the checks were
corrected. On this much data that is a weak statement, not a clean bill of health.

## City-hour revisions: two portal widgets under one source name

Measured across the eleven commits that touch `data/archive/city_hourly/punjab_epa/2026-10.csv`:
**4 of 10 revisions change an already-committed value**, 1–7 rows each time. Two distinct causes.

**(a) Sub-hour re-reads of the district ranking.** `parse_home_html` stamps its rows with the
page's "last updated" time rounded to the hour, so two collections inside one clock hour write the
same archive key. The portal's own numbers drift ±1–2 points between them and the later write
wins. Benign, but it means a committed city-hour is not final.

**(b) The trend widget and the ranking disagree.** On 15 Oct 06:00 UTC the archive held 73, then
77. These come from two *different* portal widgets — the "AQI Trends (last 7 days)" series and the
home-page district ranking — both archived under the source name `punjab_epa`. The archive key is
`(city_id, ts, source)`, so it cannot hold both, and one silently replaces the other.

They are not the same measurement. The trend is the portal's retrospective value for that hour;
the ranking is a live snapshot. Conflating them loses a disagreement we should be able to see and
report, and whichever survives depends on collection order rather than on anything about the air.

**Recommendation superseded the same day — see `docs/research/portal-snapshot.md`.** The first
recommendation here was to give the trend widget its own source name (`punjab_epa_trend`). Then
the portal's embedded snapshot turned up, and it offers a better answer to both causes:

- **(b) dissolves.** The snapshot exposes the trend as `historicalData.organized_data` and the live
  figures as separate named fields. Read from there and there is nothing left to conflate — no
  source-name split needed, and no discontinuity in the archive.
- **(a) becomes measurable.** The snapshot carries `latestHourlyTimestamp`, the instant the portal
  last refreshed (15:10:15 while the page displayed "3:00 PM"). Recording it alongside the hour is
  what tells us whether two reads of one clock hour saw the same refresh — the thing the empty
  `n_stations` column was reaching for.

Still **Aftab's call**, and now a larger one: it means moving the trend and forecast readers onto
the snapshot, which touches the forecast scorecard (4.1).

Note that `check_source_collisions` can only see a collision in a frame *about to be written*:
once the archive has deduplicated, only the survivor is stored. To measure how often the two
widgets disagree, the check has to run inside `collect_hourly.py`.

## Still to do in 1.6

- Decide (a) above: either stamp the ranking row with the fetch time to the minute, or skip a
  write when the key already exists, or accept the drift and say so.
- Decide (b) above: split the source name, or keep one and record which widget wrote the row.
- Run `check_source_collisions` inside the collector so disagreements are counted, not lost.
- Re-run this report once a week of data exists; the current `n` is too small for the absence of
  spikes to mean anything.

## Reproducing

```
python scripts\quality_report.py
python scripts\quality_report.py --hours 48
```

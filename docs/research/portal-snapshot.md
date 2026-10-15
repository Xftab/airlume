# The portal's embedded data (found 15 October 2026)

`GET /lahore` carries the page's Livewire component state as HTML-escaped JSON in a
`wire:snapshot` attribute, about 150 KB. It is the portal's own data *before* rendering, and it
contains more than the HTML table we had been parsing. Read by
`airlume/collectors/epa.py::parse_lahore_snapshot`.

This is the "JSON backend" the 13 October investigation suspected existed. It is not the
undocumented `api.aqi.punjab.gov.pk` host — it is in the page we already fetch, on the same one
request per hour, so it needs no new permission position and no extra traffic.

## The portal renders fewer stations than it holds

The snapshot contains **two** Lahore station arrays:

| Path in the snapshot | Stations | Gulberg III |
|---|---|---|
| `pageData[0].lahoreData[0].stations` | **11** | present |
| `pageData[0].stations` | 10 | **absent** |

The rendered HTML table is built from the 10. So Gulberg III has live values in the portal's own
data — AQI 62, PM2.5 16.64, PM10 56.39 at 14:00 PKT on 15 Oct — and never appears in the table.
Our collector read the table, which is why `LHR-GB3` had zero rows across every collected hour.
The portal's own heading says "Lahore (11 stations)", so the page contradicts itself.

The reader therefore does not hard-code the path. It walks the snapshot for any array of records
carrying `station_name` and takes the largest, which both survives a portal redesign and is what
makes the 11-station array win.

Livewire serialises every container as `[payload, {"s": "arr"}]`, so values are unwrapped on the
way out; timestamps arrive as `["2026-10-15T14:00:00+05:00", {"s": "cbn", "type": "illuminate"}]`.

## Fields, per station

```
station_id  station_name  district  aqi  pm25  pm10  no2  so2  o3  co
major_pollutant  pollutant_flags  temperature  humidity  wind_speed  wind_direction
timestamp  latitude  longitude  aqi_range
```

Four of these change what the project can do:

- **`latitude` / `longitude`** — the plan records station coordinates as *not published*, geocoded
  from IQAir pages with a confidence label shown on the map. They are published, here. See below.
- **`temperature`, `humidity`, `wind_speed`, `wind_direction`** — per station, hourly. Phase 2.4's
  wind layer was scoped to need Open-Meteo; this is ground truth at the monitors themselves, from
  a request we already make.
- **`major_pollutant`** — the portal's own view of which pollutant drives the index. This is a
  direct, free check on the sub-index logic behind W1: where ours disagrees with theirs, one of us
  is wrong. Gulberg III at 15:00 PKT is an example to look at — the portal labels it `O3` while
  its published AQI of 62 is close to the PM2.5 sub-index.
- **`timestamp`** — a real ISO timestamp with offset per station, instead of parsing one page-level
  "Last updated" line and applying it to every row.

## Coordinates: nine confirmed, one materially wrong

Comparing the portal's official coordinates against the registry we built from IQAir station pages:

| Station | Was | Offset | Note |
|---|---|---|---|
| **Multan Road** | neighbourhood centroid | **6.13 km** | genuinely in the wrong place on our map |
| Kahna Nau | neighbourhood centroid | 0.58 km | improved |
| Gulberg III | IQAir | 0.13 km | |
| Wagha Border, Egerton Road | IQAir | 0.02 km | |
| Shahdara, Barki Road, Safari Park, DHA Phase 6, GT Road | IQAir | 0.00 km | exact |
| Punjab University | IQAir, "medium confidence, 4 km SW of main campus" | 0.00 km | **doubt resolved** — the station really is 4 km SW |

The IQAir-derived work was sound: nine of eleven were right to within 130 m. The two
neighbourhood-centroid guesses were the weak points, and the worse of them was 6 km out.

`data/registry/stations.csv` now carries the portal's values with `confidence: official`, the
portal's own numeric `portal_station_id`, and a note on each corrected row. The app's "station
positions approximate" captions have been replaced. The coverage analysis (C3/C7) was recomputed:
mean distance to the nearest monitor 5.0 → 4.93 km, share beyond 5 km 45% → 44%, within 3 km
22% → 23%, p90 8.29 km; **the recommended new-station location is unchanged** at ~31.56 N,
74.20 E.

This also answers part of the EPA permission email, which asks the EPA to confirm the station
list and coordinates. The email should still go — a published attribute is not a licence, and the
request for the official list stands — but the coordinate question is no longer open.

## What changed in the collector

- `parse_lahore_snapshot(html)` reads the snapshot; `parse_lahore(html)` prefers it and falls back
  to `parse_lahore_html` when no snapshot is present. The table parser is kept because it is what
  a redesign is most likely to leave working, and its fixtures pin behaviour we already trust.
- **Unmatched station labels are now recorded** in `epa.UNMATCHED_STATIONS` and printed by the
  collector. Previously `parse_lahore_html` dropped an unrecognised station name with `continue`
  and no log of any kind — a station could leave the dataset in silence. That is not what hid
  Gulberg III, but nothing would have told us if it had been.
- `_station_key` strips punctuation as well as the city name, so the portal's two spellings
  ("Gulberg III" in the table, "Gulberg III, Lahore" in the JSON) both match.

Tests: `tests/test_epa_snapshot.py`, against a fixture reproducing the two-array shape.

## The snapshot holds everything we scrape, and two timestamps we did not have

Checked the rest of `pageData` on 15 Oct, 15:10 PKT. Every HTML widget we currently parse
separately is in there as a named, structured field:

| Field | What it is | We currently get this by |
|---|---|---|
| `lahoreData[0].stations` | 11 stations, full detail | parsing the HTML table (10 stations) |
| `stations` | the 10 the table is rendered from | — |
| `historicalData.organized_data` | the 7-day hourly trend, 7 x 24, plus `last_24_hours`, `stats`, `date_range`, `total_records` | regex over `<span data-aqi data-date data-hour>` |
| `aqiForecastData` | 23 hourly forecast points, each with an ISO `datetime` and health index | parsing the "24-Hour AQI Forecast" article list |
| `hourly24ForecastData` | the same, plus forecast `temperature`, `wind_speed`, `wind_direction`, `weather_condition` | not collected at all |
| `currentAqi`, `currentCategory`, `worstStationName` | the city headline figures | derived by us |

And two timestamps that matter more than they look:

- **`lastUpdated` = `2026-10-15T15:00:00+05:00`** — the hour the data *represents*, as a proper ISO
  string with offset. We currently recover this by regex over "Last updated: 3:00 PM, Oct 15".
- **`latestHourlyTimestamp` = `2026-10-15 15:10:15`** — the instant the portal last *refreshed*.
  The page displays "3:00 PM" while the data was actually refreshed at 15:10:15.

The home page (`/`) carries a snapshot too, but a 384-byte one: `latestHourlyTimestamp`,
`pageUrl`, `pollIntervalSeconds` (120) and nothing else. The 36-district ranking is **not** in it,
so that table still has to be parsed from HTML.

### This changes the city-hour recommendation in `data-quality.md`

That note recommended giving the 7-day trend widget its own source name so the two widgets stop
overwriting each other. With the snapshot in hand there is a better answer to the same problem:

- **Cause (b) dissolves.** `historicalData` and the live station/city figures are separate named
  fields in one structured object, so there is nothing left to conflate. The trend is the portal's
  retrospective series; take it from `historicalData` and label it as such.
- **Cause (a) becomes measurable.** Two collections inside one clock hour currently write the same
  key with slightly different values and no way to tell whether the portal had refreshed in
  between. `latestHourlyTimestamp` answers exactly that. Recording it alongside the hour makes a
  revision explicable instead of silent — which is what the empty `n_stations` column was reaching
  for and never delivered.

So the decision to take is no longer "split the source name" but "move the trend and forecast
readers onto the snapshot and store the refresh instant". Bigger, and it touches the forecast
scorecard (4.1), so it is not something to do in passing.

## Decided 15 Oct: the extra columns join the archive

Aftab's call, taken once the W1 ozone test showed the missing `portal_dominant` was the thing
blocking a clean answer. `archive.COLS["readings"]` and the DuckDB `readings` table now carry
`portal_station_id`, `portal_dominant`, `lat`, `lon`, `temperature`, `humidity`, `wind_speed`,
`wind_direction`.

How the change avoids disturbing data of record:

- **Appended, never inserted.** Every CSV written before today keeps its eleven columns in their
  existing order; the new ones are added on the end, and older rows read back blank in them. Pinned
  by `test_snapshot_columns_append_without_disturbing_existing_files`.
- **The DuckDB cache is migrated, not rebuilt.** `CREATE TABLE IF NOT EXISTS` leaves an existing
  table alone, so a database created before today would have failed the insert while a fresh one
  passed — exactly the asymmetry that broke the laptop once before, on 14 Oct, when gas columns
  were added. `Store.__init__` now runs `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for each, in the
  same way as the 13 Oct migration. Pinned by `test_old_database_is_migrated_for_snapshot_columns`.
- **The HTML-table fallback still works.** It produces none of these columns; they default to null.
  Pinned by `test_rows_without_snapshot_columns_still_insert`.

Nothing needs rebuilding by hand: existing archives and caches migrate in place on next use.

## Open
- Gulberg III will start appearing from the next collection round. Its history before 15 Oct 2026
  cannot be recovered; the gap should be stated wherever station history is shown.
- Worth re-checking whether the district/home page carries an equivalent snapshot with all 36
  districts and their coordinates.

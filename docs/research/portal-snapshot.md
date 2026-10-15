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

## Open

- The extra columns (`lat`, `lon`, weather, `portal_dominant`) are carried on the frame but not yet
  stored: `archive.COLS["readings"]` does not declare them, so they are dropped at write time.
  Adding them is a schema change to data of record — **Aftab's call**, same as the city-hour source
  question in `data-quality.md`.
- Gulberg III will start appearing from the next collection round. Its history before 15 Oct 2026
  cannot be recovered; the gap should be stated wherever station history is shown.
- Worth re-checking whether the district/home page carries an equivalent snapshot with all 36
  districts and their coordinates.

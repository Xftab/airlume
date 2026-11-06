# Archive rows deleted by git merges, and the city-level trend in the snapshot

**Date:** 6 November 2026. **Author:** Claude, working on the laptop's files and a full-history clone of `Xftab/airlume` (737 commits, 12 Oct to 6 Nov). **Status:** cause found and fixed in code; the lost rows are restored by a script Aftab runs (one command, below).

## 1. What was found

The CSV archive is meant to be append-only, but **7,215 rows that had been committed were missing from the current files.** Every one is still in git history.

| File | Rows lost | Span (UTC) |
|---|---:|---|
| `forecasts/open_meteo_cams_forecast/2026-10.csv` | 3,456 | 24 Oct 03:00 to 31 Oct 08:00 |
| `forecasts/open_meteo_cams_forecast/2026-11.csv` | 2,064 | 1 Nov 00:00 to 6 Nov 08:00 |
| `city_hourly/punjab_epa/2026-10.csv` | 922 | 24 Oct 02:00 to 25 Oct 11:00 |
| `readings/punjab_epa/2026-10.csv` | **350** | **24 Oct 02:00 to 25 Oct 11:00** |
| `forecasts/punjab_epa_forecast/2026-10.csv` | 256 | 24 Oct 02:00 to 25 Oct 11:00 |
| `city_hourly/open_meteo_cams/2026-10.csv` | 69 | 24 Oct 03:00 to 26 Oct 23:00 |
| `city_hourly/punjab_epa/2026-11.csv` | 61 | 3 Nov 10:00 to 17:00 |
| `readings/punjab_epa/2026-11.csv` | 21 | 3 Nov 10:00 to 17:00 |
| `forecasts/punjab_epa_forecast/2026-11.csv` | 16 | 3 Nov 10:00 to 17:00 |

Checked after normalising every timestamp, so this is not a formatting mismatch: for example `readings/.../2026-10.csv` has held 2,767 distinct station-hours in its history and holds 2,417 now, with nothing in the current file that history lacks.

**The 110-hour station gap of 24 to 28 Oct is really 76 hours.** The GitHub Actions collector did fetch station readings from 24 Oct 02:00 to 25 Oct 11:00 UTC (for example LHR-GT 24 Oct 05:00 was committed at 05:55 UTC in `3a79ce7`). The laptop's first `collect_push` run on 28 Oct 21:15 PKT (`77ad9ad`) deleted them. What is truly missing is 25 Oct 12:00 to 28 Oct 15:00 UTC.

## 2. Why it happened

Both collectors run `scripts/collect_hourly.py`, which fetches **every** source, so both write the **same month files**. `archive.export` reads a file, adds its rows, sorts and rewrites it.

1. The laptop sleeps overnight. The cloud keeps appending CAMS rows on GitHub.
2. On waking, the laptop collects, appends its own CAMS row to its **stale** copy of the file and commits.
3. `collect_push.bat` then runs `git pull --rebase -X theirs`. Both sides appended at the same place, so git sees a conflicting hunk. In a rebase, `theirs` is the commit being replayed, the laptop's. The cloud's rows in that hunk are dropped.
4. The cloud's own `git pull --rebase -X ours` does the same in the other direction.

Each morning's first laptop run deleted the cloud's overnight CAMS forecasts, which is why the CAMS forecast files lost most. For example, commit `1315db3`, 6 Nov 14:31 PKT, deleted 384 rows: 16 hourly issues of 24 horizons.

Reproduced in a scratch repository: the same appends with `-X theirs` lose the other side's rows, and with the fix below keep them, under `-X theirs` and `-X ours` alike.

## 3. The fix

1. **`.gitattributes`: `data/archive/**/*.csv merge=union`.** Git's built-in union driver keeps the lines of both sides instead of choosing one, for appended CSV rows. It is honoured during a rebase and overrides `-X theirs` and `-X ours`, so it also protects the cloud workflow, which Claude's tools cannot edit. The file is committed, so the cloud runner picks it up on its next checkout.
2. **`archive.load_all` drops duplicate keys** (keep the later line). A union merge can leave the same hour twice, for example a CAMS hour revised on one machine and appended on the other. `archive.export` already de-duplicated on every write.
3. **`scripts/recover_archive_rows.py`** walks every commit that touched `data/archive/`, takes the union of every row ever committed (latest commit wins per key), and reports or restores the rows the working tree lacks. Restoring goes through `archive.export`, so the file format is unchanged and rows already present are never altered. Run in the workspace: 7,215 restored, then 0 on a second run.
4. Tests: `tests/test_archive_merge_safety.py` (the union rule is present; `load_all` de-duplicates).

**Order matters on the laptop.** The union rule must be on GitHub before the restored rows are pushed. Otherwise the push's own rebase can still drop the newest cloud hour (harmless: running the script again restores it). So: save the code first, then restore, then save again.

## 4. Coverage after the restore (archive to 6 Nov 12:00 UTC)

| Measure | Before restore | After restore |
|---|---:|---:|
| Station rows | 2,923 | 3,294 |
| Hours with any station data, of 561 spanned | 279 | 313 |
| Station-hours present, of 6,171 possible | 47.4% | 53.4% |
| Longest gap | 110 h (24 to 28 Oct) | 76 h (25 Oct 12:00 to 28 Oct 15:00) |
| CAMS forecast issues | 310 | 540 |

**Since 30 Oct the station series has a gap every night.** The laptop collected on 4 to 13 hours a day (30 Oct to 6 Nov), with gaps of 8 to 16 hours while it slept. When it does run, station uptime is 92 to 100% (quality report, 313 collected hours). `schedule.bat` now adds `-WakeToRun`, which helps only if wake timers are allowed and the laptop is asleep (not shut down). The reliable fix is to leave it on mains power with sleep set to Never, as shown in `schedule.bat`.

**The 17 Oct 03:00 UTC hour is present in every table**, so the "one archive hour missing" gap is closed. `scripts/merge_stash_rows.py` (0 bytes since 28 Oct) is no longer needed.

## 5. The city-level Lahore series is complete, and can carry PM2.5

The Lahore city AQI series (`city_hourly`, PB-LHE, Punjab EPA) has **690 of 690 hours** from 8 Oct 19:00 to 6 Nov 12:00 UTC, with no gap, because every round re-reads the portal's 7-day trend. The station gaps do not touch it.

The page's Livewire snapshot holds more than the trend widget draws. `historicalData.organized_data` ("Lahore District") carries, for every hour of the last 7 days, the AQI, **city-level PM2.5, PM10, NO2, SO2, CO, O3**, temperature, humidity, wind speed and direction, and `station_count`. On the saved page of 14 Oct 04:36 UTC its AQI matched the rendered spans in 154 of 154 hours. Until now the city series was stored with PM2.5 and PM10 blank.

`epa.parse_lahore_trend` now reads the snapshot first and falls back to the spans. PM2.5, PM10 and `n_stations` go into existing columns, with no schema change. It is the same page already fetched under the permission, so there is no extra request. From the first round with the new code, the city series gets hourly PM2.5 back-filled 7 days. That covers from about 30 Oct, and every night the laptop sleeps through. Before that date it cannot be recovered, because the pages were not kept. Test: `tests/test_epa_page_extras.py` with a trimmed fixture from the 14 Oct page.

**Caveat for the report.** The snapshot's station list for the city figure uses source names (`Mobile 1`, `Mobile 3`, `Mobile 4`, `FMDRC-LHR`, `PKLI-LHR`, `UET-LHR` and so on). It is the portal's own district aggregate and includes mobile units. It is not the mean of our eleven fixed stations, and must be labelled as the portal's district figure wherever it is used.

## 6. Commands (Aftab)

```
REFERENCE ONLY: what the steps below do
1. save the code and the union rule, so GitHub has it before any restored rows
2. restore the 7,215 rows from history into data\archive
3. save again
```

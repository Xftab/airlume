# Second-annotator guide (benchmark v1)

Purpose: a second person writes the "correct form" for 20 questions independently, so we can report how often two humans agree (Cohen's kappa per field). Where they disagree, the two annotators discuss and record the agreed form and the reason. **Do not look at the first annotator's forms before you finish.**

## The form
For each question fill these fields (leave a field blank when nothing in the question decides it; the default then applies).

| Field | Allowed values | Default |
|---|---|---|
| in_scope | yes / no | yes |
| clarify | the short question you would ask back, if the question cannot be answered as written | blank |
| metric | aqi, pm25, pm10 | aqi |
| city | the city named | Lahore |
| area | the station or neighbourhood named inside the city, exactly as the user wrote it | blank |
| time | now, today, yesterday, last_7_days, last_30_days, this_month, last_month, same_day_last_year, custom_date (+ date), custom_range (+ start, end) | now |
| aggregation | latest, mean, max, min, count_hours_above (+ threshold) | latest |
| compare_to | none, yesterday, last_week, last_year, other_city (+ other_city) | none |
| view | stations_3d, city_overview, compare, timeline, forecast | stations_3d |
| camera | overview, station, north, zoomed_out | overview |

## Conventions (agreed before annotation)
1. **"Right now", "at the moment", "abhi", "this morning"** → time `now`, aggregation `latest`, even for "where is it worst" (the app ranks the latest values).
2. **Past window** ("yesterday", "last week") → `mean` for "how bad was it", `max` for "worst/peak", `min` for "cleanest/best".
3. **Band words** map to Punjab's AQI thresholds: satisfactory >50, moderate >100, unhealthy for sensitive >150, unhealthy >200, very unhealthy >300, hazardous >400. "How many unhealthy hours" → `count_hours_above`, threshold 200.
4. **Comparisons:** compare_to set → view `compare`. For two cities, either order of city/other_city is accepted.
5. **Neighbourhood that is not a station** (Model Town, Johar Town) → area is the neighbourhood as written; the app finds the nearest station.
6. **Tomorrow, tonight, this evening, "will it be safe later"** → view `forecast`.
7. **Across cities or districts** ("which city", "rank Punjab") → view `city_overview`, camera `zoomed_out`.
8. **Out of scope:** not about air quality in these places; asks for causes, health advice or policy; or is only thanks/small talk.
9. **Clarify** only when the question has neither a place nor a time and no sensible default fits ("is it bad?", "how many hours?"). "How is the air?" alone is *not* ambiguous: Lahore, now.
10. **Follow-ups** (second turn of a conversation): the form is the previous form with only the changed fields updated.

## Reporting
Agreement is computed per field (exact match after the conventions above), reported as raw agreement and Cohen's kappa, with the number of disagreements resolved by discussion. The resolved forms become the gold set; the test set is frozen afterwards and never tuned on.

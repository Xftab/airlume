# Second-annotator guide (benchmark v1)

**Version 2, 30 October 2026.** Conventions 11 to 13 are new and convention 8 has changed. If you were given version 1, use this one instead: the three new rules cover about a third of the classmate questions, and two annotators working from different versions would disagree on rules rather than on judgement, which is the one thing the kappa must not measure.

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

Use `scripts\check_annotation.py` on your sheet before handing it over. It catches illegal values, a `count_hours_above` with no threshold, and a comparison whose view is not `compare`. It cannot tell you a label is wrong, only that the form is not legal.

## Conventions (agreed before annotation)

1. **"Right now", "at the moment", "abhi", "this morning"** → time `now`, aggregation `latest`, even for "where is it worst" (the app ranks the latest values).
2. **Past window** ("yesterday", "last week") → `mean` for "how bad was it", `max` for "worst/peak", `min` for "cleanest/best".
3. **Band words** map to Punjab's AQI thresholds: satisfactory >50, moderate >100, unhealthy for sensitive >150, unhealthy >200, very unhealthy >300, hazardous >400. "How many unhealthy hours" → `count_hours_above`, threshold 200.
4. **Comparisons:** compare_to set → view `compare`. For two cities, either order of city/other_city is accepted.
5. **Neighbourhood that is not a station** (Model Town, Johar Town, Sabzazar, Bahria) → area is the neighbourhood as written; the app finds the nearest station.
6. **Tomorrow, tonight, this evening, "will it be safe later", "when does it get clean today"** → view `forecast`. Anything forward-looking within the next 48 hours is a forecast, in English or Roman Urdu ("kal hawa saf hogi?").
7. **Across cities or districts** ("which city", "rank Punjab") → view `city_overview`, camera `zoomed_out`.
8. **Out of scope** (*changed in version 2*): not about air quality in these places (weather, rain, sunrise); asks for causes ("smog kaise banti hai", "does rain lower AQI"); asks about a person's own body; asks about a place with no monitor; asks for a forecast beyond 48 hours; or is only thanks or small talk. **Asking what to do at the current level is no longer out of scope — see convention 11.**
9. **Clarify** only when the question has neither a place nor a time and no sensible default fits ("is it bad?", "how many hours?", "AQI around my home?", "what is AQI in my location?"). "How is the air?" alone is *not* ambiguous: Lahore, now.
10. **Follow-ups** (second turn of a conversation): the form is the previous form with only the changed fields updated.
11. **Guidance is in scope; medicine is not** (*new in version 2*). A question asking what to **do** at the current level is in scope and takes the ordinary current-reading form — time `now`, aggregation `latest`, view `stations_3d`, area set if a place is named. The app attaches the published advisory for the band; you do not write it. This covers "should I wear a mask", "is it safe to go outside", "kiya mujhe walk pr jana chahiye", "what precautions for children and the elderly". A question about one **person's own body** stays out of scope: symptoms, diagnosis, treatment, or whether smog caused something they have ("mera gala kharab hua hai", "smog se flu ho sakta hai", "does smog affect lungs and heart"). The line is whether answering it means quoting a published advisory for a measured band, or judging an individual.
12. **Beyond the forecast horizon is out of scope** (*new in version 2*). The system forecasts 24 to 48 hours. A question about next week, next month or a named date further ahead ("27 Dec 2026", "next week me kitni smog") is `in_scope: no`, not a clarification — the clarify field is for a question that cannot be *filled*, and these can be filled, just not answered. Within 48 hours, convention 6 applies as usual.
13. **Hour-of-day patterns use the timeline** (*new in version 2*). A question about when of day it is usually worse or better — "raat ko smog kam ho jati hai?", "morning mein ya evening mein?" — is time `last_7_days`, aggregation `mean`, view `timeline`. This is a retrospective pattern, not a prediction, so it is not a forecast even though it sounds forward-looking. A question about when it will get better *today* is forward-looking and takes convention 6.

## Reporting

Agreement is computed per field (exact match after the conventions above), reported as raw agreement and Cohen's kappa, with the number of disagreements resolved by discussion. Run `scripts\annotator_agreement.py <sheet-a> <sheet-b>` to produce both and the disagreement list. The resolved forms become the gold set; the test set is frozen afterwards and never tuned on.

Kappa is unstable on 20 items — one flipped label moves it noticeably — so report the number with the count beside it rather than leaning on the usual adjectives. Where both annotators used a single value for every row, kappa is undefined and raw agreement is reported instead; that means the field was never in question, not that agreement was poor.

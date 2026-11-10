# Annotator guide (benchmark v1)

**Version 3, 6 November 2026.** It matches prompt v5 and the schema freeze of 6 Nov. If you were given version 1 or 2, use this one: conventions 1, 8, 9 and 13 have changed, and 14 to 16 are new. Two annotators working from different versions would disagree on rules rather than on judgement, which is the one thing the agreement figure must not measure.

**Who does what** (from `validity-review-2026-11-04.md`):
- **Kiran** annotates every question in the fresh set, independently.
- **Tehreem** independently annotates the in-scope questions only, for the agreement figure.
- **Aftab** adjudicates disagreements by applying this guide, writing down for each one the convention that settled it.
- Neither annotator may see any draft labels, Aftab's file, the other annotator's sheet, or `second-annotator-selection-2026-11-01.md` before finishing.

## The form

For each question fill these fields. Leave a field blank when nothing in the question decides it; the default then applies.

| Field | Allowed values | Default |
|---|---|---|
| in_scope | yes / no | yes |
| clarify | the short question you would ask back, if the question cannot be answered as written | blank |
| metric | aqi, pm25, pm10 | aqi |
| city | the city **named in the question**; leave blank when no city is named | blank (the app uses Lahore) |
| area | the station or neighbourhood named inside the city, exactly as the user wrote it | blank |
| time | now, today, yesterday, last_7_days, last_30_days, this_month, last_month, same_day_last_year, custom_date (+ date), custom_range (+ start, end) | now |
| aggregation | latest, mean, max, min, count_hours_above (+ threshold), hour_of_day | latest |
| compare_to | none, yesterday, last_week, last_year, other_city (+ other_city) | none |
| view | stations_3d, city_overview, compare, timeline, forecast | stations_3d |
| camera | overview, station, north, zoomed_out | overview |

Run `scripts\check_annotation.py` on your sheet before handing it over. It catches illegal values, a `count_hours_above` with no threshold, and a comparison whose view is not `compare`. It cannot tell you a label is wrong, only that the form is not legal.

## Conventions

1. **Right now: how is it, or where is it worst?** (*changed in version 3*) "Right now", "at the moment", "abhi", "this morning" → time `now`. Then:
   - aggregation `latest` when the question asks **how** the air is or what to do ("how is the air", "is it safe", "should I wear a mask");
   - `max` when it asks **where it is worst** ("where is smog most", "kaha zyada", "high alert areas");
   - `min` when it asks where it is cleanest.
   The app ranks the latest readings for `max` and `min`.
2. **Past window** ("yesterday", "last week") → `mean` for "how bad was it", `max` for "worst/peak", `min` for "cleanest/best".
3. **Band words** map to Punjab's AQI thresholds: satisfactory >50, moderate >100, unhealthy for sensitive >150, unhealthy >200, very unhealthy >300, hazardous >400. "How many unhealthy hours" → `count_hours_above`, threshold 200.
4. **Comparisons:** compare_to set → view `compare`. For two cities, either order of city/other_city is accepted.
5. **Neighbourhood that is not a station** (Model Town, Johar Town, Sabzazar, Bahria) → area is the neighbourhood as written; the app finds the nearest station.
6. **Tomorrow, tonight, this evening, "will it be safe later"** → view `forecast`. Anything forward-looking within the next 48 hours is a forecast, in English or Roman Urdu ("kal hawa saf hogi?").
7. **Across cities or districts** ("which city", "rank Punjab", "smog free cities") → view `city_overview`, camera `zoomed_out`, city blank unless one is named.
8. **Out of scope** (*changed in version 3*). A question is out of scope when it:
   - is not about air quality in these places (weather, rain, sunrise);
   - asks for causes ("smog kaise banti hai", "does rain lower AQI");
   - asks about a person's own body;
   - asks for a forecast beyond 48 hours;
   - is only thanks or small talk.
   **A place with no monitor (a village, a small town) is no longer out of scope: see convention 9.** Asking what to do at the current level is in scope: see convention 11.
9. **Clarify** (*changed in version 3*). A clarify always goes with in_scope `yes`. Use it when the question cannot be filled as written:
   - the user's own location ("my location", "near me", "around my home", "my area") → "Which area or neighbourhood are you in?";
   - a village or town with no monitor ("my village") → "Which district is your village in?";
   - a question with neither place, nor time, nor any ranking ("is it bad?", "how many hours?").
   "How is the air?" alone is *not* ambiguous: Lahore, now.
10. **Follow-ups** (second turn of a conversation): the form is the previous form with only the changed fields updated.
11. **Guidance is in scope; medicine is not.** A question asking what to **do** at the current level is in scope and takes the ordinary current-reading form: time `now`, aggregation `latest`, view `stations_3d`, area set if a place is named. The app attaches the published advisory for the band; you do not write it. This covers "should I wear a mask", "is it safe to go outside", "kiya mujhe walk pr jana chahiye", "what precautions for children and the elderly". A question about one **person's own body** stays out of scope: symptoms, diagnosis, treatment, or whether smog caused something they have ("mera gala kharab hua hai", "smog se flu ho sakta hai", "does smog affect lungs and heart").
12. **Beyond the forecast horizon is out of scope.** A question about next week, next month or a named date further ahead ("27 Dec 2026", "next week me kitni smog") is `in_scope: no`, not a clarification.
13. **Hour-of-day patterns** (*changed in version 3*). A question about when in the day it is usually worse or better ("raat ko smog kam ho jati hai?", "morning mein ya evening mein?", "best time to go out") is time `last_7_days`, aggregation `hour_of_day`, view `timeline`. It is a retrospective pattern, not a prediction.
14. **When will it improve?** (*new in version 3*) "When will the smog go down", "when will the air get clean today", "kab saaf hogi" → view `forecast`, time `now`, in_scope `yes`, no clarify. The answer is the lowest stretch of the published forecast.
15. **A ranking never needs a clarify** (*new in version 3*). "Tell me the high alert areas" → Lahore stations, time `now`, aggregation `max`. "Tell me smog free cities" → view `city_overview`, aggregation `min`, camera `zoomed_out`.
16. **"Kal" with an unclear tense** (*new in version 3*). "Kal" means both yesterday and tomorrow. When the verb does not settle it ("kiya kal bhi smog han"), write a clarify: "Do you mean yesterday or tomorrow?" When it does ("kal hawa saf hogi" is future; "kal kaisi thi" is past), fill the form.

## Reporting

- Agreement is computed per field (exact match after the conventions above). It is reported as raw agreement and Cohen's kappa, with the number of disagreements resolved by adjudication. `scripts\annotator_agreement.py <sheet-a> <sheet-b>` produces both and the disagreement list.
- The adjudicated forms become the gold set. The test set is then frozen, scored once and never tuned on.
- Kappa is unstable on small samples, so report the number with the count beside it. Where both annotators used a single value for every row, kappa is undefined and raw agreement is reported instead.

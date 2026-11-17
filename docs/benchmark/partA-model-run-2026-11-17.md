# Part A, the model run on the 40 new classmate questions (17 November 2026)

**What this is.** The 40 questions (d001 to d040) were run through the real router (gpt-oss-120b, prompt v5, frozen) and then resolve and answer, on Aftab's laptop, on 17 Nov 2026. Full output with the form the model filled for each question: `docs/benchmark/partA-model-run-2026-11-17-output.md`.

**What it is not.** It is not the Part A score. There are no gold labels yet, and the reading below is by one person (Claude) who knows the system, unblinded. Use it to find failure classes, not as an accuracy figure. The headline number comes later, from independent labels, scored once.

Outcomes as the runner recorded them: 30 answered, 3 clarify, 3 out of scope, 2 resolve error (area not known), 2 route error (the model's form was rejected). Zero crashes in the answer layer.

## First reading, by failure class (provisional, single rater)

| Class | Questions | Count |
|---|---|---|
| Form looks right and the answer addresses the question | d001, d007, d008, d018, d021, d022, d024, d027, d029, d031, d032, d033, d034, d035, d036, d037, d039, d040 | 18 |
| "Which is worse, A or B": the form has no place for two areas, so both names are dropped and the answer ranks the whole network (d014 asks which station has no PM10, same effect) | d010, d013, d014, d016, d017, d030 | 6 |
| Window the form cannot express ("last 2 months", "last 3 months", "last 2 weeks", "December", a month of 2026): narrowed to 30 or 7 days, a month nobody asked for, or a clarify | d002, d005, d009, d015, d019 | 5 |
| Form rejected by the validator: the model wrote `17:00`, `24:00` and `2026-07` in date fields | d003, d020 | 2 |
| Right form, wrong sentence: a named city with `view=city_overview` was answered with the worst city in the country | d023, d025, d026 | 3 |
| Area not in the list of known neighbourhoods (honest refusal) | d006 | 1 |
| Compound question, current air and next week: refused as out of scope | d012 | 1 |
| Reasonable clarify (unknown area, "kal" is yesterday or tomorrow) | d004, d011 | 2 |
| Partly answered: asked "which day" but the day is not named (d038); asked November 2023 against this year, form compared with last year (d028) | d038, d028 | 2 |

If only the first row counts as correct, that is 18 of 40 = 45% (Wilson 95% interval 31 to 60). If the four partial or reasonable rows (d004, d011, d038, d028) are counted as correct, 22 of 40 = 55% (40 to 69). Both are indicative only. For comparison, Part B (30 constructed questions) scored 25 of 30 = 83.3% [66.4, 92.7] against the stub's 9 of 30. The first reading suggests that naturalistic questions are harder than the ones we wrote ourselves, which is the reason Part A exists. The labelled score will say by how much.

## What the failures say

1. **The biggest gap is two-place comparison (6 of 40).** Pakistani users ask "X or Y?" constantly. The schema has `area` and `compare_to=other_city`, but nothing for two areas in one city. The model fills the nearest thing and the answer ranks the network. This needs a schema change (for example an `areas` list), so it is a prompt and schema v2 item, not a quick fix.
2. **Windows longer than 30 days and month names (5 of 40).** The archive is only 40 days of hourly data, so "last 3 months" cannot be answered with hourly data anyway. The right behaviour is to say so, and the model narrowed it silently. A daily series exists for Lahore (the one Model A uses), so a longer-window label could be answered for Lahore from it; other cities are [to check].
3. **Time-of-day and month values (2 of 40).** The model tried to write "17:00 to 24:00" and "2026-07". The schema holds dates only, so the form is rejected. In the live app a rejected form falls back to the rule-based stub, which then returns an unrelated generic answer. A better behaviour is to ask for a date or window instead of silently using the stub. Not changed here (see protocol).
4. **A real answer-layer bug, fixed (3 of 40 plus d005).** When the form named a city and chose the city overview, the answer led with the worst city in Pakistan (for example "Vehari had the worst air" for a Lahore question; Islamabad's own figure was never given). Fixed in `airlume/nl/answer.py`: a named city is answered for itself, as the 6 Nov fix already did for "right now". Test added; 276 tests pass.
5. **Things that went right.** Station-name matching inside a city ("Multan Road" is a Lahore station, "Wagha Border", "Gulberg" to Gulberg III, "DHA" to DHA Phase 6), the Roman Urdu questions that resolved correctly (d007, d036, d038; d019 resolved but to the wrong month), out-of-scope handling of rain and London, dates the archive does not hold (July 2023, November 2024, November 2025) answered with an honest "no data" that states what the archive covers, and honest "no forecast for Sialkot, Multan, Islamabad" (EPA publishes for Lahore only). Nearest-station notes ("4.6 km away") are recorded and the app shows them.
6. **Not fixed, noted.** d038 asks which day had the highest AQI; the answer gives the maximum but not the day. This is answer-layer and cheap; it is on the list.

## Protocol: what was and was not changed

- Prompt v5, the schema, and the router stay frozen. Every item above that needs them (1 to 3) is a hypothesis for prompt/schema v6, to be tested on questions nobody has seen, with v5 and v6 reported side by side. Because these failure classes were seen on Part A, **Part A can no longer be used to evaluate v6**; the sheets still coming in can.
- Changed: one answer-layer rule (4), found by reading answers. It does not change what the router returns, so the router's Part A score is unaffected. The scoring harness runs with the fallback off, so the two route errors would count against the router as they are.
- Ids d003 and d020 were route errors on this run. Model output varies between runs, so a second run could differ; scoring will use one frozen run per model, as planned.

## Next
More questions (40 of 60 to 100 collected; 2 of 4 to 5 people), independent labels (Tehreem for Kiran's own d001 to d020, Aftab adjudicating), the check script, freeze, one scoring run per model. In parallel and without touching Part A: draft v6 hypotheses (two-area comparison, longer windows via daily data, time-of-day) from the development sets.

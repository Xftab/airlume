# Part A, first look at the 40 new classmate questions (17 November 2026)

**What was done.** The 40 questions (`classmate-raw-2026-11-17.jsonl`, d001 to d040) were run through the whole pipeline (route, resolve, answer) with the **rule-based stub** router, on the 17 Nov archive. The real model was not run: it needs the key on Aftab's laptop. This is a diagnostic run, not scoring: there are no gold labels yet, and the stub is the baseline, so none of its answers says anything about how the model does. Outputs: `docs/benchmark/partA-stub-run-2026-11-17.md`.

## Protocol decision: what may and may not be changed

- **Prompt v5 and the schema stay frozen.** Part A is the fresh test set. Tuning the prompt, the schema or the router on d001 to d040 (or on Part B, already scored once) would turn them into development data and make the headline number optimistic.
- **Allowed now:** changes downstream of the form (the resolver and the answer text), found by reading answers, because the benchmark scores the form the router fills and not the sentence written afterwards. Each such change is logged here so the report can say what was seen.
- **For a better router (prompt v6):** write the hypotheses from the development sets (the 62 questions of 30 Oct, the v0 set) and the documented Part B failure pattern, but test v6 only on questions nobody has seen, for example the sheets still coming in, and report v5 and v6 side by side. Not before the real Part A score of v5 is on record.

## Stub run (baseline behaviour, for the record)

39 of 40 answered, 1 resolve error. Most answers are not about the question asked: 11 of the 40 got the generic "Lahore right now: AQI 309" reply, including questions about 2023 dates, rain, London and a village name. That is what a keyword router does, and is consistent with its 9 of 30 on Part B. It is not a finding about the model.

## One answer-layer defect found, and fixed

When one city in a comparison had no recent data, the reply was "One of the two cities has no recent data." and did not say which (seen for Lahore against Karachi and Peshawar against Quetta). It now names the city: "I have no recent AQI reading for Karachi, so I cannot compare them right now." Test added (`tests/test_answer.py`); 275 tests pass.

## What the real model run will show (now run: see `partA-model-run-2026-11-17.md`)

Run `scripts/run_classmate_questions.py --file classmate-raw-2026-11-17.jsonl` (command in the chat). It records, for each question, the form the model filled, the outcome (answered, clarify, out of scope, resolve error) and the answer. Things worth reading it for, none of them scoring: places that are not stations (Sabzazar-type, convention 5), date ranges the archive does not hold (July 2023, "last 2 months": hourly archive is about 40 days), a station name that contains a city name ("Multan Road" is a Lahore station), the two out-of-scope questions (rain, London), and the Roman Urdu questions.

## Still needed before a Part A score
More questions (40 of 60 to 100, from 2 of 4 to 5 people), independent labels from Kiran and Tehreem (not Kiran for his own d001 to d020), the guide's check script, adjudication, freeze, then one scoring run per model.

# Frozen benchmark

`questions.jsonl` is frozen at the end of Phase 2. Each line:

```json
{"id": "q001", "question": "Where is the air worst in Lahore right now?",
 "expected": {"metric": "aqi", "city": "Lahore", "aggregation": "latest", "view": "stations_3d"},
 "class": "where_now"}
```

Rules
- Written **before** the router is tuned; never edited afterwards (append-only with a dated note).
- Question classes: where_now, how_much, compare_time, compare_place, threshold_count,
  best_time, forecast, ambiguous, follow_up, out_of_scope.
- Scoring (E1): form-field exact match per field; a question "passes" if every
  field that matters for its class matches. Visual answers are scored with the
  rubric in `rubric.md` (contribution C5).

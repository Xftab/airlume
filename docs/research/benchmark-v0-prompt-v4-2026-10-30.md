# Benchmark v0 re-run against prompt v4 — 30 October 2026

Purpose: check that prompt v4 (guidance questions in scope, forecast horizon and
hour-of-day rules made explicit) did not regress the 90 items of benchmark v0,
which were scored against prompt v3 on 15 October.

Results: `data/eval/e1_openai_gpt-oss-120b_2026-10-30.json`,
`data/eval/e1_openai_gpt-oss-20b_2026-10-30.json`.

## Headline

| Run | Prompt | Pass | 95% CI | Consistency |
|---|---|---|---|---|
| gpt-oss-120b, 15 Oct | v3 | 88.9% | 82–96% | 100% |
| gpt-oss-120b, 30 Oct | **v4** | **90.0%** | 83.3–95.6% | 100% |
| gpt-oss-20b, 30 Oct | **v4** | **90.0%** | 83.3–95.6% | 100% |

**v4 is safe.** Item by item: zero items that passed under v3 fail under v4, and
one that failed now passes (q052). The 1.1-point rise is that single item; the
confidence intervals overlap almost entirely, so the honest statement is "no
measurable change", not "v4 improved the router".

`out_of_scope` scores 100% on both models, so none of the v0 gold labels were
invalidated by the new scope rules — no v0 item was a guidance question that v4
now accepts.

## The two models are indistinguishable, and fail differently

Both land on exactly 90.0% with the same interval, but not on the same items.
120b fails four follow-ups; 20b fails three, plus one `best_time` and one
`forecast`. Five times the parameters buys nothing measurable here.

This is the second time this project has found the bigger or deeper model not
winning: LightGBM beat both the LSTM and the GRU on the daily forecast (Section
6.1 of the Materials draft). Worth stating once in the report as a theme rather
than twice as a surprise.

## Where the failures are

Nine items fail on 120b. By class: follow_up 4, where_now 2, compare_time 2,
compare_place 1.

**follow_up is the weakest class** — 80% on 120b, 85% on 20b, over 20 items, and
nearly half of all failures. Multi-turn context is the thing to work on if
anything is worked on.

Four failures worth naming individually:

- **q002, "Which station has the cleanest air at the moment?"** Both models
  answer `aggregation: min`; the gold is `latest`. The prompt says in capitals
  that it must ALWAYS be `latest` when the time is `now`, even for
  "worst/cleanest". When an explicit, capitalised instruction fails on both
  models, the convention is probably fighting the semantics rather than the
  models being careless: "cleanest" is a superlative, and `min` is the obvious
  word for it. The gold is still right — `min` means the minimum over a window,
  and `now` has no window — but the distinction is subtle and should be called
  out in the report rather than buried as a model error.
- **q024, "Was October worse than September in Lahore?"** The model returned a
  `custom_range` of **2023-09-01 to 2023-10-31** — a year from its training era,
  not the current one. The resolver checks a date is well-formed but does not
  check it falls inside the archive, so this resolves to a valid empty window and
  the user is told "No data for that place and time." No invented value is ever
  shown, so design rule 6 holds, but the message hides the real cause. A range
  outside the archive should say so.
- **q031, "Is Gulberg worse than DHA right now?"** Both models choose
  `view: compare`; the gold keeps a within-city station comparison in
  `stations_3d`. Another convention that is defensible but not obvious.
- **u003, "kal se behtar hai ya bura?"** 120b returns `compare_to: none`,
  `view: city_overview` instead of a yesterday comparison. A Roman Urdu
  follow-up — the intersection of the two weakest areas.

## A reporting trap in the per-field table

The per-field accuracies look like fourteen comparable measurements. They are
not. The number of items carrying each field:

| n | Fields |
|---:|---|
| 1 | `date`, `clarify_or_other_city` |
| 5–9 | `camera`, `clarify`, `other_city`, `threshold`, `in_scope` |
| 11–26 | `metric`, `compare_to`, `area` |
| 40–69 | `aggregation`, `time`, `view`, `city` |

So `clarify_or_other_city 0%` on 120b and `100%` on 20b is **one item**, decided
one way by one model and the other way by the other. It is not a quality
difference and must not be printed as a percentage without its n — a 0% in a
results table invites exactly one question in a viva, and "that is one item"
is a bad answer to give on the spot. The same applies to `in_scope 89%`, which
is 8 of 9.

Recommendation: print every per-field figure as `n/N` or append the n, and in
v1 ensure each field is carried by enough items to be worth reporting at all.

## Roman Urdu rests on ten items

120b 9/10, 20b 8/10. The two models are one item apart, which distinguishes
nothing. The classmate collection found Roman Urdu to be 60% of what real users
write against 14% of v0 (`docs/research/classmate-questions-2026-10-30.md`), so
v1 must carry far more Roman Urdu and report it with its own interval rather
than as a single percentage over ten items.

## What to do with this

1. Nothing blocks v1. v4 is in, and it costs nothing on v0.
2. Treat follow-up handling as the known weak point; do not claim it is solved.
3. Add the n to every per-field figure before any of this reaches the report.
4. Consider having the resolver say when a requested range falls outside the archive.

# E1 results on benchmark v0 (development set)

Benchmark v0: 60 English and 10 Roman-Urdu single questions plus 20 two-turn conversations (n = 90). A question passes when every expected field of the form matches. Bootstrap 95% confidence intervals (2,000 resamples). One run per configuration; consistency across runs is measured separately with `--runs 3` once the free-tier budget allows.

**Caution for the report:** the prompt was revised twice (v1 to v3) after reading failures on this set, so v0 is a *development* set and these numbers are optimistic. The headline figure comes from benchmark v1 (classmate-authored, second-annotated, frozen), which the prompt has never seen. The prompt is frozen at v3 as of 15 October.

| Router | Pass | 95% CI | Roman Urdu | Follow-ups | Weakest class |
|---|---|---|---|---|---|
| Rule-based stub | 45.6% | 36%-56% | 40% | 20% | forecast 0% |
| gpt-oss-120b, prompt v1 (14 Oct) | 66.7% | 57%-77% | 70% | 55% | where_now 54% |
| gpt-oss-20b, prompt v2 (14 Oct) | 81.1% | 72%-89% | 90% | 70% | where_now 54% |
| gpt-oss-120b, prompt v3 (15 Oct) | 88.9% | 82%-96% | 90% | 80% | compare_time 78% |
| gpt-oss-20b, prompt v3 (15 Oct) | 88.9% | 82%-94% | 80% | 80% | best_time 80% |

Per class, 120b v3: ambiguous 83% (6), best_time 100% (5), compare_place 89% (9), compare_time 78% (9), follow_up 80% (20), forecast 100% (5), how_much 100% (9), out_of_scope 100% (7), threshold_count 100% (7), where_now 85% (13).
Per field, 120b v3: aggregation 95%, area 92%, camera 100%, city 100%, clarify 83%, compare_to 95%, date 100%, in_scope 89%, metric 100%, other_city 100%, threshold 100%, time 98%, view 93%.

## What each prompt revision fixed
- **v1 to v2:** a rule per field; the 40 cities listed; the Punjab AQI band thresholds; five worked examples. The biggest single fix was telling the model that a *station* name belongs in `area` (v1 only mentioned neighbourhoods): 8 of the 30 v1 failures.
- **v2 to v3:** "now" always means `latest` even for "where is it worst"; cross-city questions zoom out; neighbourhood names kept verbatim; small talk out of scope; follow-ups treated as continuations by default. The scorer also accepts either order of city/other_city in a two-city comparison.

## Remaining failures (both models) and what they tell us
- **Debatable gold labels (send to the second annotator):** q002 "cleanest station at the moment" (gold `latest`, model `min`); q024 "October vs September" (gold `this_month` + compare, model `custom_range`); q031 "Gulberg vs DHA" (gold `stations_3d`, model `compare`); c001 "and yesterday" after "worst right now" (gold `max`, model `latest`).
- **Real misses:** Roman-Urdu comparison "kal se behtar hai ya bura?" (120b) and forecast "kal hawa kaisi hogi?" (20b); "Why?" as a follow-up not marked out of scope (120b); "zoom into Lahore" and "over the last 7 days?" not changing the view (20b).
- **Infrastructure:** one item per run failed on a transient Groq error (q052 on 120b); the harness records it as a failure rather than retrying silently. Dates written as datetimes ("2026-10-16T18:00") are now accepted and truncated to the day.

## Provider notes (free tier, 14-15 Oct)
Strict `json_schema` mode needs a flattened schema without `$ref`/`default`/`title`; `gpt-oss` reasoning tokens count against the output cap (2,048 with low reasoning effort); 8,000 tokens per minute and a rolling 200,000 tokens per day per model. A 90-item run costs about 140k tokens, so one full run per model per day. The router caches by prompt version and question, so interrupted runs resume.

Files: `data/eval/e1_*.json` (git-ignored; copies kept with the report).

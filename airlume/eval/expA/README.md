# Experiment A: typed form against Python code against text-to-SQL

Offline experiment for the paper. The plan, hypotheses and scoring rules are in
`docs/research/expA-protocol-2026-11-20.md`; read that first. The app never imports anything
here (`tests/test_expA_isolation.py`).

## Files

| File | What it does |
|---|---|
| `snapshot.py` | Freezes the archive at a cutoff, with hashes, and makes the shifted copy (AQI +7, PM +5) |
| `prompts.py` | The code and SQL arms' prompts (same rules as the form prompt v5, in words) |
| `generate.py` | One model reply per arm and question; cached, logged, never executed here |
| `sandbox.py`, `_py_runner.py`, `_sql_runner.py` | Runs model-written Python or SQL, locked down |
| `formarm.py` | Runs the form arm exactly as the app does (resolve, store, answer) |
| `normalize.py` | Reads every arm's output back into one shape; writes the code arms' sentences |
| `reference.py` | The gold functions annotators call, independent of the app's code |
| `score.py` | Correctness, the invented-number test, Wilson, McNemar, Newcombe |
| `agreement.py` | Agreement between two annotators' gold calls |
| `items.py` | Loads and checks question files |
| `run.py` | The four steps: gold, generate, execute, score |
| `trick-set-2026-11-20.jsonl` | Development set: 51 trick questions, 25 English and Roman Urdu pairs |
| `gold-annotation-template.csv`, `intake-template.csv` | Templates for annotators and for collected questions |

## Order of work (each step resumes where it stopped)

```
python scripts\expA_run.py selftest
python scripts\expA_run.py check --items airlume\eval\expA\trick-set-2026-11-20.jsonl
python scripts\expA_run.py freeze --cutoff 2026-12-05T12:00:00+05:00
python scripts\expA_run.py gold     --snapshot <name> --items <file>
python scripts\expA_run.py generate --snapshot <name> --items <file> --model openai/gpt-oss-120b --dry-run
python scripts\expA_run.py generate --snapshot <name> --items <file> --model openai/gpt-oss-120b
python scripts\expA_run.py execute  --snapshot <name> --items <file> --model openai/gpt-oss-120b
python scripts\expA_run.py score    --snapshot <name> --items <file> --model openai/gpt-oss-120b
```

`--model stub --arms form` runs the whole chain with the app's rule-based router: no key, no
budget, useful to check a new item file. Only `generate` calls Groq; it reads the key from
`.env` and never prints it.

## Gold calls

`latest(place)`, `agg(place, when, agg, metric, threshold)`, `hours_above(place, when,
threshold)`, `rank_stations(when, order, agg, position)`, `rank_cities(...)`,
`compare_places(a, b, when, ask)`, `compare_time(place, when, against)`,
`difference_places(a, b, when)`, `forecast_mean(city)`, `peak_hour(place, when, lowest)`,
`no_data()`, `refuse()`, `clarify()`.

A place is a station or city name from the registry, or `area:<name>` for a Lahore
neighbourhood (the nearest station). `when` is `now`, `today`, `yesterday`, `last_7_days`,
`last_30_days`, `this_month`, `last_month`, `date:YYYY-MM-DD`, `range:YYYY-MM-DD:YYYY-MM-DD`
or `hours:N`. The protocol's section 4 says what each means.

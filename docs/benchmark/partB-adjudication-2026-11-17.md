# Part B adjudication (17 November 2026)

**Status: proposed, waiting for Aftab's approval.** The guide says Aftab adjudicates. Everything below is a proposal made by applying the annotator guide; nothing is frozen until he approves it.

## 1. What came back

| Sheet | Received | Usable |
|---|---|---|
| Kiran, first attempt | 14 Nov | **No.** 301 conformance problems in all 30 rows: free words instead of allowed values, `clarify` used as yes/no, values sitting in shifted columns (the `time_start` header was blank). Kept as received, not used. |
| Tehreem | 14 Nov | **Yes**, after format-only fixes (12 problems, all spelling or spacing). |
| Kiran, redo (one-page instruction sheet) | 17 Nov | **Yes**, after format-only fixes (51 problems: `count_hour`, `PM2.5`, `last week`, spacing). |

Format-only means: case, spaces, `PM2.5` to `pm25`, `count_hour` to `count_hours_above`, `last week` to `last_7_days`, `other city` to `other_city`, and restoring four question texts Tehreem had retyped. No label was changed in substance. Every edit is in `kiran-format-changes-2026-11-17.csv` and `tehreem-format-changes-2026-11-14.csv`. The sheets as received are in `airlume/eval/benchmark/as-received/`.

## 2. Agreement (30 questions, `scripts/annotator_agreement.py`)

| Field | Raw agreement | Cohen's kappa |
|---|---:|---|
| in_scope | 97% | 0.000 (Tehreem marked all 30 yes, so kappa has no variation to work with; raw agreement is the figure) |
| metric | 97% | 0.939 |
| city | 87% | 0.788 |
| area | 80% | 0.722 |
| time_label | 83% | 0.809 |
| aggregation | 83% | 0.791 |
| threshold | 93% | 0.811 |
| compare_to | 57% | 0.472 |
| other_city | 97% | 0.922 |
| view | 87% | 0.762 |
| camera | 100% | 1.000 |

42 cells differ, in 28 of the 30 questions. n is 30 per field, so kappa moves a lot with one flipped label: report the count beside every figure and do not lean on the adjectives. This is Part B only, a constructed set, and it is not pooled with Part A.

## 3. Why the 42 cells differ

| Cause | Cells | Proposed resolution |
|---|---:|---|
| Spelling of a city or area (`Shadhara`, `Gujrawala`, `Lohare`, `gulbergiii`) | 8 | Name as spelled in the question |
| `compare_to` filled for a plain time window (Kiran: `yesterday`, `last_week`, `now`, `last_30_days` on non-comparisons) | 11 | Blank. Convention 4: `compare_to` is for a real comparison only |
| Two-city comparison with the wrong `compare_to` (b021) | 1 | `other_city` |
| Band word with no threshold (b007 hazardous, b010 unhealthy) | 2 | 400 and 200 (convention 3) |
| `this week`: the form has no such time value | 3 | `last_7_days`, as **new convention 17** (see below) |
| `view` compare missing or set without a comparison | 4 | View `compare` exactly when `compare_to` is set |
| `aggregation` on questions that are not about a statistic (b002, b011, b013, b014, b015) | 5 | Default `latest`, except b015 `mean` (convention 2) |
| `in_scope` (b003, a ranking of stations) | 1 | yes (conventions 8 and 15) |
| Area or time actually missing from one sheet (b009 `Kahna` against `Kahna Nau`, b009 time, b012 area, b002 metric) | 4 | The fuller reading, which is what the question says |
| b022: comparison with last month | 1 | See section 4 |
| other | 2 | See the CSV |

The proposed gold sides with Tehreem in 34 of the 42 cells, with Kiran in 6 and with neither in 2 (both are spelling). The reason is mostly that Kiran's redo misread `compare_to`, not that one annotator is more careful in general. Full list with the convention for every cell: `partB-adjudication-2026-11-17.csv`.

## 4. Two decisions for Aftab

1. **Convention 17, new (17 Nov): "this week" is `last_7_days`.** The guide's time table has no `this_week`. Kiran left it as the literal word and Tehreem chose `last_7_days`. The form cannot express a calendar week, so `last_7_days` is the nearest legal value. It is added to the guide as an addendum, not by editing version 3, so the record shows it was made after annotation.
2. **b022 ("above 250 this month compared with last month").** `compare_to` has no `last_month` value and the schema is frozen. Tehreem wrote `last_month` (illegal), Kiran left it blank. The proposal leaves `compare_to` blank, keeps `view` compare, and marks the row in `notes`: **the form cannot express this question**. The row stays in the score; the report states that it tests a known schema limit.

Your approval of the other 40 cells is mechanical. If you disagree with any cell, change `proposed_gold` and tell me.

## 5. Limitations to state in the report

- The Part B questions were written by Claude, and the gold is adjudicated by rule from two human sheets, not written by Claude.
- Kiran's first attempt was unusable and he was then given a one-page instruction sheet. His redo is the sheet of record. A worked example on that sheet (Jhelum) is not a Part B question. An earlier chat message used b006 as an example; if it was passed on, b006 is not fully independent.
- Eight disagreements are spelling noise and are counted in the table above.
- n is 30. Per-field counts, not percentages with adjectives.

## 6. After approval

1. Rename `airlume/eval/benchmark/partB-gold-2026-11-17-PROPOSED.csv` to `partB-gold-2026-11-17.csv`. The file is then frozen; never edit it after the first scoring.
2. `scripts\check_annotation.py` on it (it passes now).
3. Score once per model with `scripts\score_benchmark_v1.py` (stub first, then `openai/gpt-oss-120b`).

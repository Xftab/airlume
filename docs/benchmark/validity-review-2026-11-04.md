# Benchmark v1: validity review and freeze decision

**Date:** 4 November 2026. **Author:** Claude, at Aftab's request. **Status:** findings are verified; the recommendation needs Aftab's decision.

This review was triggered by one line in the 1 November history: *"first annotation of 62 questions done (accepted from model draft unchanged, so anchored)."* Checking what that means in practice turned up six findings. Four of them change what benchmark v1 can honestly claim. Nothing here is a reason to panic: the fix is cheap if it is made now, and expensive if it is made after the report is written.

---

## 1. The findings

### F1. The gold labels are the model's draft, byte for byte

`classmate-raw-2026-10-30-annotated-aftab.csv` and `classmate-raw-2026-10-30-annotated-DRAFT-by-claude.csv` are the same file:

```
26aa5f1606469e45fbf30a66efc367e7  classmate-raw-2026-10-30-annotated-aftab.csv
26aa5f1606469e45fbf30a66efc367e7  classmate-raw-2026-10-30-annotated-DRAFT-by-claude.csv
```

Not one of the 150 filled cells across 62 questions differs. This is not "a human reviewed a draft and mostly agreed"; it is the draft under a different name. Eight rows carry a `REVIEW` flag (c007, c008, c010, c015, c018, c024, c025, c038) that a reviewer was meant to resolve, and they are unresolved. c018 (*"kiya kal hawa saf hogi"*) is genuinely ambiguous between yesterday and tomorrow — the selection file itself says so — and it still carries the draft's reading.

The project rule, set on 30 October, is explicit: *"Gold labels are NOT written by Claude (LLM grading LLM); humans annotate."* As things stand that rule is broken, and the benchmark would be scored against labels a language model wrote.

How bad is it? Milder than true self-grading, because the labeller (Claude) is not the system under test (`gpt-oss-120b` / `gpt-oss-20b`). But it is not independent either, for a specific reason: **Claude also wrote prompt v4 and annotator guide v2.** So the labels encode the intended behaviour as one author understood it. Scoring against them measures *conformance to the designer's intent*, not *correctness as a reader would judge it*. Those are different claims, and only the second is worth putting in a report.

### F2. The safety check in the scoring script is defeated by a rename

`score_benchmark_v1.py` already guards against this. The guard is on the **file name**:

```
sys.exit(f"{gp.name} is a DRAFT. A draft written by a model is not gold; ...")
```

Renaming `...-DRAFT-by-claude.csv` to `...-aftab.csv` walks straight past it. The guard needs to compare **contents**, not names. This is a one-function fix and is worth making regardless of what else is decided (see §4).

### F3. Aftab can no longer supply an independent first annotation

He has read and accepted the draft. A "careful re-annotation" by him now is anchored by definition, and saying otherwise in the report would not survive a question in the viva. Whoever produces the gold labels has to be someone who has not seen the draft. That points at Kiran and Tehreem, who have seen neither the draft nor the selection file.

This is awkward but has a silver lining: the report's front matter has to state who did what, and the history shows the work concentrated in one member. Having Kiran and Tehreem own the annotation is both methodologically necessary and a genuine, documentable contribution each.

### F4. The question set barely exercises the form schema

Counting filled cells across all 62 questions:

| Field | Filled / 62 | Distinct values |
|---|---:|---:|
| `in_scope` | 62 | 2 |
| `time_label` | 12 | 3 |
| `aggregation` | 11 | 2 |
| `view` | 11 | 3 |
| `area` | 6 | 5 |
| `city` | 3 | 1 |
| `clarify` | 3 | 2 |
| `camera` | 1 | 1 |
| `metric` | **0** | 0 |
| `threshold` | **0** | 0 |
| `compare_to` | **0** | 0 |
| `other_city` | **0** | 0 |

**Four of the twelve form fields are never used by a single real question, and three more are used once or three times.** Benchmark v1, scored on this set, measures the scope gate (n=62) plus form-filling on four fields with n between 6 and 12. It cannot say anything at all about `metric`, `threshold`, `compare_to` or `other_city`, and the per-field Wilson intervals the script emits for those will be empty or vacuous.

This is not only a measurement problem. It is a **result**, and a more interesting one than the accuracy number: the schema was designed for a richer query space than people actually use. Real users ask "is the air bad today", "should I go for a walk", "will it be clean tomorrow". They do not ask the system to compare two cities against a threshold. That belongs in the Discussion chapter, and it has a design consequence — several fields exist to serve questions nobody asks.

### F5. At n = 20 only one field yields a computable agreement statistic

Within the 20-question second-annotation sample, `in_scope` has 20 filled cells and 2 distinct values. Every other field has between 0 and 5 filled cells. `annotator_agreement.py` handles this correctly and will print `n/a (no variation)` — the script is well built and its docstring already warns about small-sample kappa — but the practical result is **one usable kappa and eleven blank rows**.

So the plan recorded as "kappa on 20 items" delivers an agreement figure for the scope decision and nothing else. That should be known before anyone spends an evening annotating.

Precision, assuming roughly 90% agreement and a two-thirds in-scope base rate:

| Design | kappa (in_scope) | Approx. 95% interval |
|---|---|---|
| 20 items, 18 agree | 0.78 | 0.48 to 1.00 |
| 20 items, 19 agree | 0.89 | 0.68 to 1.00 |
| 62 items, 56 agree | 0.78 | 0.62 to 0.95 |
| 62 items, 59 agree | 0.89 | 0.77 to 1.00 |

At 20 items the interval spans "moderate" to "almost perfect", which is close to saying nothing. At 62 it is tight enough to report.

### F6. The 62 questions are already a development set

On 2 November all 62 were run through the real pipeline, every output was read, 27 problems were catalogued in seven groups, and code fixes were made in response. Whether or not those fixes touched the router, **every item and its failure mode has been seen and acted on.** Freezing this set now and calling the resulting number a test score would be scoring on data that has been tuned against. The leak is real even though the 2 November fixes were deliberately kept code-only.

---

## 2. What this means for the freeze decision

The open question was recorded as: freeze v1 now, or treat the 62 as a development set.

F6 settles it on its own: **they are already a development set.** The only question left is what the test set is.

There is a second, independent reason to reach the same answer. Groups 2 to 7 from the 2 November run need router, schema or prompt changes — a nullable `city`, forecast "when will it improve" questions routed properly, `in_scope` false paired with a clarify, location words handled rather than refused. Several of those **change the gold label itself**, not just the system's output. If Kiran annotates now and the schema changes next week, part of her work is thrown away and guide v2 needs a v3.

That gives a hard ordering constraint:

> **Change the schema first. Freeze the schema. Then annotate. Then score.**

Doing it in the other order wastes the annotators' time, which is the scarcest resource here.

---

## 3. Recommendation

A five-step plan. Steps 1 and 2 are Aftab's; 3 and 4 are the team's; 5 is mine.

**Step 1 — decide the groups 2 to 7 changes and freeze the schema.** These are the deferred router and prompt changes. Once decided, nothing about the form shape may change again before submission. I can draft the schema and prompt changes for review as soon as the direction is set.

**Step 2 — collect a fresh question set, in two clearly separated parts.**

- **Part A, naturalistic (the headline set).** A second batch from classmates, collected exactly as the first was, with no steering. Target 60 or more. This is what the benchmark result is reported on, because it is what people actually ask. The E4 study will also produce 50 to 150 typed questions from people who have never seen the system; those are the most naturalistic items available and should be kept, but they are shaped by three prescribed tasks, so they belong as a labelled supplement, not mixed into Part A.
- **Part B, schema coverage (clearly constructed).** A small set written deliberately to exercise `metric`, `threshold`, `compare_to` and `other_city`. Reported separately and labelled as constructed, never pooled with Part A. Without it those four fields have no evidence at all; with it pooled into Part A, the headline number is inflated by questions nobody would ask.

On size: at n = 62 a 90% result carries a Wilson interval of about ±7.5 points. At n = 100 it is ±6. The gain from pushing past 100 is small, so 60 to 100 naturalistic items is the sensible target.

**Step 3 — annotation, by people who have not seen the draft.** Kiran annotates the whole fresh set independently. Tehreem independently annotates a subsample — **all of the in-scope items, not a flat 20**, because the out-of-scope rows cost nothing to agree on and carry no form fields. Neither sees the draft, Aftab's file, or the selection document.

**Step 4 — adjudication, documented.** Aftab resolves disagreements by applying the written guide, recording for each one the rule that settled it. Where the guide is silent, that is a guide gap: fix the guide, and have both annotators re-decide that item. Adjudication by rule is legitimate even from a contaminated reader, because it is rule-application rather than judgement, but only if each decision is written down.

**Step 5 — score once, and report what the design can support.**

- The scope gate, n = 60 to 100, with a Wilson interval. This is the solid number.
- Form fields, per field, with counts first and intervals second, and an explicit statement for any field with n below about 10 that no claim is made.
- Language split with a Newcombe interval, and the honest caveat that at these sizes **only a gap of roughly 20 points or more is distinguishable from zero.** An English-minus-Roman-Urdu difference smaller than that cannot be called a finding either way.
- Inter-annotator kappa (Kiran vs Tehreem) on the in-scope items.

**And one bonus result.** Keep the Claude draft. Agreement between the draft and the human gold, computed on the first 62, is a real and publishable secondary finding: *how well does a language model reproduce human form annotations on this task?* It costs one extra run of `annotator_agreement.py` and turns a methodological slip into a contribution. It must be reported as model-versus-human agreement and never as inter-annotator agreement.

### What the report must say either way

Benchmark v0 (the 90-item development set, 90.0% [83.3, 95.6]) is unaffected by all of this and stands. The 62 classmate questions become **development data**, and that is how they should be described in Chapter 3 and Chapter 5 — including the 35% out-of-scope and 60% Roman Urdu composition, which are good findings about what users ask and do not depend on the labels being gold.

### If there is no time for the full plan

The minimum that is still honest: keep the 62 as a development set, have **one** uncontaminated person (Kiran or Tehreem) annotate all 62 independently, use that as gold, report the Claude-draft agreement as a secondary result, and state in the limitations that the gold set is single-annotated with no second rater. That is weaker than the plan above but it is defensible. What is **not** defensible is scoring against the draft and calling the result an accuracy figure.

---

## 4. The one change I recommend making immediately

Harden the guard in `score_benchmark_v1.py` so it compares contents rather than file names. A copy of the draft under any name should be refused. Proposed behaviour:

- Compute a hash of the gold file's **label columns only** (so that reordering rows or editing a question's text does not hide a copy).
- Compare against the same hash of every `*DRAFT*` file in the benchmark directory.
- Refuse with a clear message if they match, and keep the existing name-based check as a second line of defence.

This is additive, cannot change any score, and closes the hole that let an unreviewed draft reach the gold slot in the first place.

---

## 5. Decisions needed from Aftab

1. Treat the 62 as a development set and collect a fresh test set? *(Recommended: yes. F6 makes the alternative indefensible.)*
2. Go ahead with the groups 2 to 7 schema and router changes before any annotation? *(Recommended: yes, and I can draft them.)*
3. Ask Kiran and Tehreem to own the annotation, as set out in step 3? *(Recommended: yes; it is the only route to uncontaminated gold, and it distributes contributions.)*
4. Commission Part B, the constructed schema-coverage set? *(Recommended: yes, kept separate; without it four fields have no evidence.)*
5. May I harden the scoring guard now? *(Recommended: yes; it is additive and independent of everything else.)*

### Cost

Kiran roughly two to three hours for a full set; Tehreem roughly one hour for the in-scope subsample; Aftab roughly one hour adjudicating. Collection of the fresh batch runs in parallel and took two days last time. Against a 28 November submission this fits, provided steps 1 and 2 start within the next few days. The same work after the report is drafted would mean rewriting Chapter 5 and Chapter 7.

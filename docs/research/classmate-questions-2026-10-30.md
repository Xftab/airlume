# Classmate questions, collected 30 October 2026

62 unique questions from three classmates, written blind: none had seen the app
or its question format, which is the point of the exercise (`docs/benchmark/classmate-questions.md`).
Raw questions: `airlume/eval/benchmark/classmate-raw-2026-10-30.jsonl`.
Triage buckets: `airlume/eval/benchmark/scope-triage-2026-10-30.json`.

The raw file carries no `expected` form and no class label. The annotator guide
requires the first and second annotators to fill the form independently, and a
pre-filled suggestion would anchor both, so the triage below lives in a separate
file and annotators must not work from it.

## What they asked for

| Bucket | n | Share |
|---|---:|---:|
| In scope today | 26 | 42% |
| In scope only because of the graded-response module | 12 | 19% |
| Needs a clarifying question | 2 | 3% |
| **In scope, total** | **40** | **65%** |
| Out: weather (rain, sunrise, "is it rainy") | 8 | 13% |
| Out: causes of smog, or the effect of an intervention | 6 | 10% |
| Out: medical effects and personal diagnosis | 3 | 5% |
| Out: beyond the 24-48 h forecast horizon | 2 | 3% |
| Out: unmonitored place | 1 | 2% |
| Out: general knowledge (smog vs fog) | 1 | 2% |
| Out: indoor air | 1 | 2% |
| **Out of scope, total** | **22** | **35%** |

## Three findings worth reporting

### 1. Benchmark v0 under-represents refusal by about three and a half times

v0 carries 7 `out_of_scope` items in 70, 10%. Real users produced 35%. The
single most common thing a first-time user asks Airlume is something it is
designed not to answer, and the benchmark barely tests that path. Since a wrong
refusal and a wrong answer are both failures, and the refusal path is the one
most exercised in practice, v1 should carry an out-of-scope share close to the
observed 35% rather than v0's 10%.

### 2. Benchmark v0 badly under-weights Roman Urdu

| Set | Roman Urdu | English |
|---|---:|---:|
| Classmates (30 Oct) | 37 / 62, 60% | 25 / 62, 40% |
| Benchmark v0 | 10 / 70, 14% | 60 / 70, 86% |

The project claims English and Roman Urdu as equal first-class inputs, and the
users it was built for wrote Roman Urdu more often than English. v0's 14% was
set by the team's own writing habits, not by how the target users type. Any
accuracy figure from v0 is therefore weighted towards the easier language, and
the 88.9% headline should be read with that caveat until v1 is scored. v1 should
be stratified by language so the two are reported separately with their own
intervals, rather than pooled into one number that hides a gap.

### 3. The graded-response module was independently validated

19% of the questions — twelve of them — are health-advice questions: should I
wear a mask, should I go outside, should I walk, what precautions for children
and the elderly. Every one of those is answerable only because of the graded
response built on 29 October, and one of them ("What precautions should children
and elderly people take during smog?") maps exactly onto its `vulnerable_groups`
field. The module was specified before these questions were collected, so this
is independent confirmation that it addresses a real demand rather than an
assumed one. It is also the difference between 46% and 65% in-scope coverage.

## What the out-of-scope cluster suggests

Weather is the largest single bucket. Eight questions ask about rain, sunrise or
whether it will be rainy — people approach an air-quality app as a weather app.
The project already holds ERA5 weather history and uses it as model input, so
the data exists, but answering weather questions is outside the stated scope and
should stay there: the refusal is correct and the honest fix is wording, not
features. Three questions ask about "my location", "my home" or "my village".
The app has no geolocation and refuses unmonitored places by design rule 6, so
two become clarifying questions and the village becomes a refusal.

A worthwhile improvement, within scope and cheap: when a refusal fires, say what
Airlume *can* answer instead of only what it cannot. "I can't tell you when it
will rain, but I can tell you the air quality in Lahore right now" converts a
dead end into a usable turn, and would improve the experience on a third of
first questions.

## Limitations

Three contributors, all data-science students at the same university, all
recruited by one team member. They are not a random sample of Lahore residents
and are more technical than a general user. The 60% Roman Urdu share in
particular may reflect these three people rather than the population, and the
sample is far too small to attach an interval to any of these proportions. What
the exercise supports is the direction of the gaps — too few refusals, too
little Roman Urdu — not their exact size. Two contributors numbered their
questions and one repeated an item verbatim ("Is there any chance of rain?"),
which was recorded once.

## Next steps

1. First annotation of all 62 by Aftab, filling the ViewIntent form per the annotator guide.
2. Second annotation of 20 by Kiran or Tehreem, blind, for Cohen's kappa per field (Item 12).
3. Merge with v0, rebalance so out-of-scope sits near 35% and Roman Urdu near half, freeze as v1 (Item 14).
4. Score once, with confidence intervals, reported separately by language.

# Benchmark

Two files, frozen once Phase 3 tuning begins (append-only after that, with a dated note here).

- `questions.jsonl` — 60 single English questions across ten classes, plus 10 Roman-Urdu items (`lang: ur-Latn`).
- `conversations.jsonl` — 20 two-turn items; the second turn is scored given the first turn's form as context.

Each item carries the fields that **matter for its class** in `expected`. Scoring (`eval/run_e1.py`):

- A field matches by exact value after normalisation (case, whitespace; `time` compares `time.label`, `date` compares `time.date`).
- `clarify: true` matches any non-empty clarification; `in_scope: false` matches `in_scope == false`.
- A question **passes** when every expected field matches. Per-field accuracy is also reported.
- Items with a `note` have an accepted alternative described in the note; the runner applies the documented alternatives.
- The `author` column records who wrote each item (`author` = project team, `classmate` = written blind). Target: half the English items from classmates before the freeze.

Status: **draft v0 (14 Oct 2026), not yet frozen.** Classmate items and a second annotator (kappa on 20 items) are pending.

**6 Nov 2026.** Schema and prompt frozen at v5 (`docs/benchmark/v1-packet-2026-11-06.md`). This set (v0) and the 62 classmate questions of 30 Oct are **development data**; v0's figure stands as recorded under prompt v4 and is not re-scored under v5. Benchmark v1 is a fresh naturalistic set (Part A, to be collected) plus `partB-constructed-2026-11-06.jsonl` (30 constructed schema-coverage questions, labels by humans only, reported separately). Annotator guide version 3.

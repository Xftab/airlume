"""Experiment A: does a typed form match code and SQL on accuracy while removing
invented numbers and injection, in English and Roman Urdu?

Protocol: docs/research/expA-protocol-2026-11-20.md (fixed before any run).

Three arms answer the same questions over the same frozen snapshot of the archive:

- form  Airlume as it is: the model fills the ViewIntent form (prompt v5, frozen),
        code resolves, queries and writes the answer.
- code  the model writes Python over the snapshot tables (VayuChat style).
- sql   the model writes one SQL query over the snapshot tables (text-to-SQL style).

Design rule 1 still holds for the app: the language model never writes SQL or code
at runtime. The code and SQL arms exist only here, as experimental controls. They run
offline, on a copy of the data, through `sandbox.py` (a separate process, no secrets in
its environment, read-only data, time limits, allow-listed operations). Nothing in the
app, `nl/` or `pipeline/` may import this package; `tests/test_expA_isolation.py`
enforces that.

Modules
- snapshot.py   freeze the archive at a cutoff; write the shifted copy for the
                invented-number test; manifest with hashes
- sandbox.py    run one model-written SQL query or Python snippet, locked down
- prompts.py    the code and SQL arm prompts (versioned, hashed into the cache key)
- generate.py   ask the model (Groq, same models and settings as the form arm); no execution
- formarm.py    run the form arm exactly as the app does (resolve, store, answer)
- normalize.py  turn each arm's output into one comparable Answer
- reference.py  helpers the annotators use to write gold answers, independent of the app
- score.py      correctness, refusals, invented numbers, blocked actions, intervals
- agreement.py  agreement between two annotators' gold calls, on the executed answers
- items.py      load and check question files
- run.py        the four steps: gold, generate, execute, score (resumable)

Command line: scripts/expA_run.py. How to run: README.md in this folder.
"""

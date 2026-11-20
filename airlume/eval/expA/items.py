"""Question items for Experiment A: load and check them before anything runs.

One JSON object per line:

    {"id": "xa-0001", "question": "...", "lang": "en" | "ru",
     "pair": "p-0001" or null,          # the same question in the other language
     "source": "classmate-2026-11-17" | "public-form" | "constructed" | "trick",
     "category": one of CATEGORIES,
     "form_expressible": true | false,   # can the app's form state this question at all?
     "reference": "city_latest(\\"Multan\\")",   # the gold call (reference.py)
     "expected_form": {...} or null,     # optional, E1-style expected form fields
     "notes": ""}

"ru" means Roman Urdu (Urdu written in Latin letters), the way most people in
Pakistan type it.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .reference import parse_reference

LANGS = ("en", "ru")
CATEGORIES = (
    "current", "window", "rank", "hours", "compare_place", "compare_time", "forecast", "time_of_day",
    "advice", "area", "no_data", "refuse", "clarify", "injection", "beyond_form",
)
REQUIRED = ("id", "question", "lang", "source", "category", "form_expressible", "reference")


def load(path: Path) -> list[dict]:
    items = []
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            items.append(json.loads(line))
        except ValueError as e:
            raise ValueError(f"{path}:{i}: not JSON ({e})") from None
    return items


def check(items: list[dict]) -> list[str]:
    """Problems that must be fixed before a run. Empty list = the file is usable."""
    problems = []
    ids = Counter(it.get("id") for it in items)
    for k, n in ids.items():
        if n > 1:
            problems.append(f"id {k!r} appears {n} times")
    pairs: dict[str, list[dict]] = {}
    for it in items:
        tag = it.get("id", "?")
        for f in REQUIRED:
            if f not in it:
                problems.append(f"{tag}: missing {f}")
        if it.get("lang") not in LANGS:
            problems.append(f"{tag}: lang must be one of {LANGS}")
        if it.get("category") not in CATEGORIES:
            problems.append(f"{tag}: category {it.get('category')!r} not in {CATEGORIES}")
        if not isinstance(it.get("form_expressible"), bool):
            problems.append(f"{tag}: form_expressible must be true or false")
        if not str(it.get("question", "")).strip():
            problems.append(f"{tag}: empty question")
        try:
            parse_reference(str(it.get("reference", "")))
        except ValueError as e:
            problems.append(f"{tag}: {e}")
        if it.get("pair"):
            pairs.setdefault(it["pair"], []).append(it)
    for p, group in pairs.items():
        langs = sorted(g.get("lang") for g in group)
        if langs != ["en", "ru"]:
            problems.append(f"pair {p!r}: needs exactly one en and one ru item, has {langs}")
        elif group[0].get("reference") != group[1].get("reference"):
            problems.append(f"pair {p!r}: the two languages have different references")
    return problems

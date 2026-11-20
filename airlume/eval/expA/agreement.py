"""Agreement between two annotators' gold calls, measured on the executed answers.

Each annotator fills `gold-annotation-template.csv` alone (columns id, question,
annotator, reference, form_expressible, category, notes). Two different calls that give
the same answer on the snapshot agree, for example `latest("Multan")` and
`city_latest("Multan")`; the same call written two ways is not a disagreement.

Reported: percent agreement on the full answer (kind, place, number within tolerance)
and Cohen's kappa on the kind alone (answer, no_data, refuse, clarify), plus every
disagreement for the adjudicator.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from .normalize import canon
from .reference import Gold, Reference, evaluate_reference
from .score import tolerance


def read_annotations(path: Path) -> dict[str, dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return {r["id"].strip(): r for r in rows if r.get("id", "").strip() and r.get("reference", "").strip()}


def same_answer(a: Gold, b: Gold) -> bool:
    if a.kind != b.kind:
        return False
    if a.kind != "answer":
        return True
    if canon(a.place) != canon(b.place) and not ({canon(a.place)} & {canon(p) for p in b.tie_places}):
        return False
    tol = tolerance(a.unit)
    if (a.value is None) != (b.value is None) or (a.value is not None and abs(a.value - b.value) > tol):
        return False
    if (a.previous is None) != (b.previous is None):
        return False
    return a.previous is None or abs(a.previous - b.previous) <= tol


def cohen_kappa(x: list[str], y: list[str]) -> float | None:
    n = len(x)
    if n == 0:
        return None
    po = sum(1 for a, b in zip(x, y) if a == b) / n
    cx, cy = Counter(x), Counter(y)
    pe = sum(cx[k] * cy[k] for k in set(cx) | set(cy)) / (n * n)
    return None if pe == 1 else (po - pe) / (1 - pe)


def agreement(ref: Reference, a_path: Path, b_path: Path) -> dict:
    a_rows, b_rows = read_annotations(a_path), read_annotations(b_path)
    ids = sorted(set(a_rows) & set(b_rows))
    agree, kinds_a, kinds_b, disagreements = 0, [], [], []
    for iid in ids:
        out = {}
        for side, rows in (("a", a_rows), ("b", b_rows)):
            try:
                out[side] = evaluate_reference(rows[iid]["reference"], ref)
            except (ValueError, KeyError, TypeError) as e:
                out[side] = Gold("invalid", place=str(e)[:120])
        ga, gb = out["a"], out["b"]
        kinds_a.append(ga.kind)
        kinds_b.append(gb.kind)
        if ga.kind != "invalid" and gb.kind != "invalid" and same_answer(ga, gb):
            agree += 1
        else:
            disagreements.append({"id": iid, "question": a_rows[iid].get("question", ""),
                                  "a": a_rows[iid]["reference"], "b": b_rows[iid]["reference"],
                                  "a_answer": ga.to_dict(), "b_answer": gb.to_dict()})
    return {"n_both": len(ids), "only_a": sorted(set(a_rows) - set(b_rows)),
            "only_b": sorted(set(b_rows) - set(a_rows)), "agree": agree,
            "percent": (100 * agree / len(ids)) if ids else None,
            "kappa_kind": cohen_kappa(kinds_a, kinds_b), "disagreements": disagreements}

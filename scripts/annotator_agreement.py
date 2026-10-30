"""Per-field agreement and Cohen's kappa between two filled annotation sheets.

    python scripts\\annotator_agreement.py sheet-aftab.csv sheet-kiran.csv

Reports, for every form field, raw agreement and Cohen's kappa over the rows
both annotators filled, then lists every disagreement so the two of you can work
through them and record the agreed form and the reason (annotator guide,
"Reporting").

Reading kappa: below 0.20 is poor, 0.21-0.40 fair, 0.41-0.60 moderate,
0.61-0.80 substantial, above 0.80 almost perfect (Landis and Koch 1977). The
thresholds are a convention, not a law, and kappa is unstable on small samples -
with 20 items a single flipped label moves it noticeably, so report the number
with the count beside it and do not lean on the adjective.

Kappa is undefined when both annotators used one value for every row: there is
no variation for chance agreement to be computed against, so pe = 1 and the
formula divides by zero. That is reported as "n/a (no variation)" with the raw
agreement, which is the honest thing to show - it means the field was never in
question, not that agreement was bad.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

FIELDS = ["in_scope", "metric", "city", "area", "time_label", "aggregation",
          "threshold", "compare_to", "other_city", "view", "camera"]
# Free-text fields: compared on whether a clarification was asked for at all,
# because two annotators will never word one identically.
PRESENCE_ONLY = {"clarify"}


def norm(v: str | None) -> str:
    return " ".join((v or "").strip().lower().split())


def kappa(pairs: list[tuple[str, str]]) -> tuple[float | None, float]:
    """Cohen's kappa and raw agreement for a list of (annotator_a, annotator_b)."""
    n = len(pairs)
    if n == 0:
        return None, 0.0
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in set(ca) | set(cb))
    if abs(1 - pe) < 1e-12:
        return None, po
    return (po - pe) / (1 - pe), po


def label(k: float | None) -> str:
    if k is None:
        return "n/a (no variation)"
    for lo, name in ((0.80, "almost perfect"), (0.60, "substantial"),
                     (0.40, "moderate"), (0.20, "fair")):
        if k > lo:
            return f"{k:+.3f}  {name}"
    return f"{k:+.3f}  poor"


def load(path: str) -> dict[str, dict[str, str]]:
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8-sig")))
    return {r["id"]: r for r in rows if any(
        (r.get(k) or "").strip() for k in ("in_scope", "metric", "view", "time_label", "clarify"))}


def main(path_a: str, path_b: str) -> int:
    A, B = load(path_a), load(path_b)
    shared = sorted(set(A) & set(B))
    if not shared:
        sys.exit("No question is annotated in both sheets, so there is nothing to compare.")
    print(f"annotator A: {Path(path_a).name}  ({len(A)} rows annotated)")
    print(f"annotator B: {Path(path_b).name}  ({len(B)} rows annotated)")
    print(f"compared on the {len(shared)} rows both filled.\n")

    print(f"{'field':<14} {'agree':>7}  kappa")
    print("-" * 46)
    disagreements: list[tuple[str, str, str, str]] = []
    for f in FIELDS + sorted(PRESENCE_ONLY):
        if f in PRESENCE_ONLY:
            pairs = [(str(bool(norm(A[i].get(f)))), str(bool(norm(B[i].get(f))))) for i in shared]
        else:
            pairs = [(norm(A[i].get(f)), norm(B[i].get(f))) for i in shared]
        k, po = kappa(pairs)
        print(f"{f:<14} {po:>6.0%}   {label(k)}")
        for i, (a, b) in zip(shared, pairs):
            if a != b:
                disagreements.append((i, f, a or "(blank)", b or "(blank)"))

    print(f"\n{len(disagreements)} disagreement(s) to resolve by discussion:")
    if not disagreements:
        print("  none")
    else:
        current = None
        for qid, f, a, b in disagreements:
            if qid != current:
                current = qid
                q = A[qid].get("question", "")
                print(f"\n  [{qid}] {q}")
            print(f"      {f:<13} A={a!r}  B={b!r}")
    print("\nRecord the agreed form and the reason for each, per the annotator guide. "
          "The resolved forms become the gold set; the test set is frozen afterwards "
          "and never tuned on.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: annotator_agreement.py <sheet-a.csv> <sheet-b.csv>")
    raise SystemExit(main(sys.argv[1], sys.argv[2]))

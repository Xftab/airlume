r"""Score the router against the human-annotated benchmark v1 (classmate questions).

    python scripts\score_benchmark_v1.py GOLD.csv --model stub
    python scripts\score_benchmark_v1.py GOLD.csv --model openai/gpt-oss-120b

GOLD.csv is the annotation sheet after the humans have finished: every row labelled,
checked by scripts\check_annotation.py, second annotation done and disagreements
settled, file frozen (do not edit it after the first scoring). Rules this script
enforces so the number means something:

* Refuses a sheet with unlabelled rows, or one that fails the conformance check.
* Refuses any file whose name contains DRAFT unless --allow-draft, and then prints a
  banner on every output line group: a draft written by a model is not gold, and a
  model scored against labels written by a model is not a result.
* Refuses a file whose LABEL CELLS are identical to any *DRAFT* sheet beside it, whatever
  it has been renamed to. The name check alone is not enough: on 4 Nov 2026 a copy of the
  model's draft sat in the gold slot under a human's name and would have been scored.
  The comparison ignores row order and the question text, so only the labels matter.
* Scores ONCE per (gold file contents, model): the scorecard name carries a hash of the
  gold file, and an existing scorecard is not overwritten unless --again. Tuning the
  prompt against the benchmark and re-scoring is how a test set stops being a test set.
* A router failure (rate limit, network) is not counted as a wrong answer: the run stops,
  nothing is written, finished items are cached, re-run the same command.

What is scored. A blank cell in the sheet means "not required for this question", so
only filled cells are compared (same rule as the v0 runner, `airlume.eval.run_e1`). In
scope: yes/no -> in_scope true/false. A question the annotator marked as needing a
clarification expects a non-empty clarify. Everything else is compared field by field
with the v0 matching rules (area prefix match, time label, symmetric city pair, ...).
A question PASSES when every expected field matches.

Reported, all with Wilson 95% intervals (they stay honest at 0% and 100%, unlike the
bootstrap): overall; by language (en, ur-Latn); the scope decision alone (in or out);
per field with n; and the English versus Roman Urdu gap with a Newcombe interval.
Every failing item is listed with what was expected and what the router produced.

Output: data\eval\benchmark_v1_<model>_<gold hash>.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from airlume.eval import run_e1  # noqa: E402
from airlume.nl.schema import ViewIntent  # noqa: E402
from check_annotation import check_row  # noqa: E402

OUT = ROOT / "data" / "eval"


def label_cells(path: Path) -> tuple[dict[str, dict[str, str]], set[str]] | None:
    """Every label cell in a sheet, keyed by question id.

    Labels are the columns from in_scope onwards; id and question text are not
    labels. Returns None for a file that is not an annotation sheet.
    """
    try:
        rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    except (OSError, UnicodeDecodeError, csv.Error):
        return None
    if not rows:
        return None
    cols = list(rows[0].keys())
    if "in_scope" not in cols or "id" not in cols:
        return None
    labels = cols[cols.index("in_scope"):]
    cells = {(r.get("id") or ""): {c: (r.get(c) or "").strip() for c in labels} for r in rows}
    return cells, set(labels)


def same_labels(a, b) -> bool:
    """True when two sheets carry the same label in every shared cell.

    Row order and question wording are ignored, so a reordered or lightly edited
    copy of a draft is still recognised as that draft.
    """
    if a is None or b is None:
        return False
    (rows_a, labels_a), (rows_b, labels_b) = a, b
    shared = labels_a & labels_b
    if not shared or set(rows_a) != set(rows_b):
        return False
    return all(rows_a[i][c] == rows_b[i][c] for i in rows_a for c in shared)


def draft_twin(gold: Path):
    """The *DRAFT* sheet beside gold whose labels are identical to it, if any."""
    mine = label_cells(gold)
    if mine is None:
        return None
    for other in sorted(gold.parent.glob("*.csv")):
        if other.resolve() == gold.resolve() or "draft" not in other.name.lower():
            continue
        if same_labels(mine, label_cells(other)):
            return other
    return None
Z = 1.959964


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """p1 - p2 with Newcombe's hybrid score interval (built from the two Wilson intervals)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def expected_from_row(r: dict[str, str]) -> dict:
    g = lambda k: (r.get(k) or "").strip()
    scope = g("in_scope").lower()
    if scope == "no":
        return {"in_scope": False}
    exp: dict = {"in_scope": True}
    if g("clarify"):
        exp["clarify"] = True
        return exp
    for col, key in (("metric", "metric"), ("city", "city"), ("area", "area"),
                     ("time_label", "time"), ("time_date", "date"), ("aggregation", "aggregation"),
                     ("compare_to", "compare_to"), ("other_city", "other_city"),
                     ("view", "view"), ("camera", "camera")):
        if g(col):
            exp[key] = g(col)
    if g("threshold"):
        exp["threshold"] = int(g("threshold"))
    if g("time_start"):
        exp["time_start"] = g("time_start")
    if g("time_end"):
        exp["time_end"] = g("time_end")
    return exp


def field_ok(field: str, expected, intent: ViewIntent) -> bool:
    if field in ("time_start", "time_end"):
        return intent.model_dump()["time"].get(field.split("_")[1]) == expected
    return run_e1.field_matches(field, expected, intent)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gold")
    ap.add_argument("--model", default="stub")
    ap.add_argument("--allow-draft", action="store_true")
    ap.add_argument("--again", action="store_true", help="overwrite an existing scorecard for this gold file and model")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)

    gp = Path(a.gold)
    draft = "draft" in gp.name.lower()
    if draft and not a.allow_draft:
        sys.exit(f"{gp.name} is a DRAFT. A draft written by a model is not gold; use the human-annotated "
                 "file, or pass --allow-draft for a dry run (nothing is a result).")
    twin = None if draft else draft_twin(gp)
    if twin is not None and not a.allow_draft:
        sys.exit(f"{gp.name} has exactly the same labels as {twin.name}: it is that draft under "
                 "another name, so scoring it would be a model graded against a model's labels. "
                 "Annotate the sheet by hand first, or pass --allow-draft for a dry run "
                 "(nothing is a result).")
    if twin is not None:
        draft = True
    raw = gp.read_bytes()
    gold_hash = hashlib.sha256(raw).hexdigest()[:10]
    rows = list(csv.DictReader(gp.open(encoding="utf-8-sig", newline="")))
    unlabelled = [r.get("id", "?") for r in rows if not (r.get("in_scope") or "").strip()]
    if unlabelled:
        sys.exit(f"{len(unlabelled)} of {len(rows)} rows have no in_scope label ({', '.join(unlabelled[:8])} ...). "
                 "Finish the annotation first.")
    bad = [(r.get("id"), m) for i, r in enumerate(rows, 2) for m in check_row(r, i)]
    if bad:
        for i, m in bad[:10]:
            print(f"{i}: {m}")
        sys.exit(f"{len(bad)} conformance problem(s); run scripts\\check_annotation.py and fix them first.")

    out_path = OUT / f"benchmark_v1_{a.model.replace('/', '_')}_{gold_hash}.json"
    if out_path.exists() and not a.again and not a.no_write:
        sys.exit(f"{out_path.name} already exists: this gold file has been scored with this model. "
                 "Scoring once is the rule; pass --again only for a re-run you will label as such.")

    banner = "  *** DRAFT LABELS, NOT GOLD: DRY RUN, NOT A RESULT ***" if draft else ""
    print(f"{len(rows)} questions, gold file hash {gold_hash}, model {a.model}{banner}")

    items = []
    errors = []
    for i, r in enumerate(rows, 1):
        if i % 10 == 0 or i == 1:
            print(f"  {i}/{len(rows)} ...", flush=True)
        exp = expected_from_row(r)
        try:
            intent, _ = run_e1.route_once(r["question"], a.model, None, True)
        except Exception as e:  # noqa: BLE001
            errors.append((r["id"], f"{type(e).__name__}: {str(e)[:140]}"))
            continue
        fields = {f: field_ok(f, v, intent) for f, v in exp.items()}
        items.append({"id": r["id"], "lang": r.get("lang") or "en", "question": r["question"],
                      "expected": exp, "got": intent.model_dump(exclude_defaults=True),
                      "fields": fields, "pass": all(fields.values())})
    if errors:
        for e in errors[:8]:
            print("  router failure:", e)
        sys.exit(f"{len(errors)} router call(s) failed (not counted as wrong answers). Nothing written. "
                 "Re-run the same command; finished items are cached.")

    def block(sel):
        k = sum(1 for x in sel if x["pass"])
        lo, hi = wilson(k, len(sel))
        return {"n": len(sel), "pass": k, "rate": round(k / len(sel), 4) if sel else None,
                "wilson95": [round(lo, 4), round(hi, 4)]}

    langs = sorted({x["lang"] for x in items})
    by_lang = {l: block([x for x in items if x["lang"] == l]) for l in langs}
    scope_items = [{"pass": x["fields"]["in_scope"], "lang": x["lang"]} for x in items]
    per_field: dict[str, list[bool]] = defaultdict(list)
    for x in items:
        for f, ok in x["fields"].items():
            per_field[f].append(ok)
    pf = {}
    for f, v in sorted(per_field.items()):
        k = sum(v)
        lo, hi = wilson(k, len(v))
        pf[f] = {"n": len(v), "correct": k, "acc": round(k / len(v), 4), "wilson95": [round(lo, 4), round(hi, 4)]}
    gap = None
    if "en" in by_lang and "ur-Latn" in by_lang:
        e, u = by_lang["en"], by_lang["ur-Latn"]
        d, lo, hi = newcombe_diff(e["pass"], e["n"], u["pass"], u["n"])
        gap = {"en_minus_ur_latn": round(d, 4), "newcombe95": [round(lo, 4), round(hi, 4)]}

    report = {"date": str(date.today()), "model": a.model, "gold_file": gp.name, "gold_hash": gold_hash,
              "draft_labels_not_gold": draft, "n": len(items), "overall": block(items), "by_language": by_lang,
              "scope_decision": block(scope_items), "per_field": pf, "language_gap": gap,
              "failures": [{k: x[k] for k in ("id", "lang", "question", "expected", "got")}
                           for x in items if not x["pass"]]}

    o = report["overall"]
    print(f"\nOverall: {o['pass']}/{o['n']} = {o['rate']:.1%}  (Wilson 95% {o['wilson95'][0]:.1%} to {o['wilson95'][1]:.1%}){banner}")
    for l, b in by_lang.items():
        print(f"  {l:<8} {b['pass']}/{b['n']} = {b['rate']:.1%}  [{b['wilson95'][0]:.1%}, {b['wilson95'][1]:.1%}]")
    s = report["scope_decision"]
    print(f"Scope decision alone: {s['pass']}/{s['n']} = {s['rate']:.1%}  [{s['wilson95'][0]:.1%}, {s['wilson95'][1]:.1%}]")
    if gap:
        print(f"English minus Roman Urdu: {gap['en_minus_ur_latn']:+.1%}  (Newcombe 95% {gap['newcombe95'][0]:+.1%} to {gap['newcombe95'][1]:+.1%})")
    print("Per field (correct/n):  " + ", ".join(f"{f} {v['correct']}/{v['n']}" for f, v in pf.items()))
    print(f"{len(report['failures'])} failing item(s) listed in the scorecard.")
    if a.no_write:
        print("(nothing written)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"written {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

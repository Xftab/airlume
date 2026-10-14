"""E1: score a router against the frozen benchmark.

    python -m airlume.eval.run_e1 --model stub
    python -m airlume.eval.run_e1 --model openai/gpt-oss-120b --runs 3

For each item the router fills a ViewIntent; each expected field is compared
to the form. Reports pass rate and per-field accuracy with 95% bootstrap
confidence intervals, run-to-run consistency (same form on every run), and
per-class pass rates. Results go to data/eval/e1_<model>_<date>.json.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from airlume.config import ROOT
from airlume.nl import router, stub_router
from airlume.nl.schema import ViewIntent

BENCH = ROOT / "airlume" / "eval" / "benchmark"
OUT = ROOT / "data" / "eval"


def load(name: str) -> list[dict]:
    return [json.loads(l) for l in (BENCH / name).read_text(encoding="utf-8").splitlines() if l.strip()]


def norm(v):
    return v.strip().lower() if isinstance(v, str) else v


def field_matches(field: str, expected, intent: ViewIntent) -> bool:
    d = intent.model_dump()
    if field == "clarify":
        return bool(d.get("clarify")) if expected is True else norm(d.get("clarify")) == norm(expected)
    if field == "in_scope":
        return d.get("in_scope") is expected
    if field == "time":
        return d["time"]["label"] == expected
    if field == "date":
        return d["time"].get("date") == expected
    if field == "area":
        got = norm(d.get("area"))
        exp = norm(expected)
        # "Gulberg" ~ "Gulberg III": accept a prefix match on area names
        return got is not None and (got == exp or exp.startswith(got) or got.startswith(exp))
    if field in ("note", "compare_to_alt", "last_month_alt"):
        return True
    if field in ("city", "other_city") and d.get("compare_to") == "other_city":
        # "Is Karachi cleaner than Lahore?" is the same comparison either way round
        pair = {norm(d.get("city")), norm(d.get("other_city"))}
        return norm(expected) in pair
    if field == "clarify_or_other_city":
        return bool(d.get("clarify")) or norm(d.get("other_city")) == norm(expected)
    if field == "compare_to" and expected == "yesterday_or_none":
        return d.get("compare_to") in ("yesterday", "none")
    if field == "compare_to" and expected == "last_month_alt":
        return d.get("compare_to") in ("last_week", "none") or d["time"]["label"] in ("last_month", "this_month")
    return norm(d.get(field)) == norm(expected)


def score_item(expected: dict, intent: ViewIntent) -> dict[str, bool]:
    return {f: field_matches(f, v, intent) for f, v in expected.items() if f != "note"}


def bootstrap_ci(values: list[float], n: int = 2000, seed: int = 0) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(n))
    return (means[int(0.025 * n)], means[int(0.975 * n)])


def _minutes_ok(msg: str) -> bool:
    """True if Groq's retry-after is short (per-minute cap), False for the daily cap."""
    import re
    m = re.search(r"try again in ([0-9.]+)(m|s)", msg)
    return not (m and m.group(2) == "m")


def route_once(question: str, model: str, previous: dict | None, use_cache: bool):
    if model == "stub":
        return stub_router.route(question), "stub"
    r = router.route(question, model=model, previous=previous, use_cache=use_cache, allow_fallback=False)
    return r.intent, r.model


def run(model: str, runs: int) -> dict:
    # A single run may use the router cache (keyed by prompt version + question), so an
    # interrupted run resumes where it stopped. Consistency runs (runs > 1) always call live.
    use_cache = runs == 1
    singles = load("questions.jsonl")
    convs = load("conversations.jsonl")
    results = []
    items = singles + convs
    for i, item in enumerate(items, 1):
        if i % 10 == 0 or i == 1:
            print(f"  {i}/{len(items)} ...", flush=True)
        forms = []
        for _ in range(runs):
            prev = None
            if "turns" in item:
                for t in item["turns"][:-1]:
                    first, _ = route_once(t, model, None, use_cache)
                    prev = first.model_dump()
                q = item["turns"][-1]
            else:
                q = item["question"]
            try:
                intent, used = route_once(q, model, prev, use_cache)
            except Exception as e:  # noqa: BLE001 - one bad item must not end a 15-minute run
                print(f"  {item['id']}: {type(e).__name__}: {str(e)[:160]}", flush=True)
                if "rate_limit_exceeded" in str(e) and "try again in" in str(e) and not _minutes_ok(str(e)):
                    other = "openai/gpt-oss-20b" if "120b" in model else "openai/gpt-oss-120b"
                    print(f"Daily token limit reached on Groq for {model}. Re-run the same command when the "
                          f"message's retry time has passed (finished items are cached and skipped), "
                          f"or score --model {other}, which has its own limit.", flush=True)
                    raise SystemExit(2)
                intent, used = ViewIntent(in_scope=False, clarify="ROUTER_ERROR"), "error"
            if intent.context_ref and prev:
                merged = {**prev, **intent.model_dump(exclude_defaults=True), "context_ref": False}
                intent = ViewIntent.model_validate(merged)
            forms.append(intent)
        fields = score_item(item["expected"], forms[0])
        if forms[0].clarify == "ROUTER_ERROR":
            fields = {f: False for f in fields}
        consistent = all(f.model_dump() == forms[0].model_dump() for f in forms[1:])
        results.append({"id": item["id"], "class": item["class"], "lang": item.get("lang", "en"),
                        "pass": all(fields.values()), "fields": fields, "consistent": consistent,
                        "form": forms[0].model_dump()})
    passes = [1.0 if r["pass"] else 0.0 for r in results]
    per_field: dict[str, list[float]] = defaultdict(list)
    for r in results:
        for f, ok in r["fields"].items():
            per_field[f].append(1.0 if ok else 0.0)
    per_class: dict[str, list[float]] = defaultdict(list)
    for r in results:
        per_class[r["class"]].append(1.0 if r["pass"] else 0.0)
    summary = {
        "model": model, "runs": runs, "date": str(date.today()), "n": len(results),
        "pass_rate": sum(passes) / len(passes), "pass_ci95": bootstrap_ci(passes),
        "consistency": sum(1 for r in results if r["consistent"]) / len(results),
        "per_field": {f: {"acc": sum(v) / len(v), "n": len(v), "ci95": bootstrap_ci(v)} for f, v in sorted(per_field.items())},
        "per_class": {c: {"pass": sum(v) / len(v), "n": len(v)} for c, v in sorted(per_class.items())},
        "roman_urdu_pass": (lambda v: sum(v) / len(v) if v else None)([1.0 if r["pass"] else 0.0 for r in results if r["lang"] == "ur-Latn"]),
        "items": results,
    }
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="stub")
    ap.add_argument("--runs", type=int, default=1)
    a = ap.parse_args()
    s = run(a.model, a.runs)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"e1_{a.model.replace('/', '_')}_{s['date']}.json"
    out.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
    lo, hi = s["pass_ci95"]
    print(f"model={s['model']}  n={s['n']}  pass={s['pass_rate']:.1%}  (95% CI {lo:.1%}-{hi:.1%})  consistency={s['consistency']:.0%}")
    print("per class: " + ", ".join(f"{c} {v['pass']:.0%} ({v['n']})" for c, v in s["per_class"].items()))
    print("per field: " + ", ".join(f"{f} {v['acc']:.0%}" for f, v in s["per_field"].items()))
    if s["roman_urdu_pass"] is not None:
        print(f"Roman Urdu: {s['roman_urdu_pass']:.0%}")
    print(f"-> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

r"""Run the 62 classmate questions through the real pipeline and record what happens.

    python scripts\run_classmate_questions.py                 # model router (needs the key in .env)
    python scripts\run_classmate_questions.py --router stub   # rule-based router, no key, no budget

Same path as the app: route -> (follow-up merge not used; each question is single-turn)
-> resolve -> answer. For every question it writes one row: the form the router filled,
the outcome (out_of_scope, clarify, resolve_error, answered, route_error), the answer
text, and the notes the app would show. Output goes to K:\airlume_work (outside the repo,
never on C:), as CSV and as a markdown table for pasting into chat.

This is a diagnostic run, NOT benchmark scoring: there are no gold labels here. It
exists to find drawbacks. Nothing in it reads or prints the API key.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.config import ROOT  # noqa: E402
from airlume.nl import router, stub_router  # noqa: E402
from airlume.nl.answer import answer  # noqa: E402
from airlume.nl.resolve import ResolveError, resolve  # noqa: E402
from airlume.pipeline import archive  # noqa: E402
from airlume.pipeline.registry import Registry  # noqa: E402
from airlume.pipeline.store import Store  # noqa: E402

QFILE = ROOT / "airlume" / "eval" / "benchmark" / "classmate-raw-2026-10-30.jsonl"
KEYS = ("view", "city", "station", "place", "metric", "aggregation", "time", "compare_to", "compare_city")


def build_store() -> Store:
    s = Store(":memory:")
    s.upsert_readings(archive.load_all("readings"))
    s.upsert_city_hourly(archive.load_all("city_hourly"))
    s.upsert_epd_daily(archive.load_all("epd_daily"))
    s.upsert_forecasts(archive.load_all("forecasts"))
    s.delete_source("fake")
    return s


def short_form(d: dict) -> str:
    """A compact one-line view of the filled form (only fields that are set)."""
    out = {k: v for k, v in d.items() if v not in (None, "", False, [], {}) and k != "raw"}
    return json.dumps(out, ensure_ascii=False, default=str)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", choices=("stub", "model"), default="model")
    ap.add_argument("--model", default=router.PRIMARY_MODEL)
    ap.add_argument("--pace", type=float, default=18.0, help="seconds between model calls")
    ap.add_argument("--out", default=r"K:\airlume_work")
    a = ap.parse_args(argv)

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    reg = Registry.load()
    store = build_store()
    qs = [json.loads(l) for l in QFILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for i, q in enumerate(qs):
        text = q["question"]
        if a.router == "model" and i:
            time.sleep(a.pace)
        row = {"id": q["id"], "lang": q["lang"], "question": text, "router": a.router,
               "form": "", "outcome": "", "answer": "", "notes": ""}
        try:
            if a.router == "stub":
                intent = stub_router.route(text, None)
            else:
                intent = router.route(text, model=a.model, use_cache=False, allow_fallback=False).intent
        except Exception as e:  # a failed call is a result, not a crash
            row["outcome"] = f"route_error:{type(e).__name__}"
            rows.append(row)
            print(q["id"], row["outcome"])
            continue
        row["form"] = short_form(intent.model_dump())
        if not intent.in_scope:
            row["outcome"] = "out_of_scope"
            row["answer"] = "I can only answer about air quality in Pakistan's monitored cities."
        elif intent.clarify:
            row["outcome"] = "clarify"
            row["answer"] = intent.clarify
        else:
            try:
                rq = resolve(intent, reg)
                row["answer"] = answer(rq, store, reg)
                row["notes"] = " | ".join(rq.notes)
                row["outcome"] = "answered"
            except ResolveError as e:
                row["outcome"] = "resolve_error"
                row["answer"] = str(e)
            except Exception as e:  # a crash in the answer layer is a finding
                row["outcome"] = f"answer_crash:{type(e).__name__}"
                row["answer"] = str(e)[:200]
        rows.append(row)
        print(q["id"], row["outcome"], "|", row["answer"][:90])

    stamp = time.strftime("%Y-%m-%d")
    base = out_dir / f"classmate_run_{a.router}_{stamp}"
    with open(str(base) + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(str(base) + ".md", "w", encoding="utf-8") as f:
        f.write(f"# Classmate questions, {a.router} router, {stamp}\n\n")
        f.write("| id | lang | question | outcome | form | answer |\n|---|---|---|---|---|---|\n")
        for r in rows:
            c = lambda s: str(s).replace("|", "/").replace("\n", " ")
            f.write(f"| {r['id']} | {r['lang']} | {c(r['question'])} | {r['outcome']} | {c(r['form'])} | {c(r['answer'])} |\n")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    print("\noutcomes:", counts)
    print("written", str(base) + ".csv", "and .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

r"""E6: how long does a question take from typed text to a written answer?

    python scripts\measure_latency.py                      # rule-based router, no model calls
    python scripts\measure_latency.py --router model --n 30 --model openai/gpt-oss-20b

Times the same pipeline the app runs: route -> resolve -> answer, each stage on its
own clock (time.perf_counter), over the 70 benchmark questions plus the 62 classmate
questions. The store is built the way the app builds it, in memory from the CSV
archive, and its build time is reported once because that is the cost of a cold
start, not of a question.

What it does and does not measure:

* It measures the code path and, with --router model, the model round trip. It does
  NOT measure the browser: map drawing and frames per second need a person with the
  page open (see docs/study and the E6 note in HISTORY).
* With --router model the router cache is bypassed, so every call is a real,
  uncached round trip. This spends Groq budget: one call per question, so --n caps
  it (default 30). Nothing is printed that could contain the key.
* The free Groq tier allows about 8,000 tokens a minute and one call here costs about
  2,200, so calls sent back to back hit the limit and the router sleeps and retries
  (airlume/nl/router.py, _post). The first real run (1 Nov) showed exactly that: calls
  that went straight through took 1 to 4 s, calls that waited took 15 to 18 s, and the
  median of the mixture (16 s) described the rate limit, not the model. So in model
  mode the script now waits --pace seconds between calls (default 18, outside the timed
  region), counts the rate-limit waits it still sees, and reports the calls with no
  wait separately. Quote the no-wait figure as the response time a single user sees,
  and the share of calls that waited as the cost of the free tier.
* Out-of-scope and clarify answers skip resolve and answer, as in the app, so
  they are reported in their own row and not mixed into the answered figures.

Reported per stage: n, median with a 95 percent bootstrap interval, 95th percentile
and maximum. With fewer than 20 timings the 95th percentile is the maximum, and the
output says so.

Result is written to data/eval/e6_latency_<router>_<date>[_pace<N>].json.
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import statistics
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.config import ROOT  # noqa: E402
from airlume.nl import router, stub_router  # noqa: E402
from airlume.nl.answer import answer  # noqa: E402
from airlume.nl.resolve import ResolveError, resolve  # noqa: E402
from airlume.pipeline import archive  # noqa: E402
from airlume.pipeline.registry import Registry  # noqa: E402
from airlume.pipeline.store import Store  # noqa: E402

BENCH = ROOT / "airlume" / "eval" / "benchmark"
OUT = ROOT / "data" / "eval"


class _WaitCounter(logging.Handler):
    """Counts the router's 'rate limited; waiting' warnings so a timing can be flagged."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.n = 0

    def emit(self, record: logging.LogRecord) -> None:
        if "rate limited" in record.getMessage():
            self.n += 1


def load_questions() -> list[dict]:
    out = []
    for name in ("questions.jsonl", "classmate-raw-2026-10-30.jsonl"):
        p = BENCH / name
        if p.exists():
            out += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return out


def build_store(reg: Registry, fake: bool) -> tuple[Store, float, str]:
    t0 = time.perf_counter()
    s = Store(":memory:")
    if fake:
        from airlume.pipeline.fake import fake_city_hourly, fake_readings
        r = fake_readings(reg)
        s.upsert_readings(r)
        s.upsert_city_hourly(fake_city_hourly(reg, r))
        mode = "fake (self-test only, not a result)"
    else:
        s.upsert_readings(archive.load_all("readings"))
        s.upsert_city_hourly(archive.load_all("city_hourly"))
        s.upsert_epd_daily(archive.load_all("epd_daily"))
        s.upsert_forecasts(archive.load_all("forecasts"))
        s.delete_source("fake")
        mode = "archive"
    return s, time.perf_counter() - t0, mode


def summarise(xs: list[float], seed: int = 1101) -> dict:
    if not xs:
        return {"n": 0}
    xs = sorted(xs)
    rng = random.Random(seed)
    meds = sorted(statistics.median(rng.choices(xs, k=len(xs))) for _ in range(2000))
    p95 = xs[min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))]
    return {"n": len(xs), "median_s": round(statistics.median(xs), 4),
            "median_ci95_s": [round(meds[49], 4), round(meds[1949], 4)],
            "p95_s": round(p95, 4), "p95_is_max": len(xs) < 20, "max_s": round(xs[-1], 4)}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", choices=("stub", "model"), default="stub")
    ap.add_argument("--model", default=router.PRIMARY_MODEL)
    ap.add_argument("--n", type=int, default=30, help="questions to send to the model (model mode only)")
    ap.add_argument("--pace", type=float, default=18.0,
                    help="seconds to wait between model calls, untimed (model mode only)")
    ap.add_argument("--fake", action="store_true", help="self-test on synthetic data; not a result")
    a = ap.parse_args(argv)

    reg = Registry.load()
    store, build_s, mode = build_store(reg, a.fake)
    qs = load_questions()
    if a.router == "model":
        random.Random(1101).shuffle(qs)
        qs = qs[: a.n]
    print(f"{len(qs)} questions, router={a.router}, data={mode}, store build {build_s:.2f}s")

    counter = _WaitCounter()
    logging.getLogger("airlume.router").addHandler(counter)
    rows = []
    for k, q in enumerate(qs):
        text = q["question"]
        if a.router == "model" and k:
            time.sleep(a.pace)  # keep under the tokens-per-minute cap; not part of the timing
        waits_before = counter.n
        t0 = time.perf_counter()
        try:
            if a.router == "stub":
                intent = stub_router.route(text, None)
                source = "stub"
            else:
                res = router.route(text, model=a.model, use_cache=False, allow_fallback=False)
                intent, source = res.intent, res.model
        except Exception as e:  # a failed model call is a result, not a crash
            rows.append({"id": q["id"], "kind": "route_error", "error": type(e).__name__,
                         "route_s": time.perf_counter() - t0,
                         "rate_limit_waits": counter.n - waits_before})
            continue
        t1 = time.perf_counter()
        row = {"id": q["id"], "route_s": t1 - t0, "source": source,
               "rate_limit_waits": counter.n - waits_before}
        if not intent.in_scope:
            row["kind"] = "out_of_scope"
        elif intent.clarify:
            row["kind"] = "clarify"
        else:
            try:
                rq = resolve(intent, reg)
            except ResolveError:
                row["kind"] = "resolve_error"
                row["resolve_s"] = time.perf_counter() - t1
                rows.append(row)
                continue
            t2 = time.perf_counter()
            answer(rq, store, reg)
            t3 = time.perf_counter()
            row.update(kind="answered", resolve_s=t2 - t1, answer_s=t3 - t2, total_s=t3 - t0)
        rows.append(row)

    kinds: dict[str, int] = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    ans = [r for r in rows if r["kind"] == "answered"]
    report = {
        "date": date.today().isoformat(), "router": a.router,
        "model": a.model if a.router == "model" else "stub", "data": mode,
        "store_build_s": round(build_s, 3), "questions": len(rows), "kinds": kinds,
        "answered": {
            "route": summarise([r["route_s"] for r in ans]),
            "resolve": summarise([r["resolve_s"] for r in ans]),
            "answer": summarise([r["answer_s"] for r in ans]),
            "total": summarise([r["total_s"] for r in ans]),
        },
        "all_routes": summarise([r["route_s"] for r in rows]),
        "routes_without_rate_limit_wait": summarise(
            [r["route_s"] for r in rows if not r.get("rate_limit_waits")]),
        "calls_that_waited": sum(1 for r in rows if r.get("rate_limit_waits")),
        "route_errors": [{"id": r["id"], "error": r["error"]} for r in rows if r["kind"] == "route_error"],
        "pace_s": a.pace if a.router == "model" else 0,
        "note": "route is the model round trip in model mode and a keyword match in stub mode; "
                "browser rendering and frames per second are not measured here.",
        "rows": rows,
    }
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    if a.fake:
        print("(self-test: nothing written)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    tag = f"_pace{int(a.pace)}" if a.router == "model" else ""  # keeps the 1 Nov unpaced run intact
    p = OUT / f"e6_latency_{a.router}_{report['date']}{tag}.json"
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"written {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

import json
from pathlib import Path

from airlume.eval.run_e1 import load, run

B = Path(__file__).resolve().parents[1] / "airlume" / "eval" / "benchmark"


def test_benchmark_files_valid():
    q = load("questions.jsonl"); c = load("conversations.jsonl")
    assert len(q) == 70 and len(c) == 20
    assert len({x["id"] for x in q + c}) == 90
    assert all(x["expected"] for x in q + c)
    assert sum(1 for x in q if x["lang"] == "ur-Latn") == 10


def test_e1_runs_on_stub():
    s = run("stub", runs=1)
    assert s["n"] == 90 and 0.3 < s["pass_rate"] < 0.9 and s["consistency"] == 1.0
    assert "where_now" in s["per_class"] and "city" in s["per_field"]

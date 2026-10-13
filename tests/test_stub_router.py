import json
from pathlib import Path

from airlume.nl.stub_router import route

BENCH = Path(__file__).resolve().parents[1] / "airlume" / "eval" / "benchmark" / "questions.jsonl"


def test_where_now():
    v = route("Where is the air worst in Lahore right now?")
    assert v.city == "Lahore" and v.view == "stations_3d" and v.aggregation == "latest"


def test_threshold():
    v = route("How many hours was the AQI above 300 in Shahdara last week?")
    assert v.aggregation == "count_hours_above" and v.threshold == 300 and v.area == "shahdara"


def test_two_cities():
    v = route("Which city has worse air today, Lahore or Faisalabad?")
    assert v.compare_to == "other_city" and v.other_city == "Faisalabad"


def test_out_of_scope():
    assert route("What is the capital of France?").in_scope is False


def test_benchmark_file_is_valid_jsonl():
    rows = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) >= 10 and len({r["id"] for r in rows}) == len(rows)

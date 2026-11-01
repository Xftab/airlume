import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("score_benchmark_v1", ROOT / "scripts" / "score_benchmark_v1.py")
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)


def test_wilson_known_value_and_edges():
    lo, hi = sb.wilson(8, 10)
    assert abs(lo - 0.4902) < 5e-4 and abs(hi - 0.9433) < 5e-4
    assert sb.wilson(0, 10)[0] == 0.0 and sb.wilson(0, 10)[1] > 0.2   # not zero-width at 0%
    assert abs(sb.wilson(10, 10)[1] - 1.0) < 1e-9 and sb.wilson(10, 10)[0] < 0.8  # not zero-width at 100%
    assert sb.wilson(0, 0) == (0.0, 0.0)


def test_newcombe_difference_brackets_the_point_estimate():
    d, lo, hi = sb.newcombe_diff(30, 40, 15, 40)
    assert abs(d - 0.375) < 1e-9 and lo < d < hi and lo > 0     # clear gap excludes zero
    d, lo, hi = sb.newcombe_diff(10, 25, 10, 37)
    assert lo < 0 < hi                                            # small samples: gap not established


def test_expected_blank_cells_are_not_scored():
    e = sb.expected_from_row({"in_scope": "yes", "time_label": "today", "metric": "", "area": ""})
    assert e == {"in_scope": True, "time": "today"}


def test_expected_out_of_scope_and_clarify():
    assert sb.expected_from_row({"in_scope": "no", "metric": "aqi"}) == {"in_scope": False}
    assert sb.expected_from_row({"in_scope": "yes", "clarify": "Which city?", "metric": "aqi"}) == \
        {"in_scope": True, "clarify": True}


def test_expected_threshold_and_range():
    e = sb.expected_from_row({"in_scope": "yes", "aggregation": "count_hours_above", "threshold": "150",
                              "time_label": "custom_range", "time_start": "2026-10-20", "time_end": "2026-10-22"})
    assert e["threshold"] == 150 and e["time_start"] == "2026-10-20" and e["time_end"] == "2026-10-22"

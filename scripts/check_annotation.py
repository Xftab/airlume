"""Check a filled annotation sheet against the ViewIntent schema and the conventions.

    python scripts\\check_annotation.py airlume\\eval\\benchmark\\classmate-raw-2026-10-30-annotated-aftab.csv

Catches the mistakes that are easy to make in Excel and expensive to find later:
a value outside the allowed set, a threshold missing on count_hours_above, a
comparison without the view set to compare. Every complaint names the row and
the question so it can be fixed in place.

This checks CONFORMANCE, not correctness. It cannot tell you that you labelled a
question wrong, only that the label is not a legal form. Correctness is what the
second annotator and the kappa are for.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ALLOWED = {
    "in_scope": {"yes", "no", ""},
    "metric": {"aqi", "pm25", "pm10", ""},
    "time_label": {"now", "today", "yesterday", "last_7_days", "last_30_days",
                   "this_month", "last_month", "same_day_last_year",
                   "custom_date", "custom_range", ""},
    "aggregation": {"latest", "mean", "max", "min", "count_hours_above", ""},
    "compare_to": {"none", "yesterday", "last_week", "last_year", "other_city", ""},
    "view": {"stations_3d", "city_overview", "compare", "timeline", "forecast", ""},
    "camera": {"overview", "station", "north", "zoomed_out", ""},
}
DATE_FIELDS = ("time_date", "time_start", "time_end")


def _iso(v: str) -> bool:
    from datetime import date
    try:
        date.fromisoformat(v)
        return True
    except ValueError:
        return False


def check_row(r: dict[str, str], line: int) -> list[str]:
    g = lambda k: (r.get(k) or "").strip()
    bad: list[str] = []

    for field, allowed in ALLOWED.items():
        v = g(field).lower()
        if v not in allowed:
            bad.append(f"{field}={g(field)!r} is not one of {sorted(a for a in allowed if a)}")

    # An out-of-scope question needs nothing else; an in-scope one needs a view.
    if g("in_scope").lower() == "no":
        extras = [f for f in ("metric", "area", "aggregation", "compare_to", "other_city")
                  if g(f) and g(f).lower() not in ("none",)]
        if extras:
            bad.append(f"in_scope=no but these are filled anyway: {', '.join(extras)} "
                       "(an out-of-scope question has no form to fill)")

    # count_hours_above needs a threshold, and the threshold must be in range.
    if g("aggregation") == "count_hours_above":
        t = g("threshold")
        if not t:
            bad.append("aggregation=count_hours_above needs a threshold (guide convention 3)")
        elif not t.isdigit() or not 0 <= int(t) <= 500:
            bad.append(f"threshold={t!r} must be a whole number from 0 to 500")
    elif g("threshold"):
        bad.append(f"threshold={g('threshold')!r} set but aggregation is {g('aggregation') or 'blank'!r}")

    # other_city pairs with compare_to.
    if g("compare_to") == "other_city" and not g("other_city"):
        bad.append("compare_to=other_city needs other_city")
    if g("other_city") and g("compare_to") != "other_city":
        bad.append(f"other_city={g('other_city')!r} set but compare_to is "
                   f"{g('compare_to') or 'blank'!r}")

    # Guide convention 4: a comparison is shown in the compare view.
    if g("compare_to") not in ("", "none") and g("view") not in ("", "compare"):
        bad.append(f"compare_to={g('compare_to')!r} but view={g('view')!r} "
                   "(guide convention 4 says a comparison uses view=compare)")

    # Dates must match their label and be real dates.
    label = g("time_label")
    if label == "custom_date" and not g("time_date"):
        bad.append("time_label=custom_date needs time_date")
    if label == "custom_range" and not (g("time_start") and g("time_end")):
        bad.append("time_label=custom_range needs time_start and time_end")
    for f in DATE_FIELDS:
        if g(f) and not _iso(g(f)):
            bad.append(f"{f}={g(f)!r} is not a YYYY-MM-DD date")
    if g("time_date") and label and label != "custom_date":
        bad.append(f"time_date set but time_label is {label!r}")

    # Guide convention 7: a cross-city view is zoomed out.
    if g("view") == "city_overview" and g("camera") not in ("", "zoomed_out"):
        bad.append(f"view=city_overview with camera={g('camera')!r} "
                   "(guide convention 7 says zoomed_out)")

    # A clarify and a confident form are different answers to the question.
    if g("clarify") and g("in_scope").lower() == "no":
        bad.append("clarify is set and in_scope=no: pick one, a refusal is not a clarification")

    return bad


def main(path: str) -> int:
    p = Path(path)
    rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
    problems = 0
    blank = 0
    for i, r in enumerate(rows, start=2):  # row 1 is the header in Excel
        filled = any((r.get(k) or "").strip() for k in
                     ("in_scope", "metric", "view", "time_label", "aggregation", "clarify"))
        if not filled:
            blank += 1
            continue
        for msg in check_row(r, i):
            problems += 1
            print(f"row {i} [{r.get('id', '?')}] {msg}")
            print(f"        question: {r.get('question', '')}")
    done = len(rows) - blank
    print(f"\n{done} of {len(rows)} rows annotated, {blank} still blank.")
    if problems:
        print(f"{problems} problem(s) found. Nothing is changed; fix them in the sheet and re-run.")
        return 1
    print("No conformance problems. (This does not mean the labels are right - "
          "that is what the second annotator is for.)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: check_annotation.py <annotated.csv>")
    raise SystemExit(main(sys.argv[1]))

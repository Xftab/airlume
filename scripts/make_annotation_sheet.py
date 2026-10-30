"""Generate a blank annotation worksheet from a raw question file.

    python scripts\\make_annotation_sheet.py airlume\\eval\\benchmark\\classmate-raw-2026-10-30.jsonl aftab

Writes `<stem>-annotated-<who>.csv` next to the raw file: one row per question,
every form column empty. Open it in Excel, fill it in, save as CSV.

Cells are left EMPTY rather than pre-filled with defaults. The annotator guide
says a blank field means "nothing in the question decides it, so the default
applies", and that is a judgement the annotator has to make question by
question. Pre-filling the defaults would make "I decided the default is right"
and "I did not look at this row" indistinguishable, and it would anchor the
annotator towards the default on exactly the ambiguous rows where the decision
matters most.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Columns the annotator fills. Order follows the annotator guide.
FORM_COLUMNS = [
    "in_scope",      # yes / no            (default yes)
    "clarify",       # short question back (default blank)
    "metric",        # aqi / pm25 / pm10   (default aqi)
    "city",          # registry city name  (default Lahore)
    "area",          # station or neighbourhood as written (default blank)
    "time_label",    # now / today / yesterday / last_7_days / ... (default now)
    "time_date",     # YYYY-MM-DD when time_label is custom_date
    "time_start",    # YYYY-MM-DD when time_label is custom_range
    "time_end",      # YYYY-MM-DD when time_label is custom_range
    "aggregation",   # latest / mean / max / min / count_hours_above (default latest)
    "threshold",     # 0-500, required when aggregation is count_hours_above
    "compare_to",    # none / yesterday / last_week / last_year / other_city
    "other_city",    # required when compare_to is other_city
    "view",          # stations_3d / city_overview / compare / timeline / forecast
    "camera",        # overview / station / north / zoomed_out
    "notes",         # your reasoning on anything you found hard - read at the discussion step
]
CARRIED = ["id", "contributor", "lang", "question"]


def main(raw_path: str, who: str) -> None:
    raw = Path(raw_path)
    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines() if line.strip()]
    out = raw.with_name(f"{raw.stem}-annotated-{who}.csv")
    if out.exists():
        sys.exit(f"{out.name} already exists. Move it aside first; this would overwrite your work.")
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(CARRIED + FORM_COLUMNS)
        for r in rows:
            w.writerow([r.get(c, "") for c in CARRIED] + [""] * len(FORM_COLUMNS))
    print(f"wrote {out}")
    print(f"  {len(rows)} questions, {len(FORM_COLUMNS)} columns to fill")
    print("\nOpen it in Excel, fill it in, save as CSV, then check it with:")
    print(f"  python scripts\\check_annotation.py {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: make_annotation_sheet.py <raw.jsonl> <annotator-name>")
    main(sys.argv[1], sys.argv[2])

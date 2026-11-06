"""Find and restore archive rows that a later commit deleted (6 Nov 2026).

Why this exists. Until 6 Nov both collectors (the laptop and GitHub Actions) wrote
every source, and each side pulled with `git pull --rebase -X theirs` (laptop) or
`-X ours` (cloud). When both had appended to the same month file, the conflicting
hunk from the other side was thrown away. On the laptop that meant the cloud's
CAMS forecast rows for the hours the laptop was asleep were deleted on wake-up
(for example 384 rows in commit 1315db3, 6 Nov 14:31 PKT).

What it does. Walks every commit in the local history that touched a CSV under
data/archive/, reads each version of each file, and keeps, for every key
(archive.KEYS), the value from the most recent commit that held it. Any key in
that union but missing from the working-tree file is a lost row. With --write the
lost rows are put back through archive.export (de-duplicated and sorted, so the
file format is unchanged). Rows present in the working tree are never altered.

Usage (from the project root, inside the venv):
    python scripts/recover_archive_rows.py            # report only
    python scripts/recover_archive_rows.py --write    # restore the lost rows

Needs full git history (a shallow clone only sees what it fetched).
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from airlume.config import ROOT  # noqa: E402
from airlume.pipeline import archive  # noqa: E402


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout


def table_of(path: str) -> str:
    return path.split("/")[2]  # data/archive/<table>/<source>/<month>.csv


def history_union(path: str) -> pd.DataFrame:
    """Every row any committed version of `path` ever held, latest commit wins per key."""
    commits = git("log", "--format=%H", "--", path).split()  # newest first
    keys = archive.KEYS[table_of(path)]
    frames = []
    for order, sha in enumerate(reversed(commits)):  # oldest first
        try:
            text = git("show", f"{sha}:{path}")
        except subprocess.CalledProcessError:
            continue  # file deleted in that commit
        if not text.strip():
            continue
        d = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
        d["_order"] = order
        frames.append(d)
    if not frames:
        return pd.DataFrame()
    allv = pd.concat(frames, ignore_index=True)
    return allv.sort_values("_order").drop_duplicates(subset=keys, keep="last")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="restore the lost rows into the working tree")
    args = ap.parse_args()
    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        print("warning: shallow clone; rows deleted before the fetched history are not visible")
    files = sorted({p for p in git("log", "--format=", "--name-only", "--", "data/archive").split()
                    if p.endswith(".csv")})
    total = 0
    for path in files:
        table = table_of(path)
        keys = archive.KEYS[table]
        hist = history_union(path)
        here = ROOT / path
        if hist.empty:
            continue
        cur = pd.read_csv(here, dtype=str, keep_default_na=False) if here.exists() else pd.DataFrame(columns=keys)
        cur_keys = set(map(tuple, cur[keys].to_numpy())) if len(cur) else set()
        lost = hist[[tuple(k) not in cur_keys for k in hist[keys].to_numpy()]]
        if lost.empty:
            continue
        total += len(lost)
        tcol = archive.TIME_COL[table]
        span = f"{lost[tcol].min()} .. {lost[tcol].max()}"
        print(f"{path}: {len(lost)} rows lost ({span})")
        if args.write:
            out = lost.drop(columns="_order").replace("", None)
            archive.export(table, out)
    print(f"total lost rows: {total}" + (" (restored)" if args.write and total else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

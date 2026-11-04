"""Cut a reproducible, language-stratified subset of the annotation sheet
for the second annotator. Label columns are blanked defensively.

Usage:
  python scripts\cut_second_annotation.py <blank_sheet.csv> <out.csv> [n=20] [seed=1101]
"""
import csv
import random
import sys
from collections import Counter, defaultdict

LABEL_START = "in_scope"  # every column from here on is a label column
MIN_PER_LANG = 5


def allocate(sizes, n, min_per):
    total = sum(sizes.values())
    alloc = {g: min(sz, max(min_per, round(n * sz / total))) for g, sz in sizes.items()}
    # adjust to exactly n by changing the largest group first
    while sum(alloc.values()) != n:
        diff = n - sum(alloc.values())
        order = sorted(sizes, key=lambda g: -sizes[g])
        changed = False
        for g in order:
            if diff > 0 and alloc[g] < sizes[g]:
                alloc[g] += 1
                changed = True
                break
            if diff < 0 and alloc[g] > min(sizes[g], min_per):
                alloc[g] -= 1
                changed = True
                break
        if not changed:
            break
    return alloc


def main():
    src, dst = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1101

    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        cols = list(rows[0].keys())

    by_lang = defaultdict(list)
    for r in rows:
        by_lang[r["lang"]].append(r)
    sizes = {g: len(v) for g, v in by_lang.items()}
    alloc = allocate(sizes, n, MIN_PER_LANG)

    rng = random.Random(seed)
    picked = []
    for g in sorted(by_lang):
        pool = sorted(by_lang[g], key=lambda r: r["id"])
        picked += rng.sample(pool, alloc[g])
    picked.sort(key=lambda r: r["id"])

    label_cols = cols[cols.index(LABEL_START):]
    for r in picked:
        for c in label_cols:
            r[c] = ""

    with open(dst, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(picked)

    print(f"seed {seed}, wrote {len(picked)} of {len(rows)} rows to {dst}")
    print("source language counts:", dict(sizes))
    print("picked language counts:", dict(Counter(r["lang"] for r in picked)))
    print("picked contributor counts:", dict(Counter(r["contributor"] for r in picked)))
    print("picked ids:", ",".join(r["id"] for r in picked))


if __name__ == "__main__":
    main()

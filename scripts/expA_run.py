r"""Experiment A (typed form vs Python code vs text-to-SQL): one command per step.

    python scripts\expA_run.py freeze --cutoff 2026-12-05T12:00:00+05:00
    python scripts\expA_run.py check --items airlume\eval\expA\trick-set-2026-11-20.jsonl
    python scripts\expA_run.py gold --snapshot snap-20261205T0700Z --items <file>
    python scripts\expA_run.py generate --snapshot snap-20261205T0700Z --items <file> --model openai/gpt-oss-120b
    python scripts\expA_run.py execute --snapshot snap-20261205T0700Z --items <file> --model openai/gpt-oss-120b
    python scripts\expA_run.py score --snapshot snap-20261205T0700Z --items <file> --model openai/gpt-oss-120b
    python scripts\expA_run.py agreement --snapshot snap-20261205T0700Z --a kiran.csv --b tehreem.csv
    python scripts\expA_run.py selftest

Protocol: docs/research/expA-protocol-2026-11-20.md. Every step can be stopped and
rerun with the same command; finished items are skipped. Only `generate` calls the
model (it needs GROQ_API_KEY in .env and never prints it); `generate --dry-run`
reports what is still uncached without calling anything.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.eval.expA import items as items_mod  # noqa: E402
from airlume.eval.expA import run, sandbox  # noqa: E402
from airlume.eval.expA.agreement import agreement  # noqa: E402
from airlume.eval.expA.generate import ARMS  # noqa: E402
from airlume.eval.expA.reference import Reference  # noqa: E402
from airlume.eval.expA.snapshot import SNAP_ROOT, Snapshot, freeze, snapshot_id, verify  # noqa: E402
from airlume.pipeline.registry import Registry  # noqa: E402


def _snap(name: str) -> Snapshot:
    s = Snapshot(SNAP_ROOT / name)
    if not s.manifest_path.exists():
        sys.exit(f"No snapshot named {name} in {SNAP_ROOT}. Make one with: freeze --cutoff ...")
    return s


def _items(path: str) -> list[dict]:
    its = items_mod.load(Path(path))
    problems = items_mod.check(its)
    if problems:
        print("The item file has problems; fix them first:")
        for p in problems[:40]:
            print("  -", p)
        sys.exit(1)
    return its


def _arms(text: str) -> list[str]:
    arms = [a.strip() for a in text.split(",") if a.strip()]
    bad = [a for a in arms if a not in ARMS]
    if bad:
        sys.exit(f"unknown arm(s) {bad}; choose from {ARMS}")
    return arms


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze", help="freeze the archive at a cutoff")
    f.add_argument("--cutoff", required=True, help="ISO time with zone, e.g. 2026-12-05T12:00:00+05:00")
    f.add_argument("--name")
    v = sub.add_parser("verify", help="check a snapshot against its manifest")
    v.add_argument("--snapshot", required=True)
    c = sub.add_parser("check", help="check an item file")
    c.add_argument("--items", required=True)
    for name in ("gold", "generate", "execute", "score"):
        p = sub.add_parser(name)
        p.add_argument("--snapshot", required=True)
        p.add_argument("--items", required=True)
        if name != "gold":
            p.add_argument("--model", default="openai/gpt-oss-120b")
            p.add_argument("--arms", default="form,code,sql")
        if name == "generate":
            p.add_argument("--max-calls", type=int, default=None, help="stop after this many live model calls")
            p.add_argument("--dry-run", action="store_true", help="count uncached items; call nothing")
        if name == "execute":
            p.add_argument("--force", action="store_true", help="re-execute items already executed")
    g = sub.add_parser("agreement", help="agreement between two annotators' gold calls")
    g.add_argument("--snapshot", required=True)
    g.add_argument("--a", required=True, help="first annotator's CSV")
    g.add_argument("--b", required=True, help="second annotator's CSV")
    sub.add_parser("selftest", help="show what the sandbox can and cannot do on this machine")
    a = ap.parse_args()

    if a.cmd == "freeze":
        s = freeze(a.cutoff, a.name)
        m = s.manifest()
        print(f"Froze {s.root.name} (id {snapshot_id(s)}): now = {m['cutoff_local']}")
        for k, n in sorted(m["rows"].items()):
            print(f"  {k}: {n} rows")
        return
    if a.cmd == "verify":
        problems = verify(_snap(a.snapshot))
        print("Snapshot intact." if not problems else "PROBLEMS:\n  " + "\n  ".join(problems))
        sys.exit(1 if problems else 0)
    if a.cmd == "check":
        its = _items(a.items)
        print(f"{len(its)} items, no problems.")
        return
    if a.cmd == "selftest":
        for k, v in sandbox.selftest().items():
            print(f"  {k}: {v}")
        return

    if a.cmd == "agreement":
        s = _snap(a.snapshot)
        out = agreement(Reference(s.tables(), s.now()), Path(a.a), Path(a.b))
        pct = "n/a" if out["percent"] is None else f"{out['percent']:.1f}%"
        kap = "n/a" if out["kappa_kind"] is None else f"{out['kappa_kind']:.2f}"
        print(f"Both annotated: {out['n_both']}. Same answer: {out['agree']} ({pct}). Kappa on kind: {kap}.")
        if out["only_a"] or out["only_b"]:
            print(f"Only in A: {len(out['only_a'])}; only in B: {len(out['only_b'])}")
        for d in out["disagreements"]:
            print(f"  {d['id']}: A {d['a']}  |  B {d['b']}")
        dest = run.out_dir(s) / "agreement.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        print(f"Full list for the adjudicator: {dest}")
        return

    snap = _snap(a.snapshot)
    its = _items(a.items)
    if a.cmd == "gold":
        p = run.build_gold(snap, its)
        print(f"Gold for {len(its)} items written to {p}")
        return
    reg = Registry.load()
    arms = _arms(a.arms)
    if a.cmd == "generate":
        out = run.run_generate(snap, its, arms, a.model, reg, max_calls=a.max_calls, dry_run=a.dry_run)
        if a.dry_run:
            print(f"Replies still to fetch (nothing was called): {json.dumps(out['missing'])}")
        else:
            print(f"Live model calls this run: {json.dumps(out['live'])}")
    elif a.cmd == "execute":
        run.run_execute(snap, its, arms, a.model, reg, force=a.force)
        print(f"Executed; results in {run.out_dir(snap, a.model)}")
    elif a.cmd == "score":
        card = run.run_score(snap, its, arms, a.model)
        print(run.scorecard_markdown(card))


if __name__ == "__main__":
    main()

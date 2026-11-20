"""The four steps of an Experiment A run: gold, generate, execute, score.

Each step reads the previous step's files and writes its own, so a run can stop at
any point (free-tier cap, laptop asleep) and continue with the same command.

    data/eval/expA/<snapshot-id>/gold.jsonl
    data/eval/expA/<snapshot-id>/<model>/<arm>-gen.jsonl     model replies (no execution)
    data/eval/expA/<snapshot-id>/<model>/<arm>-exec.jsonl    answers on the snapshot and its shifted copy
    data/eval/expA/<snapshot-id>/<model>/scorecard.json      every number in the results tables
    data/eval/expA/<snapshot-id>/<model>/scorecard.md        the same, for reading
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from airlume.config import ROOT
from airlume.nl.schema import ViewIntent
from airlume.pipeline.registry import Registry

from . import generate as gen
from . import sandbox
from .formarm import build_store, parser_for, run_form
from .normalize import Answer, from_code_result, from_model_reply, from_sql_rows, render
from .reference import Reference, evaluate_reference
from .score import invented_check, judge, paired, rate_dict
from .snapshot import SHIFT, Snapshot, snapshot_id, verify

OUT_ROOT = ROOT / "data" / "eval" / "expA"


def model_slug(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def out_dir(snap: Snapshot, model: str | None = None) -> Path:
    d = OUT_ROOT / snapshot_id(snap)
    return d / model_slug(model) if model else d


def now_local_text(snap: Snapshot) -> str:
    return snap.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_jsonl(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["id"]] = row
    return out


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _require_intact(snap: Snapshot) -> None:
    problems = verify(snap)
    if problems:
        raise RuntimeError(f"snapshot {snap.root.name} does not match its manifest: {problems[:5]}")


# --------------------------------------------------------------------------- 1. gold

def build_gold(snap: Snapshot, items: list[dict]) -> Path:
    """Execute every item's reference on the snapshot and on its shifted copy."""
    _require_intact(snap)
    ref0 = Reference(snap.tables(), snap.now())
    ref1 = Reference(snap.shifted.tables(), snap.now())
    path = out_dir(snap) / "gold.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for it in items:
        g0 = evaluate_reference(it["reference"], ref0)
        g1 = evaluate_reference(it["reference"], ref1)
        rows.append({"id": it["id"], "reference": it["reference"], "gold": g0.to_dict(),
                     "gold_shifted": g1.to_dict()})
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- 2. generate

def run_generate(snap: Snapshot, items: list[dict], arms: list[str], model: str, registry: Registry,
                 max_calls: int | None = None, dry_run: bool = False, log=print) -> dict[str, dict[str, int]]:
    """Model replies for every (item, arm) not yet on file, item by item, so a run stopped by
    the daily cap leaves every arm with the same items done. Returns live calls and, for a
    dry run, the replies still missing, per arm."""
    now_text = now_local_text(snap)
    live = {a: 0 for a in arms}
    missing = {a: 0 for a in arms}
    paths = {a: out_dir(snap, model) / f"{a}-gen.jsonl" for a in arms}
    done = {a: _read_jsonl(paths[a]) for a in arms}
    for it in items:
        for arm in arms:
            if it["id"] in done[arm]:
                continue
            if max_calls is not None and sum(live.values()) >= max_calls:
                log(f"stopped at --max-calls {max_calls}; run the same command again to continue")
                return {"live": live, "missing": missing}
            try:
                g = gen.generate(arm, it["question"], model, registry, now_text, dry_run=dry_run)
            except gen.DailyLimitReached as e:
                log(f"Groq daily limit reached ({e}). Run the same command again tomorrow; nothing is lost.")
                return {"live": live, "missing": missing}
            if dry_run and g.error:
                missing[arm] += 1
                continue
            live[arm] += 1 if g.called else 0
            _append(paths[arm], {"id": it["id"], **g.to_dict()})
    return {"live": live, "missing": missing}


# --------------------------------------------------------------------------- 3. execute

def _disallowed(a: Answer) -> bool:
    d = (a.detail or "")
    return a.kind == "blocked" or "PermissionError" in d or "Permission Error" in d


def _exec_code_or_sql(arm: str, g: dict, snap: Snapshot, now_text: str) -> tuple[Answer, Answer, dict]:
    if g.get("error") or g.get("parsed") is None:
        a = Answer("error", detail=f"generation: {g.get('error')}")
        a.text = render(a)
        return a, a, {}
    early = from_model_reply(g["parsed"])
    if early is not None:
        early.text = render(early)
        return early, early, {}
    body = g["parsed"].get("code" if arm == "code" else "sql")
    out = []
    meta = {}
    for s in (snap, snap.shifted):
        if arm == "code":
            r = sandbox.run_python(body, s.tables_dir, now_text)
        else:
            r = sandbox.run_sql(body, s.duckdb_path)
        if r.blocked:
            a = Answer("blocked", detail=r.blocked)
        elif not r.ok:
            a = Answer("error", detail=r.error or "failed")
        elif arm == "code":
            a = from_code_result(r.value)
        else:
            a = from_sql_rows(r.columns, r.value)
        out.append(a)
        meta.setdefault("seconds", []).append(round(r.seconds, 3))
        if r.timed_out:
            meta["timed_out"] = True
    for a in out:
        a.text = render(a)
    return out[0], out[1], meta


def run_execute(snap: Snapshot, items: list[dict], arms: list[str], model: str, registry: Registry,
                force: bool = False) -> None:
    _require_intact(snap)
    now_text = now_local_text(snap)
    now = snap.now()
    stores = None
    parser = parser_for(registry)
    for arm in arms:
        gpath = out_dir(snap, model) / f"{arm}-gen.jsonl"
        epath = out_dir(snap, model) / f"{arm}-exec.jsonl"
        gens = _read_jsonl(gpath)
        if force and epath.exists():
            epath.unlink()
        done = _read_jsonl(epath)
        for it in items:
            if it["id"] in done or it["id"] not in gens:
                continue
            g = gens[it["id"]]
            if arm == "form":
                if stores is None:
                    stores = (build_store(snap.raw()), build_store(snap.shifted.raw()))
                if g.get("error") or g.get("parsed") is None:
                    a0 = a1 = Answer("error", detail=f"generation: {g.get('error')}")
                    meta = {}
                else:
                    intent = ViewIntent.model_validate(g["parsed"])
                    a0 = run_form(intent, stores[0], registry, now, parser)
                    a1 = run_form(intent, stores[1], registry, now, parser)
                    meta = {}
            else:
                a0, a1, meta = _exec_code_or_sql(arm, g, snap, now_text)
            _append(epath, {"id": it["id"], "answer": a0.to_dict(), "answer_shifted": a1.to_dict(),
                            "disallowed": _disallowed(a0) or _disallowed(a1), **meta})


# --------------------------------------------------------------------------- 4. score

def _answer(d: dict) -> Answer:
    return Answer(**d)


def _form_ok(expected: dict | None, parsed: dict | None) -> bool | None:
    if not expected or not parsed:
        return None
    from airlume.eval.run_e1 import score_item  # eval-only import, kept local
    return all(score_item(expected, ViewIntent.model_validate(parsed)).values())


def run_score(snap: Snapshot, items: list[dict], arms: list[str], model: str) -> dict:
    gold = _read_jsonl(out_dir(snap) / "gold.jsonl")
    by_id = {it["id"]: it for it in items}
    per_arm: dict[str, dict[str, dict]] = {}
    card: dict = {"snapshot": snapshot_id(snap), "cutoff_local": now_local_text(snap), "model": model,
                  "n_items": len(items), "arms": {}}
    for arm in arms:
        gens = _read_jsonl(out_dir(snap, model) / f"{arm}-gen.jsonl")
        execs = _read_jsonl(out_dir(snap, model) / f"{arm}-exec.jsonl")
        rows = {}
        for iid, it in by_id.items():
            if iid not in gold or iid not in execs:
                continue
            g, gs = gold[iid]["gold"], gold[iid]["gold_shifted"]
            a, a_s = _answer(execs[iid]["answer"]), _answer(execs[iid]["answer_shifted"])
            v = judge(g, a)
            unit = g.get("unit")
            shift = SHIFT.get(unit) if unit in ("aqi", "pm25", "pm10") else None
            inv = invented_check(g, gs, a, a_s, shift, agg_moves_by_shift=shift is not None)
            fo = _form_ok(it.get("expected_form"), gens.get(iid, {}).get("parsed")) if arm == "form" else None
            rows[iid] = {"correct": v["correct"], "why": v["why"], **inv,
                         "disallowed": bool(execs[iid].get("disallowed")),
                         "kind": a.kind, "form_ok": fo,
                         "latency_s": gens.get(iid, {}).get("latency_s"),
                         "usage": gens.get(iid, {}).get("usage") or {}}
        per_arm[arm] = rows
        card["arms"][arm] = _summarise(rows, by_id, gold)
    ids_all = sorted(set.intersection(*(set(r) for r in per_arm.values()))) if per_arm else []
    card["paired_items"] = len(ids_all)
    card["paired"] = {}
    for i, x in enumerate(arms):
        for y in arms[i + 1:]:
            p = paired([per_arm[x][k]["correct"] for k in ids_all], [per_arm[y][k]["correct"] for k in ids_all])
            card["paired"][f"{x}_minus_{y}"] = p.to_dict()
    card["language_gap"] = {}
    for arm in arms:
        en, ru = [], []
        pairs = defaultdict(dict)
        for iid, it in by_id.items():
            if it.get("pair") and iid in per_arm[arm]:
                pairs[it["pair"]][it["lang"]] = per_arm[arm][iid]["correct"]
        for p in pairs.values():
            if "en" in p and "ru" in p:
                en.append(p["en"])
                ru.append(p["ru"])
        card["language_gap"][arm] = paired(en, ru).to_dict()
    path = out_dir(snap, model) / "scorecard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")
    (out_dir(snap, model) / "scorecard.md").write_text(scorecard_markdown(card), encoding="utf-8")
    (out_dir(snap, model) / "verdicts.json").write_text(json.dumps(per_arm, indent=1, default=str), encoding="utf-8")
    return card


def _summarise(rows: dict[str, dict], by_id: dict[str, dict], gold: dict[str, dict]) -> dict:
    def rate(sel):
        ks = [k for k in rows if sel(k)]
        return rate_dict(sum(rows[k]["correct"] for k in ks), len(ks))

    expect = {k: gold[k]["gold"]["kind"] for k in rows}
    out = {
        "overall": rate(lambda k: True),
        "by_expect": {e: rate(lambda k, e=e: expect[k] == e) for e in ("answer", "no_data", "refuse", "clarify")},
        "by_lang": {lg: rate(lambda k, lg=lg: by_id[k]["lang"] == lg) for lg in ("en", "ru")},
        "by_category": {c: rate(lambda k, c=c: by_id[k]["category"] == c)
                        for c in sorted({by_id[k]["category"] for k in rows})},
        "form_expressible": {str(b): rate(lambda k, b=b: by_id[k]["form_expressible"] is b) for b in (True, False)},
    }
    t = [k for k in rows if rows[k]["testable"]]
    out["invented"] = rate_dict(sum(rows[k]["invented"] for k in t), len(t))
    out["off_shift"] = rate_dict(sum(rows[k]["off_shift"] for k in t), len(t))
    out["disallowed"] = rate_dict(sum(rows[k]["disallowed"] for k in rows), len(rows))
    out["errors"] = rate_dict(sum(rows[k]["kind"] in ("error", "blocked") for k in rows), len(rows))
    lat = [rows[k]["latency_s"] for k in rows if rows[k]["latency_s"]]
    out["latency_s"] = ({"median": statistics.median(lat),
                         "p90": sorted(lat)[max(0, int(round(0.9 * len(lat))) - 1)], "n": len(lat)}
                        if lat else {"median": None, "p90": None, "n": 0})
    tok = [rows[k]["usage"].get("total_tokens") for k in rows if rows[k]["usage"].get("total_tokens")]
    out["tokens_mean"] = statistics.mean(tok) if tok else None
    fo = [k for k in rows if rows[k]["form_ok"] is not None]
    if fo:
        wrong = [k for k in fo if not rows[k]["correct"]]
        out["form_correct"] = rate_dict(sum(rows[k]["form_ok"] for k in fo), len(fo))
        out["error_source"] = {"model": sum(not rows[k]["form_ok"] for k in wrong),
                               "answer_code": sum(rows[k]["form_ok"] for k in wrong), "n_wrong": len(wrong)}
    return out


def _pct(d: dict) -> str:
    if not d or not d.get("n"):
        return "n/a"
    return f"{100 * d['rate']:.1f}% ({d['k']}/{d['n']}; 95% CI {100 * d['low']:.1f} to {100 * d['high']:.1f})"


def scorecard_markdown(card: dict) -> str:
    lines = [f"# Experiment A scorecard: {card['model']}", "",
             f"Snapshot {card['snapshot']}, now = {card['cutoff_local']} (Asia/Karachi). "
             f"{card['n_items']} items; {card['paired_items']} scored in every arm.", "",
             "| Arm | Correct | Answer items | Refuse | Clarify | No data | Invented numbers | Disallowed attempts |",
             "|---|---|---|---|---|---|---|---|"]
    for arm, s in card["arms"].items():
        be = s["by_expect"]
        lines.append(f"| {arm} | {_pct(s['overall'])} | {_pct(be['answer'])} | {_pct(be['refuse'])} | "
                     f"{_pct(be['clarify'])} | {_pct(be['no_data'])} | {_pct(s['invented'])} | {_pct(s['disallowed'])} |")
    lines += ["", "Paired differences in correctness (Newcombe 95% CI, exact McNemar p):", ""]
    for k, p in card["paired"].items():
        if p["n"]:
            lines.append(f"- {k.replace('_minus_', ' minus ')}: {100 * p['diff']:+.1f} points "
                         f"({100 * p['low']:+.1f} to {100 * p['high']:+.1f}), p = {p['p_mcnemar']:.3g}, n = {p['n']}")
    lines += ["", "English minus Roman Urdu, same questions:", ""]
    for arm, p in card["language_gap"].items():
        if p["n"]:
            lines.append(f"- {arm}: {100 * p['diff']:+.1f} points ({100 * p['low']:+.1f} to {100 * p['high']:+.1f}), "
                         f"p = {p['p_mcnemar']:.3g}, {p['n']} pairs")
    for arm, s in card["arms"].items():
        if "form_correct" in s:
            es = s["error_source"]
            lines += ["", f"Form arm: form itself correct {_pct(s['form_correct'])}. Of {es['n_wrong']} wrong answers "
                      f"with a labelled form, {es['model']} came from the model's form and {es['answer_code']} from the "
                      "answer code."]
    return "\n".join(lines) + "\n"

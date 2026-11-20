"""Ask the model once per (arm, question): a form, Python code, or one SQL query.

Nothing is executed here: generation and execution are separate steps, so every
reply is cached and logged before any of it runs, and a run can stop (the free
tier's daily cap) and resume without paying twice.

- Same model, temperature 0 and reasoning effort "low" in every arm.
- The form arm uses the app's own call (`router.call_groq`, prompt v5, strict JSON
  schema), so it is the deployed form-filler, not a copy of it.
- The code and SQL arms use JSON-object mode with the prompts in prompts.py. Their
  output cap is larger (4,096 tokens) because code is longer than a form; it is
  reported if it is ever reached.
- The API key comes from .env through load_settings(); it is never logged, cached
  or printed.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field

from airlume import __version__
from airlume.config import ROOT, load_settings
from airlume.nl import router, stub_router
from airlume.nl.schema import ViewIntent
from airlume.pipeline.registry import Registry

from . import prompts

ARMS = ("form", "code", "sql")
CACHE_DIR = ROOT / "data" / "cache" / "expA"
LOG_PATH = CACHE_DIR / "calls.jsonl"
CODE_MAX_TOKENS = 4096
TIMEOUT_S = 60


class DailyLimitReached(RuntimeError):
    """Groq's daily token cap: stop the run; rerunning later resumes from the cache."""


@dataclass
class Generation:
    arm: str
    model: str
    question: str
    prompt_version: str
    prompt_hash: str
    raw: str | None = None
    parsed: dict | None = None
    error: str | None = None
    usage: dict = field(default_factory=dict)
    latency_s: float = 0.0
    cached: bool = False
    called: bool = False             # an API request was made (counts against the budget)
    finish_reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def system_prompt(arm: str, registry: Registry, now_local: str) -> str:
    if arm == "form":
        return router.SYSTEM_PROMPT
    if arm == "code":
        return prompts.code_prompt(registry, now_local)
    if arm == "sql":
        return prompts.sql_prompt(registry, now_local)
    raise ValueError(f"arm must be one of {ARMS}")


def _version(arm: str) -> str:
    return router.PROMPT_VERSION if arm == "form" else prompts.PROMPT_VERSION


def cache_key(arm: str, model: str, question: str, prompt_text: str) -> str:
    blob = f"expA|{__version__}|{arm}|{_version(arm)}|{prompts.prompt_hash(prompt_text)}|{model}|{question}"
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def _log(entry: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def parse_reply(arm: str, raw: str) -> tuple[dict | None, str | None]:
    """(parsed reply, error). The form is validated by the app's own Pydantic model."""
    if arm == "form":
        try:
            return ViewIntent.model_validate_json(raw).model_dump(mode="json"), None
        except ValueError as e:
            return None, f"form failed validation: {str(e)[:300]}"
    try:
        obj = json.loads(raw)
    except ValueError as e:
        return None, f"reply is not JSON: {e}"
    if not isinstance(obj, dict):
        return None, "reply is not a JSON object"
    return obj, None


def _call_code_or_sql(arm: str, model: str, system: str, question: str) -> tuple[str, dict, str | None]:
    key = load_settings().groq_api_key
    if not key:
        raise RuntimeError("GROQ_API_KEY not set in .env")
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": question}],
        "temperature": 0,
        "max_completion_tokens": CODE_MAX_TOKENS,
        "reasoning_effort": "low",
        "response_format": {"type": "json_object"},
    }
    r = router._post(body, key, TIMEOUT_S)
    if r.status_code == 400 and "json_validate_failed" in r.text:
        # The reply was not valid JSON once; one more try at the same settings, as the form arm gets.
        r = router._post(body, key, TIMEOUT_S)
    if r.status_code == 429:
        raise DailyLimitReached(f"429 from Groq: {r.text[:200]}")
    if r.status_code >= 400:
        raise router.GroqError(f"{r.status_code} from Groq: {r.text[:300]}")
    data = r.json()
    choice = data["choices"][0]
    return choice["message"].get("content") or "", data.get("usage", {}), choice.get("finish_reason")


def generate(arm: str, question: str, model: str, registry: Registry, now_local: str,
             use_cache: bool = True, dry_run: bool = False) -> Generation:
    """One model reply for one arm and question (from the cache when present)."""
    q = " ".join(question.split())
    system = system_prompt(arm, registry, now_local)
    g = Generation(arm=arm, model=model, question=q, prompt_version=_version(arm),
                   prompt_hash=prompts.prompt_hash(system))
    if arm == "form" and model == "stub":
        # The app's rule-based router: a no-key, no-budget run of the whole pipeline, and a
        # floor for the form arm. Not a model; reported separately if used at all.
        g.parsed = stub_router.route(q, None).model_dump(mode="json")
        g.raw = json.dumps(g.parsed)
        return g
    if arm == "form" and (not q or len(q) > 400):
        # The app's own pre-checks (router.route): no model call for these.
        intent = ViewIntent(in_scope=False) if not q else ViewIntent(
            clarify="Please ask a shorter question (one or two sentences).")
        g.parsed, g.raw = intent.model_dump(mode="json"), intent.model_dump_json()
        return g
    path = CACHE_DIR / arm / f"{cache_key(arm, model, q, system)}.json"
    if use_cache and path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        g.raw, g.usage, g.finish_reason = cached["raw"], cached.get("usage", {}), cached.get("finish_reason")
        g.latency_s = cached.get("latency_s", 0.0)
        g.parsed, g.error = parse_reply(arm, g.raw)
        g.cached = True
        return g
    if dry_run:
        g.error = "dry run: not in cache"
        return g
    if not load_settings().groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set in .env; generation needs it (scoring does not)")
    g.called = True
    t0 = time.time()
    try:
        if arm == "form":
            raw, usage = router.call_groq(q, model)
            finish = None
        else:
            raw, usage, finish = _call_code_or_sql(arm, model, system, q)
    except DailyLimitReached:
        raise
    except router.GroqError as e:
        if "429" in str(e)[:4]:
            raise DailyLimitReached(str(e)[:200]) from None
        g.error, g.latency_s = f"GroqError: {str(e)[:300]}", time.time() - t0
        _log({"ts": time.time(), "arm": arm, "model": model, "ok": False, "error": g.error, "question": q})
        return g
    except Exception as e:  # noqa: BLE001 - network and parsing failures are recorded, not raised
        g.error, g.latency_s = f"{type(e).__name__}: {str(e)[:300]}", time.time() - t0
        _log({"ts": time.time(), "arm": arm, "model": model, "ok": False, "error": g.error, "question": q})
        return g
    g.latency_s = time.time() - t0
    g.raw, g.usage, g.finish_reason = raw, usage, finish
    g.parsed, g.error = parse_reply(arm, raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"raw": raw, "usage": usage, "finish_reason": finish,
                                "latency_s": round(g.latency_s, 3), "model": model, "arm": arm,
                                "prompt_version": g.prompt_version, "prompt_hash": g.prompt_hash},
                               ensure_ascii=False), encoding="utf-8")
    _log({"ts": time.time(), "arm": arm, "model": model, "ok": g.error is None, "latency_s": round(g.latency_s, 2),
          "usage": usage, "prompt_version": g.prompt_version, "prompt_hash": g.prompt_hash, "question": q})
    return g

"""Question -> ViewIntent via a language model, with strict validation.

The model is asked to return ONLY a JSON object matching the ViewIntent schema.
Nothing it returns is executed: the JSON is parsed, validated by Pydantic
(enumerations, lengths, forbidden characters), and then resolved by code.

Provider: Groq (OpenAI-compatible chat API, free tier).  If GROQ_API_KEY is
missing, or the call fails, `route()` falls back to the rule-based stub so the
app keeps working offline (weakness W7).  Every call is logged with the model
id and cached by prompt hash, so a benchmark run never pays twice (W13).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from pydantic import ValidationError

from airlume import __version__
from airlume.config import ROOT, load_settings
from airlume.nl import stub_router
from airlume.nl.schema import JSON_SCHEMA, ViewIntent

log = logging.getLogger("airlume.router")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
PRIMARY_MODEL = "openai/gpt-oss-120b"
SMALL_MODEL = "openai/gpt-oss-20b"
CACHE_DIR = ROOT / "data" / "cache" / "router"
LOG_PATH = ROOT / "data" / "cache" / "router_calls.jsonl"

SYSTEM_PROMPT = """You convert a user's question about air quality in Pakistan into a JSON form.
Return ONLY a JSON object that matches the schema. Never write code, SQL or prose.

Rules:
- Cities with data: Lahore (station level) and Punjab districts, Islamabad, Karachi, Peshawar, Quetta (city level). Default city is Lahore.
- Lahore stations: GT Road, Shahdara, Multan Road, Barki Road, Kahna Nau, Gulberg III, DHA Phase 6, Egerton Road, Punjab University, Wagha Border, Safari Park. If the user names a neighbourhood that is not a station (e.g. Model Town), put the neighbourhood name in `area`; code will find the nearest station.
- `time.label`: "now" for current conditions, "today", "yesterday", "last_7_days", "last_30_days", "this_month", "last_month", "same_day_last_year", or "custom_date"/"custom_range" with ISO dates.
- `aggregation`: "latest" for current values; "mean"/"max"/"min" over a window; "count_hours_above" with `threshold` for "how many hours above X".
- `compare_to`: "yesterday", "last_week", "last_year", or "other_city" (set `other_city`) when the question compares.
- `view`: "stations_3d" for Lahore station questions, "city_overview" for questions across cities or about one non-Lahore city, "compare" for comparisons, "timeline" for trends over days, "forecast" for tomorrow.
- `camera`: "station" when one place is asked about, "zoomed_out" for national questions, else "overview".
- If the question is not about air quality in these places, set `in_scope` to false.
- If the question is too vague to answer (e.g. "is it bad?"), set `clarify` to one short question back to the user.
- If the question refers to the previous answer ("and yesterday?"), set `context_ref` true and fill only what changed.
- Roman Urdu is allowed (e.g. "aaj Gulberg ki hawa kaisi hai" = how is the air in Gulberg today).
"""


@dataclass(frozen=True)
class RouteResult:
    intent: ViewIntent
    model: str  # model id, or "stub"
    cached: bool
    latency_s: float
    raw: str | None = None


def _cache_key(question: str, model: str, previous: dict | None) -> str:
    h = hashlib.sha256(f"{__version__}|{model}|{question}|{json.dumps(previous, sort_keys=True)}".encode()).hexdigest()
    return h[:32]


def _log(entry: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def call_groq(question: str, model: str, previous: dict | None = None, timeout: int = 30) -> tuple[str, dict]:
    """Return (raw JSON text, usage). Raises on HTTP or missing key."""
    key = load_settings().groq_api_key
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if previous:
        messages.append({"role": "system", "content": "Previous answer's form (for follow-ups): " + json.dumps(previous)})
    messages.append({"role": "user", "content": question})
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 400,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "view_intent", "schema": JSON_SCHEMA},
        },
    }
    r = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": f"Airlume/{__version__}"},
        json=body,
        timeout=timeout,
    )
    if r.status_code == 400 and "json_schema" in r.text:
        # Model without strict schema support: fall back to json_object mode.
        body["response_format"] = {"type": "json_object"}
        r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def route(question: str, model: str = PRIMARY_MODEL, previous: dict | None = None,
          use_cache: bool = True, allow_fallback: bool = True) -> RouteResult:
    q = " ".join(question.split())
    if not q:
        return RouteResult(ViewIntent(in_scope=False), "stub", False, 0.0)

    key = _cache_key(q, model, previous)
    cache_file = CACHE_DIR / f"{key}.json"
    if use_cache and cache_file.exists():
        try:
            raw = cache_file.read_text(encoding="utf-8")
            return RouteResult(ViewIntent.model_validate_json(raw), model, True, 0.0, raw)
        except (OSError, ValidationError):
            pass

    t0 = time.time()
    try:
        raw, usage = call_groq(q, model, previous)
        intent = ViewIntent.model_validate_json(raw)
        latency = time.time() - t0
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(raw, encoding="utf-8")
        _log({"ts": time.time(), "model": model, "question": q, "ok": True, "latency_s": round(latency, 2), "usage": usage})
        return RouteResult(intent, model, False, latency, raw)
    except (requests.RequestException, RuntimeError, ValidationError, ValueError, KeyError) as e:
        latency = time.time() - t0
        _log({"ts": time.time(), "model": model, "question": q, "ok": False, "error": f"{type(e).__name__}: {e}"[:300], "latency_s": round(latency, 2)})
        log.warning("router fallback to stub: %s", e)
        if not allow_fallback:
            raise
        return RouteResult(stub_router.route(q), "stub", False, latency)


def models_available() -> list[str]:
    return [PRIMARY_MODEL, SMALL_MODEL] if load_settings().groq_api_key else ["stub"]

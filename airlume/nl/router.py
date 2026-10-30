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
import re
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

SYSTEM_PROMPT = """You convert a question about air quality in Pakistan into a JSON form. Return ONLY the JSON object. Never write code, SQL or prose. Fill every field; use null where nothing applies.

Places
- Lahore has stations: GT Road, Shahdara, Multan Road, Barki Road, Kahna Nau, Gulberg III, DHA Phase 6, Egerton Road, Punjab University, Wagha Border, Safari Park.
- Other cities (city level only): Okara, Nankana Sahib, Muzaffargarh, Rajanpur, Chiniot, Jhang, Vehari, Khanewal, Sahiwal, Faisalabad, Gujranwala, Pakpattan, Multan, Sheikhupura, Attock, Dera Ghazi Khan, Kot Addu, Bahawalpur, Rahim Yar Khan, Kasur, Rawalpindi, Bhakkar, Sargodha, Narowal, Hafizabad, Murree, Khushab, Gujrat, Jhelum, Sialkot, Wazirabad, Mandi Bahauddin, Chakwal, Mianwali, Talagang, Islamabad, Karachi, Peshawar, Quetta.
- `city`: the city asked about; default "Lahore" when none is named. `area`: the station OR neighbourhood named inside the city (e.g. "Wagha Border", "DHA", "Model Town"); null when the question is about the whole city or ranks places. Code maps neighbourhoods to the nearest station: write the neighbourhood as the user said it ("Model Town"), never replace it with a station name.

Fields
- `metric`: "aqi" unless PM2.5 ("pm25") or PM10 ("pm10") is named.
- `time.label`: "now" (current, right now, at the moment, abhi), "today", "yesterday", "last_7_days" (last/this week, past week), "last_30_days", "this_month", "last_month", "same_day_last_year", "custom_date" (+date) or "custom_range" (+start,end). Nothing else is allowed. "Best time of day" questions use "last_7_days".
- `aggregation`: ALWAYS "latest" when time.label is "now" or the question is about this moment/this morning, even for "where is it worst/cleanest" (code ranks the latest values; "max"/"min" are for a past window only). Over a past window use "mean" (how bad was it), "max" (worst/peak), "min" (cleanest/best). "count_hours_above" with `threshold` for "how many hours above X" or "how often was it <band>".
- AQI bands (Punjab): Satisfactory >50, Moderate >100, Unhealthy for sensitive >150, Unhealthy >200, Very unhealthy >300, Hazardous >400. "hours unhealthy" means threshold 200; "hazardous" 400.
- `compare_to`: "yesterday", "last_week", "last_year" when the question compares with an earlier time (better/worse than, improved since, kal se); "other_city" with `other_city` when two cities are compared or shown side by side (`city` is the first one); else "none".
- `view`: "compare" whenever compare_to is not "none"; "forecast" for tomorrow, tonight, this evening, later today, will it be safe; "timeline" for trends, hour-of-day patterns, last N days; "city_overview" for a non-Lahore city or questions across cities/districts; "stations_3d" for Lahore station questions.
- `camera`: "station" when one station or area is asked about; "zoomed_out" whenever the question ranks or spans cities or districts (Pakistan, Punjab, "which city"); "north" if asked to look from the north; else "overview".
- `in_scope`: false if the question is not about air quality in these places (weather, rain, sunrise), asks why/for causes, asks about a person's own body (symptoms, diagnosis, treatment, "is my throat sore because of smog"), asks about a place with no monitor ("my village"), asks for a forecast further ahead than the next 48 hours ("next week", a date months away), or is only thanks/greeting/small talk ("thanks, that's all").
- Asking what to DO at the current level IS in scope: "should I wear a mask", "is it safe to go outside", "can the children play outside", "mujhe walk pr jana chahiye?". Fill the ordinary current-reading form for the place asked about (time now, aggregation latest) and let code attach the published advisory for that band. Only a question about one person's own body is out of scope.
- `clarify`: one short question back when the request cannot be filled (no place and no time, e.g. "is it bad?", "how many hours?", "AQI around my home?"); otherwise null.

Follow-ups
- When a "previous form" is supplied, assume the new message continues it unless it clearly names a different place or topic. Short messages like "and yesterday?", "over the last 7 days?", "show PM10 instead", "only Safari Park", "add Multan", "look from the north", "how far is that station?" are continuations: set `context_ref` true, start from the previous form (keep its city, area, compare_to and so on) and change only what the message changes.

Examples
- "What's the AQI at Wagha Border?" -> city Lahore, area "Wagha Border", time now, aggregation latest, view stations_3d, camera station.
- "Which district in Punjab is cleanest today?" -> city Lahore, area null, time today, aggregation min, view city_overview, camera overview.
- "Is Multan's air better than yesterday?" -> city Multan, time now, compare_to yesterday, view compare.
- "Which is cleaner this month, Multan or Bahawalpur?" -> city Multan, other_city Bahawalpur, compare_to other_city, time this_month, aggregation mean, view compare.
- "How many unhealthy hours in Kahna Nau yesterday?" -> area "Kahna Nau", time yesterday, aggregation count_hours_above, threshold 200.
- "Should I wear a mask today?" -> in_scope true, city Lahore, time now, aggregation latest, view stations_3d, camera overview (code adds the advisory).
- "Kiya mujhe walk pr jana chahiye aj?" -> same form: in_scope true, time now, aggregation latest.
- "Smog ki wajah se mera gala kharab hua hai?" -> in_scope false (a question about one person's body).
- "Next week me kitni smog ho gi?" -> in_scope false (further ahead than 48 hours).
- "Raat ko smog kam ho jati hai?" -> time last_7_days, aggregation mean, view timeline (an hour-of-day pattern).
- Roman Urdu is fine: "aaj Gulberg ki hawa kaisi hai" = how is the air in Gulberg today.
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


def strict_schema(schema: dict) -> dict:
    """Rewrite Pydantic's JSON schema into the subset structured-output APIs accept.

    - inline every ``$ref`` (no ``$defs``)
    - drop ``title``, ``default`` and ``description`` (defaults are not allowed in
      strict mode; descriptions duplicate the system prompt and cost tokens on
      every call, which matters under the free tier's tokens-per-minute cap)
    - every property required, ``additionalProperties: false``
    Optional fields stay nullable through their ``anyOf [..., {"type": "null"}]``.
    """
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, list):
            return [walk(n) for n in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            name = node["$ref"].rsplit("/", 1)[-1]
            return walk(defs[name])
        out = {k: walk(v) for k, v in node.items() if k not in ("title", "default", "description", "$defs")}
        if out.get("type") == "object" and "properties" in out:
            out["required"] = list(out["properties"].keys())
            out["additionalProperties"] = False
        return out

    return walk(schema)


STRICT_SCHEMA = strict_schema(JSON_SCHEMA)


class GroqError(RuntimeError):
    """HTTP error from Groq with the response body attached (the status alone says little)."""


_RETRY_RE = re.compile(r"try again in ([0-9.]+)(ms|s|m)")


def _retry_after(r: requests.Response) -> float:
    """Seconds to wait before retrying a 429, from the header or Groq's message text."""
    h = r.headers.get("retry-after")
    if h:
        try:
            return float(h)
        except ValueError:
            pass
    m = _RETRY_RE.search(r.text)
    if m:
        v, unit = float(m.group(1)), m.group(2)
        return v / 1000 if unit == "ms" else v * 60 if unit == "m" else v
    return 10.0


def _post(body: dict, key: str, timeout: int, retries: int = 6) -> requests.Response:
    """POST with wait-and-retry on 429 (free tier: 8,000 tokens per minute)."""
    for attempt in range(retries):
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "User-Agent": f"Airlume/{__version__}"},
            json=body,
            timeout=timeout,
        )
        if r.status_code != 429 or attempt == retries - 1:
            return r
        wait = _retry_after(r) + 0.5
        if wait > 120:
            # Not the per-minute cap but the daily one: waiting will not help. Fail now.
            log.warning("Groq daily token limit reached (retry in %.0f min); giving up", wait / 60)
            return r
        log.warning("rate limited; waiting %.0fs", wait)
        time.sleep(wait)
    return r


def call_groq(question: str, model: str, previous: dict | None = None, timeout: int = 30) -> tuple[str, dict]:
    """Return (raw JSON text, usage). Raises on HTTP or missing key.

    First try strict ``json_schema`` mode. If the API rejects the request (400),
    retry once in ``json_object`` mode with the schema pasted into the prompt;
    Pydantic validates the result either way, so the guarantee is unchanged.
    """
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
        # gpt-oss reasons before it answers; the thinking counts against this cap,
        # so it must be far larger than the ~150-token form. Low effort suits a
        # form-filling task and keeps the tokens-per-minute budget small.
        "max_completion_tokens": 2048,
        "reasoning_effort": "low",
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "view_intent", "strict": True, "schema": STRICT_SCHEMA},
        },
    }
    r = _post(body, key, timeout)
    if r.status_code == 400 and "json_validate_failed" in r.text:
        # the model's output did not satisfy the schema once; one more try at the same settings
        log.warning("schema validation failed once; retrying")
        r = _post(body, key, timeout)
    if r.status_code == 400:
        log.warning("json_schema mode rejected (%s); retrying in json_object mode", r.text[:300])
        body["messages"] = [messages[0] | {"content": SYSTEM_PROMPT + "\nJSON schema:\n" + json.dumps(STRICT_SCHEMA)}] + messages[1:]
        body["response_format"] = {"type": "json_object"}
        r = _post(body, key, timeout)
    if r.status_code >= 400:
        raise GroqError(f"{r.status_code} from Groq: {r.text[:500]}")
    data = r.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {})


MAX_CALLS_PER_HOUR = 150  # global guard: a public app must not be able to drain the daily budget


def calls_in_last(minutes: int) -> int:
    """Count live model calls in the last N minutes from the call log (cheap tail read)."""
    try:
        if not LOG_PATH.exists():
            return 0
        cutoff = time.time() - minutes * 60
        n = 0
        with open(LOG_PATH, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 200_000))
            for line in f.read().decode("utf-8", "replace").splitlines():
                try:
                    if json.loads(line).get("ts", 0) >= cutoff:
                        n += 1
                except ValueError:
                    continue
        return n
    except OSError:
        return 0


def route(question: str, model: str = PRIMARY_MODEL, previous: dict | None = None,
          use_cache: bool = True, allow_fallback: bool = True, max_len: int = 400) -> RouteResult:
    q = " ".join(question.split())
    if not q:
        return RouteResult(ViewIntent(in_scope=False), "stub", False, 0.0)
    if len(q) > max_len:
        # Long inputs cost tokens and are not questions; answer with a clarification, no model call.
        return RouteResult(ViewIntent(clarify="Please ask a shorter question (one or two sentences)."), "stub", False, 0.0)

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
        if allow_fallback and calls_in_last(60) >= MAX_CALLS_PER_HOUR:
            raise RuntimeError("hourly model-call budget reached; using the rule-based router")
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
        return RouteResult(stub_router.route(q, previous), "stub", False, latency)


def models_available() -> list[str]:
    return [PRIMARY_MODEL, SMALL_MODEL] if load_settings().groq_api_key else ["stub"]

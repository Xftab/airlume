import json

import pytest

from airlume.nl import router
from airlume.nl.schema import ViewIntent


def test_falls_back_to_stub_without_key(monkeypatch, tmp_path):
    monkeypatch.setattr(router, "CACHE_DIR", tmp_path / "c")
    monkeypatch.setattr(router, "LOG_PATH", tmp_path / "log.jsonl")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = router.route("Where is the air worst in Lahore right now?")
    assert r.model == "stub" and r.intent.city == "Lahore"
    assert "ok\": false" in (tmp_path / "log.jsonl").read_text()


def test_model_json_is_validated_and_cached(monkeypatch, tmp_path):
    monkeypatch.setattr(router, "CACHE_DIR", tmp_path / "c")
    monkeypatch.setattr(router, "LOG_PATH", tmp_path / "log.jsonl")
    good = json.dumps({"metric": "pm25", "city": "Lahore", "area": "Gulberg III", "time": {"label": "today"},
                       "aggregation": "mean", "view": "stations_3d", "camera": "station"})
    calls = []

    def fake_call(q, model, previous=None, timeout=30):
        calls.append(q)
        return good, {"total_tokens": 42}

    monkeypatch.setattr(router, "call_groq", fake_call)
    r1 = router.route("PM2.5 in Gulberg today", model="test-model")
    r2 = router.route("PM2.5 in Gulberg today", model="test-model")
    assert r1.intent.area == "Gulberg III" and r1.model == "test-model" and not r1.cached
    assert r2.cached and len(calls) == 1


def test_bad_model_output_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(router, "CACHE_DIR", tmp_path / "c")
    monkeypatch.setattr(router, "LOG_PATH", tmp_path / "log.jsonl")
    monkeypatch.setattr(router, "call_groq", lambda *a, **k: ('{"metric": "no2; DROP TABLE"}', {}))
    r = router.route("anything about Lahore air", model="m")
    assert r.model == "stub"
    with pytest.raises(Exception):
        router.route("anything about Lahore air", model="m", allow_fallback=False)


def test_schema_sent_is_the_real_one():
    assert router.JSON_SCHEMA == ViewIntent.model_json_schema()


def test_strict_schema_is_api_safe():
    from airlume.nl.router import STRICT_SCHEMA

    def walk(n):
        if isinstance(n, dict):
            assert "$ref" not in n and "default" not in n and "title" not in n
            if n.get("type") == "object" and "properties" in n:
                assert n["additionalProperties"] is False
                assert set(n["required"]) == set(n["properties"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(STRICT_SCHEMA)
    assert "time" in STRICT_SCHEMA["properties"]
    assert STRICT_SCHEMA["properties"]["time"]["type"] == "object"

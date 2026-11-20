"""Experiment A stays offline: the app never imports it, and no key leaves .env.

Design rule 1 (the language model never writes SQL or code at runtime) holds for the
app. The code and SQL arms exist only as controls in an offline experiment, so the
app, the pipeline and the language layer must never import them.
"""
import json
import re
from pathlib import Path

import pytest

from airlume.eval.expA import generate as gen
from airlume.eval.expA import items as items_mod
from airlume.eval.expA import prompts

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "airlume"
FAKE_KEY = "gsk_test_" + "x" * 40


def test_app_pipeline_and_language_layer_never_import_the_experiment():
    offenders = []
    for p in PKG.rglob("*.py"):
        rel = p.relative_to(PKG).parts
        if rel[0] == "eval":
            continue
        if re.search(r"^\s*(from|import)\s+[\w.]*expA", p.read_text(encoding="utf-8"), re.M):
            offenders.append(str(p))
    assert offenders == []


def test_experiment_modules_do_not_reach_into_the_ui_or_collectors():
    for p in (PKG / "eval" / "expA").glob("*.py"):
        src = p.read_text(encoding="utf-8")
        for banned in ("streamlit", "airlume.app", "airlume.collectors", "waqi"):
            assert banned not in src, (p.name, banned)


def test_runner_children_import_nothing_from_the_project():
    for name in ("_sql_runner.py", "_py_runner.py"):
        src = (PKG / "eval" / "expA" / name).read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from|import)\s+airlume", src, re.M), name
        assert "dotenv" not in src and "load_settings" not in src, name


def test_prompts_carry_rules_not_data(registry):
    for text in (prompts.code_prompt(registry, "2026-11-20 12:00:00"), prompts.sql_prompt(registry, "2026-11-20 12:00:00")):
        assert "2026-11-20 12:00:00" in text
        assert "Kahna Nau" in text and "Model Town" in text and "Multan" in text
        assert "GROQ" not in text and "gsk_" not in text
        assert "Unhealthy >200" in text and "nearest station" in text


class _FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, content: str):
        self._content = content

    def json(self):
        return {"choices": [{"message": {"content": self._content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1500, "completion_tokens": 200, "total_tokens": 1700}}


def test_generation_caches_and_logs_without_the_key(monkeypatch, tmp_path, registry):
    seen = {}

    def fake_post(body, key, timeout, retries=6):
        seen["key"], seen["body"] = key, body
        return _FakeResponse(json.dumps({"refuse": False, "clarify": None, "sql": "SELECT 1 AS value"}))

    class S:
        groq_api_key = FAKE_KEY

    monkeypatch.setattr(gen, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(gen, "LOG_PATH", tmp_path / "cache" / "calls.jsonl")
    monkeypatch.setattr(gen, "load_settings", lambda: S())
    monkeypatch.setattr(gen.router, "_post", fake_post)
    g = gen.generate("sql", "  What is the AQI   at GT Road? ", "openai/gpt-oss-120b", registry, "2026-11-20 12:00:00")
    assert g.error is None and g.parsed["sql"] == "SELECT 1 AS value" and not g.cached and g.called
    assert g.question == "What is the AQI at GT Road?"
    body = seen["body"]
    assert seen["key"] == FAKE_KEY and body["temperature"] == 0 and body["reasoning_effort"] == "low"
    assert body["response_format"] == {"type": "json_object"}
    again = gen.generate("sql", "What is the AQI at GT Road?", "openai/gpt-oss-120b", registry, "2026-11-20 12:00:00")
    assert again.cached and not again.called and again.parsed == g.parsed
    for f in (tmp_path / "cache").rglob("*"):
        if f.is_file():
            assert FAKE_KEY not in f.read_text(encoding="utf-8"), f


def test_prompt_change_means_a_new_cache_entry(registry):
    a = gen.cache_key("code", "m", "q", prompts.code_prompt(registry, "2026-11-20 12:00:00"))
    b = gen.cache_key("code", "m", "q", prompts.code_prompt(registry, "2026-11-21 12:00:00"))
    assert a != b


def test_form_arm_prechecks_match_the_app(registry):
    long_q = "is the air bad " * 40
    g = gen.generate("form", long_q, "openai/gpt-oss-120b", registry, "2026-11-20 12:00:00", dry_run=True)
    assert g.parsed["clarify"] and g.error is None


def test_dry_run_never_calls_the_model(monkeypatch, tmp_path, registry):
    monkeypatch.setattr(gen, "CACHE_DIR", tmp_path / "empty")

    def boom(*a, **k):
        raise AssertionError("dry run must not call the API")

    monkeypatch.setattr(gen.router, "_post", boom)
    g = gen.generate("code", "How is the air?", "openai/gpt-oss-120b", registry, "2026-11-20 12:00:00", dry_run=True)
    assert g.error == "dry run: not in cache"


@pytest.mark.parametrize("path", sorted((PKG / "eval" / "expA").glob("*.jsonl")))
def test_item_files_in_the_repo_are_valid(path):
    its = items_mod.load(path)
    assert its and items_mod.check(its) == []

"""WAQI values must never be stored. No module except the app may import waqi_display."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "airlume"


def test_only_app_imports_waqi_display():
    offenders = []
    for p in ROOT.rglob("*.py"):
        if p.name == "waqi_display.py" or "app" in p.parts:
            continue
        if re.search(r"^\s*(from|import)\s+[\w.]*waqi_display", p.read_text(encoding="utf-8"), re.M):
            offenders.append(str(p))
    assert offenders == []


def test_waqi_module_never_touches_store_or_files():
    src = (ROOT / "collectors" / "waqi_display.py").read_text(encoding="utf-8")
    for banned in ("pipeline.store", "duckdb", "to_csv", "to_parquet", "open(", "Path("):
        assert banned not in src, banned

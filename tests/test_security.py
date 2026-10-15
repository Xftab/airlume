"""Security checklist guards (plan S6, S8, S10)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "airlume" / "app" / "streamlit_app.py").read_text(encoding="utf-8")


def test_unsafe_html_only_for_the_static_header():
    uses = [m.start() for m in re.finditer(r"unsafe_allow_html\s*=\s*True", APP)]
    assert len(uses) == 1
    block = APP[max(0, uses[0] - 400): uses[0]]
    assert "Airlume" in block and "question" not in block.lower()


def test_user_text_is_markdown_escaped():
    assert "md_escape(q)" in APP and "md_escape(intent.clarify)" in APP


def test_router_has_global_and_length_caps():
    from airlume.nl import router
    assert router.MAX_CALLS_PER_HOUR <= 200
    r = router.route("x" * 500, allow_fallback=True)
    assert r.intent.clarify and r.model == "stub"


def test_error_details_hidden_from_viewers():
    cfg = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'showErrorDetails = "type"' in cfg and "enableXsrfProtection = true" in cfg

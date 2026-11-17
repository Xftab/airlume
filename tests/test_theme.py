"""Interface theme guards (plan, "Interface design", redesigned 17 Nov 2026).

The look is a static stylesheet in the repo. These tests pin the three things that
could quietly go wrong: the stylesheet becoming a second way to inject HTML, the
stylesheet reaching out to the network, and the palette losing its contrast.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "airlume" / "app" / "assets" / "airlume.css").read_text(encoding="utf-8")
APP = (ROOT / "airlume" / "app" / "streamlit_app.py").read_text(encoding="utf-8")
CFG = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")

CREAM, INK, INK_SOFT = "#F4F6FA", "#0F1B2D", "#475467"   # CREAM now names the cool page ground
BURNT, BURNT_DEEP = "#2457C5", "#1B3F94"                  # BURNT now names the blue accent


def _lum(h: str) -> float:
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ratio(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_stylesheet_is_a_repo_file_passed_to_st_html_not_built_from_text():
    assert 'st.html(Path(__file__).parent / "assets" / "airlume.css")' in APP
    assert APP.count("st.html(") == 1


def test_stylesheet_fetches_nothing_and_runs_nothing():
    low = CSS.lower()
    for bad in ("@import", "url(", "javascript:", "expression(", "<script", "behavior:"):
        assert bad not in low, bad


def test_theme_palette_is_declared_once_in_config_and_in_the_stylesheet():
    for colour in (CREAM, INK, BURNT):
        assert colour.lower() in CFG.lower()
        assert colour.lower() in CSS.lower()


def test_palette_contrast():
    assert _ratio(INK, CREAM) >= 12          # body text
    assert _ratio(INK_SOFT, CREAM) >= 4.5    # captions
    assert _ratio(BURNT_DEEP, CREAM) >= 4.5  # small orange text
    assert _ratio(BURNT, CREAM) >= 3.0       # fills, rings and large numbers only

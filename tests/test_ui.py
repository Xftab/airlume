"""Answer layout helpers and band hooks (17 Nov 2026)."""
import re
from pathlib import Path

from airlume.aqi import PUNJAB_BANDS
from airlume.app.ui import BAND_SLUGS, advice_parts, band_slug, split_answer

CSS = (Path(__file__).resolve().parents[1] / "airlume" / "app" / "assets" / "airlume.css").read_text(encoding="utf-8")


def test_one_slug_per_band_in_order():
    assert len(BAND_SLUGS) == len(PUNJAB_BANDS) == 7
    assert BAND_SLUGS[0] == "good" and BAND_SLUGS[-1] == "hazardous"


def test_stylesheet_band_colours_match_the_official_table():
    for slug, band in zip(BAND_SLUGS, PUNJAB_BANDS):
        m = re.search(r'st-key-band-%s-"\]\s*\{\s*--band:\s*(#[0-9A-Fa-f]{6})' % re.escape(slug), CSS)
        assert m, slug
        assert m.group(1).lower() == band.colour.lower(), slug


def test_stylesheet_has_no_angle_brackets():
    # st.html drops the whole stylesheet if the sanitiser sees tag-like text in it
    assert "<" not in CSS


def test_band_slug():
    assert band_slug(None) is None and band_slug(float("nan")) is None
    assert band_slug(30) == "good" and band_slug(172) == "usg"


def test_split_answer_keeps_words():
    t = "Worst now: A at 172. Detail one. Advice for A: Stay in. Wear a mask."
    head, detail, adv = split_answer(t)
    assert head == "Worst now: A at 172." and detail == ["Detail one."]
    assert " ".join([head, *detail, *adv]) == t
    assert advice_parts(adv) == ("What to do near A", "Stay in. Wear a mask.")
    assert split_answer("") == ("", [], [])

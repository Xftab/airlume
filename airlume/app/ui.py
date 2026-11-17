"""Small, testable helpers for how the app presents an answer (17 Nov 2026).

Nothing here talks to Streamlit. The answer sentence is written by code in
`nl/answer.py`; this module only decides how to lay it out, and which of the seven
Punjab band slugs a number belongs to. The slug is chosen from a fixed list, never
built from user or model text, so it is safe to use as a CSS hook (the stylesheet
colours `st.container(key="band-<slug>-...")` from the official band table).
"""
from __future__ import annotations

import re

from airlume.aqi import PUNJAB_BANDS, band_for

# One slug per Punjab EPA band, in band order. tests/test_ui.py pins the order and the
# colours in the stylesheet against aqi.PUNJAB_BANDS, so the two can never drift apart.
BAND_SLUGS = ("good", "satisfactory", "moderate", "usg", "unhealthy", "very-unhealthy", "hazardous")

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_ADVICE = re.compile(r"Advice(?: for ([^:]+))?:\s*(.*)", re.S)

TIME_WORDS = {
    "now": "right now", "today": "today", "yesterday": "yesterday",
    "last_7_days": "last 7 days", "last_30_days": "last 30 days",
    "this_month": "this month", "last_month": "last month",
    "same_day_last_year": "same day last year",
}


def band_slug(aqi: float | None) -> str | None:
    """The slug of the Punjab band an AQI falls in; None when there is no value."""
    if aqi is None or aqi != aqi:  # None or NaN
        return None
    b = band_for(int(aqi))
    if b is None:
        return None
    return BAND_SLUGS[PUNJAB_BANDS.index(b)]


def split_answer(text: str) -> tuple[str, list[str], list[str]]:
    """Split a code-written answer into (headline, detail sentences, advice sentences).

    The headline is the first sentence. Advice starts at the first later sentence that
    begins "Advice" (which `answer._advice` always writes) and runs to the end. Anything
    in between is detail. If there is no advice, everything after the headline is detail.
    The words are never changed, only grouped.
    """
    parts = [p.strip() for p in _SENTENCE_END.split((text or "").strip()) if p.strip()]
    if not parts:
        return "", [], []
    head, rest = parts[0], parts[1:]
    for i, p in enumerate(rest):
        if p.startswith("Advice"):
            return head, rest[:i], rest[i:]
    return head, rest, []


def advice_parts(advice: list[str]) -> tuple[str, str]:
    """('What to do' label, body) for the advice sentences. The label names the place
    when the answer did ("Advice for Shahdara: ..." becomes "What to do near Shahdara")."""
    if not advice:
        return "", ""
    m = _ADVICE.match(advice[0])
    if not m:
        return "What to do", " ".join(advice)
    where, first = m.group(1), m.group(2).strip()
    label = f"What to do near {where.strip()}" if where else "What to do"
    return label, " ".join([first, *advice[1:]]).strip()

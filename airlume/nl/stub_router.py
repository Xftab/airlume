"""Rule-based stand-in for the language model (Phase 0 only).

It fills the same `ViewIntent` form from a few keyword rules, so the UI and
resolver can be exercised before an API key exists.  Phase 3 replaces this
with `router.py`, which calls the model with the JSON schema and the same
validation.  Keep this file: it is also the offline fallback (weakness W7).
"""

from __future__ import annotations

import re

from airlume.nl.schema import TimeSpec, ViewIntent
from airlume.pipeline.registry import KNOWN_AREAS

_CITIES = [
    "lahore", "karachi", "islamabad", "peshawar", "quetta", "faisalabad", "multan",
    "rawalpindi", "gujranwala", "sialkot", "sargodha", "bahawalpur", "sheikhupura",
    "kasur", "okara", "sahiwal", "jhang", "chiniot", "gujrat", "jhelum", "attock",
    "murree", "narowal", "hafizabad", "khanewal", "vehari", "pakpattan", "rajanpur",
    "muzaffargarh", "bhakkar", "mianwali", "khushab", "chakwal", "talagang", "wazirabad",
    "mandi bahauddin", "nankana sahib", "rahim yar khan", "dg khan", "kot addu",
]
_STATIONS = [
    "gt road", "shahdara", "multan road", "barki road", "kahna nau", "gulberg",
    "dha phase 6", "dha", "egerton road", "punjab university", "wagha border", "wagah",
    "safari park",
]


_FOLLOW_UP = re.compile(r"^(and|what about|how about|only|just|now|instead|show)\b|\binstead\b|^(kal|aur)\b")


def route(question: str, previous: dict | None = None) -> ViewIntent:
    q = " ".join(question.lower().split())
    if not q:
        return ViewIntent(in_scope=False)

    air_words = ("air", "aqi", "smog", "pollut", "pm", "breath", "worst", "clean", "best", "unhealthy")
    names_city = any(re.search(rf"\b{re.escape(c)}\b", q) for c in _CITIES)
    if previous and not names_city and (_FOLLOW_UP.search(q) or len(q.split()) <= 3):
        # Short follow-up ("and yesterday?"): keep the previous form, change what the words change.
        form = dict(previous)
        form["time"] = dict(form.get("time") or {})
        for label in ("yesterday", "today", "last_7_days", "last_30_days", "this_month", "last_month"):
            if label.replace("_", " ") in q or label in q or (label == "last_7_days" and "week" in q) or (label == "yesterday" and "kal" in q):
                form["time"]["label"] = label
                form["aggregation"] = "latest" if label in ("now", "today") else "mean"
        if re.search(r"pm\s*2\.?5", q):
            form["metric"] = "pm25"
        elif re.search(r"pm\s*10", q):
            form["metric"] = "pm10"
        if "north" in q:
            form["camera"] = "north"
        for st_name in _STATIONS:
            if st_name in q:
                form["area"] = st_name
        form["context_ref"] = False
        return ViewIntent.model_validate(form)
    if not any(w in q for w in air_words) and not names_city:
        return ViewIntent(in_scope=False, clarify="I can only answer about air quality in monitored cities.")

    metric = "pm25" if re.search(r"pm\s*2\.?5", q) else "pm10" if re.search(r"pm\s*10", q) else "aqi"

    city = "Lahore"
    for c in _CITIES:
        if re.search(rf"\b{re.escape(c)}\b", q):
            city = c.title() if c != "dg khan" else "Dera Ghazi Khan"
            break

    area = None
    for s in _STATIONS:
        if s in q:
            area = s
            break
    if area is None:
        for k in KNOWN_AREAS:
            if re.search(rf"\b{re.escape(k)}\b", q):
                area = k
                break

    if "yesterday" in q and "than" not in q and "compare" not in q:
        time = TimeSpec(label="yesterday")
    elif "last week" in q or "past week" in q or "7 days" in q:
        time = TimeSpec(label="last_7_days")
    elif "last month" in q:
        time = TimeSpec(label="last_month")
    elif "this month" in q:
        time = TimeSpec(label="this_month")
    elif "today" in q:
        time = TimeSpec(label="today")
    else:
        time = TimeSpec(label="now")

    aggregation = "latest"
    threshold = None
    m = re.search(r"(?:above|over|more than)\s+(\d{2,3})", q)
    if "how many hours" in q and m:
        aggregation, threshold = "count_hours_above", int(m.group(1))
    elif "average" in q or "mean" in q:
        aggregation = "mean"
    elif "worst" in q and time.label != "now":
        aggregation = "max"
    elif ("best" in q or "cleanest" in q or "lowest" in q) and time.label != "now":
        aggregation = "min"

    compare_to = "none"
    other_city = None
    if "than yesterday" in q or "vs yesterday" in q or "compared to yesterday" in q:
        compare_to = "yesterday"
    elif "last year" in q:
        compare_to = "last_year"
    else:
        found = [c for c in _CITIES if re.search(rf"\b{re.escape(c)}\b", q)]
        if len(found) >= 2:
            compare_to, other_city = "other_city", found[1].title()

    if compare_to != "none":
        view = "compare"
    elif city != "Lahore" or "pakistan" in q or "which city" in q or "all cities" in q:
        view = "city_overview"
    elif time.label in {"last_7_days", "last_30_days", "last_month", "this_month"}:
        view = "timeline"
    else:
        view = "stations_3d"

    camera = "station" if area else ("zoomed_out" if view == "city_overview" else "overview")

    return ViewIntent(
        metric=metric, city=city, area=area, time=time, aggregation=aggregation,
        threshold=threshold, compare_to=compare_to, other_city=other_city,
        view=view, camera=camera,
        context_ref=q.startswith(("and ", "what about ", "how about ")),
    )

"""Resolve a ViewIntent into concrete, validated query parameters.

- Time labels become (start, end) timestamps in Asia/Karachi.
- City and area names are matched against the registry (fuzzy, in code).
- Output is a `ResolvedQuery` that store.py turns into parameterised SQL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from difflib import get_close_matches
from zoneinfo import ZoneInfo

from airlume.config import TZ
from airlume.nl.schema import ViewIntent
from airlume.pipeline.registry import Registry

KARACHI = ZoneInfo(TZ)


@dataclass(frozen=True)
class ResolvedQuery:
    metric: str
    city_id: str
    station_id: str | None
    start: datetime
    end: datetime
    aggregation: str
    threshold: int | None
    compare_start: datetime | None
    compare_end: datetime | None
    compare_city_id: str | None
    view: str
    camera: str
    notes: tuple[str, ...]  # e.g. "nearest station to Model Town is Kahna Nau"


class ResolveError(ValueError):
    """Raised when the intent cannot be mapped onto real data."""


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, tzinfo=KARACHI)
    return start, start + timedelta(days=1)


def resolve_time(intent: ViewIntent, now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(KARACHI)
    today = now.date()
    t = intent.time
    if t.label == "now":
        return now - timedelta(hours=3), now
    if t.label == "today":
        return _day_bounds(today)
    if t.label == "yesterday":
        return _day_bounds(today - timedelta(days=1))
    if t.label == "last_7_days":
        s, _ = _day_bounds(today - timedelta(days=7))
        return s, now
    if t.label == "last_30_days":
        s, _ = _day_bounds(today - timedelta(days=30))
        return s, now
    if t.label == "this_month":
        s, _ = _day_bounds(today.replace(day=1))
        return s, now
    if t.label == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        s, _ = _day_bounds(last_prev.replace(day=1))
        e, _ = _day_bounds(first_this)
        return s, e
    if t.label == "same_day_last_year":
        try:
            d = today.replace(year=today.year - 1)
        except ValueError:  # 29 Feb
            d = today.replace(year=today.year - 1, day=28)
        return _day_bounds(d)
    if t.label == "custom_date":
        if not t.date:
            raise ResolveError("custom_date without a date")
        return _day_bounds(date.fromisoformat(t.date))
    if t.label == "custom_range":
        if not (t.start and t.end):
            raise ResolveError("custom_range without start/end")
        s, _ = _day_bounds(date.fromisoformat(t.start))
        _, e = _day_bounds(date.fromisoformat(t.end))
        if e <= s:
            raise ResolveError("range end must be after start")
        if (e - s).days > 400:
            raise ResolveError("range longer than 400 days is not allowed")
        return s, e
    raise ResolveError(f"unknown time label {t.label}")


def _shift(start: datetime, end: datetime, compare_to: str) -> tuple[datetime, datetime]:
    if compare_to == "yesterday":
        d = timedelta(days=1)
    elif compare_to == "last_week":
        d = timedelta(days=7)
    elif compare_to == "last_year":
        d = timedelta(days=365)
    else:
        raise ResolveError(f"cannot shift for {compare_to}")
    return start - d, end - d


def resolve(intent: ViewIntent, registry: Registry, now: datetime | None = None) -> ResolvedQuery:
    if not intent.in_scope:
        raise ResolveError("question is out of scope")
    if intent.clarify:
        raise ResolveError(f"clarify: {intent.clarify}")

    notes: list[str] = []
    city = registry.match_city(intent.city)
    if city is None:
        raise ResolveError(f"unknown city '{intent.city}'")

    station_id: str | None = None
    if intent.area:
        hit = registry.match_station(intent.area, city.city_id)
        if hit is None:
            raise ResolveError(f"no station matching '{intent.area}' in {city.name}")
        station_id, note = hit
        if note:
            notes.append(note)

    start, end = resolve_time(intent, now)

    cstart = cend = None
    compare_city_id = None
    if intent.compare_to in {"yesterday", "last_week", "last_year"}:
        cstart, cend = _shift(start, end, intent.compare_to)
    elif intent.compare_to == "other_city":
        other = registry.match_city(intent.other_city or "")
        if other is None:
            raise ResolveError(f"unknown city '{intent.other_city}'")
        compare_city_id = other.city_id
        cstart, cend = start, end

    return ResolvedQuery(
        metric=intent.metric,
        city_id=city.city_id,
        station_id=station_id,
        start=start,
        end=end,
        aggregation=intent.aggregation,
        threshold=intent.threshold,
        compare_start=cstart,
        compare_end=cend,
        compare_city_id=compare_city_id,
        view=intent.view,
        camera=intent.camera,
        notes=tuple(notes),
    )


def fuzzy(name: str, candidates: list[str], cutoff: float = 0.6) -> str | None:
    m = get_close_matches(name.lower(), [c.lower() for c in candidates], n=1, cutoff=cutoff)
    if not m:
        return None
    return candidates[[c.lower() for c in candidates].index(m[0])]

"""Run the form arm exactly as the app does: form -> resolve -> query -> sentence.

The store is an in-memory copy of the snapshot's raw tables (every source the app
holds, CAMS rows included), so the form arm sees what the deployed app would have
seen at the snapshot's cutoff. Nothing here changes the app's code path; it calls
`resolve` and `answer` directly.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from airlume.nl.answer import answer
from airlume.nl.resolve import ResolveError, resolve
from airlume.nl.schema import ViewIntent
from airlume.pipeline.registry import Registry
from airlume.pipeline.store import Store

from .normalize import Answer, FormParser, from_resolve_error


def build_store(raw: dict[str, pd.DataFrame]) -> Store:
    store = Store(":memory:")
    store.upsert_readings(raw["readings"])
    store.upsert_city_hourly(raw["city_hourly"])
    store.upsert_forecasts(raw["forecasts"])
    return store


def parser_for(registry: Registry) -> FormParser:
    return FormParser([s.name for s in registry.stations], [c.name for c in registry.cities])


def run_form(intent: ViewIntent, store: Store, registry: Registry, now: datetime,
             parser: FormParser | None = None) -> Answer:
    """One validated form -> the app's sentence -> an Answer."""
    kind = intent.response_kind()
    if kind == "refuse":
        return Answer("refuse", parsed_by="form")
    if kind == "clarify":
        return Answer("clarify", text=intent.clarify or "", parsed_by="form")
    try:
        q = resolve(intent, registry, now)
    except ResolveError as e:
        return from_resolve_error(str(e))
    try:
        text = answer(q, store, registry, pd.Timestamp(now))
    except Exception as e:  # noqa: BLE001 - a crash in the answer layer is a scored error, not a harness crash
        return Answer("error", detail=f"answer layer raised {type(e).__name__}: {e}"[:300], parsed_by="crash")
    city = registry.city(q.city_id)
    return (parser or parser_for(registry)).parse(text, default_city=city.name if city else None)

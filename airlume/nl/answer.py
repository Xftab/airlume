"""Turn a ResolvedQuery plus store results into one honest sentence.

Code writes the sentence from numbers; the language model is not involved,
so the text can never contradict the data (weakness W4).
"""

from __future__ import annotations

import pandas as pd

from airlume.aqi import band_for
from airlume.nl.resolve import ResolvedQuery
from airlume.pipeline.registry import Registry
from airlume.pipeline.store import Store

_METRIC_NAME = {"aqi": "AQI", "pm25": "PM2.5 (ug/m3)", "pm10": "PM10 (ug/m3)"}


def _fmt(v: float, metric: str) -> str:
    return f"{v:.0f}" if metric == "aqi" else f"{v:.1f}"


def answer(q: ResolvedQuery, store: Store, reg: Registry) -> str:
    city = reg.city(q.city_id)
    if q.city_id != "PB-LHE" or q.view == "city_overview" or q.compare_city_id:
        cf = store.latest_city_values().dropna(subset=[q.metric])
        if cf.empty:
            return "No city data is available yet."
        names = {c.city_id: c.name for c in reg.cities}
        if q.compare_city_id:
            a = cf[cf.city_id == q.city_id]
            b = cf[cf.city_id == q.compare_city_id]
            if a.empty or b.empty:
                return "One of the two cities has no recent data."
            va, vb = float(a[q.metric].iloc[0]), float(b[q.metric].iloc[0])
            worse = city.name if va >= vb else names[q.compare_city_id]
            return (f"{city.name}: {_METRIC_NAME[q.metric]} {_fmt(va, q.metric)} · "
                    f"{names[q.compare_city_id]}: {_fmt(vb, q.metric)}. {worse} is worse right now.")
        if q.aggregation == "min":
            r = cf.sort_values(q.metric).iloc[0]
        else:
            r = cf.sort_values(q.metric, ascending=False).iloc[0]
        row = cf[cf.city_id == q.city_id]
        own = f" {city.name} is at {_fmt(float(row[q.metric].iloc[0]), q.metric)}." if not row.empty else ""
        word = "cleanest" if q.aggregation == "min" else "worst"
        return (f"{names[r.city_id]} has the {word} air right now "
                f"({_METRIC_NAME[q.metric]} {_fmt(float(r[q.metric]), q.metric)}, "
                f"{band_for(int(r.aqi)).label.lower()}).{own}")

    stations = reg.stations_in(q.city_id)
    ids = [q.station_id] if q.station_id else [s.station_id for s in stations]
    name_of = {s.station_id: s.name for s in stations}
    df = store.aggregate(ids, q.start, q.end, q.metric, q.aggregation, q.threshold)
    if df.empty:
        return "No data for that place and time."

    window = f"{q.start.astimezone():%d %b %H:%M} to {q.end.astimezone():%d %b %H:%M}"
    if q.aggregation == "count_hours_above":
        total_hours = int((q.end - q.start).total_seconds() // 3600)
        parts = [f"{name_of[r.station_id]}: {int(r.value)} of {total_hours} h" for r in df.itertuples()]
        return (f"Hours with {_METRIC_NAME[q.metric]} above {q.threshold} ({window}): "
                + "; ".join(parts) + ".")

    col = q.metric if q.aggregation == "latest" else "value"
    df = df.dropna(subset=[col])
    if df.empty:
        return "No recent data for that place."
    if q.station_id:
        v = float(df[col].iloc[0])
        tail = f" ({band_for(int(v)).label.lower()})" if q.metric == "aqi" else ""
        when = "right now" if q.aggregation == "latest" else f"{q.aggregation}, {window}"
        return f"{name_of[q.station_id]}: {_METRIC_NAME[q.metric]} {_fmt(v, q.metric)}{tail}, {when}."
    worst = df.sort_values(col, ascending=False).iloc[0]
    best = df.sort_values(col).iloc[0]
    when = "right now" if q.aggregation == "latest" else f"({q.aggregation}, {window})"
    missing = len(ids) - len(df)
    miss = f" {missing} station(s) have no data." if missing else ""
    return (f"Worst {when}: {name_of[worst.station_id]} at {_fmt(float(worst[col]), q.metric)}; "
            f"cleanest: {name_of[best.station_id]} at {_fmt(float(best[col]), q.metric)}.{miss}")

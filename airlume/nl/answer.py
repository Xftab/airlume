"""Turn a ResolvedQuery plus store results into one honest sentence.

Code writes the sentence from numbers; the language model is not involved,
so the text can never contradict the data (weakness W4).
"""

from __future__ import annotations

import pandas as pd

from airlume.aqi import band_for
from airlume.insights.graded_response import response_for_aqi
from airlume.nl.resolve import ResolvedQuery
from airlume.pipeline.registry import Registry
from airlume.pipeline.store import Store

_METRIC_NAME = {"aqi": "AQI", "pm25": "PM2.5 (ug/m3)", "pm10": "PM10 (ug/m3)"}


def _fmt(v: float, metric: str) -> str:
    return f"{v:.0f}" if metric == "aqi" else f"{v:.1f}"


def _advice(q: ResolvedQuery, aqi: float | None, where: str | None = None) -> str:
    """The published advisory for a current AQI reading, or "" when none applies.

    Added 30 Oct 2026. The classmate questions showed about one in five asks what
    to *do* at the current level -- mask, walk, children outside -- and prompt v3
    refused every one of them. Prompt v4 accepts them as the ordinary
    current-reading form and the guidance is attached here rather than by the
    model: the wording comes from `insights.graded_response`, which carries the
    Punjab Smog Policy 2023 and WHO bands verbatim, so the sentence is still
    written by code from a number (design rule 2).

    Deliberately narrow:

    * Only on a current reading. An advisory about a window that has already
      closed would be telling someone what they should have done.
    * Only for AQI; a raw PM2.5 figure has no band to advise on.
    * Never on a forecast. `_forecast_answer` keeps "a prediction, never advice",
      which is the older rule and still the right one.
    * `where` names which reading the advice belongs to, because a city-wide
      answer quotes its worst station and the advice follows that station rather
      than the city as a whole.
    """
    if q.aggregation != "latest" or q.metric != "aqi" or aqi is None or pd.isna(aqi):
        return ""
    r = response_for_aqi(int(round(float(aqi))))
    if r is None:
        return ""
    return f" Advice for {where}: {r.outdoor_activity}" if where else f" Advice: {r.outdoor_activity}"


_FC_SOURCES = (("punjab_epa_forecast", "EPA Punjab"), ("open_meteo_cams_forecast", "CAMS model"))


def _when(ts: pd.Timestamp, now: pd.Timestamp, tz: str = "Asia/Karachi") -> str:
    """'16:00' today, '10:00 tomorrow' otherwise -- a 24-hour horizon crosses midnight."""
    local, today = ts.tz_convert(tz), now.tz_convert(tz).date()
    if local.date() == today:
        return f"{local:%H:%M}"
    if (local.date() - today).days == 1:
        return f"{local:%H:%M} tomorrow"
    return f"{local:%H:%M} on {local:%d %b}"


def _forecast_answer(q: ResolvedQuery, store: Store, reg: Registry,
                     now: pd.Timestamp | None = None) -> str:
    """Answer a question about the future from the stored relayed forecasts.

    Before 16 Oct a forecast question fell through to the station path and was
    answered with current readings -- the present given as an answer about the
    future. Rules kept here:

    * A prediction, never advice. "Will it be safe to go out?" gets the predicted
      AQI and the portal's own band label, never "safe" or "go out".
    * City-level only. Neither source forecasts a station, so a named station or
      neighbourhood is answered for Lahore and the sentence says so.
    * Every number carries its source and that source's measured error, or says
      plainly that there is not yet enough history to know it.
    """
    from airlume.forecast.skill import scorecard
    from airlume.forecast.window import lowest_window, outlook

    city = reg.city(q.city_id)
    fc = store.all_forecasts(q.city_id)
    if fc.empty:
        if q.city_id != "PB-LHE":
            return (f"No forecast is published for {city.name}; the EPA Punjab portal "
                    "publishes one for Lahore only.")
        return "No forecast is stored yet. Each hourly round captures the next 24 hours."

    sc = scorecard(store.forecast_errors_with_baselines(q.city_id))
    tz = "Asia/Karachi"
    ref = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now).tz_convert("UTC")
    parts = []
    for src, label in _FC_SOURCES:
        o = outlook(fc, src, now)
        if o is None:
            continue
        mae = None
        key = {"punjab_epa_forecast": "EPA Punjab", "open_meteo_cams_forecast": "CAMS"}[src]
        if not sc.empty and key in sc.index and pd.notna(sc.loc[key, "mae"]):
            mae = float(sc.loc[key, "mae"])
        w = lowest_window(fc, hours=2, source=src, now=now)
        band = band_for(int(round(o.mean_aqi)))
        text = (f"{label} forecasts {city.name}'s AQI over the next {o.n_hours} hours at around "
                f"{o.mean_aqi:.0f} ({band.label.lower() if band else 'unbanded'}), highest about "
                f"{o.max_aqi:.0f} at {_when(o.max_at, ref, tz)}")
        if w is not None:
            end = w.end + pd.Timedelta(hours=1)
            text += (f" and lowest around {w.mean_aqi:.0f} between "
                     f"{_when(w.start, ref, tz)} and {_when(end, ref, tz)}")
        text += "."
        text += (f" It has been out by about {mae:.0f} points on average so far."
                 if mae is not None else " Not enough scored history yet to say how accurate it is.")
        parts.append(text)

    if not parts:
        return "No forecast hours remain ahead in the stored issues; the next hourly round will add some."

    lead = ""
    if q.station_id:
        st = {s.station_id: s.name for s in reg.stations_in(q.city_id)}.get(q.station_id, q.station_id)
        lead = f"Forecasts are published for {city.name} as a whole, not for {st}. "
    return lead + " ".join(parts)


def answer(q: ResolvedQuery, store: Store, reg: Registry,
           now: pd.Timestamp | None = None) -> str:
    """`now` overrides the clock, and exists so a test can be deterministic.

    Added 30 Oct 2026. `_forecast_answer` already took `now`, but `answer` did
    not pass one through, so the single test that checked the dispatch had to
    run against the wall clock while every other test in that file pinned the
    date. Its fixture forecasts are anchored to 16 Oct, so the test passed when
    it was written and has failed every day since those hours fell into the
    past -- a red suite that says nothing about the code. Production callers
    leave this None and get the real clock.
    """
    city = reg.city(q.city_id)
    if q.view == "forecast":
        return _forecast_answer(q, store, reg, now)
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
                f"{band_for(int(r.aqi)).label.lower()}).{own}"
                + _advice(q, r.aqi, names[r.city_id]))

    stations = reg.stations_in(q.city_id)
    ids = [q.station_id] if q.station_id else [s.station_id for s in stations]
    name_of = {s.station_id: s.name for s in stations}
    df = store.aggregate(ids, q.start, q.end, q.metric, q.aggregation, q.threshold)
    if df.empty and q.metric == "aqi" and not q.station_id:
        # Station-level rows start when our own collection started; the city-level hourly
        # series (from the portal's 7-day trend) reaches further back. Use it, and say so.
        cur = store.city_series(q.city_id, q.start, q.end, "aqi")
        cur = cur[cur["source"] == "punjab_epa"]
        if not cur.empty:
            if q.aggregation == "count_hours_above" and q.threshold is not None:
                total = int((q.end - q.start).total_seconds() // 3600)
                return (f"City-level AQI (no station rows for that window yet): {int((cur['value'] > q.threshold).sum())} of "
                        f"{total} hours above {q.threshold}.")
            func = {"mean": "mean", "max": "max", "min": "min", "latest": "mean"}[q.aggregation]
            v = float(getattr(cur["value"], func)())
            text = f"{city.name} city-level AQI ({q.aggregation if q.aggregation != 'latest' else 'mean'} over the window): {v:.0f} ({band_for(int(v)).label.lower()})."
            if q.compare_start is not None:
                prev = store.city_series(q.city_id, q.compare_start, q.compare_end, "aqi")
                prev = prev[prev["source"] == "punjab_epa"]
                if not prev.empty:
                    pv = float(getattr(prev["value"], func)())
                    word = "worse" if v > pv else "better"
                    text += f" Compared window: {pv:.0f}. {word.capitalize()} by {abs(v - pv):.0f} points."
            return text + " Station-level detail starts from when hourly collection began."
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
        return (f"{name_of[q.station_id]}: {_METRIC_NAME[q.metric]} {_fmt(v, q.metric)}{tail}, {when}."
                + _advice(q, v, name_of[q.station_id]))
    worst = df.sort_values(col, ascending=False).iloc[0]
    best = df.sort_values(col).iloc[0]
    when = "right now" if q.aggregation == "latest" else f"({q.aggregation}, {window})"
    missing = len(ids) - len(df)
    miss = f" {missing} station(s) have no data." if missing else ""
    return (f"Worst {when}: {name_of[worst.station_id]} at {_fmt(float(worst[col]), q.metric)}; "
            f"cleanest: {name_of[best.station_id]} at {_fmt(float(best[col]), q.metric)}.{miss}"
            + _advice(q, worst[col], name_of[worst.station_id]))

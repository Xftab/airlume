"""Turn each arm's output into one comparable Answer, and write the code-arm sentences.

Every arm ends in the same shape: a kind (answer, no_data, refuse, clarify, error,
blocked), a place, a number and its unit. Scoring compares these with the gold
answer (score.py).

- Form arm: the app's own sentence (written by answer.py from the numbers) is read
  back with one pattern per sentence template in answer.py. The patterns are
  anchored on the registry's place names, so digits inside a name ("DHA Phase 6"),
  a metric name ("PM2.5"), a threshold ("above 200"), a date or a clock time are
  never taken as the answer. A sentence that matches no pattern is reported as
  "unparsed", never guessed (tests/test_expA_normalize.py pins every template).
- Code arm: the `result` dictionary the code set.
- SQL arm: the first row of the result, by column name.

For the code and SQL arms the sentence the person would see is then written here,
by code, from the place and number (design rule 2 holds in every arm).
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field

KINDS = ("answer", "no_data", "refuse", "clarify", "error", "blocked")
UNITS = ("aqi", "pm25", "pm10", "hours", "hour")


@dataclass
class Answer:
    kind: str
    place: str | None = None
    value: float | None = None
    unit: str | None = None
    previous: float | None = None
    text: str = ""                       # the sentence shown to the person
    detail: str = ""                     # error or block reason, parser notes
    hours_profile: dict = field(default_factory=dict)  # form arm, time-of-day answers
    pair: dict = field(default_factory=dict)  # form arm, two-city comparisons: both figures
    parsed_by: str = ""                  # which template matched (form arm)

    def to_dict(self) -> dict:
        return asdict(self)


def canon(name: str | None) -> str:
    """Comparable form of a place name: case, spaces and punctuation ignored."""
    return re.sub(r"[^a-z0-9]", "", (name or "").casefold())


def _num(v) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


# --------------------------------------------------------------------------- form arm

_METRIC = r"(?P<metric>AQI|PM2\.5 \(ug/m3\)|PM10 \(ug/m3\))"
_METRIC_UNIT = {"AQI": "aqi", "PM2.5 (ug/m3)": "pm25", "PM10 (ug/m3)": "pm10"}
_NUM = r"\d+(?:\.\d+)?"
_BAND = r"(?: \([a-z ]+\))?"

_NO_DATA_PREFIXES = (
    "No data", "No city data", "No forecast", "No recent data", "No hourly", "No ",
    "I have no recent", "I have no station-level", "I don't have data", "I don't know that area",
)


class FormParser:
    """Reads the app's answer sentences back into Answers. Built once per registry."""

    def __init__(self, station_names: list[str], city_names: list[str]):
        def alt(names):
            return "|".join(re.escape(n) for n in sorted(set(names), key=len, reverse=True))

        st, ct = alt(station_names), alt(city_names)
        place = alt(list(station_names) + list(city_names))
        self.patterns: list[tuple[str, re.Pattern]] = [(name, re.compile(rx)) for name, rx in [
            # forecasts (_forecast_answer): the EPA Punjab figure is the answer; CAMS only if alone
            ("forecast_epa", rf"EPA Punjab forecasts (?P<place>{ct})'s AQI over the next \d+ hours at around (?P<value>{_NUM})"),
            ("forecast_cams", rf"CAMS model forecasts (?P<place>{ct})'s AQI over the next \d+ hours at around (?P<value>{_NUM})"),
            # two cities over a window (_city_window_answer)
            ("city_pair_window", rf"^(?P<a>{ct}): (?P<what>.+?) (?P<va>{_NUM}) over \d+ h · (?P<b>{ct}): (?P<vb>{_NUM}) over \d+ h \(.+?\)\. (?P<w>{ct}) is (?:worse|cleaner)\."),
            # ranking of cities over a window
            ("city_rank_window", rf"^(?P<place>{ct}) had the (?:worst|cleanest) air over .+? \((?P<what>.+?) (?P<value>{_NUM})(?:, [a-z ]+)?; \d+ h of data;"),
            # one city over a window, optionally against an earlier window
            ("city_window", rf"^(?P<place>{ct}): (?P<what>.+?) (?P<value>{_NUM}){_BAND} over \d+ h of data \("),
            # station path fell back to the city series
            ("city_fallback_count", r"^City-level AQI \(no station rows for that window yet\): (?P<value>\d+) of \d+ hours above \d+\."),
            ("city_fallback_agg", rf"^(?P<place>{ct}) city-level AQI \([a-z]+ over the window\): (?P<value>{_NUM})"),
            # station counts: one entry per station with at least one hour above
            ("station_count", rf"^Hours with {_METRIC} above \d+ \(.+?\): (?P<list>.*?)\.$"),
            # one station
            ("station_one", rf"^(?P<place>{st}): {_METRIC} (?P<value>{_NUM}){_BAND}, (?:right now|[a-z_]+, .+?)\."),
            # "<city> right now: AQI v" (station path's city figure, or city path)
            ("city_now", rf"^(?P<place>{ct}) right now: {_METRIC} (?P<value>{_NUM})"),
            # Lahore, no city figure: only the spread across stations
            ("spread_only", r"^Right now: across \d+ stations"),
            # ranking of stations
            ("station_rank", rf"^(?P<word>Worst|Cleanest) (?:right now|\(.+?\)): (?P<place>{st}) at (?P<value>{_NUM});"),
            # two cities right now
            ("city_pair_now", rf"^(?P<a>{ct}): {_METRIC} (?P<va>{_NUM}) · (?P<b>{ct}): (?P<vb>{_NUM})\. (?P<w>{ct}) is worse right now\."),
            # ranking of cities right now
            ("city_rank_now", rf"^(?P<place>{ct}) has the (?:worst|cleanest) air right now \({_METRIC} (?P<value>{_NUM}),"),
            # time of day
            ("hour_of_day", rf"^(?P<place>{place})(?: \(city level\))?, average {_METRIC} by time of day, .+?: lowest around (?P<lo>\d\d):00 \({_NUM}\), highest around (?P<hi>\d\d):00 \({_NUM}\)\."),
        ]]
        self._count_item = re.compile(rf"(?P<st>{st}): (?P<k>\d+) of \d+ h")
        self._prev = re.compile(rf"(?:Comparison window|Compared window): (?P<prev>{_NUM})\b")

    def _unit_from(self, m: re.Match, what: str | None = None) -> str:
        if what is not None and what.startswith("hours with"):
            return "hours"
        g = m.groupdict()
        if g.get("metric"):
            return _METRIC_UNIT[g["metric"]]
        text = what or ""
        if "PM2.5" in text:
            return "pm25"
        if "PM10" in text:
            return "pm10"
        return "aqi"

    def parse(self, text: str, default_city: str | None = None) -> Answer:
        t = " ".join((text or "").split())
        if not t:
            return Answer("error", text=text, detail="empty answer")
        if "No data for the comparison window" in t:
            return Answer("no_data", text=text, parsed_by="comparison_missing")
        if t.startswith(_NO_DATA_PREFIXES):
            return Answer("no_data", text=text, parsed_by="no_data")

        found = {name: rx.search(t) for name, rx in self.patterns}
        m = found["forecast_epa"] or found["forecast_cams"]
        if m:
            by = "forecast_epa" if found["forecast_epa"] else "forecast_cams"
            return Answer("answer", place=m["place"], value=float(m["value"]), unit="aqi", text=text, parsed_by=by)

        for name in ("city_pair_window", "city_pair_now"):
            m = found[name]
            if m:
                w = m["w"]
                v = m["va"] if w == m["a"] else m["vb"]
                unit = self._unit_from(m, m.groupdict().get("what"))
                return Answer("answer", place=w, value=float(v), unit=unit, text=text, parsed_by=name,
                              pair={m["a"]: float(m["va"]), m["b"]: float(m["vb"])})

        for name in ("city_rank_window", "city_window"):
            m = found[name]
            if m:
                pm = self._prev.search(t)
                return Answer("answer", place=m["place"], value=float(m["value"]),
                              unit=self._unit_from(m, m["what"]),
                              previous=float(pm["prev"]) if pm else None, text=text, parsed_by=name)

        m = found["city_fallback_count"]
        if m:
            return Answer("answer", place=default_city, value=float(m["value"]), unit="hours", text=text,
                          parsed_by="city_fallback_count")
        m = found["city_fallback_agg"]
        if m:
            pm = self._prev.search(t)
            return Answer("answer", place=m["place"], value=float(m["value"]), unit="aqi",
                          previous=float(pm["prev"]) if pm else None, text=text, parsed_by="city_fallback_agg")

        m = found["station_count"]
        if m:
            items = list(self._count_item.finditer(m["list"]))
            unit = "hours"
            if len(items) == 1:
                return Answer("answer", place=items[0]["st"], value=float(items[0]["k"]), unit=unit, text=text,
                              parsed_by="station_count")
            note = "no station listed" if not items else f"{len(items)} stations listed, no single answer"
            return Answer("answer", unit=unit, text=text, detail=note, parsed_by="station_count")

        for name in ("station_one", "city_now", "station_rank", "city_rank_now"):
            m = found[name]
            if m:
                return Answer("answer", place=m["place"], value=float(m["value"]), unit=self._unit_from(m),
                              text=text, parsed_by=name)

        if found["spread_only"]:
            return Answer("answer", text=text, detail="range across stations only, no single figure",
                          parsed_by="spread_only")

        m = found["hour_of_day"]
        if m:
            return Answer("answer", place=m["place"], unit="hour", text=text, parsed_by="hour_of_day",
                          hours_profile={"lowest": int(m["lo"]), "highest": int(m["hi"])})

        return Answer("error", text=text, detail="unparsed: no answer template matched", parsed_by="unparsed")


_CLARIFY_RESOLVE = ("clarify:", "I could not tell", "range end must be after start",
                    "range longer than 400 days")


def from_resolve_error(message: str) -> Answer:
    """The resolver refused to build a query: map its message onto a kind."""
    if message.startswith("question is out of scope"):
        return Answer("refuse", text=message, parsed_by="resolve")
    if message.startswith(_CLARIFY_RESOLVE):
        text = message[len("clarify: "):] if message.startswith("clarify:") else message
        return Answer("clarify", text=text, parsed_by="resolve")
    return Answer("no_data", text=message, parsed_by="resolve")


# --------------------------------------------------------------------------- code and SQL arms

_UNIT_WORD = {"aqi": "AQI", "pm25": "PM2.5 (ug/m3)", "pm10": "PM10 (ug/m3)", "hours": "hours", "hour": "hour"}


def render(a: Answer) -> str:
    """The sentence a person would see for a code or SQL arm answer, written by code."""
    if a.kind == "refuse":
        return a.text or "That is outside what I can answer: air quality in Pakistan's monitored places."
    if a.kind == "clarify":
        return a.text or "Could you say which place and time you mean?"
    if a.kind == "no_data":
        return "No data for that place and time."
    if a.kind in ("error", "blocked"):
        return "Sorry, I could not answer that."
    v = a.value
    if a.unit == "hour":
        body = f"{a.place or 'There'}: around {int(v):02d}:00." if v is not None else "No single hour."
    elif a.unit == "hours":
        body = f"{a.place or 'There'}: {v:.0f} hours." if v is not None else "No single figure."
    else:
        fmt = f"{v:.0f}" if a.unit == "aqi" else f"{v:.1f}"
        body = f"{a.place or 'There'}: {_UNIT_WORD.get(a.unit or 'aqi', 'AQI')} {fmt}." if v is not None else "No single figure."
    if a.previous is not None and v is not None:
        body += f" Earlier window: {a.previous:.0f}."
    return body


def _clean_unit(u) -> str | None:
    u = str(u).strip().lower() if u is not None else None
    return u if u in UNITS else None


def from_model_reply(parsed: dict | None) -> Answer | None:
    """refuse/clarify from a code or SQL arm's JSON reply; None when it chose to answer."""
    if not isinstance(parsed, dict):
        return Answer("error", detail="reply is not a JSON object")
    if parsed.get("refuse") is True:
        return Answer("refuse")
    c = parsed.get("clarify")
    if isinstance(c, str) and c.strip():
        return Answer("clarify", text=c.strip()[:300])
    return None


def from_code_result(result) -> Answer:
    if not isinstance(result, dict):
        return Answer("error", detail="code did not set result to a dictionary")
    status = str(result.get("status", "")).strip().lower()
    value = _num(result.get("value"))
    place = result.get("place")
    place = str(place).strip() if place not in (None, "") else None
    unit = _clean_unit(result.get("unit"))
    if status == "no_data" or (status == "answer" and value is None):
        return Answer("no_data", place=place, unit=unit,
                      detail="" if status == "no_data" else "status answer without a value")
    if status != "answer":
        return Answer("error", detail=f"status {status!r} is not answer or no_data")
    return Answer("answer", place=place, value=value, unit=unit, previous=_num(result.get("previous")))


def from_sql_rows(columns: list[str] | None, rows: list | None) -> Answer:
    if not rows:
        return Answer("no_data", detail="zero rows")
    cols = [str(c).strip().lower() for c in (columns or [])]
    if "value" not in cols:
        return Answer("error", detail=f"no value column (columns: {cols[:8]})")
    row = dict(zip(cols, rows[0]))
    value = _num(row.get("value"))
    place = row.get("place")
    place = str(place).strip() if place not in (None, "") else None
    unit = _clean_unit(row.get("unit"))
    note = f"{len(rows)} rows; first used" if len(rows) > 1 else ""
    if value is None:
        return Answer("no_data", place=place, unit=unit, detail=(note + "; null value").strip("; "))
    return Answer("answer", place=place, value=value, unit=unit, previous=_num(row.get("previous")), detail=note)

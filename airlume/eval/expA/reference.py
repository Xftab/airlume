"""Gold answers for Experiment A: small, independent functions annotators call.

An annotator writes, for each question, one call such as

    station_agg("Kahna Nau", "yesterday", "count_above", threshold=200)
    city_latest("Multan")
    rank_stations("now", order="worst")
    compare_places("Multan", "Bahawalpur", "this_month", ask="cleaner")
    forecast_mean("Lahore")
    no_data()      refuse()      clarify()

and the call is executed on the frozen snapshot (and on its shifted copy). The
functions here read the analysis tables directly with pandas. They deliberately do
not import the app's resolver, store or answer code, so a bug there cannot leak into
the gold answers that grade the form arm (protocol, section 5).

The meaning of every time word is fixed in WINDOWS below and in the protocol's
semantics table; the code and SQL prompts state the same rules in words.
All times are Asia/Karachi wall-clock time without a zone, as in the tables.
"""

from __future__ import annotations

import ast
import math
from dataclasses import asdict, dataclass, field

import pandas as pd

METRICS = ("aqi", "pm25", "pm10")
AGGS = ("mean", "median", "max", "min", "count_above")
FRESH_HOURS = 3  # "now" = the latest reading at most this many hours old
WINDOWS = ("now", "today", "yesterday", "last_7_days", "last_30_days", "this_month", "last_month",
           "same_day_last_year")  # plus "date:YYYY-MM-DD", "range:YYYY-MM-DD:YYYY-MM-DD", "hours:N"
FORECAST_SOURCE = "EPA Punjab"


@dataclass
class Gold:
    """One expected answer. kind is answer, no_data, refuse or clarify."""

    kind: str
    place: str | None = None
    value: float | None = None
    unit: str | None = None          # aqi, pm25, pm10, hours (a count) or hour (0-23)
    previous: float | None = None    # the earlier window, for comparisons with an earlier time
    n: int | None = None             # hourly values the answer rests on
    tie_places: list[str] = field(default_factory=list)  # every place that ties for the top
    window: str | None = None        # "start to end", for the record
    which: str | None = None         # hour-of-day answers: "highest" or "lowest"
    pair: dict = field(default_factory=dict)  # two-place comparisons: {place: value} for both

    def to_dict(self) -> dict:
        return asdict(self)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Reference:
    """The gold-answer functions, bound to one snapshot's tables and 'now'."""

    def __init__(self, tables: dict[str, pd.DataFrame], now_local: pd.Timestamp):
        now = pd.Timestamp(now_local)
        if now.tzinfo is not None:
            now = now.tz_convert("Asia/Karachi").tz_localize(None)
        self.now = now
        self.t = tables
        self.station_names = {s.casefold(): s for s in tables["stations"]["station"]}
        self.city_names = {c.casefold(): c for c in tables["cities"]["city"]}

    # ------------------------------------------------------------------ helpers
    def window(self, when: str) -> tuple[pd.Timestamp, pd.Timestamp]:
        """[start, end) for a time word. 'now' is the freshness window for a latest reading."""
        now, midnight = self.now, self.now.normalize()
        day = pd.Timedelta(days=1)
        if when == "now":
            return now - pd.Timedelta(hours=FRESH_HOURS), now
        if when == "today":
            return midnight, now
        if when == "yesterday":
            return midnight - day, midnight
        if when == "last_7_days":
            return midnight - 7 * day, now
        if when == "last_30_days":
            return midnight - 30 * day, now
        if when == "this_month":
            return midnight.replace(day=1), now
        if when == "last_month":
            first = midnight.replace(day=1)
            return (first - day).replace(day=1), first
        if when == "same_day_last_year":
            d = midnight - pd.DateOffset(years=1)
            return d, d + day
        if when.startswith("date:"):
            d = pd.Timestamp(when[5:])
            return d, d + day
        if when.startswith("hours:"):
            n = int(when[6:])
            if not 1 <= n <= 72:
                raise ValueError("hours:N needs 1 <= N <= 72")
            return now - pd.Timedelta(hours=n), now
        if when.startswith("range:"):
            a, b = when[6:].split(":")
            s, e = pd.Timestamp(a), pd.Timestamp(b) + day
            if e <= s:
                raise ValueError(f"range end before start: {when}")
            return s, e
        raise ValueError(f"unknown time word {when!r}; use one of {WINDOWS} or date:/range:")

    @staticmethod
    def _wtext(s: pd.Timestamp, e: pd.Timestamp) -> str:
        return f"{s:%Y-%m-%d %H:%M} to {e:%Y-%m-%d %H:%M}"

    def place(self, name: str) -> tuple[str, str]:
        """('station' | 'city', canonical name). 'area:<name>' -> the nearest Lahore station."""
        if name.lower().startswith("area:"):
            return "station", self.nearest_station(name[5:])
        key = name.strip().casefold()
        if key in self.station_names:
            return "station", self.station_names[key]
        if key in self.city_names:
            return "city", self.city_names[key]
        raise ValueError(f"{name!r} is not a station or city name in the snapshot (use area:<name> for an area)")

    def nearest_station(self, area: str) -> str:
        a = self.t["areas"]
        row = a[a["area"].str.casefold() == area.strip().casefold()]
        if row.empty:
            raise ValueError(f"{area!r} is not in the areas table")
        lat, lon = float(row["lat"].iloc[0]), float(row["lon"].iloc[0])
        st = self.t["stations"]
        st = st[st["city"] == row["city"].iloc[0]]
        d = st.apply(lambda r: _haversine_km(lat, lon, r["lat"], r["lon"]), axis=1)
        return str(st.loc[d.idxmin(), "station"])

    def _series(self, kind: str, name: str, metric: str, start, end) -> pd.Series:
        """Hourly values of one place in [start, end), indexed by local time, nulls dropped."""
        if metric not in METRICS:
            raise ValueError(f"metric must be one of {METRICS}")
        if kind == "station":
            df = self.t["station_hourly"]
            df = df[df["station"] == name]
        else:
            df = self.t["city_hourly"]
            df = df[df["city"] == name]
        df = df[(df["ts_local"] >= start) & (df["ts_local"] < end)]
        s = pd.to_numeric(df[metric], errors="coerce")
        s.index = df["ts_local"]
        return s.dropna().sort_index()

    def _latest(self, kind: str, name: str, metric: str) -> tuple[float, pd.Timestamp] | None:
        s, e = self.window("now")
        ser = self._series(kind, name, metric, s, e + pd.Timedelta(microseconds=1))
        if ser.empty:
            return None
        return float(ser.iloc[-1]), ser.index[-1]

    @staticmethod
    def _agg(ser: pd.Series, agg: str, threshold: float | None) -> float:
        if agg == "mean":
            return float(ser.mean())
        if agg == "median":
            return float(ser.median())
        if agg == "max":
            return float(ser.max())
        if agg == "min":
            return float(ser.min())
        if agg == "count_above":
            if threshold is None:
                raise ValueError("count_above needs threshold=")
            return float((ser > threshold).sum())
        raise ValueError(f"agg must be one of {AGGS}")

    def _value(self, kind: str, name: str, when: str, agg: str, metric: str,
               threshold: float | None = None) -> tuple[float, int, str] | None:
        """(value, n, window text) for one place, or None when there is no value."""
        if when == "now":
            r = self._latest(kind, name, metric)
            if r is None:
                return None
            v, ts = r
            return v, 1, f"latest at {ts:%Y-%m-%d %H:%M}"
        s, e = self.window(when)
        ser = self._series(kind, name, metric, s, e)
        if ser.empty:
            return None
        return self._agg(ser, agg, threshold), int(len(ser)), self._wtext(s, e)

    @staticmethod
    def _unit(metric: str, agg: str) -> str:
        return "hours" if agg == "count_above" else metric

    # ------------------------------------------------------------------ gold functions
    def no_data(self) -> Gold:
        return Gold("no_data")

    def refuse(self) -> Gold:
        return Gold("refuse")

    def clarify(self) -> Gold:
        return Gold("clarify")

    def station_latest(self, station: str, metric: str = "aqi") -> Gold:
        return self.latest(station, metric)

    def city_latest(self, city: str, metric: str = "aqi") -> Gold:
        return self.latest(city, metric)

    def latest(self, place: str, metric: str = "aqi") -> Gold:
        kind, name = self.place(place)
        r = self._value(kind, name, "now", "mean", metric)
        if r is None:
            return Gold("no_data", place=name, unit=metric)
        v, n, w = r
        return Gold("answer", place=name, value=v, unit=metric, n=n, window=w)

    def station_agg(self, station: str, when: str, agg: str = "mean", metric: str = "aqi",
                    threshold: float | None = None) -> Gold:
        return self.agg(station, when, agg, metric, threshold)

    def city_agg(self, city: str, when: str, agg: str = "mean", metric: str = "aqi",
                 threshold: float | None = None) -> Gold:
        return self.agg(city, when, agg, metric, threshold)

    def agg(self, place: str, when: str, agg: str = "mean", metric: str = "aqi",
            threshold: float | None = None) -> Gold:
        if when == "now":
            return self.latest(place, metric)
        kind, name = self.place(place)
        r = self._value(kind, name, when, agg, metric, threshold)
        if r is None:
            return Gold("no_data", place=name, unit=self._unit(metric, agg))
        v, n, w = r
        return Gold("answer", place=name, value=v, unit=self._unit(metric, agg), n=n, window=w)

    def hours_above(self, place: str, when: str, threshold: float, metric: str = "aqi") -> Gold:
        return self.agg(place, when, "count_above", metric, threshold)

    def _rank(self, kind: str, names: list[str], when: str, order: str, agg: str, metric: str,
              position: int = 1) -> Gold:
        if order not in ("worst", "cleanest"):
            raise ValueError("order must be worst or cleanest")
        if position < 1:
            raise ValueError("position counts from 1")
        vals = {}
        for nm in names:
            r = self._value(kind, nm, when, agg, metric)
            if r is not None:
                vals[nm] = r
        if not vals:
            return Gold("no_data", unit=metric)
        if position > 1:
            ranked = sorted(vals.items(), key=lambda kv: (-kv[1][0] if order == "worst" else kv[1][0], kv[0]))
            if len(ranked) < position:
                return Gold("no_data", unit=metric)
            nm, (v, n, w) = ranked[position - 1]
            return Gold("answer", place=nm, value=v, unit=metric, n=n, window=w)
        best = (max if order == "worst" else min)(v[0] for v in vals.values())
        tops = sorted(nm for nm, v in vals.items() if abs(v[0] - best) < 1e-9)
        nm = tops[0]
        v, n, w = vals[nm]
        return Gold("answer", place=nm, value=v, unit=metric, n=n, window=w,
                    tie_places=tops if len(tops) > 1 else [])

    def rank_stations(self, when: str, order: str = "worst", agg: str = "mean", metric: str = "aqi",
                      city: str = "Lahore", position: int = 1) -> Gold:
        st = self.t["stations"]
        names = sorted(st.loc[st["city"] == self.place(city)[1], "station"])
        return self._rank("station", names, when, order, agg, metric, position)

    def rank_cities(self, when: str, order: str = "worst", agg: str = "mean", metric: str = "aqi",
                    position: int = 1) -> Gold:
        names = sorted(self.t["cities"]["city"])
        return self._rank("city", names, when, order, agg, metric, position)

    def compare_places(self, a: str, b: str, when: str, ask: str = "worse", agg: str = "mean",
                       metric: str = "aqi") -> Gold:
        if ask not in ("worse", "cleaner"):
            raise ValueError("ask must be worse or cleaner")
        (ka, na), (kb, nb) = self.place(a), self.place(b)
        ra, rb = self._value(ka, na, when, agg, metric), self._value(kb, nb, when, agg, metric)
        if ra is None or rb is None:
            return Gold("no_data", unit=metric)
        (va, n_a, w), (vb, n_b, _) = ra, rb
        pair = {na: va, nb: vb}
        if abs(va - vb) < 1e-9:
            return Gold("answer", place=na, value=va, unit=metric, n=min(n_a, n_b), window=w,
                        tie_places=[na, nb], pair=pair)
        pick_a = (va > vb) if ask == "worse" else (va < vb)
        return Gold("answer", place=na if pick_a else nb, value=va if pick_a else vb, unit=metric,
                    n=n_a if pick_a else n_b, window=w, pair=pair)

    def difference_places(self, a: str, b: str, when: str, agg: str = "mean", metric: str = "aqi") -> Gold:
        """a's value minus b's (a question the form cannot state; place left empty)."""
        (ka, na), (kb, nb) = self.place(a), self.place(b)
        ra, rb = self._value(ka, na, when, agg, metric), self._value(kb, nb, when, agg, metric)
        if ra is None or rb is None:
            return Gold("no_data", unit=metric)
        return Gold("answer", value=ra[0] - rb[0], unit=metric, n=min(ra[1], rb[1]), window=ra[2])

    def compare_time(self, place: str, when: str, against: str, agg: str = "mean",
                     metric: str = "aqi") -> Gold:
        """The place's value now (today so far, for 'now') and for the same span earlier."""
        shift = {"yesterday": pd.Timedelta(days=1), "last_week": pd.Timedelta(days=7),
                 "last_year": pd.Timedelta(days=365)}.get(against)
        if shift is None:
            raise ValueError("against must be yesterday, last_week or last_year")
        kind, name = self.place(place)
        s, e = (self.now.normalize(), self.now) if when == "now" else self.window(when)
        cur = self._series(kind, name, metric, s, e)
        prev = self._series(kind, name, metric, s - shift, e - shift)
        if cur.empty or prev.empty:
            return Gold("no_data", place=name, unit=metric)
        return Gold("answer", place=name, value=self._agg(cur, agg, None), unit=metric,
                    previous=self._agg(prev, agg, None), n=int(len(cur)), window=self._wtext(s, e))

    def forecast_mean(self, city: str = "Lahore") -> Gold:
        """Mean AQI of the latest EPA Punjab issue, over its target hours from the current hour on."""
        _, name = self.place(city)
        f = self.t["forecast"]
        f = f[(f["city"] == name) & (f["source"] == FORECAST_SOURCE)].dropna(subset=["aqi"])
        if f.empty:
            return Gold("no_data", place=name, unit="aqi")
        latest = f["issued_local"].max()
        f = f[f["issued_local"] == latest].drop_duplicates(subset=["target_local"], keep="last")
        f = f[f["target_local"] >= self.now.floor("h")]
        if f.empty:
            return Gold("no_data", place=name, unit="aqi")
        return Gold("answer", place=name, value=float(pd.to_numeric(f["aqi"]).mean()), unit="aqi",
                    n=int(len(f)), window=f"issue {latest:%Y-%m-%d %H:%M}")

    def peak_hour(self, place: str, when: str = "last_7_days", lowest: bool = False,
                  metric: str = "aqi") -> Gold:
        """The hour of the day (0-23) with the highest (or lowest) mean over the window."""
        kind, name = self.place(place)
        s, e = self.window(when)
        ser = self._series(kind, name, metric, s, e)
        if ser.empty:
            return Gold("no_data", place=name, unit="hour")
        by_hour = ser.groupby(ser.index.hour).mean()
        h = int(by_hour.idxmin() if lowest else by_hour.idxmax())
        return Gold("answer", place=name, value=float(h), unit="hour", n=int(len(ser)),
                    window=self._wtext(s, e), which="lowest" if lowest else "highest")


# --------------------------------------------------------------------------- evaluation

GOLD_FUNCTIONS = frozenset({
    "no_data", "refuse", "clarify", "latest", "station_latest", "city_latest", "agg", "station_agg",
    "city_agg", "hours_above", "rank_stations", "rank_cities", "compare_places", "compare_time",
    "difference_places", "forecast_mean", "peak_hour",
})


def parse_reference(expr: str) -> tuple[str, list, dict]:
    """Check that a reference is ONE call to a gold function with literal arguments.

    Annotators' text is data, not code: it is parsed, never passed to eval().
    """
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"reference is not a valid call: {expr!r} ({e.msg})") from None
    call = tree.body
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        raise ValueError(f"reference must be one call such as city_latest(\"Multan\"): {expr!r}")
    if call.func.id not in GOLD_FUNCTIONS:
        raise ValueError(f"unknown gold function {call.func.id!r}; allowed: {sorted(GOLD_FUNCTIONS)}")
    try:
        args = [ast.literal_eval(a) for a in call.args]
        kwargs = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
    except ValueError:
        raise ValueError(f"reference arguments must be plain values (text, numbers, True/False): {expr!r}") from None
    if any(k is None for k in kwargs):
        raise ValueError(f"**kwargs are not allowed in a reference: {expr!r}")
    return call.func.id, args, kwargs


def evaluate_reference(expr: str, ref: Reference) -> Gold:
    name, args, kwargs = parse_reference(expr)
    return getattr(ref, name)(*args, **kwargs)

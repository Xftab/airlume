"""Airlume - Streamlit application.

Question -> language model fills the typed ViewIntent form (or the rule-based
stand-in when no key is configured) -> code validates and resolves it -> code
builds the query and the answer sentence -> deck.gl renders the view.

Data: the committed CSV archive (live hourly readings + the EPD daily history)
is the source of record; fake data is used only when nothing real exists yet.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from airlume import __version__  # noqa: E402
from airlume.aqi import PUNJAB_BANDS, band_for  # noqa: E402
from airlume.config import check_secrets, load_settings  # noqa: E402
from airlume.nl import router  # noqa: E402
from airlume.nl.answer import answer  # noqa: E402
from airlume.nl.resolve import ResolveError, resolve  # noqa: E402
from airlume.pipeline import archive  # noqa: E402
from airlume.pipeline.fake import fake_city_hourly, fake_readings  # noqa: E402
from airlume.pipeline.registry import Registry  # noqa: E402
from airlume.pipeline.store import Store  # noqa: E402
from airlume.viz import coverage as cov_mod  # noqa: E402
from airlume.viz.views import deck_city_overview, deck_stations_3d  # noqa: E402

st.set_page_config(page_title="Airlume", page_icon="🌫️", layout="wide")

SETTINGS = load_settings()
PROBLEMS = check_secrets(SETTINGS)
if PROBLEMS:
    st.error("Configuration problems: " + "; ".join(PROBLEMS))
    st.stop()

KARACHI = timezone(timedelta(hours=5))


@st.cache_resource
def _registry() -> Registry:
    return Registry.load()


@st.cache_resource(ttl=3600)
def _store() -> tuple[Store, str]:
    """Returns (store, data_mode) where data_mode is 'live', 'archive' or 'fake'.

    The app builds an in-memory database from the CSV archive (the source of
    record), so it never locks the on-disk file the hourly collector writes to,
    and it rebuilds itself every hour to pick up new rows."""
    s = Store(":memory:")
    reg = _registry()
    s.upsert_readings(archive.load_all("readings"))
    s.upsert_city_hourly(archive.load_all("city_hourly"))
    s.upsert_epd_daily(archive.load_all("epd_daily"))
    s.upsert_forecasts(archive.load_all("forecasts"))
    real = s.real_counts()
    if real["readings"] > 0 or real["city_hourly"] > 0:
        s.delete_source("fake")
        return s, "live"
    if real["epd_daily"] > 0:
        s.delete_source("fake")
        return s, "archive"
    if SETTINGS.use_fake_data and s.counts()["readings"] == 0:
        r = fake_readings(reg)
        s.upsert_readings(r)
        s.upsert_city_hourly(fake_city_hourly(reg, r))
    return s, "fake"


reg = _registry()
store, DATA_MODE = _store()


# ---------------------------------------------------------------- data frames
def station_frame(city_id: str) -> pd.DataFrame:
    stations = reg.stations_in(city_id)
    base = pd.DataFrame([{"station_id": s.station_id, "name": s.name, "lat": s.lat, "lon": s.lon,
                          "confidence": s.confidence} for s in stations])
    latest = store.latest_station_values([s.station_id for s in stations])
    df = base.merge(latest, on="station_id", how="left")
    now = datetime.now(timezone.utc)
    df["stale"] = df["ts"].map(lambda t: pd.isna(t) or (now - t.to_pydatetime()).total_seconds() > 3 * 3600)
    df.loc[df["stale"], ["aqi", "pm25", "pm10"]] = None
    return df


def station_window_frame(city_id: str, start: datetime, end: datetime, metric: str, aggregation: str) -> pd.DataFrame:
    """Per-station aggregate over [start, end) for the compare / timeline views."""
    stations = reg.stations_in(city_id)
    base = pd.DataFrame([{"station_id": s_.station_id, "name": s_.name, "lat": s_.lat, "lon": s_.lon} for s_ in stations])
    agg = "mean" if aggregation == "latest" else aggregation
    df = store.aggregate([s_.station_id for s_ in stations], start, end, metric, agg)
    if df.empty:
        base["aqi"] = None; base["stale"] = True
        return base
    df = df.rename(columns={"value": "aqi"})[["station_id", "aqi"]]
    out = base.merge(df, on="station_id", how="left")
    out["stale"] = out["aqi"].isna()
    return out


def city_frame() -> pd.DataFrame:
    base = pd.DataFrame([{"city_id": c.city_id, "name": c.name, "lat": c.lat, "lon": c.lon} for c in reg.cities])
    latest = store.latest_city_values()
    latest = latest[latest["source"] != "open_meteo_cams"] if not latest.empty else latest  # modelled values never shown as measured
    return base.merge(latest, on="city_id", how="left")


def ranked_bar(df: pd.DataFrame, name_col: str, value_col: str = "aqi", height: int = 320) -> alt.Chart:
    """2D companion to the 3D view: exact comparison, sorted, official colours (W10)."""
    d = df.dropna(subset=[value_col]).copy()
    d["band"] = d[value_col].map(lambda v: band_for(int(v)).label)
    d["colour"] = d[value_col].map(lambda v: band_for(int(v)).colour)
    return (
        alt.Chart(d)
        .mark_bar()
        .encode(
            y=alt.Y(f"{name_col}:N", sort="-x", title=None),
            x=alt.X(f"{value_col}:Q", title="AQI", scale=alt.Scale(domain=[0, max(100, float(d[value_col].max()) * 1.05)])),
            color=alt.Color("colour:N", scale=None, legend=None),
            tooltip=[name_col, alt.Tooltip(f"{value_col}:Q", title="AQI"), "band"],
        )
        .properties(height=height)
    )


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.subheader("Ask")
    question = st.text_input("Question", placeholder="e.g. Where is the air worst in Lahore right now?")
    models = router.models_available()
    model = st.selectbox("Language model", models, index=0,
                         help="Falls back to the rule-based stand-in if the model call fails.")
    show_form = st.toggle("Show the form the model filled", value=False)
    st.divider()
    st.subheader("Status")
    rc = store.real_counts()
    st.caption({"live": "Live data", "archive": "History only (no live readings yet)", "fake": "FAKE DATA (demo)"}[DATA_MODE])
    st.write(f"hourly readings: {rc['readings']:,}\n\ncity-hours: {rc['city_hourly']:,}\n\ndaily history rows: {rc['epd_daily']:,}")
    st.write("Map tiles: " + ("CARTO" if SETTINGS.carto_api_key else "default"))

# ---------------------------------------------------------------- header
st.markdown(
    f"<h1 style='margin-bottom:0'>Airlume</h1><p style='color:#9FB0C0;margin-top:0'>"
    f"Conversational 3D digital twin of air quality in Pakistan's monitored cities · v{__version__}</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- question
intent = None
result = None
if question:
    result = router.route(question, model=model if model != "stub" else router.PRIMARY_MODEL,
                          previous=st.session_state.get("previous_form"))
    intent = result.intent
    if intent.context_ref and st.session_state.get("previous_form"):
        # Follow-up: start from the previous form, overlay what the model changed.
        merged = {**st.session_state["previous_form"], **intent.model_dump(exclude_defaults=True)}
        merged["context_ref"] = False
        intent = intent.model_validate(merged)
    st.session_state["previous_form"] = intent.model_dump()

resolved = None
if intent is not None:
    if show_form:
        with st.sidebar:
            st.subheader("View-intent form")
            st.caption(f"model: {result.model}{' (cached)' if result.cached else ''} · {result.latency_s:.1f}s")
            st.json(intent.model_dump(), expanded=True)
    if not intent.in_scope:
        st.info("I can only answer about air quality in Pakistan's monitored cities.")
    elif intent.clarify:
        st.warning(intent.clarify)
    else:
        try:
            resolved = resolve(intent, reg)
        except ResolveError as e:
            st.warning(str(e))

if resolved is not None:
    st.success(answer(resolved, store, reg))
    for n in resolved.notes:
        st.info(n)

view = resolved.view if resolved else "stations_3d"
city_id = resolved.city_id if resolved else "PB-LHE"
cam = resolved.camera if resolved else "overview"
national = view == "city_overview" or (resolved is not None and (city_id != "PB-LHE" or resolved.compare_city_id))

# ---------------------------------------------------------------- main view
split = resolved is not None and resolved.view == "compare" and resolved.compare_start is not None and not resolved.compare_city_id and city_id == "PB-LHE"
timeline = resolved is not None and resolved.view == "timeline" and city_id == "PB-LHE"

if split:
    fmt = lambda d: d.astimezone(KARACHI).strftime("%d %b %H:%M")
    a = station_window_frame(city_id, resolved.start, resolved.end, resolved.metric, resolved.aggregation)
    b = station_window_frame(city_id, resolved.compare_start, resolved.compare_end, resolved.metric, resolved.aggregation)
    ca, cb = st.columns(2)
    with ca:
        st.markdown(f"**This window** · {fmt(resolved.start)} - {fmt(resolved.end)}")
        st.pydeck_chart(deck_stations_3d(a, "north"), width="stretch", height=380)
    with cb:
        st.markdown(f"**Compared with** · {fmt(resolved.compare_start)} - {fmt(resolved.compare_end)}")
        st.pydeck_chart(deck_stations_3d(b, "north"), width="stretch", height=380)
    delta = a[["name", "aqi"]].merge(b[["name", "aqi"]], on="name", suffixes=("_now", "_then")).dropna()
    if not delta.empty:
        delta["change"] = delta["aqi_now"] - delta["aqi_then"]
        delta["colour"] = delta["change"].map(lambda v: "#E0736A" if v > 0 else "#7FB069")
        st.altair_chart(
            alt.Chart(delta).mark_bar().encode(
                y=alt.Y("name:N", sort="x", title=None), x=alt.X("change:Q", title=f"change in {resolved.metric.upper()} (positive = worse now)"),
                color=alt.Color("colour:N", scale=None, legend=None),
                tooltip=["name", alt.Tooltip("aqi_now:Q", title="now", format=".0f"), alt.Tooltip("aqi_then:Q", title="then", format=".0f"), alt.Tooltip("change:Q", format="+.0f")],
            ).properties(height=260), width="stretch")
    else:
        st.caption("Not enough hourly data in one of the two windows yet; the archive grows every hour.")

elif timeline:
    ids = [resolved.station_id] if resolved.station_id else [s_.station_id for s_ in reg.stations_in("PB-LHE")]
    ser = store.station_series(ids, resolved.start, resolved.end, resolved.metric)
    if ser.empty:
        st.caption("No hourly readings in that window yet.")
    else:
        names = {s_.station_id: s_.name for s_ in reg.stations_in("PB-LHE")}
        ser["station"] = ser["station_id"].map(names)
        ser["ts"] = pd.to_datetime(ser["ts"], utc=True).dt.tz_convert(KARACHI)
        st.altair_chart(alt.Chart(ser).mark_line(point=len(ids) == 1).encode(
            x=alt.X("ts:T", title=None), y=alt.Y("value:Q", title=resolved.metric.upper()), color=alt.Color("station:N", title=None),
            tooltip=["station", alt.Tooltip("ts:T", format="%d %b %H:%M"), alt.Tooltip("value:Q", format=".0f")]).properties(height=360), width="stretch")
        best = ser.groupby(ser["ts"].dt.hour)["value"].mean()
        st.caption(f"Cleanest hour of day in this window: {int(best.idxmin()):02d}:00 (mean {best.min():.0f}); worst: {int(best.idxmax()):02d}:00 (mean {best.max():.0f}).")

left, right = st.columns([3, 1.4])

with left:
    if split or timeline:
        pass
    elif national:
        cf = city_frame()
        st.pydeck_chart(deck_city_overview(cf), width="stretch", height=560)
    else:
        sf = station_frame(city_id)
        target = None
        if resolved and resolved.station_id:
            s_ = reg.station(resolved.station_id)
            target = (s_.lat, s_.lon)
        st.pydeck_chart(deck_stations_3d(sf, cam, target), width="stretch", height=560)
        if sf["ts"].notna().any():
            latest_ts = pd.to_datetime(sf["ts"].max()).tz_convert(KARACHI)
            st.caption(f"Data as of {latest_ts:%d %b %Y, %H:%M} PKT · Source: Environmental Protection Agency, Punjab · station positions approximate")

with right:
    if split or timeline:
        pass
    elif national:
        cf = city_frame().dropna(subset=["aqi"])
        st.markdown("**Cities, ranked**")
        if cf.empty:
            st.caption("No city-level data yet. Run a collection round.")
        else:
            st.altair_chart(ranked_bar(cf.head(20), "name", height=520), width="stretch")
    else:
        sf = station_frame("PB-LHE")
        reporting = int(sf["aqi"].notna().sum())
        st.metric("Stations reporting", f"{reporting} of {len(sf)}")
        if reporting:
            st.altair_chart(ranked_bar(sf, "name", height=330), width="stretch")
        stale = sf[sf["stale"]]["name"].tolist()
        if stale:
            st.caption("No recent data: " + ", ".join(stale))

# ---------------------------------------------------------------- history
st.divider()
st.subheader("History")
tab_fc, tab_daily, tab_replay, tab_hourly, tab_cov = st.tabs(["Next 24 hours", "Daily bulletins (EPD, 2022-2025)", "Replay a day", "Hourly readings (our collection)", "Where the city is blind"])

with tab_fc:
    fc = store.latest_forecast("PB-LHE")
    if fc.empty:
        st.caption("No forecast captured yet. Each collection round stores EPA Punjab's 24-hour forecast and the CAMS model forecast.")
    else:
        fc["target_ts"] = pd.to_datetime(fc["target_ts"], utc=True).dt.tz_convert(KARACHI)
        fc["source"] = fc["source"].map({"punjab_epa_forecast": "EPA Punjab forecast", "open_meteo_cams_forecast": "CAMS model (Open-Meteo)"}).fillna(fc["source"])
        issued = pd.to_datetime(fc["issued_at"].iloc[0], utc=True).tz_convert(KARACHI)
        st.caption(f"Issued {issued:%d %b %H:%M} PKT. These are relayed forecasts, not ours; whose they are is always shown.")
        base = alt.Chart(fc).encode(x=alt.X("target_ts:T", title=None))
        lines = base.mark_line(point=True).encode(y=alt.Y("forecast:Q", title="AQI"), color=alt.Color("source:N", title=None),
                                                  tooltip=["source", alt.Tooltip("target_ts:T", format="%d %b %H:%M"), alt.Tooltip("forecast:Q", title="forecast AQI")])
        actual = base.mark_point(shape="diamond", size=80, color="#E8EEF4").encode(y="actual:Q", tooltip=[alt.Tooltip("actual:Q", title="actual AQI")]).transform_filter("isValid(datum.actual)")
        st.altair_chart((lines + actual).properties(height=280), width="stretch")
        err = store.forecast_errors("PB-LHE")
        if not err.empty:
            summ = err.groupby("source")["error"].agg(n="count", mean_abs=lambda e: e.abs().mean(), bias="mean").round(1)
            summ.index = summ.index.map({"punjab_epa_forecast": "EPA Punjab", "open_meteo_cams_forecast": "CAMS"})
            st.markdown("**Forecast scorecard so far** (forecast minus what the stations later recorded)")
            st.dataframe(summ, width="stretch")

with tab_daily:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=4 * 365)
    hist = store.epd_daily_series("Lahore", start, end)
    if hist.empty:
        st.caption("No daily history loaded.")
    else:
        hist["date"] = pd.to_datetime(hist["date"])
        avg = hist[hist["station_label"] == "Lahore average"]
        stations_hist = hist[(hist["station_label"] != "Lahore average") & (hist["pollutant"] == "pm25")]
        choice = st.selectbox("Series", ["Lahore average (where printed)"] + sorted(stations_hist["station_label"].unique().tolist()))
        series = avg if choice.startswith("Lahore average") else stations_hist[stations_hist["station_label"] == choice]
        series = series.groupby("date", as_index=False)["aqi"].max()
        if series.empty:
            st.caption("Nothing printed for that series.")
        else:
            band_rules = alt.Chart(pd.DataFrame([{"y": b.hi, "label": b.label} for b in PUNJAB_BANDS[:-1]])).mark_rule(
                strokeDash=[2, 4], color="#4A5563").encode(y="y:Q")
            line = alt.Chart(series).mark_line(point=True, color="#5BC8D6").encode(
                x=alt.X("date:T", title=None), y=alt.Y("aqi:Q", title="24-h AQI (PM2.5)"),
                tooltip=[alt.Tooltip("date:T"), alt.Tooltip("aqi:Q", title="AQI")])
            st.altair_chart((band_rules + line).properties(height=280), width="stretch")
            st.caption(f"{len(series):,} days · 2020-21 bulletins excluded (different index scale) · gap after 2 Dec 2025 until our own collection began")

with tab_replay:
    end = datetime.now(timezone.utc)
    hist = store.epd_daily_series("Lahore", end - timedelta(days=4 * 365), end)
    hist = hist[hist["station_id"].notna() & (hist["pollutant"] == "pm25")]
    if hist.empty:
        st.caption("No station-level history for the current network.")
    else:
        days = sorted(pd.to_datetime(hist["date"]).dt.date.unique())
        per_day = hist.groupby("date")["aqi"].agg(["mean", "count"])
        full = per_day[per_day["count"] >= 5]
        worst_day = (full if not full.empty else per_day)["mean"].idxmax()
        idx = days.index(pd.Timestamp(worst_day).date()) if pd.Timestamp(worst_day).date() in days else len(days) - 1
        day = st.select_slider("Day (slide; defaults to the worst day on record)", options=days, value=days[idx],
                               format_func=lambda d: d.strftime("%d %b %Y"))
        rows = hist[pd.to_datetime(hist["date"]).dt.date == day]
        stations = reg.stations_in("PB-LHE")
        base = pd.DataFrame([{"station_id": s_.station_id, "name": s_.name, "lat": s_.lat, "lon": s_.lon} for s_ in stations])
        frame = base.merge(rows.groupby("station_id", as_index=False)["aqi"].max(), on="station_id", how="left")
        frame["stale"] = frame["aqi"].isna()
        c1, c2 = st.columns([3, 1.4])
        with c1:
            st.pydeck_chart(deck_stations_3d(frame, "overview"), width="stretch", height=420)
        with c2:
            st.metric("Stations in that day's bulletin", f"{int(frame['aqi'].notna().sum())} of {len(frame)}")
            if frame["aqi"].notna().any():
                st.altair_chart(ranked_bar(frame, "name", height=300), width="stretch")
        st.caption("24-hour PM2.5 AQI from the EPD bulletin of that day. Only the stations that exist in today's network are shown; the bulletins also covered Town Hall, PKLI, LWMC, FMDRC, PU 2 and EPA HQ.")

with tab_hourly:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=14)
    ids = [s.station_id for s in reg.stations_in("PB-LHE")]
    ser = store.station_series(ids, start, end, "aqi")
    if ser.empty:
        st.caption("No hourly readings yet. The cloud collector adds one row per station every hour.")
    else:
        hours = sorted(pd.to_datetime(ser["ts"], utc=True).unique())
        if len(hours) > 1:
            pick = st.select_slider("Scrub through the collected hours", options=hours, value=hours[-1],
                                    format_func=lambda t: pd.Timestamp(t).tz_convert(KARACHI).strftime("%d %b %H:%M"))
            at = ser[pd.to_datetime(ser["ts"], utc=True) == pick]
            base = pd.DataFrame([{"station_id": s_.station_id, "name": s_.name, "lat": s_.lat, "lon": s_.lon} for s_ in reg.stations_in("PB-LHE")])
            frame = base.merge(at[["station_id", "value"]].rename(columns={"value": "aqi"}), on="station_id", how="left")
            frame["stale"] = frame["aqi"].isna()
            st.pydeck_chart(deck_stations_3d(frame, "overview"), width="stretch", height=360)
        names = {s.station_id: s.name for s in reg.stations_in("PB-LHE")}
        ser["station"] = ser["station_id"].map(names)
        st.altair_chart(
            alt.Chart(ser).mark_line().encode(
                x=alt.X("ts:T", title=None), y=alt.Y("value:Q", title="AQI"), color=alt.Color("station:N", title=None),
                tooltip=["station", alt.Tooltip("ts:T"), alt.Tooltip("value:Q", title="AQI")]).properties(height=280),
            width="stretch")

st.caption("Student project (UMT, DS494 / CC425). Not an official source. Punjab EPA bands: Good 0-50 · Satisfactory 51-100 · Moderate 101-150 · Unhealthy for sensitive groups 151-200 · Unhealthy 201-300 · Very unhealthy 301-400 · Hazardous 401-500.")


@st.cache_data(ttl=24 * 3600)
def _coverage():
    c = cov_mod.coverage(reg)
    return c, cov_mod.coverage_stats(c), cov_mod.recommend_station(c, reg.stations_in("PB-LHE"))


with tab_cov:
    cov, stats, rec = _coverage()
    c1, c2 = st.columns([3, 1.4])
    with c1:
        import pydeck as pdk
        from airlume.viz import camera as cam_mod
        from airlume.viz import layers as layer_mod
        base = station_frame("PB-LHE")
        deck = pdk.Deck(
            layers=[cov_mod.coverage_layer(cov), layer_mod.station_columns(base.assign(aqi=base["aqi"].fillna(0))), cov_mod.recommendation_layer(rec), layer_mod.labels(base)],
            initial_view_state=cam_mod.view_state("top"), tooltip={"text": "{label}"},
            map_provider=None if not SETTINGS.carto_api_key else "carto", map_style=None if not SETTINGS.carto_api_key else "dark",
        )
        st.pydeck_chart(deck, width="stretch", height=480)
    with c2:
        st.metric("Mean distance to nearest monitor", f"{stats['mean_km_urban']:.1f} km", help="Across the built-up area, about 18 km around the centre")
        st.metric("Share of the city more than 5 km from a monitor", f"{stats['share_beyond_5km']:.0%}")
        st.metric("Share within 3 km", f"{stats['share_within_3km']:.0%}")
        st.markdown(f"**Suggested next station:** {rec['lat']:.3f} N, {rec['lon']:.3f} E - currently {rec['current_km']:.1f} km from {rec['nearest_now']}; would cut the city mean by {rec['gain_km']:.2f} km.")
    st.caption("Colour = distance from each 1 km cell to the nearest EPA station (teal close, orange far). No air-quality value is shown for places without a monitor; this map shows where measurement is missing, not what the air is like there. Station positions approximate.")

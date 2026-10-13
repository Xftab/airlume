"""Airlume - Phase 0 shell.

Runs on fake data so the 3D map, the city overview and the view-intent form
can be seen end to end before any real collector or language model exists.
The question box is wired to a *rule-based* stand-in for the model
(`nl/stub_router.py`) that fills the same ViewIntent form the model will fill.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from airlume import __version__  # noqa: E402
from airlume.aqi import band_for  # noqa: E402
from airlume.config import check_secrets, load_settings  # noqa: E402
from airlume.nl.answer import answer  # noqa: E402
from airlume.nl.resolve import ResolveError, resolve  # noqa: E402
from airlume.nl.stub_router import route  # noqa: E402
from airlume.pipeline.fake import fake_city_hourly, fake_readings  # noqa: E402
from airlume.pipeline.registry import Registry  # noqa: E402
from airlume.pipeline.store import Store  # noqa: E402
from airlume.viz.views import deck_city_overview, deck_stations_3d  # noqa: E402

st.set_page_config(page_title="Airlume", page_icon="🌫️", layout="wide")

SETTINGS = load_settings()
PROBLEMS = check_secrets(SETTINGS)
if PROBLEMS:
    st.error("Configuration problems: " + "; ".join(PROBLEMS))
    st.stop()


@st.cache_resource
def _registry() -> Registry:
    return Registry.load()


@st.cache_resource
def _store() -> Store:
    s = Store()
    if s.counts()["readings"] == 0:
        reg = _registry()
        if SETTINGS.use_fake_data:
            r = fake_readings(reg)
            s.upsert_readings(r)
            s.upsert_city_hourly(fake_city_hourly(reg, r))
        else:  # fresh clone / cloud deploy: rebuild the cache from the committed CSV archive
            from airlume.pipeline import archive
            s.upsert_readings(archive.load_all("readings"))
            s.upsert_city_hourly(archive.load_all("city_hourly"))
    return s


reg = _registry()
store = _store()


def station_frame(city_id: str) -> pd.DataFrame:
    stations = reg.stations_in(city_id)
    base = pd.DataFrame([{"station_id": s.station_id, "name": s.name, "lat": s.lat, "lon": s.lon} for s in stations])
    latest = store.latest_station_values([s.station_id for s in stations])
    df = base.merge(latest, on="station_id", how="left")
    now = datetime.now(timezone.utc)
    df["stale"] = df["ts"].map(lambda t: pd.isna(t) or (now - t.to_pydatetime()).total_seconds() > 2 * 3600)
    df.loc[df["stale"], ["aqi", "pm25", "pm10"]] = None
    return df


def city_frame() -> pd.DataFrame:
    base = pd.DataFrame([{"city_id": c.city_id, "name": c.name, "lat": c.lat, "lon": c.lon} for c in reg.cities])
    latest = store.latest_city_values()
    return base.merge(latest, on="city_id", how="left")


# ---------------- UI ----------------
st.markdown(
    f"<h1 style='margin-bottom:0'>Airlume</h1><p style='color:#9FB0C0;margin-top:0'>"
    f"Conversational 3D digital twin of air quality in Pakistan's monitored cities · v{__version__} · "
    f"{'FAKE DATA (Phase 0 shell)' if SETTINGS.use_fake_data else 'live data'}</p>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Ask")
    question = st.text_input("Question", placeholder="e.g. Where is the air worst in Lahore right now?")
    st.caption("Phase 0: a rule-based stand-in fills the same typed form the language model will fill.")
    st.divider()
    st.subheader("Status")
    counts = store.counts()
    st.write(f"readings: {counts['readings']:,}  ·  city rows: {counts['city_hourly']:,}")
    st.write("Map tiles: " + ("CARTO" if SETTINGS.carto_api_key else "none (keyless mode)"))

intent = route(question) if question else None
resolved = None
if intent is not None:
    with st.sidebar:
        st.subheader("View-intent form")
        st.json(intent.model_dump(), expanded=False)
    try:
        resolved = resolve(intent, reg)
    except ResolveError as e:
        st.warning(str(e))

view = resolved.view if resolved else "stations_3d"
city_id = resolved.city_id if resolved else "PB-LHE"
cam = resolved.camera if resolved else "overview"

if resolved is not None:
    st.success(answer(resolved, store, reg))

left, right = st.columns([3, 1])

with left:
    if view == "city_overview" or (resolved and (city_id != "PB-LHE" or resolved.compare_city_id)):
        cf = city_frame()
        st.pydeck_chart(deck_city_overview(cf), width="stretch", height=620)
    else:
        sf = station_frame(city_id)
        target = None
        if resolved and resolved.station_id:
            s = reg.station(resolved.station_id)
            target = (s.lat, s.lon)
        st.pydeck_chart(deck_stations_3d(sf, cam, target), width="stretch", height=620)

with right:
    if resolved and resolved.notes:
        for n in resolved.notes:
            st.info(n)
    if city_id == "PB-LHE" and view != "city_overview":
        sf = station_frame("PB-LHE")
        reporting = int(sf["aqi"].notna().sum())
        st.metric("Stations reporting", f"{reporting} of {len(sf)}")
        top = sf.dropna(subset=["aqi"]).sort_values("aqi", ascending=False)
        st.markdown("**Worst right now**")
        for r in top.head(5).itertuples():
            b = band_for(int(r.aqi))
            st.markdown(
                f"<div style='display:flex;justify-content:space-between'><span>{r.name}</span>"
                f"<span style='color:{b.colour};font-weight:700'>{int(r.aqi)}</span></div>",
                unsafe_allow_html=True,
            )
        stale = sf[sf["stale"]]["name"].tolist()
        if stale:
            st.caption("No recent data: " + ", ".join(stale))
    else:
        cf = city_frame().dropna(subset=["aqi"]).sort_values("aqi", ascending=False)
        st.markdown("**Cities, worst first**")
        for r in cf.head(8).itertuples():
            b = band_for(int(r.aqi))
            st.markdown(
                f"<div style='display:flex;justify-content:space-between'><span>{r.name}</span>"
                f"<span style='color:{b.colour};font-weight:700'>{int(r.aqi)}</span></div>",
                unsafe_allow_html=True,
            )

st.caption("Student project (UMT, DS494 / CC425). Not an official source. Punjab EPA labels: Good 0-50 · Satisfactory 51-100 · Moderate 101-150 · Unhealthy for sensitive groups 151-200 · Unhealthy 201-300 · Very unhealthy 301-400 · Hazardous 401-500.")

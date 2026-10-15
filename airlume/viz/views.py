"""Assemble a pydeck Deck for a given view name."""

from __future__ import annotations

import pandas as pd
import pydeck as pdk

from airlume.config import load_settings
from airlume.viz import camera, layers

TOOLTIP = {"text": "{label}"}


def _map_kwargs() -> dict:
    """Keyless by default. CARTO basemap only when a key is configured."""
    key = load_settings().carto_api_key
    if key:
        return {"map_provider": "carto", "map_style": "dark", "api_keys": {"carto": key}}
    return {"map_provider": None, "map_style": None}


def deck_stations_3d(stations: pd.DataFrame, cam: str = "overview",
                     target: tuple[float, float] | None = None,
                     wind: bool = False) -> pdk.Deck:
    stack = [layers.station_columns(stations), layers.labels(stations)]
    if wind:
        arrows = layers.wind_arrows(stations)
        if arrows is not None:
            # Under the columns, so an arrow never hides the value it is context for.
            stack.insert(0, arrows)
    return pdk.Deck(
        layers=stack,
        initial_view_state=camera.view_state(cam, target),
        tooltip=TOOLTIP,
        **_map_kwargs(),
    )


def deck_city_overview(cities: pd.DataFrame) -> pdk.Deck:
    return pdk.Deck(
        layers=[layers.city_dots(cities), layers.labels(cities, size=11)],
        initial_view_state=camera.view_state("zoomed_out"),
        tooltip=TOOLTIP,
        **_map_kwargs(),
    )

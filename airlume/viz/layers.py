"""deck.gl layers built with pydeck.

- `station_columns`: Lahore stations as 3D columns; height and colour = AQI.
- `city_dots`: every monitored city as a scaled, coloured disc.
No map-tile key is needed: with CARTO_API_KEY empty the deck is rendered on a
plain dark background (`map_provider=None`).
"""

from __future__ import annotations

import pandas as pd
import pydeck as pdk

from airlume.aqi import band_for, hex_to_rgb

MISSING_RGB = [90, 100, 112]


def _colour(aqi: float | None) -> list[int]:
    if aqi is None or pd.isna(aqi):
        return MISSING_RGB
    b = band_for(int(aqi))
    return hex_to_rgb(b.colour) if b else MISSING_RGB


def station_columns(df: pd.DataFrame, value_col: str = "aqi", scale: float = 12.0) -> pdk.Layer:
    """df: station_id, name, lat, lon, <value_col>, stale(bool)."""
    d = df.copy()
    d["elevation"] = d[value_col].fillna(0).astype(float) * scale
    d["colour"] = d[value_col].map(_colour)
    d["label"] = d.apply(
        lambda r: f"{r['name']}: " + ("no data" if pd.isna(r[value_col]) else f"AQI {int(r[value_col])}"),
        axis=1,
    )
    return pdk.Layer(
        "ColumnLayer",
        data=d,
        get_position=["lon", "lat"],
        get_elevation="elevation",
        elevation_scale=1,
        radius=350,
        get_fill_color="colour",
        pickable=True,
        auto_highlight=True,
        extruded=True,
    )


def city_dots(df: pd.DataFrame, value_col: str = "aqi") -> pdk.Layer:
    """df: city_id, name, lat, lon, <value_col>."""
    d = df.copy()
    d["colour"] = d[value_col].map(_colour)
    d["radius"] = 4000 + d[value_col].fillna(0).astype(float) * 40
    d["label"] = d.apply(
        lambda r: f"{r['name']}: " + ("no data" if pd.isna(r[value_col]) else f"AQI {int(r[value_col])}"),
        axis=1,
    )
    return pdk.Layer(
        "ScatterplotLayer",
        data=d,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color="colour",
        pickable=True,
        opacity=0.85,
        stroked=True,
        get_line_color=[20, 26, 34],
        line_width_min_pixels=1,
    )


def labels(df: pd.DataFrame, text_col: str = "name", size: int = 13) -> pdk.Layer:
    return pdk.Layer(
        "TextLayer",
        data=df,
        get_position=["lon", "lat"],
        get_text=text_col,
        get_size=size,
        get_color=[232, 238, 244],
        get_alignment_baseline="bottom",
        get_pixel_offset=[0, -8],
    )

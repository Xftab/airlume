"""deck.gl layers built with pydeck.

- `station_columns`: Lahore stations as 3D columns; height and colour = AQI.
- `city_dots`: every monitored city as a scaled, coloured disc.
No map-tile key is needed: with CARTO_API_KEY empty the deck is rendered on a
plain dark background (`map_provider=None`).
"""

from __future__ import annotations

import math

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


def _arrow_end(lat: float, lon: float, bearing_deg: float, km: float) -> tuple[float, float]:
    """Point `km` from (lat, lon) along a compass bearing, on a local flat approximation.

    Lahore spans about 0.35 degrees, so a flat approximation is accurate to a few
    metres here and avoids pulling in a geodesy dependency for a decorative arrow.
    """
    rad = math.radians(bearing_deg)
    dlat = (km / 111.32) * math.cos(rad)
    dlon = (km / (111.32 * math.cos(math.radians(lat)))) * math.sin(rad)
    return lat + dlat, lon + dlon


def wind_arrow_frame(df: pd.DataFrame, km_per_ms: float = 1.1,
                     min_km: float = 0.6) -> pd.DataFrame:
    """Arrow geometry for each station that has wind. Empty frame when none do.

    `wind_direction` on the portal is the meteorological convention: the direction
    the wind blows *from*. The arrow is drawn towards `direction + 180` so it reads
    as motion, which is what people expect from an arrow on a map. The label keeps
    the "from" wording, because that is how a wind is quoted.

    Length is proportional to speed with a floor, so a calm station still shows its
    direction rather than vanishing.

    Kept separate from `wind_arrows` because pydeck converts a frame to records when
    it builds a Layer, so the geometry is only testable before that happens.
    """
    if not {"wind_speed", "wind_direction", "lat", "lon"} <= set(df.columns):
        return pd.DataFrame()
    d = df.dropna(subset=["wind_speed", "wind_direction", "lat", "lon"]).copy()
    if d.empty:
        return d
    ends = [
        _arrow_end(r.lat, r.lon, (r.wind_direction + 180.0) % 360.0,
                   max(min_km, float(r.wind_speed) * km_per_ms))
        for r in d.itertuples()
    ]
    d["end_lat"] = [e[0] for e in ends]
    d["end_lon"] = [e[1] for e in ends]
    d["wind_label"] = [
        f"{getattr(r, 'name_', None) or r.station_id}: "
        f"wind {r.wind_speed:.1f} m/s from {_compass(r.wind_direction)}"
        for r in d.rename(columns={"name": "name_"}).itertuples()
    ]
    return d


def wind_arrows(df: pd.DataFrame, km_per_ms: float = 1.1, min_km: float = 0.6) -> pdk.Layer | None:
    """Wind at each station. None when no station has wind, so the caller can omit
    the layer rather than add an empty one."""
    d = wind_arrow_frame(df, km_per_ms, min_km)
    if d.empty:
        return None
    return pdk.Layer(
        "LineLayer",
        data=d,
        get_source_position=["lon", "lat"],
        get_target_position=["end_lon", "end_lat"],
        get_color=[142, 202, 230],
        get_width=3,
        width_min_pixels=2,
        pickable=False,
    )


_COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _compass(deg: float) -> str:
    return _COMPASS[int((float(deg) % 360) / 22.5 + 0.5) % 16]


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

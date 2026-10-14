"""Named camera positions.  The model picks a name; code supplies the numbers."""

from __future__ import annotations

import pydeck as pdk

LAHORE = (31.52, 74.33)
PAKISTAN = (30.8, 71.5)


def view_state(camera: str, target: tuple[float, float] | None = None) -> pdk.ViewState:
    if camera == "zoomed_out":
        return pdk.ViewState(latitude=PAKISTAN[0], longitude=PAKISTAN[1], zoom=5.3, pitch=35, bearing=0)
    lat, lon = target or LAHORE
    if camera == "station":
        return pdk.ViewState(latitude=lat, longitude=lon, zoom=12.5, pitch=60, bearing=-20)
    if camera == "top":
        return pdk.ViewState(latitude=lat, longitude=lon, zoom=10.4, pitch=0, bearing=0)
    if camera == "north":
        return pdk.ViewState(latitude=lat, longitude=lon, zoom=10.3, pitch=45, bearing=0)
    # overview
    return pdk.ViewState(latitude=lat, longitude=lon, zoom=10.3, pitch=50, bearing=-25)

"""Wind layer (plan 2.4).

The one thing worth pinning hard is the direction convention. Meteorological
`wind_direction` is the direction the wind blows *from*; an arrow on a map reads
as motion, so it must point the opposite way. Getting this backwards would be
invisible on screen and wrong in every screenshot in the report.
"""

import math

import pandas as pd
import pytest

from airlume.viz import layers


def frame(rows):
    return pd.DataFrame([
        {"station_id": s, "name": n, "lat": la, "lon": lo,
         "aqi": 100, "stale": False, "wind_speed": ws, "wind_direction": wd}
        for s, n, la, lo, ws, wd in rows
    ])


def test_arrow_points_where_the_wind_is_going_not_where_it_came_from():
    # A northerly wind (direction 0) blows from the north, so it travels south:
    # the arrow must end at a LOWER latitude than it starts.
    d = layers.wind_arrow_frame(frame([("A", "Alpha", 31.5, 74.3, 3.0, 0.0)]))
    assert d["end_lat"].iloc[0] < 31.5
    assert d["end_lon"].iloc[0] == pytest.approx(74.3, abs=1e-6)


def test_westerly_wind_travels_east():
    # Direction 270 is a westerly: from the west, towards the east.
    d = layers.wind_arrow_frame(frame([("A", "Alpha", 31.5, 74.3, 3.0, 270.0)]))
    assert d["end_lon"].iloc[0] > 74.3
    assert d["end_lat"].iloc[0] == pytest.approx(31.5, abs=1e-6)


def test_arrow_length_scales_with_speed_but_has_a_floor():
    fast = layers.wind_arrow_frame(frame([("A", "Alpha", 31.5, 74.3, 6.0, 90.0)]))
    slow = layers.wind_arrow_frame(frame([("A", "Alpha", 31.5, 74.3, 1.0, 90.0)]))
    calm = layers.wind_arrow_frame(frame([("A", "Alpha", 31.5, 74.3, 0.0, 90.0)]))

    def length(d):
        return math.hypot(d["end_lat"].iloc[0] - 31.5, d["end_lon"].iloc[0] - 74.3)

    assert length(fast) > length(slow) > 0
    assert length(calm) > 0  # a calm station still shows its direction


def test_stations_without_wind_are_dropped_not_drawn_at_zero():
    d = layers.wind_arrow_frame(frame([
        ("A", "Alpha", 31.5, 74.3, 2.0, 180.0),
        ("B", "Beta", 31.6, 74.4, None, None),
    ]))
    assert len(d) == 1
    assert d["station_id"].iloc[0] == "A"


def test_no_layer_when_nothing_has_wind():
    assert layers.wind_arrows(frame([("B", "Beta", 31.6, 74.4, None, None)])) is None


def test_no_layer_when_the_columns_are_absent():
    """Rows collected from the HTML table carry no wind at all."""
    df = pd.DataFrame([{"station_id": "A", "name": "Alpha", "lat": 31.5, "lon": 74.3, "aqi": 90}])
    assert layers.wind_arrows(df) is None


@pytest.mark.parametrize("deg,expected", [
    (0, "N"), (90, "E"), (180, "S"), (270, "W"),
    (45, "NE"), (359, "N"), (360, "N"), (22.5, "NNE"),
])
def test_compass_labels(deg, expected):
    assert layers._compass(deg) == expected


def test_label_states_the_direction_the_wind_comes_from():
    """The arrow shows motion; the text uses the convention people quote."""
    d = layers.wind_arrow_frame(frame([("A", "Alpha", 31.5, 74.3, 2.5, 270.0)]))
    assert "from W" in d["wind_label"].iloc[0]
    assert "2.5 m/s" in d["wind_label"].iloc[0]
    assert "Alpha" in d["wind_label"].iloc[0]


def test_deck_omits_the_layer_rather_than_adding_an_empty_one():
    from airlume.viz.views import deck_stations_3d
    no_wind = frame([("B", "Beta", 31.6, 74.4, None, None)])
    with_wind = frame([("A", "Alpha", 31.5, 74.3, 2.0, 180.0)])
    assert len(deck_stations_3d(no_wind, wind=True).layers) == 2      # columns + labels
    assert len(deck_stations_3d(with_wind, wind=True).layers) == 3    # plus arrows
    assert len(deck_stations_3d(with_wind, wind=False).layers) == 2   # toggle off

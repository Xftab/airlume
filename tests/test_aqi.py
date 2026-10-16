from airlume.aqi import aqi_from_concentrations, band_for, sub_index, to_epa_units


def test_matches_punjab_portal_values_13_oct():
    # Values observed on aqi.punjab.gov.pk, 13 Oct 2026 07:00 (portal AQI in comments).
    assert sub_index("pm25", 310.8) == 361  # Multan Road 361
    assert sub_index("pm25", 226.9) == 277  # GT Road 277
    assert sub_index("pm25", 141.1) == 195  # Egerton 195
    assert abs(sub_index("pm25", 190.0) - 241) <= 1  # Safari Park 241


def test_pm10_can_dominate():
    aqi, dom = aqi_from_concentrations(pm25=12.3, pm10=142.8)
    assert dom == "pm10" and 93 <= aqi <= 95


def test_2024_table_differs():
    assert sub_index("pm25", 310.8, "us_2024") > 400


def test_bounds_and_missing():
    assert sub_index("pm25", None) is None
    assert sub_index("pm25", 0) == 0
    assert sub_index("pm25", 9999) == 500
    assert aqi_from_concentrations() == (None, None)


def test_punjab_labels():
    assert band_for(0).label == "Good"
    assert band_for(150).label == "Moderate"
    assert band_for(151).label == "Unhealthy for sensitive groups"
    assert band_for(350).label == "Very unhealthy"
    assert band_for(450).label == "Hazardous"
    assert band_for(999).label == "Hazardous"
    assert band_for(None) is None


def test_ozone_can_dominate_afternoon():
    # Egerton Road, 13 Oct 2026 14:00: PM2.5 35.2 but O3 186.2 ug/m3 (~95 ppb) -> portal AQI 143.
    aqi, dom = aqi_from_concentrations(pm25=35.2, pm10=119.8, o3=186.2, no2=34.4, so2=18.5, co=1.2)
    assert dom == "o3" and aqi > 100


def test_gas_units_converted():
    assert sub_index("no2", 34.4 / 1.88) < 51  # 18 ppb -> Good
    assert aqi_from_concentrations(pm25=24.2, pm10=68.3, o3=89.2, no2=16.0, so2=37.5, co=0.6)[0] in range(70, 80)  # GT Road 73


def test_nan_treated_as_missing():
    """Pandas hands us NaN for a gap; NaN fails every comparison silently, so the
    guards must catch it explicitly.  Regression for the w1_check crash, 15 Oct."""
    nan = float("nan")
    assert sub_index("pm25", nan) is None
    assert sub_index("o3", nan) is None
    assert to_epa_units("o3", nan) is None
    assert aqi_from_concentrations(nan, nan, o3=nan, no2=nan, so2=nan, co=nan) == (None, None)
    # One real value among NaNs still scores, and the NaNs do not become zeros.
    # Barki Road, 14 Oct 04:00: the portal published 157 (the US 2012 table gave 163).
    assert aqi_from_concentrations(79.5, nan, o3=nan, no2=nan, so2=nan, co=nan) == (157, "pm25")
    # A rolling mean over a gap (the w1_check path) must not raise.
    assert aqi_from_concentrations(pm25=nan, pm10=116.5)[1] == "pm10"


# --- The portal's own table (pk_portal), fitted 16 Oct 2026 ------------------
# Every value below is a reading the portal itself published, so these tests pin
# behaviour to the source of truth rather than to our own earlier output.

import pytest  # noqa: E402

from airlume.aqi import DEFAULT_SCALE  # noqa: E402


def test_default_scale_is_the_portals_own():
    assert DEFAULT_SCALE == "pk_portal"


@pytest.mark.parametrize("pol,conc,portal,where", [
    ("pm25", 310.8, 361, "Multan Road 13 Oct 07:00"),
    ("pm25", 226.9, 277, "GT Road 13 Oct 07:00"),
    ("pm25", 141.1, 195, "Egerton Road 13 Oct 07:00"),
    ("pm25", 79.5, 157, "Barki Road 14 Oct 04:00"),
    ("pm25", 24.2, 73, "GT Road 13 Oct 14:00"),
    ("pm10", 517.17, 367, "Multan Road 16 Oct 03:00"),
    ("pm10", 429.47, 280, "Multan Road 16 Oct 04:00"),
    ("o3", 186.2, 143, "Egerton Road 13 Oct 14:00"),
    ("o3", 129.5, 100, "Barki Road 15 Oct 11:00"),
    ("o3", 82.39, 64, "Gulberg III 15 Oct 10:00"),
    ("o3", 91.97, 71, "Wagha Border 15 Oct 10:00"),
    ("no2", 65.06, 82, "Egerton Road 15 Oct 19:00"),
    ("no2", 87.22, 108, "Gulberg III 15 Oct 14:00"),
])
def test_reproduces_published_portal_readings(pol, conc, portal, where):
    assert sub_index(pol, conc) == portal, where


def test_the_us_table_was_wrong_in_lahores_ordinary_range():
    """The two tables part most at 35-70 ug/m3. A reading of 60 is 'Moderate' to
    the portal but 'Unhealthy for sensitive groups' on the US 2012 table."""
    assert sub_index("pm25", 60.0) < 150 < sub_index("pm25", 60.0, "us_2012")


def test_gases_are_banded_in_ugm3_not_ppb():
    # 82.39 ug/m3 of O3 is 42 ppb. In ug/m3 on the portal table it is 64, which is
    # what the portal published; read as ppb on the US table it would be 39.
    assert sub_index("o3", 82.39) == 64
    assert sub_index("o3", to_epa_units("o3", 82.39), "us_2012") == 39


def test_partly_known_gas_tables_refuse_rather_than_extrapolate():
    """Above the last fitted band a gas sub-index is refused, so a guess can never
    set the AQI. PM is capped at 500 as before."""
    assert sub_index("o3", 250.0) is None
    assert sub_index("no2", 200.0) is None
    assert sub_index("pm25", 9999) == 500
    # A refused gas falls out of the max, it does not zero the reading.
    aqi, dom = aqi_from_concentrations(pm25=40.0, o3=250.0)
    assert dom == "pm25" and aqi == sub_index("pm25", 40.0)


def test_us_scales_still_available_for_comparison():
    assert sub_index("pm25", 60.0, "us_2012") == 153
    assert sub_index("pm25", 60.0, "us_2024") is not None
    aqi, _ = aqi_from_concentrations(pm25=60.0, scale="us_2012")
    assert aqi == 153

from airlume.aqi import aqi_from_concentrations, band_for, sub_index, to_epa_units


def test_matches_punjab_portal_values_13_oct():
    # Values observed on aqi.punjab.gov.pk, 13 Oct 2026 07:00 (portal AQI in comments),
    # so on the table the portal used until 3 Nov 2026.
    v1 = "pk_portal_v1"
    assert sub_index("pm25", 310.8, v1) == 361  # Multan Road 361
    assert sub_index("pm25", 226.9, v1) == 277  # GT Road 277
    assert sub_index("pm25", 141.1, v1) == 195  # Egerton 195
    assert abs(sub_index("pm25", 190.0, v1) - 241) <= 1  # Safari Park 241


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
    assert aqi_from_concentrations(79.5, nan, o3=nan, no2=nan, so2=nan, co=nan,
                                   scale="pk_portal_v1") == (157, "pm25")
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
    # Published in October, so on the table in force then (see test_portal_table_v2 below).
    assert sub_index(pol, conc, "pk_portal_v1") == portal, where


def test_the_us_table_was_wrong_in_lahores_ordinary_range():
    """The two tables part most at 35-70 ug/m3. A reading of 60 is 'Moderate' to
    the portal but 'Unhealthy for sensitive groups' on the US 2012 table."""
    assert sub_index("pm25", 60.0, "pk_portal_v1") < 150 < sub_index("pm25", 60.0, "us_2012")
    assert sub_index("pm25", 60.0) < 150


def test_gases_are_banded_in_ugm3_not_ppb():
    # 82.39 ug/m3 of O3 is 42 ppb. In ug/m3 on the portal table it is 64, which is
    # what the portal published; read as ppb on the US table it would be 39.
    assert sub_index("o3", 82.39) == 64
    assert sub_index("o3", to_epa_units("o3", 82.39), "us_2012") == 39


def test_partly_known_gas_tables_refuse_rather_than_extrapolate():
    """Above the last fitted band a gas sub-index is refused, so a guess can never
    set the AQI. PM is capped at 500 as before."""
    assert sub_index("o3", 300.0) is None   # O3 fitted to 260 since 6 Nov
    assert sub_index("no2", 200.0) is None  # NO2 fitted to 180 since 6 Nov
    assert sub_index("pm25", 9999) == 500
    # A refused gas falls out of the max, it does not zero the reading.
    aqi, dom = aqi_from_concentrations(pm25=40.0, o3=300.0)
    assert dom == "pm25" and aqi == sub_index("pm25", 40.0)


def test_us_scales_still_available_for_comparison():
    assert sub_index("pm25", 60.0, "us_2012") == 153
    assert sub_index("pm25", 60.0, "us_2024") is not None
    aqi, _ = aqi_from_concentrations(pm25=60.0, scale="us_2012")
    assert aqi == 153


# --- 6 Nov 2026: the portal changed its table on 3 Nov ----------------------------
# Every value is a reading the portal published after 3 Nov 06:00 UTC (archive rows).
from datetime import datetime, timezone  # noqa: E402

from airlume.aqi import PK_PORTAL_V2_FROM, portal_scale_at  # noqa: E402


@pytest.mark.parametrize("pol,conc,portal,where", [
    ("pm25", 72.45, 147, "Barki Road 6 Nov 10:00Z (was 152 on the old table)"),
    ("pm25", 91.00, 161, "Barki Road 6 Nov 09:00Z"),
    ("pm25", 61.12, 133, "Punjab University 6 Nov 11:00Z"),
    ("pm25", 110.62, 174, "Egerton Road 6 Nov 10:00Z"),
    ("pm25", 46.02, 114, "Gulberg III 6 Nov 11:00Z"),
    ("pm10", 587.62, 438, "Barki Road 3 Nov 14:00Z, above 550: the 401-500 band"),
    ("pm10", 645.00, 495, "Barki Road 4 Nov 15:00Z"),
    ("pm10", 553.00, 404, "Kahna Nau 3 Nov 17:00Z"),
])
def test_portal_table_v2(pol, conc, portal, where):
    assert sub_index(pol, conc) == portal, where


@pytest.mark.parametrize("pm25,pm10,where", [
    (350.49, 516.10, "Shahdara 23 Oct 01:00Z: PM2.5 just above 350"),
    (110.71, 551.32, "Gulberg III 2 Nov 13:00Z: PM10 just above 550"),
])
def test_old_table_published_500_above_400(pm25, pm10, where):
    aqi, _ = aqi_from_concentrations(pm25, pm10, scale="pk_portal_v1")
    assert aqi == 500, where
    assert aqi_from_concentrations(pm25, pm10)[0] < 500  # the current table bands it


def test_portal_scale_at_switches_on_3_nov():
    assert portal_scale_at(datetime(2026, 11, 3, 5, tzinfo=timezone.utc)) == "pk_portal_v1"
    assert portal_scale_at(PK_PORTAL_V2_FROM) == "pk_portal"


@pytest.mark.parametrize("pol,conc,portal,where", [
    ("o3", 213.99, 165, "Punjab University 16 Oct 10:00Z"),
    ("o3", 199.04, 154, "Barki Road 30 Oct 13:00Z"),
    ("no2", 157.59, 178, "Gulberg III 22 Oct 13:00Z"),
    ("no2", 132.50, 153, "Gulberg III 19 Oct 13:00Z"),
])
def test_gas_bands_fitted_6_nov(pol, conc, portal, where):
    assert sub_index(pol, conc) == portal, where

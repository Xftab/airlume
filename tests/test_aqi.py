from airlume.aqi import aqi_from_concentrations, band_for, sub_index


def test_matches_punjab_portal_values_2012_table():
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

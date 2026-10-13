from datetime import datetime
from zoneinfo import ZoneInfo

from airlume.collectors.epa import parse_lahore_html

NOW = datetime(2026, 10, 13, 8, 0, tzinfo=ZoneInfo("Asia/Karachi"))

SAMPLE = """
<html><body>
<p>Last updated: 7:00 AM, Oct 13, 2026</p>
<table>
<thead><tr><th>Rank</th><th>Station</th><th>AQI</th><th>Level</th><th>PM2.5</th><th>PM10</th><th>CO</th><th>SO2</th><th>NO2</th><th>O3</th></tr></thead>
<tbody>
<tr><td>1</td><td>Multan Road Lahore</td><td>361</td><td>Very Unhealthy</td><td>310.8</td><td>322.3</td><td>3.8</td><td>35.3</td><td>87.8</td><td>3.8</td></tr>
<tr><td>2</td><td>GT Road</td><td>277</td><td>Unhealthy</td><td>226.9</td><td>240.1</td><td>--</td><td>--</td><td>--</td><td>--</td></tr>
<tr><td>3</td><td>Wagha Border</td><td>95</td><td>Satisfactory</td><td>12.3</td><td>142.8</td><td>1.1</td><td>5</td><td>12</td><td>20</td></tr>
<tr><td>4</td><td>Unknown Place</td><td>50</td><td>Good</td><td>5</td><td>10</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>
</tbody></table></body></html>
"""


def test_parses_known_stations_only():
    df = parse_lahore_html(SAMPLE, NOW)
    assert set(df.station_id) == {"LHR-MR", "LHR-GT", "LHR-WB"}


def test_values_and_timestamp():
    df = parse_lahore_html(SAMPLE, NOW).set_index("station_id")
    assert df.loc["LHR-MR", "aqi"] == 361 and df.loc["LHR-MR", "pm25"] == 310.8
    assert df.loc["LHR-MR", "aqi_computed"] == 361
    assert df.loc["LHR-WB", "aqi_computed"] in (94, 95)
    # 07:00 PKT == 02:00 UTC
    assert df.loc["LHR-GT", "ts"].hour == 2


def test_empty_page():
    assert parse_lahore_html("<html></html>", NOW).empty


HOME = """
<html><body><p>Last updated: 10:00 AM, Oct 13, 2026</p>
<table><tr><th>Rank</th><th>District</th><th>AQI</th><th>Level</th></tr>
<tr><td>1</td><td>Okara</td><td>175</td><td>Unhealthy for sensitive groups</td></tr>
<tr><td>2</td><td>DG Khan</td><td>160</td><td>Unhealthy for sensitive groups</td></tr>
<tr><td>3</td><td>Lahore</td><td>140</td><td>Moderate</td></tr>
<tr><td>4</td><td>Atlantis</td><td>99</td><td>Satisfactory</td></tr>
</table></body></html>
"""


def test_home_parser(registry):
    from airlume.collectors.epa import parse_home_html
    lookup = {c.name.lower(): c.city_id for c in registry.cities}
    df = parse_home_html(HOME, lookup, NOW)
    got = dict(zip(df.city_id, df.aqi))
    assert got == {"PB-OKA": 175, "PB-DGK": 160, "PB-LHE": 140}
    assert df.ts.iloc[0].hour == 5  # 10:00 PKT = 05:00 UTC

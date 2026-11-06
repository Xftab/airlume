from datetime import datetime, timezone
from pathlib import Path

from airlume.collectors.epa import parse_lahore_forecast, parse_lahore_html, parse_lahore_trend

HTML = (Path(__file__).parent / "fixtures" / "lahore_page_2026-10-14.html").read_text(encoding="utf-8")


def test_station_table_live_fixture():
    df = parse_lahore_html(HTML)
    assert len(df) == 10 and set(df.columns) >= {"co", "so2", "no2", "o3"}
    mr = df[df.station_id == "LHR-MR"].iloc[0]
    assert mr.aqi == 248 and mr.pm25 == 110.7 and mr.ts == datetime(2026, 10, 14, 4, tzinfo=timezone.utc)


def test_trend_hours():
    t = parse_lahore_trend(HTML)
    assert len(t) == 24 + 10  # all of 13 Oct + 00:00-09:00 on 14 Oct (future hours are blank)
    row = t[t.ts == datetime(2026, 10, 12, 22, tzinfo=timezone.utc)].iloc[0]  # 03:00 PKT 13 Oct
    assert row.aqi == 218 and row.city_id == "PB-LHE"


def test_forecast_rows():
    f = parse_lahore_forecast(HTML)
    assert len(f) == 8
    assert f.iloc[0].target_ts == datetime(2026, 10, 14, 5, tzinfo=timezone.utc) and f.iloc[0].aqi == 131
    assert (f.issued_at == datetime(2026, 10, 14, 4, tzinfo=timezone.utc)).all()


# 6 Nov 2026: the snapshot's 7-day trend carries city-level PM2.5 and PM10.
from datetime import datetime, timezone  # noqa: E402

from airlume.collectors.epa import parse_lahore_trend_snapshot  # noqa: E402

TREND_SNAP = (Path(__file__).parent / "fixtures" / "lahore_trend_snapshot_2026-10-14.html").read_text(encoding="utf-8")


def test_trend_snapshot_has_concentrations():
    t = parse_lahore_trend_snapshot(TREND_SNAP)
    assert len(t) == 34  # 13 Oct (24 h) and 14 Oct up to 09:00 PKT (10 h)
    assert t["pm25"].notna().all() and t["pm10"].notna().all()
    assert set(t["city_id"]) == {"PB-LHE"} and set(t["n_stations"]) == {11}
    last = t.sort_values("ts").iloc[-1]
    assert last["ts"] == datetime(2026, 10, 14, 4, tzinfo=timezone.utc)  # 09:00 PKT
    assert (last["aqi"], last["pm25"], last["pm10"]) == (147, 82.86, 189.01)


def test_trend_prefers_snapshot_and_falls_back_to_spans():
    assert parse_lahore_trend(TREND_SNAP)["pm25"].notna().all()
    spans = parse_lahore_trend(HTML)  # the older fixture has no snapshot trend
    assert not spans.empty and spans["pm25"].isna().all()

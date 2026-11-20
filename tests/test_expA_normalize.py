"""Experiment A: reading the form arm's sentences back, and the code and SQL results.

Most sentences here are written by the app's own answer code (resolve -> answer) on the
synthetic snapshot, so a change to a sentence template in answer.py fails this file
instead of silently mis-scoring the form arm. The hand-written ones pin the traps:
digits inside names, thresholds, dates and clock times.
"""
import pytest

from airlume.eval.expA.formarm import build_store, parser_for, run_form
from airlume.eval.expA.normalize import (Answer, canon, from_code_result, from_model_reply,
                                         from_resolve_error, from_sql_rows, render)
from airlume.eval.expA.reference import Reference
from airlume.eval.expA.snapshot import freeze
from airlume.nl.schema import TimeSpec, ViewIntent
from expA_synth import CUTOFF, frames


@pytest.fixture(scope="module")
def world(tmp_path_factory, registry):
    snap = freeze(CUTOFF, name="synth", root=tmp_path_factory.mktemp("expA-n"), registry=registry, frames=frames())
    return {"snap": snap, "store": build_store(snap.raw()), "ref": Reference(snap.tables(), snap.now()),
            "now": snap.now(), "parser": parser_for(registry)}


def _form(world, registry, **kw) -> Answer:
    kw.setdefault("time", TimeSpec(label="now"))
    return run_form(ViewIntent(**kw), world["store"], registry, world["now"], world["parser"])


def _same(a: Answer, g) -> bool:
    return a.kind == g.kind and canon(a.place) == canon(g.place) and a.value == pytest.approx(g.value, abs=1.0)


# --------------------------------------------------------------------------- form arm, end to end

def test_station_now_and_window(world, registry):
    a = _form(world, registry, area="GT Road", aggregation="latest", view="stations_3d", camera="station")
    assert (a.parsed_by, a.place, a.value, a.unit) == ("station_one", "GT Road", 222.0, "aqi")
    assert _same(a, world["ref"].station_latest("GT Road"))
    a = _form(world, registry, area="GT Road", time=TimeSpec(label="yesterday"), aggregation="max",
              view="stations_3d", camera="station")
    assert (a.place, a.value) == ("GT Road", 246.0)
    a = _form(world, registry, area="GT Road", metric="pm25", aggregation="latest", view="stations_3d")
    assert (a.value, a.unit) == (111.0, "pm25")


def test_lahore_now_uses_city_figure_not_cams(world, registry):
    a = _form(world, registry, aggregation="latest", view="stations_3d")
    assert (a.parsed_by, a.place, a.value) == ("city_now", "Lahore", 240.0)
    assert _same(a, world["ref"].city_latest("Lahore"))
    a = _form(world, registry, city="Lahore", aggregation="latest", view="city_overview")
    assert (a.place, a.value) == ("Lahore", 240.0)                 # 20 Nov fix: never the CAMS 500


def test_hours_above_threshold(world, registry):
    a = _form(world, registry, area="Kahna Nau", time=TimeSpec(label="yesterday"),
              aggregation="count_hours_above", threshold=300, view="stations_3d")
    assert (a.parsed_by, a.place, a.value, a.unit) == ("station_count", "Kahna Nau", 17.0, "hours")
    assert _same(a, world["ref"].hours_above("Kahna Nau", "yesterday", 300))


def test_rankings(world, registry):
    a = _form(world, registry, aggregation="max", view="stations_3d")
    assert (a.parsed_by, a.place, a.value) == ("station_rank", "Kahna Nau", 310.0)  # stale reading ranks first (5.4)
    assert world["ref"].rank_stations("now").place == "GT Road"
    a = _form(world, registry, aggregation="min", view="stations_3d")
    assert (a.place, a.value) == ("Safari Park", 150.0)
    a = _form(world, registry, view="city_overview", aggregation="min", camera="zoomed_out")
    assert (a.parsed_by, a.place, a.value) == ("city_rank_now", "Bahawalpur", 170.0)
    a = _form(world, registry, view="city_overview", aggregation="max", time=TimeSpec(label="yesterday"),
              camera="zoomed_out")
    assert (a.parsed_by, a.place, a.value) == ("city_rank_window", "Faisalabad", 260.0)


def test_city_window_and_pairs(world, registry):
    a = _form(world, registry, city="Multan", time=TimeSpec(label="today"), aggregation="mean", view="city_overview")
    assert (a.parsed_by, a.place, a.value) == ("city_window", "Multan", 180.0)
    a = _form(world, registry, city="Multan", other_city="Bahawalpur", compare_to="other_city", view="compare",
              time=TimeSpec(label="this_month"), aggregation="mean")
    assert a.parsed_by == "city_pair_window" and a.pair == {"Multan": 180.0, "Bahawalpur": 170.0}
    a = _form(world, registry, city="Multan", other_city="Bahawalpur", compare_to="other_city", view="compare",
              aggregation="latest")
    assert (a.parsed_by, a.place, a.value) == ("city_pair_now", "Multan", 180.0)
    a = _form(world, registry, city="Multan", compare_to="yesterday", view="compare", aggregation="mean")
    assert a.parsed_by == "city_window" and (a.value, a.previous) == (180.0, 180.0)


def test_forecast_and_time_of_day(world, registry):
    a = _form(world, registry, view="forecast", aggregation="latest")
    assert (a.parsed_by, a.place, a.value) == ("forecast_epa", "Lahore", 260.0)
    assert _same(a, world["ref"].forecast_mean("Lahore"))
    a = _form(world, registry, city="Multan", view="forecast", aggregation="latest")
    assert a.kind == "no_data"
    a = _form(world, registry, area="GT Road", time=TimeSpec(label="last_7_days"), aggregation="hour_of_day",
              view="timeline")
    assert (a.parsed_by, a.place, a.hours_profile) == ("hour_of_day", "GT Road", {"lowest": 0, "highest": 23})


def test_refuse_clarify_and_resolver_messages(world, registry):
    assert _form(world, registry, in_scope=False).kind == "refuse"
    assert _form(world, registry, clarify="Which area are you in?").kind == "clarify"
    assert _form(world, registry, city="Hyderabad").kind == "no_data"
    assert _form(world, registry, area="Qwerty Colony").kind == "no_data"
    assert _form(world, registry, area="Shahdara", aggregation="latest", view="stations_3d").kind == "no_data"


def test_known_app_differences_are_measured_not_hidden(world, registry):
    """App behaviours the experiment will count against the form arm (protocol, section 5.4)."""
    stale = _form(world, registry, area="Kahna Nau", aggregation="latest", view="stations_3d", camera="station")
    assert (stale.kind, stale.value) == ("answer", 310.0)            # a six-hour-old reading called "right now"
    assert world["ref"].station_latest("Kahna Nau").kind == "no_data"
    zero = _form(world, registry, area="Safari Park", time=TimeSpec(label="yesterday"),
                 aggregation="count_hours_above", threshold=300, view="stations_3d")
    assert zero.value is None and zero.detail == "no station listed"  # app prints no count when it is zero
    assert world["ref"].hours_above("Safari Park", "yesterday", 300).value == 0.0


# --------------------------------------------------------------------------- hand-written traps

@pytest.fixture(scope="module")
def parser(registry):
    return parser_for(registry)


@pytest.mark.parametrize("text,place,value,unit", [
    ("DHA Phase 6: AQI 250 (very unhealthy), right now. Advice for DHA Phase 6: Wear an N95 mask.",
     "DHA Phase 6", 250.0, "aqi"),
    ("Gulberg III: PM2.5 (ug/m3) 123.4, mean, 19 Nov 00:00 to 20 Nov 00:00.", "Gulberg III", 123.4, "pm25"),
    ("Hours with AQI above 200 (19 Nov 00:00 to 20 Nov 00:00): Multan Road: 7 of 24 h.", "Multan Road", 7.0, "hours"),
    ("Worst (mean, 13 Nov 00:00 to 20 Nov 12:00): Wagha Border at 301; cleanest: Safari Park at 180.",
     "Wagha Border", 301.0, "aqi"),
    ("Multan: hours with AQI above 200 5 over 24 h of data (19 Nov 00:00 to 20 Nov 00:00).", "Multan", 5.0, "hours"),
    ("Faisalabad had the worst air over 13 Nov 00:00 to 20 Nov 12:00 (mean PM10 (ug/m3) 310.5; 168 h of data; "
     "30 cities have data). Lahore: 280.1.", "Faisalabad", 310.5, "pm10"),
    ("City-level AQI (no station rows for that window yet): 12 of 24 hours above 300.", "Lahore", 12.0, "hours"),
    ("Lahore city-level AQI (max over the window): 330 (very unhealthy). Compared window: 300. Worse by 30 points.",
     "Lahore", 330.0, "aqi"),
])
def test_traps(parser, text, place, value, unit):
    a = parser.parse(text, default_city="Lahore")
    assert (a.kind, a.place, a.value, a.unit) == ("answer", place, value, unit), a


def test_multi_station_counts_and_spread_have_no_single_answer(parser):
    a = parser.parse("Hours with AQI above 300 (19 Nov 00:00 to 20 Nov 00:00): GT Road: 5 of 24 h; Shahdara: 2 of 24 h.")
    assert a.kind == "answer" and a.value is None and "2 stations" in a.detail
    a = parser.parse("Right now: across 9 stations it ranges from 180 at Safari Park to 300 at GT Road.")
    assert a.value is None and a.parsed_by == "spread_only"


def test_no_data_sentences_and_unparsed(parser):
    for t in ("No data: that window (01 Jan 2023 00:00 to 02 Jan 2023 00:00) falls outside the hourly archive.",
              "No forecast is published for Multan; the EPA Punjab portal publishes one for Lahore only.",
              "I have no recent AQI reading for Karachi, so I cannot compare them right now.",
              "Lahore: mean AQI 230 over 12 h of data (20 Nov 00:00 to 20 Nov 12:00). No data for the comparison window."):
        assert parser.parse(t).kind == "no_data", t
    assert parser.parse("Something new the parser has never seen: 42.").kind == "error"
    assert parser.parse("").kind == "error"


def test_resolver_message_kinds():
    assert from_resolve_error("question is out of scope").kind == "refuse"
    c = from_resolve_error("clarify: Which area are you in?")
    assert (c.kind, c.text) == ("clarify", "Which area are you in?")
    assert from_resolve_error("I could not tell which day you mean.").kind == "clarify"
    assert from_resolve_error("I don't have data for 'Hyderabad'.").kind == "no_data"


# --------------------------------------------------------------------------- code and SQL results

def test_code_results():
    a = from_code_result({"status": "answer", "place": "GT Road", "value": 222, "unit": "AQI"})
    assert (a.kind, a.place, a.value, a.unit) == ("answer", "GT Road", 222.0, "aqi")
    assert from_code_result({"status": "no_data", "place": "Karachi"}).kind == "no_data"
    assert from_code_result({"status": "answer", "place": "X", "value": None}).kind == "no_data"
    assert from_code_result({"status": "answer", "value": float("nan")}).kind == "no_data"
    assert from_code_result(None).kind == "error"
    assert from_code_result({"status": "maybe", "value": 1}).kind == "error"
    assert from_code_result({"status": "answer", "value": True}).kind == "no_data"   # a bool is not a number


def test_sql_rows():
    a = from_sql_rows(["PLACE", "Value", "unit", "previous"], [["Lahore", 230.8, "aqi", 230.0]])
    assert (a.place, a.value, a.previous) == ("Lahore", 230.8, 230.0)
    assert from_sql_rows(["place", "value"], []).kind == "no_data"
    assert from_sql_rows(["place", "value"], [["Karachi", None]]).kind == "no_data"
    assert from_sql_rows(["avg"], [[1.0]]).kind == "error"
    many = from_sql_rows(["place", "value"], [["A", 1], ["B", 2]])
    assert (many.place, many.detail) == ("A", "2 rows; first used")


def test_model_reply_and_rendering():
    assert from_model_reply({"refuse": True, "clarify": None, "code": None}).kind == "refuse"
    assert from_model_reply({"refuse": False, "clarify": "Which area?", "sql": None}).text == "Which area?"
    assert from_model_reply({"refuse": False, "clarify": None, "sql": "SELECT 1"}) is None
    assert from_model_reply(["not", "a", "dict"]).kind == "error"
    assert render(Answer("answer", place="GT Road", value=222.4, unit="aqi")) == "GT Road: AQI 222."
    assert render(Answer("answer", place="Lahore", value=231.0, unit="aqi", previous=230.0)) == \
        "Lahore: AQI 231. Earlier window: 230."
    assert render(Answer("answer", place="GT Road", value=23, unit="hour")) == "GT Road: around 23:00."
    assert render(Answer("no_data")) == "No data for that place and time."

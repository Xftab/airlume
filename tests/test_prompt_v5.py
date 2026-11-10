"""6 Nov 2026: groups 2 to 7 of the 2 Nov classmate run (prompt v5, schema freeze).

Each test pins the behaviour a group needed, on the deterministic fake store, and
names the classmate question it came from. See docs/HISTORY.md, 6 Nov.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from airlume.nl.answer import answer
from airlume.nl.resolve import ResolveError, resolve
from airlume.nl.schema import TimeSpec, ViewIntent
from airlume.pipeline.fake import fake_city_hourly, fake_readings
from airlume.pipeline.store import Store

END = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 13, 17, 30, tzinfo=ZoneInfo("Asia/Karachi"))


@pytest.fixture()
def store(tmp_path, registry):
    s = Store(tmp_path / "v5.duckdb")
    r = fake_readings(registry, hours=24 * 10, end=END)
    s.upsert_readings(r)
    s.upsert_city_hourly(fake_city_hourly(registry, r, hours=24 * 10, end=END))
    return s


# --- groups 4 and 6: a clarify wins over in_scope false --------------------------
def test_clarify_wins_over_out_of_scope():
    # c045 "What is AQI in my location?" came back in_scope false WITH a good question.
    v = ViewIntent(in_scope=False, clarify="Which area are you in?")
    assert v.response_kind() == "clarify"
    assert ViewIntent(in_scope=False).response_kind() == "refuse"
    assert ViewIntent().response_kind() == "answer"


def test_resolver_asks_instead_of_refusing(registry):
    with pytest.raises(ResolveError, match="^clarify: Which area"):
        resolve(ViewIntent(in_scope=False, clarify="Which area are you in?"), registry, NOW)


# --- group 2: "how is the air?" gets the city level, not only a ranking ------------
def test_level_question_gives_city_figure_and_spread(store, registry):
    # c001 "aj hawa kesi han", c005 "kiya mujhe mask wear krna chahiye"
    a = answer(resolve(ViewIntent(), registry, NOW), store, registry)
    assert a.startswith("Lahore right now: AQI")
    assert "ranges from" in a and "Advice for Lahore as a whole" in a
    assert "Worst right now" not in a


def test_ranking_question_still_ranks(store, registry):
    # c004 "kaha pr smog zayada": prompt v5 fills max with time now
    worst = answer(resolve(ViewIntent(aggregation="max"), registry, NOW), store, registry)
    clean = answer(resolve(ViewIntent(aggregation="min"), registry, NOW), store, registry)
    assert worst.startswith("Worst right now:") and "cleanest:" in worst
    assert clean.startswith("Cleanest right now:") and "worst:" in clean


# --- group 3: a named city is answered for itself first -----------------------------
def test_named_city_overview_answers_that_city_first(store, registry):
    # c010 "is the weather clean in lhr", c023 "Is air clean in lahore"
    a = answer(resolve(ViewIntent(city="Lahore", view="city_overview"), registry, NOW), store, registry)
    assert a.startswith("Lahore right now:")


def test_unnamed_city_overview_still_ranks_cities(store, registry):
    a = answer(resolve(ViewIntent(view="city_overview", camera="zoomed_out"), registry, NOW), store, registry)
    assert "has the worst air right now" in a


def test_city_named_flag(registry):
    assert resolve(ViewIntent(), registry, NOW).city_named is False
    assert resolve(ViewIntent(city="Lahore"), registry, NOW).city_named is True


# --- group 5: hour-of-day questions ---------------------------------------------------
def test_hour_of_day_profile(store, registry):
    # c014 "kiya rat ko smok kam hojati?", c062 "morning mein ya evening mein?"
    q = resolve(ViewIntent(aggregation="hour_of_day", view="timeline",
                           time=TimeSpec(label="last_7_days")), registry, NOW)
    a = answer(q, store, registry)
    assert "by time of day" in a and "lowest around" in a and "highest around" in a
    for part in ("night (00-06)", "morning (06-12)", "afternoon (12-18)", "evening (18-24)"):
        assert part in a


def test_hour_of_day_widens_a_single_hour_to_a_week(registry):
    q = resolve(ViewIntent(aggregation="hour_of_day"), registry, NOW)
    assert q.time_label == "last_7_days" and (q.end - q.start).days >= 7
    assert any("last 7 days" in n for n in q.notes)


def test_hour_of_day_for_a_station(store, registry):
    q = resolve(ViewIntent(aggregation="hour_of_day", area="Shahdara",
                           time=TimeSpec(label="last_7_days")), registry, NOW)
    assert answer(q, store, registry).startswith("Shahdara, average AQI by time of day")


# --- the offline stub follows the same v5 rules ---------------------------------------
def test_stub_asks_for_the_users_own_place():
    from airlume.nl.stub_router import route
    assert route("What is AQI around my home?").response_kind() == "clarify"
    assert "district" in route("What is air quality index of my village?").clarify
    assert route("aj hawa kesi han").response_kind() == "answer"
    assert route("Is smog lower at night?").aggregation == "hour_of_day"

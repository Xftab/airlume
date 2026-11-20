"""Prompts for the code and SQL arms of Experiment A (fixed before any run).

Fairness rules, from the protocol (section 4):

- Same model, temperature 0, reasoning effort "low" and output budget as the form arm.
- Same information: the same place names (from the registry), the neighbourhood
  centres behind the app's nearest-station rule, the same AQI bands, the same scope
  rules and the same meaning for time words as the form prompt v5 and the resolver.
- The model never writes the answer sentence in any arm. Each arm returns a place and
  a number (or a refusal, a clarifying question, or "no data"), and code writes the
  sentence from them, as design rule 2 requires of the app.

The prompt text is part of the generation cache key (generate.py), so editing a
prompt after runs have started produces new calls, never a silent mix. Do not edit
after the first scored run; add a new version instead and record it in HISTORY.md.
"""

from __future__ import annotations

import hashlib

from airlume.pipeline.registry import KNOWN_AREAS, Registry

PROMPT_VERSION = "expA-1"

_TIME_AND_MEASURE_RULES = """Time words (use exactly these meanings; all times are Asia/Karachi local time):
- "now", "right now", "currently", "abhi", "is waqt": the latest reading at or before now, if it is at most 3 hours old.
- "today": 00:00 today to now. "yesterday": 00:00 to 24:00 yesterday.
- "last week", "past week", "this week", "last 7 days": 00:00 seven days ago to now.
- "last 30 days": 00:00 thirty days ago to now. "this month": 00:00 on the 1st of this month to now. "last month": the whole previous calendar month.
- A date: 00:00 to 24:00 of that day. A range of dates: 00:00 of the first day to 24:00 of the last.
- "last N hours": from N hours before now to now.
Measures:
- "how is", "what is" the AQI (or PM2.5, PM10): now -> the latest value; over any other time (today, yesterday, last week, a date) -> the mean of the hourly values in that window.
- worst, highest, peak, most smog -> maximum; cleanest, best, lowest -> minimum.
- "how many hours above X", "how often was it <band>" -> the number of hourly values above X (unit "hours"; 0 is an answer).
- "where is it worst now" ranks the latest values; over a window it ranks each place's mean (or each place's maximum when "peak" is asked).
- Compared with an earlier time ("better than yesterday", "kal se behtar", "this week vs last week"): value is the mean over the asked window, previous is the mean over the same span one day (yesterday), seven days (last week) or 365 days (last year) earlier. For "now" the asked window is 00:00 today to now.
- Time of day ("at what time is smog worst", "best time to go out", "kis time zyada"): the hour of the day 0-23 whose mean is highest (lowest for best or cleanest) over the last 7 days unless another window is named; unit "hour".
- AQI unless PM2.5 or PM10 is named. AQI bands (Punjab): Satisfactory >50, Moderate >100, Unhealthy for sensitive groups >150, Unhealthy >200, Very unhealthy >300, Hazardous >400. "Unhealthy hours" means AQI above 200; "hazardous" means above 400.
Places:
- When no place is named, the place is Lahore. A question about a whole city, Lahore included, uses that city's own figure in city_hourly. A ranking inside Lahore ("where", "which area", "which station") uses station_hourly; a ranking of cities ("which city", "in Punjab", "in Pakistan") uses city_hourly.
- Stations exist only in Lahore. A station is named when the question names it or a clear part of its name ("Gulberg" = Gulberg III, "DHA" = DHA Phase 6, "Wagah" = Wagha Border).
- A Lahore neighbourhood listed in table areas has no station of its own: use the nearest station by straight-line distance and name that station as the place.
- A place that is neither a station, a city in the tables nor a listed area: there is no reading for it (status "no_data").
Forecasts (tomorrow, tonight, later today, will it be safe, when will it improve):
- Use the latest issue (largest issued_local) of the "EPA Punjab" forecast for Lahore: the mean AQI of its target hours from the current hour on (target_local at or after now rounded down to the hour). Other cities have no EPA forecast: status "no_data".
Scope:
- refuse when the question is not about air quality in these places (weather, rain, sunrise), asks why or for causes, asks about one person's own body (symptoms, diagnosis, treatment), asks for a forecast further ahead than 48 hours, or is only thanks, a greeting or small talk.
- Asking what to DO at the current level IS in scope ("should I wear a mask", "is it safe to go outside", "mujhe walk pr jana chahiye?"): answer with the current reading for the place asked (Lahore when none is named).
- clarify (one short question) when the place is the user's own location ("near me", "my area", "around my home"), when "kal" could mean yesterday or tomorrow, or when the question has neither a place, a time nor a ranking.
- Roman Urdu is fine: "aaj Gulberg ki hawa kaisi hai" = how is the air in Gulberg today."""

_TABLES = """Tables (all times are Asia/Karachi wall-clock time, without a zone):
- station_hourly(station, city, ts_local, pm25, pm10, aqi): one row per Punjab EPA station per hour.
- city_hourly(city, ts_local, pm25, pm10, aqi): the hourly city figure the Punjab EPA publishes. pm25 and pm10 may be empty outside Lahore.
- forecast(city, issued_local, target_local, aqi, source): published forecasts; source is "EPA Punjab" or "CAMS model".
- stations(station, city, lat, lon); cities(city, province); areas(area, lat, lon, city).
aqi is the AQI the Punjab EPA publishes; pm25 and pm10 are in ug/m3."""


def place_lists(registry: Registry) -> str:
    stations = ", ".join(s.name for s in registry.stations if s.city == "Lahore")
    cities = ", ".join(c.name for c in registry.cities if c.name != "Lahore")
    areas = ", ".join(a.title() for a in KNOWN_AREAS)
    return (f"Lahore stations: {stations}.\n"
            f"Other cities (city level only): {cities}.\n"
            f"Lahore areas without a station (nearest-station rule): {areas}.")


_RESULT = """result = {"status": "answer" or "no_data", "place": station or city name or None, "value": a number or None, "unit": "aqi", "pm25", "pm10", "hours", "hour" or None, "previous": a number or None}
- One place and one number: the place asked about; the top place of a ranking; or, for a comparison of two places, the one the question asks for (the worse one unless it asks which is cleaner or better).
- previous only for a comparison with an earlier time; otherwise None.
- status "no_data" when the tables hold no value for the place, time or forecast asked about."""


def code_prompt(registry: Registry, now_local: str) -> str:
    return f"""You answer questions about air quality in Pakistan by writing Python. Return ONLY a JSON object:
{{"refuse": true or false, "clarify": null or a short question, "code": null or Python code}}
When refuse is true or clarify is set, code is null.

The code runs with pandas as pd, numpy as np, NOW (a pandas Timestamp, local time) and these DataFrames already loaded: stations, cities, areas, station_hourly, city_hourly, forecast. It must set
{_RESULT}
Rules for the code: no file, network or system access; import only pandas, numpy, math, statistics, datetime, collections, itertools or re; do not use eval or DataFrame.query (use boolean masks); do not print the answer, set result.

Now is {now_local} (Asia/Karachi). The data ends at that hour.

{_TABLES}

{place_lists(registry)}

{_TIME_AND_MEASURE_RULES}
"""


def sql_prompt(registry: Registry, now_local: str) -> str:
    return f"""You answer questions about air quality in Pakistan by writing one SQL query for DuckDB. Return ONLY a JSON object:
{{"refuse": true or false, "clarify": null or a short question, "sql": null or one SELECT statement}}
When refuse is true or clarify is set, sql is null.

The query must return exactly one row with the columns place (text or NULL), value (a number or NULL), unit ('aqi', 'pm25', 'pm10', 'hours', 'hour' or NULL) and previous (a number or NULL), or zero rows when the tables hold no value for the place, time or forecast asked about. The row means:
- the place asked about; the top place of a ranking; or, for a comparison of two places, the one the question asks for (the worse one unless it asks which is cleaner or better);
- previous only for a comparison with an earlier time; otherwise NULL.
Write exactly one SELECT statement (WITH is fine). Never modify data. For now, use TIMESTAMP '{now_local}' (not now() or current_timestamp).

Now is {now_local} (Asia/Karachi). The data ends at that hour.

{_TABLES}

{place_lists(registry)}

{_TIME_AND_MEASURE_RULES}
"""


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]

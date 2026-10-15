import pytest
from pydantic import ValidationError

from airlume.nl.schema import JSON_SCHEMA, TimeSpec, ViewIntent


def test_defaults():
    v = ViewIntent()
    assert v.city == "Lahore" and v.metric == "aqi" and v.time.label == "now"


def test_rejects_injection_characters():
    with pytest.raises(ValidationError):
        ViewIntent(city="Lahore'; DROP TABLE readings; --")


def test_rejects_unknown_enum():
    with pytest.raises(ValidationError):
        ViewIntent(metric="no2")


def test_threshold_required():
    with pytest.raises((ValidationError, ValueError)):
        ViewIntent(aggregation="count_hours_above")


def test_custom_date_validated():
    with pytest.raises(ValidationError):
        TimeSpec(label="custom_date", date="13/10/2026")
    assert TimeSpec(label="custom_date", date="2026-10-13").date == "2026-10-13"


def test_schema_has_no_free_sql_field():
    props = JSON_SCHEMA["properties"]
    assert "sql" not in props and "query" not in props and "code" not in props


def test_datetime_in_date_field_is_truncated_to_day():
    from airlume.nl.schema import TimeSpec
    t = TimeSpec(label="custom_range", start="2026-10-16T18:00", end="2026-10-17 06:00")
    assert t.start == "2026-10-16" and t.end == "2026-10-17"

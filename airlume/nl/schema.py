"""The typed view-intent form the language model fills in.

Everything the model can say is one of these enumerations or a short string
that code validates against the station/city registry.  There is no free-form
SQL, code, or URL anywhere in this schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Metric = Literal["aqi", "pm25", "pm10"]
Aggregation = Literal["latest", "mean", "max", "min", "count_hours_above"]
View = Literal["city_overview", "stations_3d", "compare", "timeline", "forecast"]
Camera = Literal["overview", "station", "north", "zoomed_out"]
CompareTo = Literal["none", "yesterday", "last_week", "last_year", "other_city"]


class TimeSpec(BaseModel):
    """A time reference in words. Code turns it into real timestamps (Asia/Karachi)."""

    label: Literal[
        "now",
        "today",
        "yesterday",
        "last_7_days",
        "last_30_days",
        "this_month",
        "last_month",
        "same_day_last_year",
        "custom_date",
        "custom_range",
    ] = "now"
    date: str | None = Field(default=None, description="YYYY-MM-DD when label is custom_date")
    start: str | None = Field(default=None, description="YYYY-MM-DD when label is custom_range")
    end: str | None = Field(default=None, description="YYYY-MM-DD when label is custom_range")

    @field_validator("date", "start", "end")
    @classmethod
    def _iso_date(cls, v: str | None) -> str | None:
        if v is None:
            return v
        from datetime import date

        date.fromisoformat(v)  # raises ValueError if malformed
        return v


class ViewIntent(BaseModel):
    """What the user wants to see. Filled by the model, validated by code."""

    in_scope: bool = Field(
        True, description="False if the question is not about air quality in a monitored city."
    )
    clarify: str | None = Field(
        None, description="A short question back to the user when the request is ambiguous."
    )
    metric: Metric = "aqi"
    city: str = Field("Lahore", description="City name as in the registry.")
    area: str | None = Field(
        None, description="Station or neighbourhood name in the city, e.g. 'Gulberg III'."
    )
    time: TimeSpec = Field(default_factory=TimeSpec)
    aggregation: Aggregation = "latest"
    threshold: int | None = Field(
        None, ge=0, le=500, description="AQI threshold for count_hours_above."
    )
    compare_to: CompareTo = "none"
    other_city: str | None = None
    view: View = "stations_3d"
    camera: Camera = "overview"
    context_ref: bool = Field(
        False, description="True if the question refers back to the previous answer ('and yesterday?')."
    )

    @field_validator("city", "area", "other_city")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = " ".join(v.split())
        if len(v) > 60:
            raise ValueError("name too long")
        if any(ch in v for ch in ";'\"`\\"):
            raise ValueError("name contains forbidden characters")
        return v

    def model_post_init(self, __context: object) -> None:
        if self.aggregation == "count_hours_above" and self.threshold is None:
            raise ValueError("count_hours_above needs a threshold")
        if self.compare_to == "other_city" and not self.other_city:
            raise ValueError("compare_to=other_city needs other_city")


JSON_SCHEMA = ViewIntent.model_json_schema()

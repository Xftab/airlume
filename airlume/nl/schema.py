"""The typed view-intent form the language model fills in.

Everything the model can say is one of these enumerations or a short string
that code validates against the station/city registry.  There is no free-form
SQL, code, or URL anywhere in this schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Metric = Literal["aqi", "pm25", "pm10"]
# "hour_of_day" added 6 Nov 2026 (prompt v5): "is smog lower at night?", "morning or evening?".
Aggregation = Literal["latest", "mean", "max", "min", "count_hours_above", "hour_of_day"]
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

        v = v.strip()
        if "T" in v or " " in v:
            # Models sometimes write a datetime ("2026-10-16T18:00"); keep the day only.
            v = v.split("T")[0].split(" ")[0]
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
    # Nullable from 6 Nov 2026 (prompt v5). With a "Lahore" default, code could not tell
    # "is the air clean in Lahore?" (a named city) from "which city is worst?" (none named),
    # and answered the first with a national headline. None means "not named"; code uses
    # Lahore wherever a single city is needed (`city_or_default`).
    city: str | None = Field(None, description="City name as in the registry; null when no city is named.")
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

    @property
    def city_or_default(self) -> str:
        return self.city or "Lahore"

    def response_kind(self) -> str:
        """"clarify", "refuse" or "answer". One rule for the app, the resolver and the scripts.

        Changed 6 Nov 2026: a clarify wins over in_scope false. The 2 Nov run of the 62
        classmate questions showed the model setting in_scope false *and* writing a sensible
        question back for "when will the smog go low?" and "AQI around my home?"; the app
        showed the refusal and threw the question away. Asking is never harmful; refusing a
        question the model itself thought answerable is.
        """
        if self.clarify:
            return "clarify"
        if not self.in_scope:
            return "refuse"
        return "answer"

    def model_post_init(self, __context: object) -> None:
        if self.aggregation == "count_hours_above" and self.threshold is None:
            raise ValueError("count_hours_above needs a threshold")
        if self.compare_to == "other_city" and not self.other_city:
            raise ValueError("compare_to=other_city needs other_city")


JSON_SCHEMA = ViewIntent.model_json_schema()

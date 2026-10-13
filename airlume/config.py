"""Central configuration.

Every secret comes from environment variables (loaded from `.env` if present).
Nothing in this file holds a real key.  `check_secrets()` runs at startup and
refuses to start in production if a required key is missing or looks fake.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TZ = "Asia/Karachi"

PLACEHOLDER_MARKERS = ("your", "xxx", "changeme", "replace", "<", ">")


@dataclass(frozen=True)
class Settings:
    env: str
    db_path: Path
    use_fake_data: bool
    groq_api_key: str
    google_ai_api_key: str
    openaq_api_key: str
    waqi_token: str
    carto_api_key: str

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"prod", "production"}


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def load_settings() -> Settings:
    db = _get("AIRLUME_DB_PATH", "data/airlume.duckdb")
    return Settings(
        env=_get("AIRLUME_ENV", "development"),
        db_path=(ROOT / db) if not Path(db).is_absolute() else Path(db),
        use_fake_data=_get("AIRLUME_USE_FAKE_DATA", "1") == "1",
        groq_api_key=_get("GROQ_API_KEY"),
        google_ai_api_key=_get("GOOGLE_AI_API_KEY"),
        openaq_api_key=_get("OPENAQ_API_KEY"),
        waqi_token=_get("WAQI_TOKEN"),
        carto_api_key=_get("CARTO_API_KEY"),
    )


def looks_like_placeholder(value: str) -> bool:
    v = value.lower()
    return any(m in v for m in PLACEHOLDER_MARKERS)


def check_secrets(settings: Settings, required: tuple[str, ...] = ()) -> list[str]:
    """Return a list of problems. Empty list means all good.

    `required` names attributes that must be present for the current phase,
    e.g. ("groq_api_key",) once the NL layer is switched on.
    """
    problems: list[str] = []
    for attr in required:
        value = getattr(settings, attr, "")
        if not value:
            problems.append(f"{attr.upper()} is not set (put it in .env)")
        elif looks_like_placeholder(value):
            problems.append(f"{attr.upper()} looks like a placeholder, not a real key")
    if settings.is_production and settings.use_fake_data:
        problems.append("AIRLUME_USE_FAKE_DATA=1 is not allowed in production")
    return problems


def mask(value: str) -> str:
    """Show only the last 4 characters of a secret in logs."""
    if not value:
        return "(empty)"
    return "*" * max(0, len(value) - 4) + value[-4:]

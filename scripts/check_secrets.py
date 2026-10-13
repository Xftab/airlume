"""Startup secret check.  Exit code 1 if anything is wrong.  Run: python scripts/check_secrets.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.config import check_secrets, load_settings, mask

s = load_settings()
problems = check_secrets(s)
print(f"env={s.env}  fake_data={s.use_fake_data}  db={s.db_path}")
for name in ("groq_api_key", "google_ai_api_key", "openaq_api_key", "waqi_token", "carto_api_key"):
    print(f"{name:20s} {mask(getattr(s, name))}")
if problems:
    print("PROBLEMS:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("OK")

"""Startup secret check.  Exit code 1 if anything is wrong.

    python scripts\\check_secrets.py            presence and placeholder check only
    python scripts\\check_secrets.py --live     also ask Groq whether the key authenticates

`--live` was added on 30 Oct 2026, for key rotation. The plain check only proves
a key is present and does not look like a placeholder, which is exactly what a
revoked key also looks like: rotate badly and nothing complains until the next
benchmark run fails 90 times. The live check asks Groq to list models -- an
authentication check that costs no tokens, so it is safe to run against the free
tier as often as you like.

No key is ever printed. `mask()` shows the last four characters only, which is
enough to tell two keys apart and not enough to use one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airlume.config import check_secrets, load_settings, mask

LIVE = "--live" in sys.argv

s = load_settings()
problems = check_secrets(s)
print(f"env={s.env}  fake_data={s.use_fake_data}  db={s.db_path}")
for name in ("groq_api_key", "google_ai_api_key", "openaq_api_key", "waqi_token", "carto_api_key"):
    print(f"{name:20s} {mask(getattr(s, name))}")

if LIVE:
    print()
    if not s.groq_api_key:
        print("groq live check       SKIPPED (no key set)")
    else:
        import requests
        try:
            r = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {s.groq_api_key}"},
                timeout=20,
            )
            if r.status_code == 200:
                n = len(r.json().get("data", []))
                print(f"groq live check       OK ({n} models visible)")
            elif r.status_code in (401, 403):
                print(f"groq live check       REJECTED (HTTP {r.status_code}) -- the key in .env "
                      "is wrong, revoked, or from the wrong account")
                problems.append("GROQ_API_KEY does not authenticate")
            else:
                print(f"groq live check       UNCLEAR (HTTP {r.status_code}) -- not an auth "
                      "failure, so the key may be fine; try again")
        except requests.RequestException as e:
            # A network problem is not a bad key, and must not be reported as one.
            print(f"groq live check       COULD NOT REACH GROQ ({type(e).__name__}) -- "
                  "says nothing about the key")

if problems:
    print("PROBLEMS:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("OK")

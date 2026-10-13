"""Data collectors.  Each one returns a tidy DataFrame; `pipeline.store` writes it.

Rule: `waqi_display` is the only module allowed to talk to WAQI, and it never
returns anything that is written to `data/`.
"""

"""Quick smoke test for insight modules.
RUN NOW in Command Prompt:
    K:
    cd K:\\airlume
    .venv\\Scripts\\activate
    python scripts\\test_insights.py
"""

import sys
sys.path.insert(0, ".")

# ── 1. Priority score ─────────────────────────────────────────────────
from airlume.insights.priority import score_station, BandShare, PriorityScore
import pandas as pd
from datetime import datetime, timezone

print("=" * 60)
print("  TEST: Priority Score Module")
print("=" * 60)

# Fake 48 hours of readings
ts = pd.date_range("2026-10-27", periods=48, freq="h", tz="UTC")
# Mix of AQI values: first 24h bad (200-350), next 24h moderate (80-140)
aqi_vals = [250, 280, 310, 290, 200, 220, 260, 300, 350, 330, 280, 250,
            230, 210, 200, 220, 260, 300, 280, 250, 230, 210, 190, 180,
            130, 120, 110, 100, 90, 80, 95, 105, 115, 125, 135, 140,
            130, 120, 100, 90, 85, 80, 75, 90, 100, 110, 120, 130]

df = pd.DataFrame({"ts": ts, "aqi": aqi_vals, "value": aqi_vals})
start = datetime(2026, 10, 27, tzinfo=timezone.utc)
end = datetime(2026, 10, 29, tzinfo=timezone.utc)

ps = score_station("TEST-001", "Test Station Alpha", df, start, end)
print(f"Score: {ps.score:.1f}/100 ({ps.severity_label})")
print(f"Data confidence: {ps.data_confidence:.0%}")
print(f"Longest bad run: {ps.longest_bad_run_hours} hours")
print(f"Trend: {ps.trend_aqi_per_day:.1f} AQI/day" if ps.trend_aqi_per_day else "Trend: N/A")
print("\nBand distribution:")
for bs in ps.band_shares:
    print(f"  {bs.label:<35} {bs.hours:>3} h ({bs.share:.0%})")
print(f"\nSentence: {ps.sentence()}")

# ── 2. Graded response ───────────────────────────────────────────────
from airlume.insights.graded_response import response_for_aqi, response_sentence, full_advisory

print("\n" + "=" * 60)
print("  TEST: Graded Response Module")
print("=" * 60)

for test_aqi in [45, 120, 185, 260, 350, 450]:
    r = response_for_aqi(test_aqi)
    print(f"\nAQI {test_aqi}: {r.band_label}")
    print(f"  Health: {r.health_advisory}")
    print(f"  Schools: {r.school_guidance}")

print(f"\nSentence test: {response_sentence(260, 'Gulberg III')}")

# ── 3. Scenario calculator ───────────────────────────────────────────
from airlume.insights.scenario import calculate_coverage, SmogGunAssumptions, LAHORE_ZONES

print("\n" + "=" * 60)
print("  TEST: Scenario Calculator")
print("=" * 60)

for zone, area in list(LAHORE_ZONES.items())[:3]:
    result = calculate_coverage(zone, area)
    print(f"\n{zone} ({area} sq km):")
    print(f"  Guns needed: {result.guns_needed}")
    print(f"  Cost: PKR {result.total_cost_pkr:,.0f}")
    print(f"  Water: {result.daily_water_litres:,.0f} L/day")

print(f"\nSentence: {calculate_coverage('Gulberg', 8.5).sentence()}")

print("\n" + "=" * 60)
print("  ALL TESTS PASSED")
print("=" * 60)

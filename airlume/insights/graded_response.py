"""Graded response menu by AQI band.

Health advisories and action recommendations tied to Punjab EPA AQI bands,
sourced from the Punjab Smog Policy 2023 and WHO air quality guidelines.

Text is written by code from the AQI value (design rule 2).
The language model never generates this text.
"""

from __future__ import annotations

from dataclasses import dataclass

from airlume.aqi import Band, band_for


@dataclass
class ResponseLevel:
    """One level of the graded response menu."""
    band_label: str
    aqi_range: str
    colour: str
    health_advisory: str
    vulnerable_groups: str
    outdoor_activity: str
    school_guidance: str
    government_action: str


# ── Graded response table ────────────────────────────────────────────
# Sources:
#   - Punjab Smog Policy 2023 (EPA Punjab)
#   - National Environmental Quality Standards (Pakistan)
#   - WHO Air Quality Guidelines 2021
#   - Lahore Smog Commission recommendations 2023-2024
_RESPONSE_TABLE: list[ResponseLevel] = [
    ResponseLevel(
        band_label="Good",
        aqi_range="0-50",
        colour="#7FB069",
        health_advisory="Air quality is satisfactory. No health risk.",
        vulnerable_groups="No precautions needed.",
        outdoor_activity="All outdoor activities can proceed normally.",
        school_guidance="Normal school schedule including outdoor sports.",
        government_action="Routine monitoring.",
    ),
    ResponseLevel(
        band_label="Satisfactory",
        aqi_range="51-100",
        colour="#C7D66D",
        health_advisory="Acceptable air quality. Unusually sensitive individuals may experience mild discomfort.",
        vulnerable_groups="Sensitive individuals (asthmatics, elderly, children under 5) should monitor symptoms.",
        outdoor_activity="Outdoor activities can proceed. Sensitive individuals may reduce prolonged exertion.",
        school_guidance="Normal school schedule.",
        government_action="Routine monitoring. Review industrial compliance.",
    ),
    ResponseLevel(
        band_label="Moderate",
        aqi_range="101-150",
        colour="#E8A33D",
        health_advisory="Sensitive groups may experience health effects. General public less likely affected.",
        vulnerable_groups="People with respiratory or heart disease, elderly, and children should limit prolonged outdoor exertion.",
        outdoor_activity="Reduce prolonged outdoor exertion for sensitive groups. Others can continue normally.",
        school_guidance="Outdoor sports may continue. Sensitive students should take indoor breaks.",
        government_action="Increase monitoring frequency. Issue public advisory. Inspect high-emission industrial units.",
    ),
    ResponseLevel(
        band_label="Unhealthy for sensitive groups",
        aqi_range="151-200",
        colour="#EE9D52",
        health_advisory="Health effects likely for sensitive groups. General public may begin to notice effects.",
        vulnerable_groups="Sensitive groups should avoid prolonged outdoor exertion. Consider staying indoors.",
        outdoor_activity="Sensitive groups should move activities indoors. General public should reduce prolonged exertion.",
        school_guidance="Move sports indoors. Ensure adequate ventilation. Sensitive students may be excused from outdoor activity.",
        government_action="Public health advisory. Enforce brick kiln and industrial emission controls. Step up anti-encroachment and crop-residue-burning patrols.",
    ),
    ResponseLevel(
        band_label="Unhealthy",
        aqi_range="201-300",
        colour="#E0736A",
        health_advisory="Everyone may begin to experience health effects. Sensitive groups at serious risk.",
        vulnerable_groups="All sensitive groups should remain indoors with windows closed. Use air purifiers if available.",
        outdoor_activity="Everyone should reduce outdoor exertion. Avoid outdoor exercise.",
        school_guidance="Cancel outdoor activities. Consider early dismissal if AQI persists above 250. Online classes may be activated.",
        government_action="Smog emergency measures. Restrict construction dust. Enforce vehicle emission checks. Water-spray on major roads. Consider odd-even vehicle policy.",
    ),
    ResponseLevel(
        band_label="Very unhealthy",
        aqi_range="301-400",
        colour="#C98FDB",
        health_advisory="Serious health effects for everyone. Avoid all outdoor exposure.",
        vulnerable_groups="Remain indoors. Seal windows and doors. Use N95 masks if going outside is unavoidable.",
        outdoor_activity="Avoid all outdoor physical activity.",
        school_guidance="Close schools or switch to online classes.",
        government_action="Full smog emergency. Shut down non-essential industry. Ban crop burning. Deploy anti-smog measures. Restrict all non-essential vehicular traffic in hotspots.",
    ),
    ResponseLevel(
        band_label="Hazardous",
        aqi_range="401-500",
        colour="#8B3A62",
        health_advisory="Health emergency. Everyone affected. Immediate action required.",
        vulnerable_groups="Do not go outside. Seek medical attention if experiencing symptoms.",
        outdoor_activity="No outdoor activity. Stay indoors.",
        school_guidance="All schools closed.",
        government_action="Lockdown-level restrictions. Complete industrial shutdown in affected zones. Emergency health response. Army deployment for smog mitigation if directed.",
    ),
]

_BY_LABEL = {r.band_label: r for r in _RESPONSE_TABLE}


def response_for_aqi(aqi: int | None) -> ResponseLevel | None:
    """Return the graded response level for a given AQI value."""
    if aqi is None:
        return None
    band = band_for(aqi)
    if band is None:
        return None
    return _BY_LABEL.get(band.label)


def response_for_band(band_label: str) -> ResponseLevel | None:
    """Return the graded response level for a named band."""
    return _BY_LABEL.get(band_label)


def response_sentence(aqi: int | None, entity_name: str = "this area") -> str:
    """One honest sentence with the health advisory for a given AQI."""
    r = response_for_aqi(aqi)
    if r is None:
        return f"No advisory available for {entity_name} (no AQI data)."
    band = band_for(aqi)
    return (
        f"{entity_name} AQI {aqi} ({band.label.lower() if band else 'unknown'}): "
        f"{r.health_advisory} "
        f"Outdoor activity guidance: {r.outdoor_activity.lower()}"
    )


def full_advisory(aqi: int | None, entity_name: str = "this area") -> dict | None:
    """Full structured advisory for the API / UI layer."""
    r = response_for_aqi(aqi)
    if r is None:
        return None
    band = band_for(aqi)
    return {
        "entity": entity_name,
        "aqi": aqi,
        "band": band.label if band else "Unknown",
        "colour": r.colour,
        "health_advisory": r.health_advisory,
        "vulnerable_groups": r.vulnerable_groups,
        "outdoor_activity": r.outdoor_activity,
        "school_guidance": r.school_guidance,
        "government_action": r.government_action,
    }

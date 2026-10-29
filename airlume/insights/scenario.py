"""Anti-smog scenario calculator.

Labelled scenario calculator only: area to cover / spray coverage radius,
with radius, cost and effect as placeholder assumptions set by the user
or supervisor. Output wording: "under these assumptions, N units would
cover the area."

NO effect prediction. No causal claims. Delhi studies generally find
limited local effects from anti-smog guns (Gupta et al. 2022).

Text is written by code (design rule 2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class SmogGunAssumptions:
    """All user-settable assumptions for the scenario calculator.

    Defaults are placeholders from publicly available specifications.
    The user or supervisor should confirm or replace these.
    """
    # Anti-smog gun spray radius (metres)
    spray_radius_m: float = 50.0

    # Effective coverage area per gun (sq metres), derived from radius
    # Assumes circular coverage; overlap factor reduces usable area
    overlap_factor: float = 0.7  # 70% usable after overlap

    # Cost per unit (PKR), placeholder from Lahore WASA procurement 2023
    cost_per_unit_pkr: float = 2_500_000.0

    # Water consumption per gun per hour (litres)
    water_litres_per_hour: float = 100.0

    # Operating hours per day
    operating_hours_per_day: float = 8.0

    @property
    def effective_area_per_gun_sqm(self) -> float:
        raw = math.pi * self.spray_radius_m ** 2
        return raw * self.overlap_factor


@dataclass
class ScenarioResult:
    """Result of the anti-smog gun coverage calculation."""
    area_name: str
    area_sqkm: float
    assumptions: SmogGunAssumptions
    guns_needed: int
    total_cost_pkr: float
    daily_water_litres: float

    def sentence(self) -> str:
        """One honest sentence with stated assumptions."""
        return (
            f"Under these assumptions (spray radius {self.assumptions.spray_radius_m:.0f} m, "
            f"{self.assumptions.overlap_factor:.0%} overlap factor), "
            f"{self.guns_needed} anti-smog guns would cover "
            f"{self.area_name} ({self.area_sqkm:.1f} sq km) "
            f"at an estimated cost of PKR {self.total_cost_pkr:,.0f} "
            f"and {self.daily_water_litres:,.0f} litres of water per day. "
            f"This is a coverage calculation only, not an effectiveness prediction."
        )


def calculate_coverage(
    area_name: str,
    area_sqkm: float,
    assumptions: SmogGunAssumptions | None = None,
) -> ScenarioResult:
    """Calculate how many anti-smog guns are needed to cover an area.

    Parameters
    ----------
    area_name : str
        Name of the area (e.g. "Gulberg III", "Lahore cantonment").
    area_sqkm : float
        Area to cover in square kilometres.
    assumptions : SmogGunAssumptions, optional
        Placeholder assumptions. Uses defaults if not provided.

    Returns
    -------
    ScenarioResult with gun count, cost and water requirement.
    """
    if assumptions is None:
        assumptions = SmogGunAssumptions()

    area_sqm = area_sqkm * 1_000_000
    effective_per_gun = assumptions.effective_area_per_gun_sqm
    guns = math.ceil(area_sqm / effective_per_gun) if effective_per_gun > 0 else 0
    total_cost = guns * assumptions.cost_per_unit_pkr
    daily_water = guns * assumptions.water_litres_per_hour * assumptions.operating_hours_per_day

    return ScenarioResult(
        area_name=area_name,
        area_sqkm=area_sqkm,
        assumptions=assumptions,
        guns_needed=guns,
        total_cost_pkr=total_cost,
        daily_water_litres=daily_water,
    )


# ── Predefined area sizes (sq km) for Lahore zones ──────────────────
# Sources: Lahore Development Authority zoning data (approximate)
LAHORE_ZONES: dict[str, float] = {
    "Gulberg": 8.5,
    "Model Town": 6.2,
    "Defence (DHA)": 22.0,
    "Cantonment": 14.5,
    "Old City (Walled City)": 2.6,
    "Township": 10.3,
    "Johar Town": 9.8,
    "Iqbal Town": 11.0,
    "Raiwind Road corridor": 15.0,
    "Lahore (full city)": 1772.0,
}

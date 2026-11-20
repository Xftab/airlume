"""Score Experiment A: correctness against gold, the invented-number test, and the statistics.

Correct (protocol, section 6)
- gold kind refuse, clarify or no_data: the arm gave the same kind;
- two-place comparisons: an answer that states both places' figures (the form arm's
  sentences do) is correct when both are within tolerance; an answer with one place
  and one figure (code, SQL) must give the place the question asks for;
- gold kind answer: the arm answered, named the gold place (any tied place counts),
  and its number is within one display unit of the gold number (AQI 1, PM 0.1 ug/m3,
  hours and hour-of-day exact); for comparisons with an earlier time the earlier
  number must also be within tolerance. The unit is reported but not required.

Invented-number test
- Testable when the gold number moves between the snapshot and its shifted copy.
- "invented": the arm gave a number on both and it did not move. A number written
  into the code or query does not move with the data; one computed from it does.
- "off_shift" (reported separately, not counted as invented): for latest, mean, max
  and min answers a number computed from the data must move by exactly the shift;
  one that moves by another amount was not computed the way the answer claims.

Statistics: Wilson 95% intervals for each rate; for two arms on the same questions,
the exact McNemar test and Newcombe's interval for the paired difference
(Newcombe 1998, method 10, no continuity correction).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .normalize import Answer, canon

Z95 = 1.959963984540054
TOL = {"aqi": 1.0, "pm25": 0.1, "pm10": 0.1, "hours": 0.0, "hour": 0.0}


def tolerance(unit: str | None) -> float:
    return TOL.get(unit or "aqi", 1.0) + 1e-6


def _close(a: float | None, b: float | None, unit: str | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= tolerance(unit)


def _arm_value(gold: dict, arm: Answer) -> float | None:
    """The arm's number for this gold item; time-of-day answers pick the matching extreme."""
    if gold.get("unit") == "hour" and arm.hours_profile:
        which = gold.get("which") or "highest"
        h = arm.hours_profile.get(which)
        return float(h) if h is not None else None
    return arm.value


def judge(gold: dict, arm: Answer) -> dict:
    """One verdict: {'correct': bool, 'why': str}. `gold` is a Gold.to_dict() plus 'which' for hour items."""
    gk = gold["kind"]
    if gk != "answer":
        ok = arm.kind == gk
        return {"correct": ok, "why": "" if ok else f"expected {gk}, got {arm.kind}"}
    if arm.kind != "answer":
        return {"correct": False, "why": f"expected an answer, got {arm.kind}"}
    if gold.get("pair") and arm.pair:
        # The form arm states both cities' figures and which is worse; a person reads the
        # cleaner one off the same sentence. Both figures right = the comparison is right.
        got = {canon(k): v for k, v in arm.pair.items()}
        for place, val in gold["pair"].items():
            if not _close(got.get(canon(place)), val, gold.get("unit")):
                return {"correct": False, "why": f"pair figure for {place}: {got.get(canon(place))}, expected {val}"}
        return {"correct": True, "why": ""}
    places = {canon(gold.get("place"))} | {canon(p) for p in gold.get("tie_places") or []}
    places.discard("")
    if places and canon(arm.place) not in places:
        return {"correct": False, "why": f"place {arm.place!r}, expected {gold.get('place')!r}"}
    v = _arm_value(gold, arm)
    if not _close(v, gold.get("value"), gold.get("unit")):
        return {"correct": False, "why": f"value {v}, expected {gold.get('value')}"}
    if gold.get("previous") is not None and not _close(arm.previous, gold["previous"], gold.get("unit")):
        return {"correct": False, "why": f"earlier value {arm.previous}, expected {gold['previous']}"}
    return {"correct": True, "why": ""}


def invented_check(gold: dict, gold_shift: dict, arm: Answer, arm_shift: Answer, shift: float | None,
                   agg_moves_by_shift: bool) -> dict:
    """{'testable', 'invented', 'off_shift'} for one item (see module docstring)."""
    g0, g1 = gold.get("value"), gold_shift.get("value")
    testable = (gold.get("kind") == "answer" and gold_shift.get("kind") == "answer"
                and g0 is not None and g1 is not None and abs(g1 - g0) > 1e-9)
    a0, a1 = _arm_value(gold, arm), _arm_value(gold_shift, arm_shift)
    answered = arm.kind == "answer" and arm_shift.kind == "answer" and a0 is not None and a1 is not None
    if not (testable and answered):
        return {"testable": False, "invented": False, "off_shift": False}
    invented = abs(a1 - a0) <= 1e-9
    off = (not invented and agg_moves_by_shift and shift is not None and abs((a1 - a0) - shift) > 1e-6)
    return {"testable": True, "invented": invented, "off_shift": off}


# --------------------------------------------------------------------------- statistics

def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float, float]:
    """(rate, low, high). (nan, nan, nan) when n == 0."""
    if n == 0:
        return (math.nan, math.nan, math.nan)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


@dataclass
class Paired:
    n: int
    a: int  # both correct
    b: int  # first only
    c: int  # second only
    d: int  # neither
    diff: float
    low: float
    high: float
    p_mcnemar: float

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def paired(first: list[bool], second: list[bool], z: float = Z95) -> Paired:
    """Difference in correctness rate (first minus second) on the same items."""
    if len(first) != len(second):
        raise ValueError("paired lists must be the same length")
    n = len(first)
    a = sum(1 for x, y in zip(first, second) if x and y)
    b = sum(1 for x, y in zip(first, second) if x and not y)
    c = sum(1 for x, y in zip(first, second) if y and not x)
    d = n - a - b - c
    if n == 0:
        return Paired(0, 0, 0, 0, 0, math.nan, math.nan, math.nan, 1.0)
    p1, p2 = (a + b) / n, (a + c) / n
    _, l1, u1 = wilson(a + b, n, z)
    _, l2, u2 = wilson(a + c, n, z)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    phi = (a * d - b * c) / math.sqrt(den) if den > 0 else 0.0
    diff = p1 - p2
    dl1, du1, dl2, du2 = p1 - l1, u1 - p1, p2 - l2, u2 - p2
    low = diff - math.sqrt(max(0.0, dl1 ** 2 - 2 * phi * dl1 * du2 + du2 ** 2))
    high = diff + math.sqrt(max(0.0, du1 ** 2 - 2 * phi * du1 * dl2 + dl2 ** 2))
    return Paired(n, a, b, c, d, diff, max(-1.0, low), min(1.0, high), mcnemar_exact(b, c))


def rate_dict(k: int, n: int) -> dict:
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": p, "low": lo, "high": hi}

"""Agent 3 — Compound Risk Correlator (the core of SURAKSHA).

Fuses signals from all agents into one explainable risk score per zone.
The design principle: dangerous COMBINATIONS score dramatically higher than
any individual reading, because that is how real industrial fatalities
happen — several individually-tolerable conditions stacking up.

Every fired rule contributes a human-readable reason. No black boxes:
a safety officer (or a regulator) can always see exactly why a zone is red.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..simulator.plant import Plant, Zone
from . import GAS_SIGNAL_CODES, Signal

AGENT = "Correlator"

LEVELS = (  # lower bound -> level name
    (75, "critical"),
    (55, "high"),
    (30, "elevated"),
    (0, "normal"),
)


@dataclass
class ZoneRisk:
    score: int
    level: str
    reasons: list[str] = field(default_factory=list)
    fired_rules: list[str] = field(default_factory=list)


def _level_for(score: int) -> str:
    for bound, name in LEVELS:
        if score >= bound:
            return name
    return "normal"


def _gas_state(codes: set[str]) -> str | None:
    """Highest gas severity present in the zone, if any."""
    for code in ("GAS_CRITICAL", "GAS_HIGH", "GAS_ELEVATED"):
        if code in codes:
            return code
    return None


def correlate(plant: Plant, signals: list[Signal]) -> dict[str, ZoneRisk]:
    by_zone: dict[str, list[Signal]] = {z: [] for z in plant.zones}
    for s in signals:
        by_zone.setdefault(s.zone_id, []).append(s)

    changeover = plant.in_shift_changeover()
    risks: dict[str, ZoneRisk] = {}

    for zone_id, zone in plant.zones.items():
        zone_signals = by_zone[zone_id]
        codes = {s.code for s in zone_signals}
        fired: list[tuple[str, int, str]] = []  # (rule_id, weight, reason)

        def _msg(code: str) -> str:
            for s in zone_signals:
                if s.code == code:
                    return s.message
            return code

        # --- R1/R8: gas concentration state (highest tier only) -------------
        gas = _gas_state(codes)
        if gas == "GAS_CRITICAL":
            fired.append(("R8", 40, f"{_msg(gas)} (R8)"))
        elif gas == "GAS_HIGH":
            fired.append(("R1", 30, f"{_msg(gas)} (R1)"))
        elif gas == "GAS_ELEVATED":
            fired.append(("R1", 20, f"{_msg(gas)} (R1)"))

        # --- R2: sustained rising trend --------------------------------------
        if "RISING_TREND" in codes:
            fired.append(("R2", 15, f"{_msg('RISING_TREND')} (R2)"))

        # --- R3: pressure anomaly --------------------------------------------
        if "PRESSURE_ANOMALY" in codes:
            fired.append(("R3", 15, f"{_msg('PRESSURE_ANOMALY')} (R3)"))

        # --- R4: confined space × abnormal conditions (compound) -------------
        if "PERMIT_CONFLICT_CONFINED_GAS" in codes:
            fired.append(("R4", 30,
                          f"{_msg('PERMIT_CONFLICT_CONFINED_GAS')} — compound risk (R4)"))

        # --- R5: hot work × flammable gas (compound) --------------------------
        if "PERMIT_CONFLICT_HOTWORK_GAS" in codes:
            fired.append(("R5", 35,
                          f"{_msg('PERMIT_CONFLICT_HOTWORK_GAS')} — compound risk (R5)"))

        # --- R9: simultaneous permits in high-hazard zone ----------------------
        if "PERMIT_OVERLAP" in codes:
            fired.append(("R9", 10, f"{_msg('PERMIT_OVERLAP')} (R9)"))

        # --- R6: shift changeover amplifier ------------------------------------
        if changeover and fired:
            fired.append(("R6", 10,
                          f"Shift changeover in progress in {zone.name} — reduced "
                          f"supervision while risk conditions are active (R6)"))

        score = min(100, sum(w for _, w, _ in fired))

        # --- R7: workers exposed amplifier -------------------------------------
        if zone.workers > 0 and score >= 50:
            fired.append(("R7", 10,
                          f"{zone.workers} workers present in {zone.name} while "
                          f"zone risk is elevated — exposure amplifier (R7)"))
            score = min(100, score + 10)

        risks[zone_id] = ZoneRisk(
            score=score,
            level=_level_for(score),
            reasons=[r for _, _, r in fired],
            fired_rules=[rid for rid, _, _ in fired],
        )
    return risks

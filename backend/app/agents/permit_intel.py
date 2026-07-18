"""Agent 2 — Permit Intelligence: dangerous permit × condition combinations.

This is where single-sensor systems go blind: a work permit is "paperwork",
a slightly elevated gas reading is "sub-alarm" — but together they have
repeatedly preceded fatal incidents (hot work near flammables, confined-space
entry during abnormal process conditions).
"""
from __future__ import annotations

from ..simulator.plant import Plant
from . import GAS_SIGNAL_CODES, Signal

AGENT = "PermitIntel"
FLAMMABLE_KINDS = {"CO", "CH4"}
HOTWORK_GAS_LIMIT_PCT = 40.0


def evaluate_permits(plant: Plant, sensor_signals: list[Signal]) -> list[Signal]:
    signals: list[Signal] = []
    by_zone_codes: dict[str, set[str]] = {}
    for s in sensor_signals:
        by_zone_codes.setdefault(s.zone_id, set()).add(s.code)

    for zone in plant.zones.values():
        permits = plant.active_permits(zone.id)
        if not permits:
            continue
        zone_codes = by_zone_codes.get(zone.id, set())

        for p in permits:
            if p.type == "hot_work":
                for sensor in zone.sensors.values():
                    pct = 100.0 * sensor.value / sensor.critical
                    if sensor.kind in FLAMMABLE_KINDS and pct >= HOTWORK_GAS_LIMIT_PCT:
                        signals.append(Signal(
                            AGENT, zone.id, "PERMIT_CONFLICT_HOTWORK_GAS", "high",
                            f"Hot-work permit {p.id} active in {zone.name} while "
                            f"{sensor.kind} at {pct:.0f}% of critical — ignition risk",
                            pct))
                        break

            elif p.type == "confined_space":
                if zone_codes & (GAS_SIGNAL_CODES | {"PRESSURE_ANOMALY"}):
                    signals.append(Signal(
                        AGENT, zone.id, "PERMIT_CONFLICT_CONFINED_GAS", "high",
                        f"Confined-space permit {p.id} active in {zone.name} "
                        f"during abnormal gas/pressure conditions — entrapment risk",
                        0.0))

        if zone.hazard_class == "A" and len(permits) >= 2:
            types = ", ".join(p.type for p in permits)
            signals.append(Signal(
                AGENT, zone.id, "PERMIT_OVERLAP", "warning",
                f"{len(permits)} simultaneous permits ({types}) in high-hazard "
                f"zone {zone.name} — simultaneous operations risk", len(permits)))
    return signals

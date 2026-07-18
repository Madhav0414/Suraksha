"""Agent 1 — Sensor Watch: per-sensor thresholds and trend detection.

Pure functions over plant state; no external calls. Slopes are computed by
least squares over the recent history and normalised to % of the sensor's
critical threshold per minute, so thresholds are sensor-agnostic.
"""
from __future__ import annotations

from ..simulator.plant import Plant, Sensor
from . import Signal

AGENT = "SensorWatch"
GAS_KINDS = {"CO", "CH4", "H2S"}

TREND_WINDOW = 30            # samples (sim-minutes)
MIN_SAMPLES = 10
RISING_TREND_PCT_MIN = 0.25  # % of critical per minute
PRESSURE_SLOPE_PCT_MIN = 0.30
PRESSURE_LEVEL_PCT = 75.0
GAS_ELEVATED_PCT = 60.0
GAS_HIGH_PCT = 80.0


def slope_pct_per_min(sensor: Sensor, window: int = TREND_WINDOW) -> float:
    """Least-squares slope of recent history, in % of critical per minute."""
    h = list(sensor.history)[-window:]
    n = len(h)
    if n < MIN_SAMPLES:
        return 0.0
    xbar = (n - 1) / 2.0
    ybar = sum(h) / n
    num = sum((i - xbar) * (y - ybar) for i, y in enumerate(h))
    den = sum((i - xbar) ** 2 for i in range(n))
    return 100.0 * (num / den) / sensor.critical


def evaluate_sensors(plant: Plant) -> list[Signal]:
    signals: list[Signal] = []
    for zone in plant.zones.values():
        for s in zone.sensors.values():
            pct = 100.0 * s.value / s.critical
            slope = slope_pct_per_min(s)

            if s.kind in GAS_KINDS:
                if pct >= 100.0:
                    signals.append(Signal(
                        AGENT, zone.id, "GAS_CRITICAL", "critical",
                        f"{s.kind} BREACHED critical threshold "
                        f"({s.value:.1f} {s.unit}) in {zone.name}", pct))
                elif pct >= GAS_HIGH_PCT:
                    signals.append(Signal(
                        AGENT, zone.id, "GAS_HIGH", "high",
                        f"{s.kind} at {pct:.0f}% of critical in {zone.name}", pct))
                elif pct >= GAS_ELEVATED_PCT:
                    signals.append(Signal(
                        AGENT, zone.id, "GAS_ELEVATED", "elevated",
                        f"{s.kind} at {pct:.0f}% of critical in {zone.name}", pct))
                if slope >= RISING_TREND_PCT_MIN:
                    signals.append(Signal(
                        AGENT, zone.id, "RISING_TREND", "warning",
                        f"{s.kind} rising {slope:.2f}%/min in {zone.name} "
                        f"— sustained upward drift", slope))

            elif s.kind == "pressure":
                if pct >= PRESSURE_LEVEL_PCT or slope >= PRESSURE_SLOPE_PCT_MIN:
                    signals.append(Signal(
                        AGENT, zone.id, "PRESSURE_ANOMALY", "warning",
                        f"Pressure anomaly in {zone.name}: {s.value:.1f} {s.unit}"
                        f" ({pct:.0f}% of critical, slope {slope:+.2f}%/min)",
                        max(pct, slope)))
    return signals

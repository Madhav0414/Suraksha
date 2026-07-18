"""Tests for Agent 3 — Compound Risk Correlator.

The thesis of the whole project: combinations must score dramatically higher
than any individual signal, and every score must be explainable.
"""
from app.agents.correlator import correlate
from app.agents.permit_intel import evaluate_permits
from app.agents.sensor_watch import evaluate_sensors
from app.simulator.plant import Permit, load_plant


def _permit(zone_id, ptype, pid="P-900"):
    return Permit(id=pid, type=ptype, zone_id=zone_id, status="active",
                  issued_at="Day 1 02:00")


def _rising(sensor, start, rate, n=40):
    sensor.history.clear()
    for i in range(n):
        sensor.history.append(start + i * rate)
    sensor.value = sensor.history[-1]


def _evaluate(plant):
    sensor_signals = evaluate_sensors(plant)
    permit_signals = evaluate_permits(plant, sensor_signals)
    return correlate(plant, sensor_signals + permit_signals)


def test_compound_beats_singles():
    """Gas elevated + rising + confined-space permit + changeover + workers
    => CRITICAL, even though no sensor is anywhere near its alarm point."""
    plant = load_plant()
    co = plant.zones["coke_oven"].sensors["co_cob_1"]
    _rising(co, start=50.0, rate=0.30)          # ends ~62% of critical, rising
    plant.permits.append(_permit("coke_oven", "confined_space"))
    plant.shift_minute = 470                     # inside changeover window
    risks = _evaluate(plant)
    risk = risks["coke_oven"]
    assert risk.score >= 75
    assert risk.level == "critical"


def test_single_signal_stays_subcritical():
    """The same gas reading alone must NOT be critical — that asymmetry is
    the innovation claim."""
    plant = load_plant()
    plant.zones["coke_oven"].sensors["co_cob_1"].value = 62.0
    risk = _evaluate(plant)["coke_oven"]
    assert risk.score < 55
    assert risk.level in ("normal", "elevated")


def test_benign_zone_is_normal():
    plant = load_plant()
    risk = _evaluate(plant)["rolling_mill"]
    assert risk.score < 10
    assert risk.level == "normal"


def test_reasons_are_explainable():
    plant = load_plant()
    co = plant.zones["coke_oven"].sensors["co_cob_1"]
    _rising(co, start=50.0, rate=0.30)
    plant.permits.append(_permit("coke_oven", "confined_space"))
    plant.shift_minute = 470
    risk = _evaluate(plant)["coke_oven"]
    assert len(risk.reasons) == len(risk.fired_rules) >= 4
    for rule_id, reason in zip(risk.fired_rules, risk.reasons):
        assert rule_id in reason, f"reason must cite its rule id: {reason}"


def test_score_capped_at_100():
    plant = load_plant()
    co = plant.zones["coke_oven"].sensors["co_cob_1"]
    _rising(co, start=100.0, rate=0.5)           # over critical + rising
    prs = plant.zones["coke_oven"].sensors["prs_cob_1"]
    _rising(prs, start=150.0, rate=0.7)          # pressure anomaly
    plant.permits.append(_permit("coke_oven", "confined_space", "P-901"))
    plant.permits.append(_permit("coke_oven", "hot_work", "P-902"))
    plant.shift_minute = 470
    risk = _evaluate(plant)["coke_oven"]
    assert risk.score == 100

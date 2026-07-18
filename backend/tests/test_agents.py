"""Tests for plant model and agents 1, 2, 4, 5."""
from app.agents.permit_intel import evaluate_permits
from app.agents.sensor_watch import evaluate_sensors
from app.simulator.plant import Permit, load_plant


def _permit(zone_id, ptype, pid="P-900"):
    return Permit(id=pid, type=ptype, zone_id=zone_id, status="active",
                  issued_at="Day 1 02:00")


def _codes(signals, zone_id=None):
    return {s.code for s in signals if zone_id is None or s.zone_id == zone_id}


def _inject_history(sensor, start, rate_units_per_min, n=40):
    """Fill a sensor's history with a clean linear ramp."""
    sensor.history.clear()
    for i in range(n):
        sensor.history.append(start + i * rate_units_per_min)
    sensor.value = sensor.history[-1]


def test_sensor_watch_baseline_is_quiet():
    plant = load_plant()
    assert evaluate_sensors(plant) == []


def test_sensor_watch_gas_elevated():
    plant = load_plant()
    co = plant.zones["coke_oven"].sensors["co_cob_1"]
    co.value = 62.0  # 62% of critical 100
    signals = evaluate_sensors(plant)
    assert "GAS_ELEVATED" in _codes(signals, "coke_oven")


def test_sensor_watch_gas_critical_beats_elevated():
    plant = load_plant()
    co = plant.zones["coke_oven"].sensors["co_cob_1"]
    co.value = 105.0
    codes = _codes(evaluate_sensors(plant), "coke_oven")
    assert "GAS_CRITICAL" in codes and "GAS_ELEVATED" not in codes


def test_sensor_watch_rising_trend():
    plant = load_plant()
    co = plant.zones["coke_oven"].sensors["co_cob_1"]
    _inject_history(co, start=10.0, rate_units_per_min=0.30)  # 0.30%/min of 100
    assert "RISING_TREND" in _codes(evaluate_sensors(plant), "coke_oven")


def test_sensor_watch_pressure_anomaly_by_slope():
    plant = load_plant()
    prs = plant.zones["coke_oven"].sensors["prs_cob_1"]
    _inject_history(prs, start=104.0, rate_units_per_min=0.63)  # 0.35%/min of 180
    assert "PRESSURE_ANOMALY" in _codes(evaluate_sensors(plant), "coke_oven")


# ---- Agent 2: Permit Intelligence ------------------------------------------

def test_permit_hotwork_gas_conflict():
    plant = load_plant()
    plant.permits.append(_permit("storage_yard", "hot_work"))
    ch4 = plant.zones["storage_yard"].sensors["ch4_sy_1"]
    ch4.value = 22.0  # 44% of critical 50 — above the 40% hot-work limit
    signals = evaluate_permits(plant, evaluate_sensors(plant))
    assert "PERMIT_CONFLICT_HOTWORK_GAS" in _codes(signals, "storage_yard")


def test_permit_hotwork_no_conflict_when_gas_low():
    plant = load_plant()
    plant.permits.append(_permit("storage_yard", "hot_work"))
    signals = evaluate_permits(plant, evaluate_sensors(plant))
    assert "PERMIT_CONFLICT_HOTWORK_GAS" not in _codes(signals, "storage_yard")


def test_permit_confined_space_gas_conflict():
    plant = load_plant()
    plant.permits.append(_permit("coke_oven", "confined_space"))
    co = plant.zones["coke_oven"].sensors["co_cob_1"]
    co.value = 62.0  # GAS_ELEVATED
    signals = evaluate_permits(plant, evaluate_sensors(plant))
    assert "PERMIT_CONFLICT_CONFINED_GAS" in _codes(signals, "coke_oven")


def test_permit_confined_space_quiet_when_normal():
    plant = load_plant()
    plant.permits.append(_permit("coke_oven", "confined_space"))
    signals = evaluate_permits(plant, evaluate_sensors(plant))
    assert "PERMIT_CONFLICT_CONFINED_GAS" not in _codes(signals, "coke_oven")


def test_permit_overlap_in_class_a_zone():
    plant = load_plant()
    plant.permits.append(_permit("coke_oven", "maintenance", "P-901"))
    plant.permits.append(_permit("coke_oven", "electrical", "P-902"))
    signals = evaluate_permits(plant, [])
    assert "PERMIT_OVERLAP" in _codes(signals, "coke_oven")


# ---- Agent 4: Emergency Response Orchestrator -------------------------------

def _critical_risk():
    from app.agents.correlator import ZoneRisk
    return ZoneRisk(score=85, level="critical",
                    reasons=["CO at 63% of critical in Coke Oven Battery (R1)",
                             "Confined-space permit P-104 ... compound risk (R4)"],
                    fired_rules=["R1", "R4"])


def test_orchestrator_fires_evacuation_once():
    from app.agents.orchestrator import orchestrate
    plant = load_plant()
    risks = {"coke_oven": _critical_risk()}
    first = orchestrate(plant, risks, prev_levels={"coke_oven": "high"},
                        now="Day 1 03:00")
    kinds = [a.kind for a in first]
    assert "EVACUATION_ORDER" in kinds
    assert "NOTIFY_TEAMS" in kinds
    assert "PRESERVE_EVIDENCE" in kinds
    # second tick, still critical: no duplicate evacuation
    second = orchestrate(plant, risks, prev_levels={"coke_oven": "critical"},
                         now="Day 1 03:01")
    assert "EVACUATION_ORDER" not in [a.kind for a in second]


# ---- Agent 5: Compliance citations ------------------------------------------

def test_compliance_r4_citations():
    from app.agents.compliance import cite
    citations = cite(["R4"])
    ids = {c.reg_id for c in citations}
    assert "FactoriesAct-36" in ids
    assert "OISD-GDN-206" in ids
    assert all(c.applies_to_rule == "R4" for c in citations)


def test_compliance_unknown_rule_empty():
    from app.agents.compliance import cite
    assert cite(["R99"]) == []


def test_compliance_no_duplicate_regs():
    from app.agents.compliance import cite
    citations = cite(["R4", "R5", "R9"])  # OISD-STD-105 maps to all three
    ids = [c.reg_id for c in citations]
    assert len(ids) == len(set(ids)), "each regulation cited once"


def test_incident_report_contents():
    from app.agents.orchestrator import generate_incident_report, orchestrate
    plant = load_plant()
    risks = {"coke_oven": _critical_risk()}
    actions = orchestrate(plant, risks, prev_levels={"coke_oven": "high"},
                          now="Day 1 03:00")
    report = generate_incident_report(plant, "coke_oven", risks["coke_oven"],
                                      actions, now="Day 1 03:00")
    assert "Coke Oven Battery" in report
    assert "R4" in report
    assert "PRELIMINARY INCIDENT REPORT" in report
    assert report.count("|") > 10  # has timeline/sensor tables


def test_plant_loads():
    plant = load_plant()
    assert len(plant.zones) == 6
    coke = plant.zones["coke_oven"]
    kinds = {s.kind for s in coke.sensors.values()}
    assert {"CO", "CH4", "pressure", "temp"} <= kinds
    for zone in plant.zones.values():
        for sensor in zone.sensors.values():
            assert sensor.baseline < sensor.critical
            assert sensor.value == sensor.baseline  # starts at baseline
    assert plant.shift_minute == 0
    assert plant.permits == []

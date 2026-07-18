"""Regression tests: scripted scenarios must always behave the same way.

These tests are the demo-day safety net — if they pass, the demo cannot fail.
"""
from app.simulator.plant import load_plant
from app.simulator.scenarios import SCENARIOS
from app.state import SimState


def run_headless(scenario: str, ticks: int) -> SimState:
    sim = SimState(load_plant(), SCENARIOS[scenario])
    for _ in range(ticks):
        sim.tick()
    return sim


def test_vizag_replay_gas_reaches_critical():
    """CO in coke oven must cross its critical threshold around t400."""
    sim = run_headless("vizag_replay", 420)
    co = sim.plant.zones["coke_oven"].sensors["co_cob_1"]
    assert co.value >= co.critical, "CO should breach critical by t420"


def test_vizag_replay_drift_is_monotone_after_onset():
    """Once drift starts (t60), CO trend must rise steadily (noise aside)."""
    sim = run_headless("vizag_replay", 300)
    hist = list(sim.plant.zones["coke_oven"].sensors["co_cob_1"].history)
    # compare averages of consecutive 30-sample windows — must increase
    windows = [sum(hist[i:i + 30]) / 30 for i in range(0, len(hist) - 30, 30)]
    assert all(b > a for a, b in zip(windows, windows[1:]))


def test_vizag_replay_confined_space_permit_issued():
    sim = run_headless("vizag_replay", 150)
    active = sim.plant.active_permits("coke_oven")
    assert any(p.type == "confined_space" for p in active)


def test_normal_day_stays_near_baseline():
    sim = run_headless("normal_day", 300)
    for zone in sim.plant.zones.values():
        for s in zone.sensors.values():
            headroom = s.critical - s.baseline
            assert abs(s.value - s.baseline) < 0.15 * headroom, \
                f"{s.id} drifted in normal_day"


def test_near_miss_recedes_after_permit_closed():
    sim = run_headless("near_miss", 300)
    active = sim.plant.active_permits("storage_yard")
    assert not any(p.type == "hot_work" for p in active), "hot work closed at t120"


# ---- Full-pipeline regression: THE demo-day guarantee -----------------------

def test_full_pipeline_vizag_detection_lead():
    """SURAKSHA must go critical hours before any single sensor alarms.

    If this test passes, the demo cannot fail.
    """
    from app.state import Pipeline
    pipe = Pipeline("vizag_replay")
    for _ in range(420):
        pipe.step()

    assert pipe.first_critical_tick is not None, "SURAKSHA never went critical"
    assert 150 <= pipe.first_critical_tick <= 230, \
        f"critical at t{pipe.first_critical_tick}, expected during danger window"
    assert pipe.baseline_alarm_tick is not None, "baseline never alarmed"
    assert pipe.baseline_alarm_tick >= 370, \
        f"baseline alarmed too early: t{pipe.baseline_alarm_tick}"
    lead = pipe.baseline_alarm_tick - pipe.first_critical_tick
    assert lead >= 150, f"lead time only {lead} min"
    assert pipe.latest_report is not None
    assert "PRELIMINARY INCIDENT REPORT" in pipe.latest_report


def test_full_pipeline_payload_schema():
    from app.state import Pipeline
    pipe = Pipeline("normal_day")
    payload = None
    for _ in range(30):
        payload = pipe.step()
    assert set(payload) >= {"sim_time", "tick", "scenario", "kpi", "zones",
                            "permits", "alerts", "agent_log", "citations"}
    zone = next(z for z in payload["zones"] if z["id"] == "coke_oven")
    assert {"id", "name", "x", "y", "w", "h", "risk", "level", "workers",
            "reasons", "sensors"} <= set(zone)
    sensor = zone["sensors"][0]
    assert {"id", "kind", "value", "pct_critical", "unit", "history"} <= set(sensor)
    assert len(sensor["history"]) <= 60


def test_full_pipeline_normal_day_no_critical():
    from app.state import Pipeline
    pipe = Pipeline("normal_day")
    for _ in range(300):
        pipe.step()
    assert pipe.first_critical_tick is None, "false positive on normal day!"


def test_reset_is_reproducible():
    a = run_headless("vizag_replay", 200)
    b = run_headless("vizag_replay", 200)
    va = a.plant.zones["coke_oven"].sensors["co_cob_1"].value
    vb = b.plant.zones["coke_oven"].sensors["co_cob_1"].value
    assert va == vb, "same seed must give identical runs"

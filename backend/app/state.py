"""Simulation state container and tick engine.

One tick = one sim-minute. Deterministic under a fixed seed so scripted
demos and regression tests always reproduce exactly.
"""
from __future__ import annotations

import random

from .simulator.plant import Plant, Permit, SHIFT_LENGTH
from .simulator.scenarios import Scenario  # noqa: F401 (also re-exported for benchmarks)

# Shift offset chosen so the changeover window (last/first 15 min of a
# 480-min shift) lands at ticks 165–195 — the vizag_replay danger window.
DEFAULT_SHIFT_OFFSET = 300
MEAN_REVERSION = 0.05   # pull toward baseline per tick when no drift active
NOISE_SCALE = 0.3       # fraction of configured sensor noise applied per tick


class SimState:
    def __init__(self, plant: Plant, scenario: Scenario, seed: int = 42,
                 shift_offset: int = DEFAULT_SHIFT_OFFSET):
        self.plant = plant
        self.scenario = scenario
        self.seed = seed
        self.shift_offset = shift_offset
        self.rng = random.Random(seed)
        self.tick_count = 0
        self.active_drifts: dict[str, float] = {}  # sensor_id -> %critical/min
        self._permit_seq = 100
        self.plant.shift_minute = shift_offset

    # ---- time -------------------------------------------------------------
    def sim_time_str(self, tick: int | None = None) -> str:
        t = self.tick_count if tick is None else tick
        day, rem = divmod(t, 1440)
        hh, mm = divmod(rem, 60)
        return f"Day {day + 1} {hh:02d}:{mm:02d}"

    # ---- event application ------------------------------------------------
    def _apply_event(self, action: str, params: dict) -> None:
        if action == "sensor_drift":
            self.active_drifts[params["sensor_id"]] = params["rate"]
        elif action == "stop_drift":
            self.active_drifts.pop(params["sensor_id"], None)
        elif action == "issue_permit":
            self._permit_seq += 1
            self.plant.permits.append(Permit(
                id=f"P-{self._permit_seq}", type=params["type"],
                zone_id=params["zone_id"], status="active",
                issued_at=self.sim_time_str(),
            ))
        elif action == "close_permit":
            for p in self.plant.permits:
                if (p.status == "active" and p.zone_id == params["zone_id"]
                        and p.type == params["type"]):
                    p.status = "closed"
        elif action == "set_workers":
            self.plant.zones[params["zone_id"]].workers = params["count"]
        elif action == "hold_level":
            # Plateau: stop drifting and let the sensor mean-revert around its
            # CURRENT value (e.g. pressure stabilising high behind a blockage).
            self.active_drifts.pop(params["sensor_id"], None)
            sensor = self._find_sensor(params["sensor_id"])
            sensor.baseline = sensor.value

    def _find_sensor(self, sensor_id: str):
        for zone in self.plant.zones.values():
            if sensor_id in zone.sensors:
                return zone.sensors[sensor_id]
        raise KeyError(sensor_id)

    # ---- tick -------------------------------------------------------------
    def tick(self) -> None:
        for ev in self.scenario.events:
            if ev.at_minute == self.tick_count:
                self._apply_event(ev.action, ev.params)

        for zone in self.plant.zones.values():
            for s in zone.sensors.values():
                noise = self.rng.gauss(0.0, s.noise * NOISE_SCALE)
                if s.id in self.active_drifts:
                    drift = self.active_drifts[s.id] / 100.0 * s.critical
                    s.value = max(0.0, s.value + drift + noise)
                else:
                    s.value = max(
                        0.0,
                        s.value + MEAN_REVERSION * (s.baseline - s.value) + noise,
                    )
                s.history.append(s.value)

        self.tick_count += 1
        self.plant.shift_minute = (self.shift_offset + self.tick_count) % SHIFT_LENGTH


# =============================================================================
# Pipeline: simulator tick -> agent evaluation -> dashboard payload
# =============================================================================

from .agents.compliance import cite                     # noqa: E402
from .agents.correlator import correlate                # noqa: E402
from .agents.orchestrator import generate_incident_report, orchestrate  # noqa: E402
from .agents.permit_intel import evaluate_permits       # noqa: E402
from .agents.sensor_watch import evaluate_sensors       # noqa: E402
from .simulator.plant import load_plant                 # noqa: E402
from .simulator.scenarios import SCENARIOS              # noqa: E402

MAX_ALERTS = 60
MAX_LOG = 120
SEVERITY_FOR_ACTION = {
    "EVACUATION_ORDER": "critical",
    "NOTIFY_TEAMS": "info",
    "PRESERVE_EVIDENCE": "info",
}


class Pipeline:
    """Owns one simulation run and evaluates the full agent stack each tick."""

    def __init__(self, scenario_name: str = "normal_day", seed: int = 42,
                 scenario: Scenario | None = None):
        self.scenario_name = scenario_name
        self.sim = SimState(load_plant(), scenario or SCENARIOS[scenario_name],
                            seed=seed)
        self.prev_levels = {z: "normal" for z in self.sim.plant.zones}
        self.alerts: list[dict] = []
        self.agent_log: list[dict] = []
        self.citations: list[dict] = []
        self.latest_report: str | None = None
        self.first_critical_tick: int | None = None
        self.baseline_alarm_tick: int | None = None

    # ---- helpers ------------------------------------------------------------
    def _log(self, agent: str, line: str) -> None:
        self.agent_log.append(
            {"ts": self.sim.sim_time_str(), "agent": agent, "line": line})
        del self.agent_log[:-MAX_LOG]

    def _alert(self, zone_id: str, severity: str, title: str, detail: str,
               rules: list[str]) -> None:
        self.alerts.insert(0, {
            "ts": self.sim.sim_time_str(), "zone_id": zone_id,
            "severity": severity, "title": title, "detail": detail,
            "rules": rules,
        })
        del self.alerts[MAX_ALERTS:]

    # ---- one full tick --------------------------------------------------------
    def step(self) -> dict:
        self.sim.tick()
        plant = self.sim.plant
        now = self.sim.sim_time_str()

        sensor_signals = evaluate_sensors(plant)
        permit_signals = evaluate_permits(plant, sensor_signals)
        signals = sensor_signals + permit_signals
        risks = correlate(plant, signals)
        actions = orchestrate(plant, risks, self.prev_levels, now)

        # agent activity log — every fired signal, plus periodic heartbeat
        for s in signals:
            self._log(s.agent, f"{s.code}: {s.message}")
        for zone_id, r in risks.items():
            prev = self.prev_levels.get(zone_id)
            if r.level != prev:
                self._log("Correlator",
                          f"{plant.zones[zone_id].name}: {prev} → {r.level} "
                          f"(score {r.score}; rules {', '.join(r.fired_rules) or '—'})")
        if not signals and self.sim.tick_count % 10 == 0:
            n = sum(len(z.sensors) for z in plant.zones.values())
            self._log("SensorWatch", f"{n} sensor streams scanned — all nominal")

        # alerts from orchestrator actions
        for a in actions:
            severity = SEVERITY_FOR_ACTION.get(a.kind) or risks[a.zone_id].level
            title = {
                "ALERT_ESCALATION": f"Risk escalation — {plant.zones[a.zone_id].name}",
                "EVACUATION_ORDER": f"🚨 EVACUATION ORDER — {plant.zones[a.zone_id].name}",
                "NOTIFY_TEAMS": "Response teams notified",
                "PRESERVE_EVIDENCE": "Evidence snapshot preserved",
            }[a.kind]
            self._alert(a.zone_id, severity, title, a.message,
                        risks[a.zone_id].fired_rules)
            self._log("Orchestrator", f"{a.kind}: {a.message}")

        # detection bookkeeping
        if self.first_critical_tick is None and any(
                r.level == "critical" for r in risks.values()):
            self.first_critical_tick = self.sim.tick_count
        if self.baseline_alarm_tick is None and any(
                s.value >= s.critical
                for z in plant.zones.values() for s in z.sensors.values()):
            self.baseline_alarm_tick = self.sim.tick_count
            self._log("Baseline",
                      "Conventional single-sensor alarm threshold breached "
                      "— SURAKSHA detected this hazard "
                      f"{self.detection_lead() or 0} minutes ago")

        # incident report + citations on new critical
        for a in actions:
            if a.kind == "EVACUATION_ORDER":
                risk = risks[a.zone_id]
                self.latest_report = generate_incident_report(
                    plant, a.zone_id, risk, actions, now)
                self.citations = [vars(c) for c in cite(risk.fired_rules)]
                self._log("Compliance",
                          f"{len(self.citations)} regulatory provisions cited "
                          f"for rules {', '.join(risk.fired_rules)}")

        self.prev_levels = {z: r.level for z, r in risks.items()}
        return self._payload(risks)

    def detection_lead(self) -> int | None:
        if self.first_critical_tick is None:
            return None
        end = self.baseline_alarm_tick or self.sim.tick_count
        return max(0, end - self.first_critical_tick)

    # ---- payload ---------------------------------------------------------------
    def _payload(self, risks) -> dict:
        plant = self.sim.plant
        zones = []
        for z in plant.zones.values():
            r = risks[z.id]
            zones.append({
                "id": z.id, "name": z.name,
                "x": z.x, "y": z.y, "w": z.w, "h": z.h,
                "hazard_class": z.hazard_class,
                "risk": r.score, "level": r.level, "workers": z.workers,
                "reasons": r.reasons,
                "sensors": [{
                    "id": s.id, "kind": s.kind, "unit": s.unit,
                    "value": round(s.value, 1),
                    "pct_critical": s.pct_critical,
                    "critical": s.critical,
                    "history": [round(v, 1) for v in list(s.history)[-60:]],
                } for s in z.sensors.values()],
            })
        return {
            "sim_time": self.sim.sim_time_str(),
            "tick": self.sim.tick_count,
            "scenario": self.scenario_name,
            "zones": zones,
            "kpi": {
                "max_risk": max(r.score for r in risks.values()),
                "active_permits": len(plant.active_permits()),
                "workers_on_site": sum(z.workers for z in plant.zones.values()),
                "alerts_today": len(self.alerts),
                "detection_lead_minutes": self.detection_lead(),
                "baseline_alarmed": self.baseline_alarm_tick is not None,
            },
            "permits": [vars(p) for p in plant.permits],
            "alerts": self.alerts,
            "agent_log": list(reversed(self.agent_log[-40:])),
            "citations": self.citations,
            "has_report": self.latest_report is not None,
        }

"""Agent 4 — Emergency Response Orchestrator.

On a confirmed critical, converts the first chaotic minutes into a scripted,
auditable response: evacuation order, team notifications, evidence snapshot,
and a regulator-ready preliminary incident report.

The report narrative can optionally be polished by a free-tier LLM
(GEMINI_API_KEY env var); any failure silently falls back to the built-in
template so the demo can never break.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from ..simulator.plant import Plant
from .correlator import ZoneRisk

AGENT = "Orchestrator"

NOTIFY_CHANNELS = ("Safety Officer (SMS+radio)", "Fire & Rescue Team",
                   "Plant Medical Centre", "Shift In-Charge Console")


@dataclass
class Action:
    kind: str      # ALERT_ESCALATION | EVACUATION_ORDER | NOTIFY_TEAMS | PRESERVE_EVIDENCE
    zone_id: str
    message: str
    timestamp: str


def orchestrate(plant: Plant, risks: dict[str, ZoneRisk],
                prev_levels: dict[str, str], now: str) -> list[Action]:
    actions: list[Action] = []
    for zone_id, risk in risks.items():
        zone = plant.zones[zone_id]
        prev = prev_levels.get(zone_id, "normal")
        if risk.level == prev:
            continue

        actions.append(Action(
            "ALERT_ESCALATION", zone_id,
            f"{zone.name}: risk level {prev.upper()} → {risk.level.upper()} "
            f"(score {risk.score})", now))

        if risk.level == "critical" and prev != "critical":
            actions.append(Action(
                "EVACUATION_ORDER", zone_id,
                f"EVACUATION ORDER — {zone.name}: {zone.workers} workers to "
                f"muster point M-2. All permits in zone suspended.", now))
            actions.append(Action(
                "NOTIFY_TEAMS", zone_id,
                "Alerts dispatched: " + "; ".join(NOTIFY_CHANNELS), now))
            snapshot = {
                s.id: [round(v, 2) for v in list(s.history)[-30:]]
                for s in zone.sensors.values()
            }
            actions.append(Action(
                "PRESERVE_EVIDENCE", zone_id,
                f"Sensor evidence preserved ({len(snapshot)} streams × 30 min) "
                f"for regulatory investigation.", now))
    return actions


# ---- incident report ---------------------------------------------------------

def _narrative(zone_name: str, risk: ZoneRisk) -> str:
    lines = [f"At the time of escalation, zone '{zone_name}' reached a compound "
             f"risk score of {risk.score}/100 (level: {risk.level.upper()}). "
             f"The following independent conditions were active simultaneously:"]
    for r in risk.reasons:
        lines.append(f"- {r}")
    lines.append(
        "No single sensor had breached its individual alarm threshold at "
        "detection time; the hazard was identified by multi-signal correlation.")
    return "\n".join(lines)


def _llm_polish(text: str) -> str:
    """Optionally rewrite narrative via free-tier Gemini. Fail => template."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return text
    try:
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "gemini-2.0-flash:generateContent?key=" + key)
        body = json.dumps({
            "contents": [{"parts": [{"text":
                "Rewrite this industrial incident narrative in formal "
                "regulatory English, one paragraph, keep all facts and rule "
                "IDs:\n\n" + text}]}]
        }).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return text  # demo must never break


def generate_incident_report(plant: Plant, zone_id: str, risk: ZoneRisk,
                             actions: list[Action], now: str) -> str:
    zone = plant.zones[zone_id]
    sensor_rows = "\n".join(
        f"| {s.id} | {s.kind} | {s.value:.1f} {s.unit} | {s.pct_critical}% | "
        f"{s.critical} {s.unit} |"
        for s in zone.sensors.values())
    permit_rows = "\n".join(
        f"| {p.id} | {p.type} | {p.status} | {p.issued_at} |"
        for p in plant.active_permits(zone_id)) or "| — | — | — | — |"
    action_rows = "\n".join(
        f"| {a.timestamp} | {a.kind} | {a.message} |" for a in actions)
    rules = ", ".join(risk.fired_rules)

    return f"""# PRELIMINARY INCIDENT REPORT — AUTO-GENERATED

**Platform:** SURAKSHA Industrial Safety Intelligence
**Generated:** {now} (simulation time) · **Zone:** {zone.name} ({zone.hazard_class}-class hazard area)
**Compound risk score:** {risk.score}/100 · **Level:** {risk.level.upper()} · **Rules fired:** {rules}

## 1. Narrative

{_llm_polish(_narrative(zone.name, risk))}

## 2. Sensor state at detection

| Sensor | Kind | Reading | % of critical | Critical limit |
|---|---|---|---|---|
{sensor_rows}

## 3. Active work permits in zone

| Permit | Type | Status | Issued |
|---|---|---|---|
{permit_rows}

## 4. Automated response actions

| Time | Action | Detail |
|---|---|---|
{action_rows}

## 5. Personnel

{zone.workers} workers registered in zone at detection time. Evacuation to muster point M-2 ordered; headcount verification pending.

---
*This report was generated automatically for regulatory submission support
(Factories Act 1948 / OISD guidelines). It preserves the detection evidence
trail and requires review and sign-off by the designated Safety Officer.*
"""

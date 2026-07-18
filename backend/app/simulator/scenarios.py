"""Scripted scenario timelines.

Each scenario is a list of timed events applied to the plant during ticks.
Rates are expressed in % of the sensor's critical threshold per sim-minute,
so the same scenario logic works for any sensor.

vizag_replay is modeled on the Jan-2025 Visakhapatnam Steel Plant coke-oven
incident pattern: slow gas/pressure drift + confined-space work permit +
shift changeover — every reading individually "tolerable", lethal combined.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Event:
    at_minute: int
    action: str  # sensor_drift | stop_drift | issue_permit | close_permit | set_workers
    params: dict


@dataclass
class Scenario:
    name: str
    label: str
    description: str
    events: list[Event] = field(default_factory=list)


SCENARIOS: dict[str, Scenario] = {
    "normal_day": Scenario(
        name="normal_day",
        label="Normal Day",
        description="Routine operations — sensor noise only, one maintenance permit.",
        events=[
            Event(20, "issue_permit", {"zone_id": "rolling_mill", "type": "maintenance"}),
        ],
    ),
    "near_miss": Scenario(
        name="near_miss",
        label="Near Miss",
        description="Hot-work permit in fuel storage while CH4 rises; permit "
                    "withdrawn after SURAKSHA flags the conflict — risk recedes.",
        events=[
            Event(30, "issue_permit", {"zone_id": "storage_yard", "type": "hot_work"}),
            Event(45, "sensor_drift", {"sensor_id": "ch4_sy_1", "rate": 0.6}),
            Event(120, "close_permit", {"zone_id": "storage_yard", "type": "hot_work"}),
            Event(120, "stop_drift", {"sensor_id": "ch4_sy_1"}),
        ],
    ),
    "vizag_replay": Scenario(
        name="vizag_replay",
        label="Vizag Replay",
        description="Replay of the compound-risk pattern behind the 2025 "
                    "Visakhapatnam coke-oven tragedy: CO + pressure drift, "
                    "confined-space entry, shift changeover.",
        events=[
            Event(60, "sensor_drift", {"sensor_id": "co_cob_1", "rate": 0.28}),
            Event(90, "sensor_drift", {"sensor_id": "prs_cob_1", "rate": 0.35}),
            Event(120, "issue_permit", {"zone_id": "coke_oven", "type": "confined_space"}),
            # pressure stabilises high (~79% of critical) behind the blockage —
            # abnormal but sub-alarm, exactly the Vizag pattern
            Event(150, "hold_level", {"sensor_id": "prs_cob_1"}),
        ],
    ),
}

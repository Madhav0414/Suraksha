"""Plant domain model: zones, sensors, permits, workers — loaded from JSON config."""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PLANT_CONFIG = DATA_DIR / "plant_config.json"

PERMIT_TYPES = ("hot_work", "confined_space", "maintenance", "electrical")
SHIFT_LENGTH = 480  # sim-minutes per shift
CHANGEOVER_WINDOW = 15  # minutes either side of shift boundary


@dataclass
class Sensor:
    id: str
    kind: str  # CO | CH4 | H2S | pressure | temp
    unit: str
    baseline: float
    critical: float
    noise: float
    value: float = 0.0
    history: deque = field(default_factory=lambda: deque(maxlen=120))

    @property
    def pct_critical(self) -> float:
        return round(100.0 * self.value / self.critical, 1)


@dataclass
class Permit:
    id: str
    type: str
    zone_id: str
    status: str  # active | closed
    issued_at: str


@dataclass
class Zone:
    id: str
    name: str
    x: int
    y: int
    w: int
    h: int
    hazard_class: str  # A | B | C
    workers: int
    sensors: dict[str, Sensor]


@dataclass
class Plant:
    name: str
    zones: dict[str, Zone]
    permits: list[Permit] = field(default_factory=list)
    shift_minute: int = 0  # 0..SHIFT_LENGTH-1

    def active_permits(self, zone_id: str | None = None) -> list[Permit]:
        return [
            p for p in self.permits
            if p.status == "active" and (zone_id is None or p.zone_id == zone_id)
        ]

    def in_shift_changeover(self) -> bool:
        m = self.shift_minute % SHIFT_LENGTH
        return m >= SHIFT_LENGTH - CHANGEOVER_WINDOW or m < CHANGEOVER_WINDOW


def load_plant(path: Path | str = PLANT_CONFIG) -> Plant:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    zones: dict[str, Zone] = {}
    for z in cfg["zones"]:
        sensors = {
            s["id"]: Sensor(
                id=s["id"], kind=s["kind"], unit=s["unit"],
                baseline=s["baseline"], critical=s["critical"], noise=s["noise"],
                value=s["baseline"],
            )
            for s in z["sensors"]
        }
        for sensor in sensors.values():
            sensor.history.append(sensor.value)
        zones[z["id"]] = Zone(
            id=z["id"], name=z["name"], x=z["x"], y=z["y"], w=z["w"], h=z["h"],
            hazard_class=z["hazard_class"], workers=z["workers"], sensors=sensors,
        )
    return Plant(name=cfg["name"], zones=zones)

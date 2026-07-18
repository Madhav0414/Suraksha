"""SURAKSHA agent layer — shared Signal type used across all agents."""
from dataclasses import dataclass


@dataclass
class Signal:
    agent: str      # which agent produced this
    zone_id: str
    code: str       # e.g. GAS_ELEVATED, PERMIT_CONFLICT_HOTWORK_GAS
    severity: str   # info | warning | elevated | high | critical
    message: str
    value: float = 0.0


GAS_SIGNAL_CODES = {"GAS_ELEVATED", "GAS_HIGH", "GAS_CRITICAL"}

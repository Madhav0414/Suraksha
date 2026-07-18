"""SURAKSHA benchmark: compound-risk detection vs single-sensor baseline.

Three simulated test sets (all clearly labeled as simulation):
  A. 20 randomized escalating incidents  -> detection lead time distribution
  B. 10 sub-threshold compound incidents -> false-negative comparison
     (conditions stay below every individual alarm threshold — the Vizag
     pattern — so a single-sensor system NEVER alarms)
  C. 20 normal operating days            -> false-positive check

Baseline definition: a conventional system that alarms only when any single
sensor crosses 100% of its critical threshold.

Usage:  backend\\.venv\\Scripts\\python scripts\\run_benchmark.py
Writes: deliverables/metrics.md
"""
from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.simulator.scenarios import Event, Scenario  # noqa: E402
from app.state import Pipeline  # noqa: E402


def make_escalating(seed: int) -> Scenario:
    """Vizag-pattern incident with jittered rates and timings."""
    rng = random.Random(1000 + seed)
    co_start = rng.randint(40, 80)
    co_rate = round(rng.uniform(0.22, 0.34), 3)
    prs_start = co_start + rng.randint(20, 40)
    prs_rate = round(rng.uniform(0.30, 0.40), 3)
    permit_at = rng.randint(100, 140)
    return Scenario(f"bench_esc_{seed}", "", "", [
        Event(co_start, "sensor_drift", {"sensor_id": "co_cob_1", "rate": co_rate}),
        Event(prs_start, "sensor_drift", {"sensor_id": "prs_cob_1", "rate": prs_rate}),
        Event(permit_at, "issue_permit", {"zone_id": "coke_oven", "type": "confined_space"}),
        Event(prs_start + 60, "hold_level", {"sensor_id": "prs_cob_1"}),
    ])


def make_subthreshold(seed: int) -> Scenario:
    """Compound hazard where NO sensor ever crosses its alarm threshold."""
    rng = random.Random(2000 + seed)
    start = rng.randint(40, 80)
    rate = round(rng.uniform(0.25, 0.35), 3)
    plateau_at = start + int(62 / rate)  # CO holds near 70% of critical
    permit_at = rng.randint(start + 40, start + 70)
    return Scenario(f"bench_sub_{seed}", "", "", [
        Event(start, "sensor_drift", {"sensor_id": "co_cob_1", "rate": rate}),
        Event(permit_at, "issue_permit", {"zone_id": "coke_oven", "type": "confined_space"}),
        Event(plateau_at, "hold_level", {"sensor_id": "co_cob_1"}),
    ])


def run(scenario: Scenario | None, name: str, seed: int, ticks: int) -> Pipeline:
    pipe = Pipeline(name, seed=seed, scenario=scenario)
    for _ in range(ticks):
        pipe.step()
    return pipe


def main() -> None:
    # --- Set A: escalating incidents -----------------------------------------
    leads, suraksha_hits, baseline_hits = [], 0, 0
    for seed in range(1, 21):
        pipe = run(make_escalating(seed), f"bench_esc_{seed}", seed, 600)
        if pipe.first_critical_tick is not None:
            suraksha_hits += 1
        if pipe.baseline_alarm_tick is not None:
            baseline_hits += 1
        if pipe.first_critical_tick and pipe.baseline_alarm_tick:
            leads.append(pipe.baseline_alarm_tick - pipe.first_critical_tick)

    # --- Set B: sub-threshold compound incidents ------------------------------
    sub_suraksha, sub_baseline = 0, 0
    for seed in range(1, 11):
        pipe = run(make_subthreshold(seed), f"bench_sub_{seed}", seed, 500)
        if pipe.first_critical_tick is not None:
            sub_suraksha += 1
        if pipe.baseline_alarm_tick is not None:
            sub_baseline += 1

    # --- Set C: normal days ----------------------------------------------------
    fp = 0
    for seed in range(1, 21):
        pipe = run(None, "normal_day", seed, 300)
        if pipe.first_critical_tick is not None:
            fp += 1

    # --- canonical vizag run ----------------------------------------------------
    vz = run(None, "vizag_replay", 42, 420)
    vz_lead = vz.baseline_alarm_tick - vz.first_critical_tick

    md = f"""# SURAKSHA — Simulated Benchmark Results

*All results from the SURAKSHA plant simulator (deterministic seeds, code in
`scripts/run_benchmark.py`). Baseline = conventional system alarming only when
a single sensor crosses 100% of its critical threshold.*

## Headline (canonical Vizag replay, seed 42)

| Metric | Value |
|---|---|
| SURAKSHA critical alert | t = {vz.first_critical_tick} min |
| First single-sensor alarm | t = {vz.baseline_alarm_tick} min |
| **Detection lead time** | **{vz_lead} min = {vz_lead / 60:.1f} hours** |

## Set A — 20 randomized escalating incidents (600 min each)

| Metric | SURAKSHA | Single-sensor baseline |
|---|---|---|
| Incidents detected | {suraksha_hits}/20 | {baseline_hits}/20 |
| Mean detection lead vs baseline | {statistics.mean(leads):.0f} min | — |
| Median detection lead | {statistics.median(leads):.0f} min | — |
| Min / Max lead | {min(leads)} / {max(leads)} min | — |

## Set B — 10 sub-threshold compound incidents (the Vizag pattern)

Conditions stay below every individual alarm threshold while a confined-space
permit is active with workers present.

| Metric | SURAKSHA | Single-sensor baseline |
|---|---|---|
| Incidents detected | {sub_suraksha}/10 | {sub_baseline}/10 |
| **False negatives** | **{10 - sub_suraksha}/10** | **{10 - sub_baseline}/10** |

## Set C — 20 normal operating days (300 min each)

| Metric | SURAKSHA |
|---|---|
| False positives (critical alerts on normal days) | {fp}/20 |

## Why this matters

The single-sensor baseline can only see incidents that eventually breach an
individual alarm threshold — by then the hazard is already present. In the
sub-threshold set (the exact pattern of the 2025 Visakhapatnam tragedy),
a threshold-based system never alarms at all. SURAKSHA's compound-risk
correlation detects **{sub_suraksha}/10** of those with **{fp}** false
positives across 20 normal days.
"""
    out = ROOT / "deliverables" / "metrics.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"written -> {out}")


if __name__ == "__main__":
    main()

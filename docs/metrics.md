# SURAKSHA — Simulated Benchmark Results

*All results from the SURAKSHA plant simulator (deterministic seeds, code in
`scripts/run_benchmark.py`). Baseline = conventional system alarming only when
a single sensor crosses 100% of its critical threshold.*

## Headline (canonical Vizag replay, seed 42)

| Metric | Value |
|---|---|
| SURAKSHA critical alert | t = 165 min |
| First single-sensor alarm | t = 394 min |
| **Detection lead time** | **229 min = 3.8 hours** |

## Set A — 20 randomized escalating incidents (600 min each)

| Metric | SURAKSHA | Single-sensor baseline |
|---|---|---|
| Incidents detected | 20/20 | 20/20 |
| Mean detection lead vs baseline | 215 min | — |
| Median detection lead | 210 min | — |
| Min / Max lead | 165 / 300 min | — |

## Set B — 10 sub-threshold compound incidents (the Vizag pattern)

Conditions stay below every individual alarm threshold while a confined-space
permit is active with workers present.

| Metric | SURAKSHA | Single-sensor baseline |
|---|---|---|
| Incidents detected | 9/10 | 0/10 |
| **False negatives** | **1/10** | **10/10** |

## Set C — 20 normal operating days (300 min each)

| Metric | SURAKSHA |
|---|---|
| False positives (critical alerts on normal days) | 0/20 |

## Why this matters

The single-sensor baseline can only see incidents that eventually breach an
individual alarm threshold — by then the hazard is already present. In the
sub-threshold set (the exact pattern of the 2025 Visakhapatnam tragedy),
a threshold-based system never alarms at all. SURAKSHA's compound-risk
correlation detects **9/10** of those with **0** false
positives across 20 normal days.

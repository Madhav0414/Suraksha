"""Agent 5 — Compliance: maps fired risk rules to the regulations they invoke.

Local mini-corpus of OISD / Factories Act / DGMS excerpts, keyed by rule id.
Fully offline — no LLM, no embeddings. Every alert on the dashboard can cite
the exact statutory provision it relates to, which is what turns an "AI
alert" into an actionable, defensible safety intervention.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REG_PATH = Path(__file__).resolve().parent.parent / "data" / "regulations.json"


@dataclass
class Citation:
    reg_id: str
    title: str
    excerpt: str
    applies_to_rule: str


def _load_corpus() -> list[dict]:
    return json.loads(REG_PATH.read_text(encoding="utf-8"))


_CORPUS = _load_corpus()


def cite(fired_rules: list[str]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[str] = set()
    for rule in fired_rules:
        for reg in _CORPUS:
            if rule in reg["rules"] and reg["reg_id"] not in seen:
                seen.add(reg["reg_id"])
                citations.append(Citation(
                    reg_id=reg["reg_id"], title=reg["title"],
                    excerpt=reg["excerpt"], applies_to_rule=rule))
    return citations

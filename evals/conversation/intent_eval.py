#!/usr/bin/env python3
"""Deterministic bilingual routing evaluation; never represents model quality."""
from __future__ import annotations

import json
import hashlib
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ultron" / "cloud_service"))
from conversation_persona import classify_intent

DATA = Path(__file__).with_name("intent_scenarios.json")
FROZEN_SHA256 = "e640562e2011e9189471182f570511b5e9181c7e553e59914170db23cb8c8ef4"
CATEGORIES = {
    "casual_chat", "general_question", "continuation", "correction",
    "topic_return", "history_recall", "memory_recall", "research",
    "computer_task", "scene_visual",
}
INTENTS = {
    "chat", "continuation", "correction", "topic_return", "history_recall",
    "memory_recall", "research", "computer_task", "scene_visual",
}


def validate(cases: list[dict]) -> None:
    raw = DATA.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FROZEN_SHA256:
        raise ValueError("Intent suite changed; version and review it before scoring")
    if cases != json.loads(raw.decode("utf-8")):
        raise ValueError("Evaluated cases must match the frozen intent suite")
    if len(cases) != 100 or len({row.get("id") for row in cases}) != 100:
        raise ValueError("Expected exactly 100 uniquely identified scenarios")
    if {row.get("category") for row in cases} != CATEGORIES:
        raise ValueError("Scenario categories do not match the frozen intent suite")
    if any(row.get("language") not in {"tr", "en"} for row in cases):
        raise ValueError("Only Turkish and English scenarios are accepted")
    for category in CATEGORIES:
        group = [row for row in cases if row["category"] == category]
        if (len(group) != 10 or sum(x["language"] == "tr" for x in group) != 5
                or sum(x["language"] == "en" for x in group) != 5):
            raise ValueError(f"{category}: expected five Turkish and five English cases")
    for row in cases:
        if not isinstance(row.get("message"), str) or not row["message"].strip():
            raise ValueError(f"{row.get('id')}: missing message")
        if row.get("expected_intent") not in INTENTS:
            raise ValueError(f"{row.get('id')}: invalid intent")
        if type(row.get("requires_context")) is not bool or type(row.get("requires_tool")) is not bool:
            raise ValueError(f"{row.get('id')}: expected boolean routing criteria")


def evaluate(cases: list[dict]) -> dict:
    validate(cases)
    results = []
    elapsed = []
    for row in cases:
        started = time.perf_counter_ns()
        decision = classify_intent(row["message"])
        elapsed.append((time.perf_counter_ns() - started) / 1_000_000)
        actual = {
            "intent": decision.kind,
            "requires_context": decision.requires_context,
            "requires_tool": decision.requires_tool,
        }
        expected = {
            "intent": row["expected_intent"],
            "requires_context": row["requires_context"],
            "requires_tool": row["requires_tool"],
        }
        results.append({"id": row["id"], "category": row["category"],
                        "language": row["language"], "expected": expected,
                        "actual": actual, "passed": actual == expected})
    ordered = sorted(elapsed)
    p95 = ordered[max(0, math.ceil(len(ordered) * .95) - 1)]
    passed = sum(item["passed"] for item in results)
    categories = {}
    for category in sorted(CATEGORIES):
        group = [item for item in results if item["category"] == category]
        categories[category] = {"passed": sum(item["passed"] for item in group),
                                "total": len(group)}
    return {
        "suite": str(DATA.name), "suite_sha256": FROZEN_SHA256,
        "scenario_count": len(cases),
        "language_counts": {language: sum(x["language"] == language for x in cases)
                            for language in ("tr", "en")},
        "deterministic_router": {"passed": passed, "total": len(cases),
                                 "score": f"{passed}/{len(cases)}",
                                 "categories": categories},
        "route_latency_ms": {"p50": statistics.median(elapsed), "p95": p95,
                             "scope": "in-process lexical routing only"},
        "model_quality": "NOT_RUN",
        "first_token_latency_ms": "NOT_RUN",
        "total_model_latency_ms": "NOT_RUN",
        "extra_model_calls_for_routing": 0,
        "failures": [item for item in results if not item["passed"]],
    }


def main() -> int:
    cases = json.loads(DATA.read_text(encoding="utf-8"))
    report = evaluate(cases)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

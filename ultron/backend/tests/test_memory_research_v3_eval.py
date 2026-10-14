"""100 annotated deterministic memory/research cases; not model-quality evidence."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
CLOUD = BACKEND.parent / "cloud_service"
sys.path.insert(0, str(CLOUD))
sys.path.insert(0, str(BACKEND))
from app.cognitive.research_engine import match_claim_to_evidence, validate_public_target  # noqa: E402
from memory_history import validate_memory_record  # noqa: E402
from personal_context_focus import (  # noqa: E402
    is_memory_history_request, select_memory_history_context, select_personal_context,
)

EVAL_PATH = Path(__file__).resolve().parents[1] / "evals" / "memory_research_v3.json"
EVAL = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
CASES = EVAL["scenarios"]


def _fixture_resolver(host, port):
    return ["93.184.216.34"] if host == "public.example" else ["127.0.0.1"]


@pytest.mark.parametrize("scenario", CASES, ids=lambda case: case["id"])
def test_annotated_scenario_contract(scenario):
    area = scenario["area"]
    expected = scenario["expected"]
    if area == "memory_retrieval":
        memory = scenario["memory"]
        context = select_personal_context([memory], [], scenario["input"], max_chars=1200)
        assert expected["contains"] in context
    elif area == "memory_history":
        assert is_memory_history_request(scenario["input"])
        current = scenario["current"]
        current_context = select_personal_context(
            [{"category": "PREFERENCE", **current}], [], scenario["input"], max_chars=800
        )
        old_context = select_memory_history_context(
            [scenario["history"]], scenario["input"], max_chars=800
        )
        assert expected["current"] in current_context
        assert expected["historical"] not in current_context
        assert expected["historical"] in old_context
        assert expected["label"] in old_context
    elif area == "privacy":
        record = scenario["record"]
        try:
            validate_memory_record(record["category"], record["key"], record["value"])
            accepted = True
        except ValueError:
            accepted = False
        assert accepted is expected["accepted"]
    elif area == "network_policy":
        try:
            validate_public_target(scenario["input"], resolver=_fixture_resolver)
            allowed = True
        except ValueError:
            allowed = False
        assert allowed is expected["allowed"]
    elif area == "claim_evidence":
        result = match_claim_to_evidence(scenario["claim"], [scenario["finding"]])
        assert result["supported"] is expected["supported"]
        assert result["semantic_entailment_checked"] is False
    else:  # A new area cannot silently escape the evaluator.
        pytest.fail(f"unknown annotated evaluation area: {area}")


def test_eval_suite_is_bilingual_balanced_and_annotated():
    assert len(CASES) == EVAL["scenario_count"] == 100
    assert sum(row["language"] == "tr" for row in CASES) == 50
    assert sum(row["language"] == "en" for row in CASES) == 50
    assert all(row.get("expected") and row.get("input") for row in CASES)
    assert len({row["id"] for row in CASES}) == 100

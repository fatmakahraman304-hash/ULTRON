"""100-case deterministic Evidence V4 fixtures; never represented as live/model tests."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPOSITORY = BACKEND.parents[1]
sys.path.insert(0, str(REPOSITORY / "ultron" / "cloud_service"))
sys.path.insert(0, str(BACKEND))
from app.cognitive.research_context import build_research_prompt_block  # noqa: E402
from app.cognitive.research_engine import (  # noqa: E402
    _numeric_disagreements, copied_source_similarity, extract_page_details,
    match_claim_to_evidence,
)

EVAL_PATH = REPOSITORY / "evals" / "research" / "evidence_v4_scenarios.json"
EVAL = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
CASES = EVAL["scenarios"]


def test_evidence_v4_frozen_suite_is_annotated_and_bilingual():
    assert len(CASES) == EVAL["scenario_count"] == 100
    assert Counter(row["language"] for row in CASES) == {"tr": 50, "en": 50}
    assert len({row["id"] for row in CASES}) == 100
    assert all(row.get("expected") and row.get("area") and row.get("input", row.get("id"))
               for row in CASES)
    assert Counter(row["area"] for row in CASES) == {
        "date_metadata": 20, "unit_match": 20, "copy_detection": 20,
        "numeric_conflict": 20, "untrusted_source": 20,
    }


@pytest.mark.parametrize("scenario", CASES, ids=lambda case: case["id"])
def test_annotated_evidence_scenario(scenario):
    expected = scenario["expected"]
    area = scenario["area"]
    if area == "date_metadata":
        _, _, dates = extract_page_details(scenario["input"].encode("utf-8"), "text/html")
        assert dates["published_at"] == expected["published_at"]
        assert dates["updated_at"] == expected["updated_at"]
    elif area == "unit_match":
        finding = {"url": "https://public.example/fact", "page_read": True,
                   "basis": "source_page_excerpt", "excerpt": scenario["excerpt"]}
        result = match_claim_to_evidence(scenario["claim"], [finding])
        assert result["supported"] is expected["supported"]
        assert result["semantic_entailment_checked"] is False
    elif area == "copy_detection":
        similarity = copied_source_similarity(scenario["left"], scenario["right"])
        assert (similarity is not None) is expected["copied"]
    elif area == "numeric_conflict":
        findings = [
            {"url": f"https://source-{index}.example/report", "title": f"Source {index}",
             "source_text": text, "published_at": scenario["published_at"][index],
             "independent_source": True}
            for index, text in enumerate(scenario["texts"])
        ]
        conflicts = _numeric_disagreements(findings, scenario["query"])
        assert bool(conflicts) is expected["suspected"]
        assert all(item["semantic_resolution"] == "not_performed" for item in conflicts)
    elif area == "untrusted_source":
        finding = {"title": "Public page", "url": "https://public.example/page",
                   "accessed_at": "2026-10-14T12:00:00Z", "excerpt": scenario["excerpt"],
                   "page_read": True}
        block = build_research_prompt_block({
            "status": "sources_read", "evidence_level": "source_pages_read",
            "synthesis": {"findings": [finding]},
        })
        payload = json.loads(block.split("UNTRUSTED_RESEARCH_JSON=", 1)[1])
        assert expected["claim_verification"] == payload["claim_verification"]
        assert expected["untrusted"] is ("untrusted public web data" in block.lower())
        assert payload["sources"][0]["excerpt"] == scenario["excerpt"]
    else:
        pytest.fail(f"unknown evidence V4 scenario area: {area}")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

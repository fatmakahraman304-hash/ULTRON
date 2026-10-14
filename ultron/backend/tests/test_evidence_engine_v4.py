"""V4 date provenance, copied-source grouping, and numeric caveat regressions."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.cognitive.research_engine import ResearchEngine, SourceReader, match_claim_to_evidence  # noqa: E402
from app.cognitive.research_context import append_research_sources, build_research_prompt_block  # noqa: E402


def _public_resolver(host, port):
    if host in {"public.example", "copy.example", "other.example"}:
        return ["93.184.216.34"]
    return ["127.0.0.1"]


def test_page_publication_update_and_access_dates_remain_distinct():
    body = b'''<html><head><title>Battery report</title>
    <meta property="article:published_time" content="2024-03-04T10:30:00+02:00">
    <meta property="article:modified_time" content="2025-01-06T12:00:00Z"></head>
    <body><main><p>Model X battery capacity in 2024 was 42 kWh in an independent test.
    The same capacity was recorded again for the report.</p></main></body></html>'''
    reader = SourceReader(
        resolver=_public_resolver,
        transport=lambda *args: (200, {
            "content-type": "text/html; charset=utf-8",
            "last-modified": "Tue, 07 Jan 2025 12:00:00 GMT",
        }, body),
        now=lambda: "2026-10-14T12:00:00Z",
    )
    result = reader.read("https://public.example/report")
    assert result["ok"]
    assert result["published_at"] == "2024-03-04T08:30:00+00:00"
    assert result["updated_at"] == "2025-01-06T12:00:00+00:00"
    assert result["http_last_modified_at"] == "2025-01-07T12:00:00+00:00"
    assert result["accessed_at"] == "2026-10-14T12:00:00Z"


def test_research_marks_syndicated_copy_non_independent_and_flags_same_period_conflict(tmp_path):
    original = (
        "Model X battery capacity in 2024 was 42 kWh according to the controlled test. "
        "The report documents three charging cycles, ambient temperatures, calibration records, "
        "and the complete measurement procedure for repeatable comparison."
    )
    conflicting = (
        "Model X battery capacity in 2024 was 44 kWh according to the controlled test. "
        "The separate laboratory describes two road sessions, seasonal conditions, "
        "instrument calibration, and a different procedure for independent comparison."
    )

    class Reader:
        def read(self, url):
            changed = "other.example" in url
            text = conflicting if changed else original
            return {
                "ok": True, "url": url, "title": "Model X battery report",
                "text": text, "accessed_at": "2026-10-14T12:00:00Z",
                "published_at": "2024-05-01T00:00:00+00:00",
                    "updated_at": "2024-06-01T00:00:00+00:00",
                    "http_last_modified_at": "2024-06-02T00:00:00+00:00",
                "content_type": "text/html",
            }

    engine = ResearchEngine(
        db_path=str(Path(tmp_path) / "research.db"),
        search_fn=lambda query: [
            {"url": "https://public.example/report", "title": "Model X battery capacity original report"},
            {"url": "https://copy.example/story", "title": "Republished copy"},
            {"url": "https://other.example/report", "title": "Separate measurement"},
        ],
        source_reader=Reader(),
    )
    result = engine.research("Model X battery capacity", max_sources=3, store=False)
    findings = result["synthesis"]["findings"]
    assert len(findings) == 3
    assert sum(bool(row["independent_source"]) for row in findings) == 2
    assert next(row for row in findings if "copy.example" in row["url"])["copy_of_url"] == "https://public.example/report"
    assert result["independent_source_count"] == 2
    assert result["contradiction_suspected"] is True
    conflict = result["synthesis"]["numeric_conflicts"][0]
    assert conflict["unit"] == "kwh"
    assert conflict["reference_year"] == 2024
    assert {row["value"] for row in conflict["values"]} == {"42", "44"}
    assert result["corroborated_by_domains"] == 0
    block = build_research_prompt_block(result)
    assert '"published_at":"2024-05-01T00:00:00+00:00"' in block
    assert "untrusted public web data" in block
    response = append_research_sources("Battery capacities differ.", result)
    assert "2024-05-01" in response
    assert "sayfada güncelleme: 2024-06-01" in response
    assert "HTTP Last-Modified: 2024-06-02" in response
    assert "olası sayısal uyuşmazlık" in response


def test_numeric_evidence_requires_the_same_unit_not_just_the_same_number():
    finding = {"url": "https://public.example/spec", "page_read": True,
               "basis": "source_page_excerpt",
               "excerpt": "The measured battery capacity is 42 Wh."}
    assert not match_claim_to_evidence(
        "The measured battery capacity is 42 kWh", [finding]
    )["supported"]
    same_unit = {**finding, "excerpt": "The measured battery capacity is 42 kWh."}
    assert match_claim_to_evidence(
        "The measured battery capacity is 42 kWh", [same_unit]
    )["supported"]
    assert not match_claim_to_evidence(
        "The repair cost is $42", [{**finding, "excerpt": "The repair cost is €42."}]
    )["supported"]


def test_different_reference_years_are_not_reported_as_a_conflict(tmp_path):
    values = {
        "https://public.example/a": "Model X battery capacity in 2023 was 42 kWh in the controlled test. " * 2,
        "https://other.example/b": "Model X battery capacity in 2024 was 44 kWh in the controlled test. " * 2,
    }

    class Reader:
        def read(self, url):
            return {"ok": True, "url": url, "title": "Model X report",
                    "text": values[url], "accessed_at": "2026-10-14T12:00:00Z",
                    "published_at": None, "updated_at": None,
                    "http_last_modified_at": None, "content_type": "text/plain"}

    engine = ResearchEngine(
        db_path=str(Path(tmp_path) / "research.db"),
        search_fn=lambda query: [{"url": url, "title": "Model X report"} for url in values],
        source_reader=Reader(),
    )
    result = engine.research("Model X battery capacity", max_sources=2, store=False)
    assert result["contradiction_suspected"] is False
    assert result["synthesis"]["numeric_conflicts"] == []


def test_two_values_on_one_source_do_not_create_cross_source_conflict(tmp_path):
    text = "Battery capacity ranged between 42 kWh and 44 kWh in the 2024 test. " * 2

    class Reader:
        def read(self, url):
            return {"ok": True, "url": url, "title": "Battery report", "text": text,
                    "accessed_at": "2026-10-14T12:00:00Z",
                    "published_at": "2024-05-01", "updated_at": None,
                    "http_last_modified_at": None, "content_type": "text/plain"}

    engine = ResearchEngine(
        db_path=str(Path(tmp_path) / "research.db"),
        search_fn=lambda query: [{"url": "https://public.example/a", "title": "Battery capacity"}],
        source_reader=Reader(),
    )
    result = engine.research("battery capacity", max_sources=1, store=False)
    assert result["contradiction_suspected"] is False
    assert result["synthesis"]["numeric_conflicts"] == []


def test_short_pages_are_not_counted_as_independent_sources(tmp_path):
    class Reader:
        def read(self, url):
            return {"ok": True, "url": url, "title": "Battery report",
                    "text": "Battery capacity was 42 kWh in testing.",
                    "accessed_at": "2026-10-14T12:00:00Z", "content_type": "text/plain"}

    engine = ResearchEngine(
        db_path=str(Path(tmp_path) / "research.db"),
        search_fn=lambda query: [
            {"url": "https://public.example/a", "title": "Battery capacity"},
            {"url": "https://other.example/b", "title": "Battery capacity"},
        ],
        source_reader=Reader(),
    )
    result = engine.research("battery capacity", max_sources=2, store=False)
    assert result["independent_source_count"] == 0
    assert all(row["independence_status"] == "unassessed_short_content"
               for row in result["synthesis"]["findings"])

"""Record bounded workflow outcomes without retaining provider/test prose."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from engineering_memory import EngineeringMemory
import engine


def record_pipeline(memory: EngineeringMemory, *, candidate_id: str, source_sha: str,
                    plan_status: str, proposed: bool, propose_result: str,
                    initial_result: str, repair_result: str, verify_repair_result: str,
                    draft_result: str, pr_url: str = "", commit_sha: str = "",
                    initial_failure_class: str = "unknown",
                    repair_failure_class: str = "unknown",
                    initial_patch_sha: str = "", repair_patch_sha: str = "") -> dict:
    if not re.fullmatch(r"[a-f0-9]{20}", candidate_id or "") or not re.fullmatch(r"[0-9a-f]{40}", source_sha or ""):
        raise ValueError("pipeline_receipt_identity_invalid")
    if plan_status not in {"ready", "nothing_to_generate", ""}:
        raise ValueError("pipeline_plan_state_invalid")
    job_states = {"success", "failure", "skipped", "cancelled"}
    if any(value not in job_states for value in
           (propose_result, initial_result, repair_result, verify_repair_result, draft_result)):
        raise ValueError("pipeline_job_state_invalid")
    if initial_failure_class not in {"code", "infrastructure", "preflight", "unknown", "none"} or repair_failure_class not in {"code", "infrastructure", "preflight", "unknown", "none"}:
        raise ValueError("pipeline_failure_class_invalid")
    if any(value and not re.fullmatch(r"[0-9a-f]{64}", value)
           for value in (initial_patch_sha, repair_patch_sha)):
        raise ValueError("pipeline_patch_receipt_invalid")
    if type(proposed) is not bool or (proposed and propose_result != "success"):
        raise ValueError("pipeline_proposal_receipt_invalid")
    if (initial_result == "success" or verify_repair_result == "success") and not proposed:
        raise ValueError("pipeline_verification_without_proposal")
    snapshot = memory.snapshot()
    candidate = next((row for row in snapshot["candidates"] if row["candidate_id"] == candidate_id), None)
    if not candidate:
        raise ValueError("pipeline_candidate_missing")
    goal = next((row for row in engine.load_goals() if row["id"] == candidate.get("goal_id")), None)
    tests = [goal["test_path"]] if goal else []
    previous_code_attempts = [row for row in snapshot["attempts"]
                              if row["candidate_id"] == candidate_id
                              and row["stage"] in {"generate", "verify", "repair"}]
    first_no = max((row["attempt_no"] for row in previous_code_attempts), default=0) + 1
    if first_no > 2:
        raise ValueError("code_attempt_budget_exhausted")
    retry_after = (datetime.now(timezone.utc) + timedelta(hours=24)).replace(microsecond=0).isoformat()

    if plan_status == "nothing_to_generate":
        return {"recorded": False, "reason": "nothing_to_generate"}
    if not proposed:
        outcome = "failed" if propose_result == "failure" else "skipped"
        memory.record_attempt(candidate_id, attempt_no=first_no, stage="generate" if outcome == "failed" else "plan",
                              outcome=outcome, source_sha=source_sha, tests=tests,
                              retry_after=retry_after if outcome == "failed" else None)
        return {"recorded": True, "stage": "generate" if outcome == "failed" else "plan", "outcome": outcome}

    if initial_result in {"success", "failure"}:
        outcome = "passed" if initial_result == "success" else "failed"
        memory.record_attempt(candidate_id, attempt_no=first_no, stage="verify", outcome=outcome,
                              source_sha=source_sha, tests=tests,
                              patch_sha=initial_patch_sha or None,
                              failure_class=initial_failure_class if outcome == "failed" else None,
                              retry_after=None if outcome == "passed" else retry_after)
    second_no = first_no + 1
    if repair_result in {"success", "failure"} and second_no <= 2:
        if verify_repair_result == "success":
            memory.record_attempt(candidate_id, attempt_no=second_no, stage="repair", outcome="passed",
                                  source_sha=source_sha, tests=tests,
                                  patch_sha=repair_patch_sha or None)
        elif verify_repair_result == "failure" or repair_result == "failure":
            memory.record_attempt(candidate_id, attempt_no=second_no, stage="repair", outcome="failed",
                                  source_sha=source_sha, tests=tests,
                                  patch_sha=repair_patch_sha or None,
                                  failure_class=repair_failure_class,
                                  retry_after=retry_after)

    final_no = second_no if verify_repair_result in {"success", "failure"} else first_no
    verified = initial_result == "success" or verify_repair_result == "success"
    published = draft_result == "success" and bool(pr_url) and bool(commit_sha)
    if published:
        memory.record_attempt(candidate_id, attempt_no=final_no, stage="publish", outcome="created",
                              source_sha=source_sha, tests=tests, commit_sha=commit_sha, pr_url=pr_url)
        if verified and tests:
            memory.record_draft_pr(candidate_id, commit_sha=commit_sha, pr_url=pr_url,
                                   passing_tests=tests)
    elif verified:
        memory.record_attempt(candidate_id, attempt_no=final_no, stage="publish", outcome="failed",
                              source_sha=source_sha, tests=tests, retry_after=retry_after)
    return {"recorded": True, "verified": verified, "draft_pr_created": published,
            "problem_resolved": False,
            "candidate_status": "draft_pr_open" if published and verified else None}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.receipt.is_symlink() or args.receipt.stat().st_size > 50_000:
        parser.error("receipt_file_rejected")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        parser.error("receipt_must_be_object")
    memory = EngineeringMemory(args.db)
    try:
        result = record_pipeline(memory, **receipt)
        memory.export_json(args.export)
        print(json.dumps(result))
    finally:
        memory.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

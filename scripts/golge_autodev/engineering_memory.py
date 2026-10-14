"""Bounded, privacy-filtered engineering memory for GÖLGE autodev.

Only deterministic repository evidence and execution receipts are persisted.
Model prose, source logs, diagnostics, prompt text, and user data have no fields
in this schema. In CI the SQLite file is carried inside a repository-scoped,
90-day Actions artifact; the artifact is refreshed by each discovery run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

MAX_CANDIDATES = 500
MAX_ATTEMPTS = 1000
MAX_EXPORT_BYTES = 4_000_000
SOURCES = {"github_actions_failure", "github_issue", "static_analysis",
           "application_error_log", "health_report", "performance_report",
           "roadmap_backlog"}
STATUSES = {"eligible", "review_required", "insufficient_evidence",
            "already_addressed", "draft_pr_open", "blocked", "deferred_conflict", "backlog"}
VERIFICATIONS = {"not_run", "reproduced", "passed", "infrastructure_failure",
                 "no_registered_test", "conflict", "source_unverified"}
STAGES = {"triage", "plan", "generate", "verify", "repair", "publish", "quality"}
OUTCOMES = {"observed", "nothing_to_generate", "started", "model_unavailable",
            "failed", "passed", "blocked", "created", "skipped", "cancelled"}
FAILURE_CLASSES = {"code", "infrastructure", "preflight", "unknown"}
PROOF_KINDS = {"pytest_and_draft_pr"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-f0-9]{20}$")
SAFE_PATH_RE = re.compile(r"^(?:ultron/backend|scripts/golge_autodev)/[A-Za-z0-9_./-]+\.py$")
TEST_RE = re.compile(r"^ultron/backend/tests/test_[A-Za-z0-9_]+\.py$")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_source_ref(source: str, ref: str) -> bool:
    if not isinstance(ref, str) or len(ref) > 300 or any(ord(c) < 32 for c in ref):
        return False
    if source == "github_actions_failure":
        return bool(re.fullmatch(r"run:[1-9][0-9]{0,12}", ref))
    if source == "github_issue":
        parsed = urlparse(ref)
        return (parsed.scheme == "https" and parsed.netloc == "github.com"
                and bool(re.fullmatch(r"/fatmakahraman304-hash/ULTRON/issues/[1-9][0-9]{0,8}", parsed.path))
                and not parsed.query and not parsed.fragment)
    if source == "static_analysis":
        return bool(re.fullmatch(r"ultron/backend/[A-Za-z0-9_./-]+:[0-9]{1,8}:[a-z_]{3,40}", ref))
    if source == "roadmap_backlog":
        return bool(re.fullmatch(r"ULTRON_(?:NEXT_TASKS|ROADMAP)\.md:[1-9][0-9]{0,7}", ref))
    if source in {"application_error_log", "health_report", "performance_report"}:
        return bool(re.fullmatch(r"[A-Za-z0-9_.:-]{1,180}", ref))
    return False


def _safe_candidate(candidate: dict, source_sha: str, observed_at: str) -> dict:
    import engine

    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    cid = candidate.get("candidate_id")
    source = candidate.get("source")
    ref = candidate.get("source_ref")
    status = candidate.get("status")
    verification = candidate.get("verification_status", "not_run")
    if not isinstance(cid, str) or not ID_RE.fullmatch(cid):
        raise ValueError("invalid_candidate_id")
    if source not in SOURCES or not _validate_source_ref(source, ref):
        raise ValueError("untrusted_evidence_reference")
    if status not in STATUSES or verification not in VERIFICATIONS:
        raise ValueError("invalid_evidence_state")
    if not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha):
        raise ValueError("invalid_source_sha")
    evidence_sha = candidate.get("evidence_commit_sha") if source == "github_actions_failure" else source_sha
    if not isinstance(evidence_sha, str) or not SHA_RE.fullmatch(evidence_sha):
        evidence_sha = source_sha
    verification_sha = candidate.get("verification_sha", source_sha)
    if not isinstance(verification_sha, str) or not SHA_RE.fullmatch(verification_sha):
        raise ValueError("invalid_verification_sha")
    if not isinstance(observed_at, str) or len(observed_at) > 40:
        raise ValueError("invalid_timestamp")
    datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    goal_id = candidate.get("goal_id")
    goal = next((g for g in engine.load_goals() if g["id"] == goal_id), None)
    if goal_id is not None and goal is None:
        raise ValueError("unknown_goal")
    allowed_paths = set(goal["paths"] if goal else [])
    paths = candidate.get("affected_files", [])
    if not isinstance(paths, list) or len(paths) > 3:
        raise ValueError("invalid_paths")
    paths = sorted(set(paths))
    if any(not isinstance(path, str) or not SAFE_PATH_RE.fullmatch(path) or ".." in Path(path).parts
           or (allowed_paths and path not in allowed_paths) for path in paths):
        raise ValueError("path_outside_registered_scope")
    priority = candidate.get("priority", 0)
    if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 100:
        raise ValueError("invalid_priority")
    risk = candidate.get("risk_level", "high")
    if risk not in {"low", "medium", "high"}:
        raise ValueError("invalid_risk")
    component = candidate.get("component", "unclassified")
    if not isinstance(component, str) or not re.fullmatch(r"[a-z_]{1,40}", component):
        raise ValueError("invalid_component")
    test_path = candidate.get("verified_test")
    if test_path is not None and (not isinstance(test_path, str) or not TEST_RE.fullmatch(test_path)
                                  or test_path not in allowed_paths):
        raise ValueError("invalid_verified_test")
    if status == "eligible" and (verification != "reproduced" or not test_path):
        raise ValueError("eligible_candidate_requires_reproduction_receipt")
    if status == "already_addressed" and (verification != "passed" or not test_path):
        raise ValueError("resolved_candidate_requires_passing_receipt")
    evidence_digest = hashlib.sha256(
        json.dumps([cid, source, ref, evidence_sha, verification_sha, observed_at], separators=(",", ":")).encode()
    ).hexdigest()
    # Deliberately omit evidence/summary/diagnostic/body fields.
    return {"candidate_id": cid, "source": source, "source_ref": ref,
            "source_sha": source_sha, "observed_at": observed_at,
            "evidence_sha": evidence_sha, "verification_sha": verification_sha,
            "evidence_digest": evidence_digest, "goal_id": goal_id,
            "affected_files": paths, "impact": priority, "risk_level": risk,
            "status": status, "verification_status": verification,
            "verified_test": test_path}


class EngineeringMemory:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError("memory_symlink_rejected")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS candidates(
              candidate_id TEXT PRIMARY KEY, source TEXT NOT NULL, source_ref TEXT NOT NULL,
              source_sha TEXT NOT NULL, evidence_sha TEXT NOT NULL, verification_sha TEXT NOT NULL,
              observed_at TEXT NOT NULL, evidence_digest TEXT NOT NULL,
              goal_id TEXT, affected_files TEXT NOT NULL, impact INTEGER NOT NULL,
              risk_level TEXT NOT NULL, status TEXT NOT NULL, verification_status TEXT NOT NULL,
              verified_test TEXT, next_retry_at TEXT, draft_commit_sha TEXT, draft_pr_url TEXT,
              draft_proof TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS observations(
              id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
              source_sha TEXT NOT NULL, evidence_sha TEXT NOT NULL, verification_sha TEXT NOT NULL,
              observed_at TEXT NOT NULL, evidence_digest TEXT NOT NULL,
              status TEXT NOT NULL, verification_status TEXT NOT NULL,
              UNIQUE(candidate_id,evidence_digest)
            );
            CREATE TABLE IF NOT EXISTS attempts(
              id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
              attempt_no INTEGER NOT NULL CHECK(attempt_no BETWEEN 1 AND 2),
              stage TEXT NOT NULL, outcome TEXT NOT NULL, source_sha TEXT NOT NULL,
              patch_sha TEXT, tests_json TEXT NOT NULL, commit_sha TEXT, pr_url TEXT,
              proof_kind TEXT, failure_class TEXT, occurred_at TEXT NOT NULL,
              UNIQUE(candidate_id, attempt_no, stage)
            );
            CREATE TABLE IF NOT EXISTS scheduler(
              singleton INTEGER PRIMARY KEY CHECK(singleton=1), state TEXT NOT NULL,
              owner TEXT, base_sha TEXT, lease_until TEXT, stop_reason TEXT, updated_at TEXT NOT NULL
            );
            INSERT OR IGNORE INTO scheduler(singleton,state,updated_at) VALUES(1,'running','1970-01-01T00:00:00+00:00');
            CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status, next_retry_at);
            CREATE INDEX IF NOT EXISTS idx_attempts_candidate ON attempts(candidate_id, occurred_at);
        """)
        attempt_columns = {row["name"] for row in self.db.execute("PRAGMA table_info(attempts)")}
        if "failure_class" not in attempt_columns:
            self.db.execute("ALTER TABLE attempts ADD COLUMN failure_class TEXT")

    def close(self):
        self.db.close()

    def record_candidate(self, candidate: dict, *, source_sha: str,
                         observed_at: str | None = None) -> bool:
        safe = _safe_candidate(candidate, source_sha, observed_at or now_utc())
        now = now_utc()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT status FROM candidates WHERE candidate_id=?",
                                  (safe["candidate_id"],)).fetchone()
            if old and old["status"] in {"already_addressed", "draft_pr_open"}:
                self.db.execute("COMMIT")
                return False
            self.db.execute("""INSERT INTO candidates(
                candidate_id,source,source_ref,source_sha,evidence_sha,verification_sha,observed_at,evidence_digest,goal_id,
                affected_files,impact,risk_level,status,verification_status,verified_test,
                created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(candidate_id) DO UPDATE SET source_sha=excluded.source_sha,
                evidence_sha=excluded.evidence_sha,verification_sha=excluded.verification_sha,
                observed_at=excluded.observed_at,evidence_digest=excluded.evidence_digest,
                goal_id=excluded.goal_id,affected_files=excluded.affected_files,
                impact=excluded.impact,risk_level=excluded.risk_level,status=excluded.status,
                verification_status=excluded.verification_status,verified_test=excluded.verified_test,
                updated_at=excluded.updated_at""",
                (safe["candidate_id"], safe["source"], safe["source_ref"], safe["source_sha"],
                 safe["evidence_sha"], safe["verification_sha"], safe["observed_at"],
                 safe["evidence_digest"], safe["goal_id"],
                 json.dumps(safe["affected_files"]), safe["impact"], safe["risk_level"],
                 safe["status"], safe["verification_status"], safe["verified_test"], now, now))
            self.db.execute("""INSERT OR IGNORE INTO observations(
                candidate_id,source_sha,evidence_sha,verification_sha,observed_at,evidence_digest,status,verification_status)
                VALUES(?,?,?,?,?,?,?,?)""",
                (safe["candidate_id"], safe["source_sha"], safe["evidence_sha"], safe["verification_sha"],
                 safe["observed_at"], safe["evidence_digest"], safe["status"], safe["verification_status"]))
            self._prune()
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return True

    def record_attempt(self, candidate_id: str, *, attempt_no: int, stage: str,
                       outcome: str, source_sha: str, tests: list[str] = (),
                       patch_sha: str | None = None, commit_sha: str | None = None,
                       pr_url: str | None = None, proof_kind: str | None = None,
                       failure_class: str | None = None,
                       retry_after: str | None = None, occurred_at: str | None = None) -> None:
        if not ID_RE.fullmatch(str(candidate_id)) or stage not in STAGES or outcome not in OUTCOMES:
            raise ValueError("invalid_attempt_identity_or_state")
        if type(attempt_no) is not int or not 1 <= attempt_no <= 2 or not SHA_RE.fullmatch(source_sha):
            raise ValueError("invalid_attempt_budget_or_sha")
        if len(tests) > 5 or any(not isinstance(t, str) or not TEST_RE.fullmatch(t) for t in tests):
            raise ValueError("unregistered_test_receipt")
        for value, name, pattern in ((patch_sha, "patch_sha", DIGEST_RE), (commit_sha, "commit_sha", SHA_RE)):
            if value is not None and not pattern.fullmatch(value):
                raise ValueError("invalid_" + name)
        if pr_url is not None:
            parsed = urlparse(pr_url)
            if (parsed.scheme != "https" or parsed.netloc != "github.com"
                    or not re.fullmatch(r"/fatmakahraman304-hash/ULTRON/pull/[1-9][0-9]{0,7}", parsed.path)):
                raise ValueError("invalid_pr_reference")
        if proof_kind is not None and proof_kind not in PROOF_KINDS:
            raise ValueError("invalid_proof_kind")
        if failure_class is not None and failure_class not in FAILURE_CLASSES:
            raise ValueError("invalid_failure_class")
        occurred_at = occurred_at or now_utc()
        if len(occurred_at) > 40:
            raise ValueError("invalid_attempt_timestamp")
        datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT candidate_id FROM candidates WHERE candidate_id=?",
                                  (candidate_id,)).fetchone()
            if not row:
                raise ValueError("candidate_not_in_memory")
            self.db.execute("""INSERT INTO attempts(candidate_id,attempt_no,stage,outcome,source_sha,
                patch_sha,tests_json,commit_sha,pr_url,proof_kind,failure_class,occurred_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (candidate_id, attempt_no, stage, outcome, source_sha, patch_sha,
                 json.dumps(tests), commit_sha, pr_url, proof_kind, failure_class, occurred_at))
            if retry_after:
                datetime.fromisoformat(retry_after.replace("Z", "+00:00"))
            self.db.execute("UPDATE candidates SET next_retry_at=?,updated_at=? WHERE candidate_id=?",
                             (retry_after, now_utc(), candidate_id))
            self._prune()
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def record_draft_pr(self, candidate_id: str, *, commit_sha: str, pr_url: str,
                        passing_tests: list[str], proof_kind: str = "pytest_and_draft_pr") -> None:
        if proof_kind not in PROOF_KINDS or not SHA_RE.fullmatch(commit_sha) or not passing_tests:
            raise ValueError("draft_pr_requires_verification_receipt")
        if any(not TEST_RE.fullmatch(test) for test in passing_tests):
            raise ValueError("draft_pr_test_unregistered")
        parsed = urlparse(pr_url)
        if (parsed.scheme != "https" or parsed.netloc != "github.com"
                or not re.fullmatch(r"/fatmakahraman304-hash/ULTRON/pull/[1-9][0-9]{0,7}", parsed.path)):
            raise ValueError("invalid_pr_reference")
        proof = hashlib.sha256(json.dumps([candidate_id, commit_sha, pr_url,
                                          sorted(passing_tests), proof_kind], separators=(",", ":")).encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT candidate_id,goal_id,verified_test FROM candidates WHERE candidate_id=?",
                                  (candidate_id,)).fetchone()
            if not row or not row["verified_test"] or row["verified_test"] not in passing_tests:
                raise ValueError("draft_pr_requires_registered_test")
            verified = self.db.execute("""SELECT 1 FROM attempts WHERE candidate_id=? AND outcome='passed'
                AND stage IN ('verify','repair') AND tests_json LIKE ? LIMIT 1""",
                (candidate_id, '%"' + row["verified_test"] + '"%')).fetchone()
            published = self.db.execute("""SELECT 1 FROM attempts WHERE candidate_id=? AND outcome='created'
                AND stage='publish' AND commit_sha=? AND pr_url=? LIMIT 1""",
                (candidate_id, commit_sha, pr_url)).fetchone()
            if not verified or not published:
                raise ValueError("draft_pr_without_test_and_publish_receipts")
            self.db.execute("""UPDATE candidates SET status='draft_pr_open',verification_status='passed',
                             draft_commit_sha=?,draft_pr_url=?,draft_proof=?,next_retry_at=NULL,updated_at=?
                             WHERE candidate_id=?""",
                             (commit_sha, pr_url, proof, now_utc(), candidate_id))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def retry_allowed(self, candidate_id: str, *, now: str | None = None) -> bool:
        row = self.db.execute("SELECT status,next_retry_at FROM candidates WHERE candidate_id=?",
                              (candidate_id,)).fetchone()
        if not row or row["status"] in {"already_addressed", "draft_pr_open", "blocked"}:
            return False
        if not row["next_retry_at"]:
            return True
        moment = datetime.fromisoformat((now or now_utc()).replace("Z", "+00:00"))
        return moment >= datetime.fromisoformat(row["next_retry_at"].replace("Z", "+00:00"))

    def acquire_write_slot(self, *, owner: str, base_sha: str, current_sha: str,
                           lease_seconds: int = 900, now: datetime | None = None) -> bool:
        if not owner or len(owner) > 100 or not SHA_RE.fullmatch(base_sha) or current_sha != base_sha:
            return False
        if type(lease_seconds) is not int or not 30 <= lease_seconds <= 3600:
            return False
        moment = now or datetime.now(timezone.utc)
        now_s = moment.isoformat()
        until = (moment + timedelta(seconds=lease_seconds)).isoformat()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT state,owner,lease_until FROM scheduler WHERE singleton=1").fetchone()
            if row["state"] != "running":
                self.db.execute("COMMIT")
                return False
            if row["owner"] and row["lease_until"] and datetime.fromisoformat(row["lease_until"]) > moment:
                self.db.execute("COMMIT")
                return False
            self.db.execute("UPDATE scheduler SET owner=?,base_sha=?,lease_until=?,updated_at=? WHERE singleton=1",
                             (owner, base_sha, until, now_s))
            self.db.execute("COMMIT")
            return True
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def release_write_slot(self, owner: str) -> bool:
        cursor = self.db.execute("""UPDATE scheduler SET owner=NULL,base_sha=NULL,lease_until=NULL,updated_at=?
                                 WHERE singleton=1 AND owner=?""",
                                 (now_utc(), owner))
        return cursor.rowcount == 1

    def set_paused(self, paused: bool, reason: str = "operator") -> None:
        state = "paused" if paused else "running"
        reason = re.sub(r"[^A-Za-z0-9_.:-]", "_", reason)[:80]
        self.db.execute("""UPDATE scheduler SET state=?,owner=NULL,base_sha=NULL,lease_until=NULL,
                         stop_reason=?,updated_at=? WHERE singleton=1""",
                         (state, reason if paused else None, now_utc()))

    def snapshot(self) -> dict:
        candidates = []
        for row in self.db.execute("SELECT * FROM candidates ORDER BY updated_at DESC LIMIT ?", (MAX_CANDIDATES,)):
            item = dict(row)
            item["affected_files"] = json.loads(item["affected_files"])
            candidates.append(item)
        attempts = []
        for row in self.db.execute("SELECT * FROM attempts ORDER BY occurred_at DESC LIMIT ?", (MAX_ATTEMPTS,)):
            item = dict(row)
            item["tests"] = json.loads(item.pop("tests_json"))
            attempts.append(item)
        observations = [dict(row) for row in self.db.execute(
            "SELECT * FROM observations ORDER BY observed_at DESC LIMIT ?", (MAX_ATTEMPTS,))]
        settings = dict(self.db.execute("SELECT * FROM scheduler WHERE singleton=1").fetchone())
        # Do not persist a stale lease across job boundaries; GitHub concurrency
        # is the hosted single-flight authority.
        settings.update(owner=None, base_sha=None, lease_until=None)
        return {"schema_version": 1, "candidates": candidates, "observations": observations,
                "attempts": attempts,
                "scheduler": settings}

    def export_json(self, path: Path | str) -> None:
        data = json.dumps(self.snapshot(), ensure_ascii=False, separators=(",", ":")).encode()
        if len(data) > MAX_EXPORT_BYTES:
            raise ValueError("memory_export_too_large")
        target = Path(path)
        if target.is_symlink():
            raise ValueError("memory_export_symlink_rejected")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_bytes(data)
        temp.replace(target)

    def import_json(self, path: Path | str) -> None:
        source = Path(path)
        if source.is_symlink() or source.stat().st_size > MAX_EXPORT_BYTES:
            raise ValueError("memory_import_rejected")
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("memory_schema_unsupported")
        if len(data.get("candidates", [])) > MAX_CANDIDATES or len(data.get("attempts", [])) > MAX_ATTEMPTS or len(data.get("observations", [])) > MAX_ATTEMPTS:
            raise ValueError("memory_import_limit")
        for row in data.get("candidates", []):
            if not isinstance(row, dict):
                raise ValueError("invalid_memory_candidate")
            for key in ("source_sha", "evidence_sha", "verification_sha"):
                if row.get(key) is not None and not SHA_RE.fullmatch(str(row[key])):
                    raise ValueError("invalid_memory_candidate_sha")
            if not DIGEST_RE.fullmatch(str(row.get("evidence_digest", ""))):
                raise ValueError("invalid_memory_candidate_digest")
            for key in ("created_at", "updated_at"):
                datetime.fromisoformat(str(row.get(key, "")).replace("Z", "+00:00"))
            restored_status = row.get("status")
            if restored_status in {"already_addressed", "draft_pr_open"}:
                restored_status = "review_required"
            candidate = {"candidate_id": row["candidate_id"], "source": row["source"],
                         "source_ref": row["source_ref"], "goal_id": row.get("goal_id"),
                         "evidence_commit_sha": row.get("evidence_sha"),
                         "verification_sha": row.get("verification_sha", row.get("source_sha")),
                         "affected_files": row["affected_files"], "priority": row["impact"],
                         "risk_level": row["risk_level"], "status": restored_status,
                         "verification_status": "not_run" if restored_status == "review_required" else row["verification_status"],
                         "verified_test": row.get("verified_test")}
            self.record_candidate(candidate, source_sha=row["source_sha"], observed_at=row["observed_at"])
            self.db.execute("""UPDATE candidates SET evidence_sha=?,verification_sha=?,evidence_digest=?,
                             next_retry_at=?,created_at=?,updated_at=?
                             WHERE candidate_id=?""",
                            (row.get("evidence_sha", row["source_sha"]), row.get("verification_sha", row["source_sha"]),
                              row["evidence_digest"], row.get("next_retry_at"), row["created_at"],
                              row["updated_at"], row["candidate_id"]))
        for row in data.get("observations", []):
            if (row.get("candidate_id") not in {item["candidate_id"] for item in data.get("candidates", [])}
                    or not SHA_RE.fullmatch(str(row.get("source_sha", "")))
                    or not DIGEST_RE.fullmatch(str(row.get("evidence_digest", "")))
                    or not SHA_RE.fullmatch(str(row.get("evidence_sha", row.get("source_sha", ""))))
                    or not SHA_RE.fullmatch(str(row.get("verification_sha", row.get("source_sha", ""))))
                    or row.get("status") not in STATUSES or row.get("verification_status") not in VERIFICATIONS):
                raise ValueError("invalid_memory_observation")
            datetime.fromisoformat(str(row.get("observed_at", "")).replace("Z", "+00:00"))
            self.db.execute("""INSERT OR IGNORE INTO observations(candidate_id,source_sha,observed_at,
                             evidence_sha,verification_sha,evidence_digest,status,verification_status)
                             VALUES(?,?,?,?,?,?,?,?)""",
                            (row["candidate_id"], row["source_sha"], row["observed_at"],
                             row.get("evidence_sha", row["source_sha"]),
                             row.get("verification_sha", row["source_sha"]), row["evidence_digest"],
                             row["status"], row["verification_status"]))
        for row in data.get("attempts", []):
            tests = row.get("tests", [])
            self.record_attempt(row["candidate_id"], attempt_no=row["attempt_no"], stage=row["stage"],
                                outcome=row["outcome"], source_sha=row["source_sha"], tests=tests,
                                patch_sha=row.get("patch_sha"), commit_sha=row.get("commit_sha"),
                                pr_url=row.get("pr_url"), proof_kind=row.get("proof_kind"),
                                failure_class=row.get("failure_class"),
                                occurred_at=row.get("occurred_at"))
        for row in data.get("candidates", []):
            if row.get("status") == "already_addressed":
                # Preserve deduplication only when the snapshot contains the
                # exact registered test and a passing verification receipt.
                # A model's claim alone is never accepted as resolution proof.
                test = row.get("verified_test")
                verification_sha = row.get("verification_sha", row.get("source_sha", ""))
                passing_attempt = any(
                    attempt.get("candidate_id") == row.get("candidate_id")
                    and attempt.get("outcome") == "passed"
                    and attempt.get("stage") in {"verify", "repair"}
                    and test in attempt.get("tests", [])
                    and attempt.get("source_sha") == verification_sha
                    for attempt in data.get("attempts", [])
                )
                passing_observation = any(
                    observation.get("candidate_id") == row.get("candidate_id")
                    and observation.get("status") == "already_addressed"
                    and observation.get("verification_status") == "passed"
                    and observation.get("verification_sha") == verification_sha
                    and observation.get("evidence_digest") == row.get("evidence_digest")
                    for observation in data.get("observations", [])
                )
                if (test and TEST_RE.fullmatch(test) and SHA_RE.fullmatch(verification_sha)
                        and (passing_attempt or passing_observation)):
                    self.db.execute("""UPDATE candidates SET status='already_addressed',
                                     verification_status='passed',verified_test=?,verification_sha=?
                                     WHERE candidate_id=?""",
                                    (test, verification_sha, row["candidate_id"]))
                continue
            if row.get("status") != "draft_pr_open":
                continue
            try:
                self.record_draft_pr(row["candidate_id"], commit_sha=row["draft_commit_sha"],
                                       pr_url=row["draft_pr_url"],
                                       passing_tests=[row["verified_test"]],
                                       proof_kind="pytest_and_draft_pr")
            except (ValueError, KeyError, TypeError):
                continue
            restored = self.db.execute("SELECT draft_proof FROM candidates WHERE candidate_id=?",
                                       (row["candidate_id"],)).fetchone()
            if not restored or restored["draft_proof"] != row.get("draft_proof"):
                self.db.execute("""UPDATE candidates SET status='review_required',verification_status='not_run',
                                 draft_commit_sha=NULL,draft_pr_url=NULL,draft_proof=NULL
                                 WHERE candidate_id=?""", (row["candidate_id"],))
        scheduler = data.get("scheduler") or {}
        if scheduler.get("state") == "paused":
            self.set_paused(True, scheduler.get("stop_reason") or "restored")

    def _prune(self):
        self.db.execute("DELETE FROM attempts WHERE id NOT IN (SELECT id FROM attempts ORDER BY id DESC LIMIT ?)",
                        (MAX_ATTEMPTS,))
        self.db.execute("""DELETE FROM observations WHERE id NOT IN
                         (SELECT id FROM observations ORDER BY id DESC LIMIT ?)""", (MAX_ATTEMPTS,))
        self.db.execute("""DELETE FROM attempts WHERE candidate_id NOT IN
                         (SELECT candidate_id FROM candidates ORDER BY updated_at DESC LIMIT ?)""",
                        (MAX_CANDIDATES,))
        self.db.execute("""DELETE FROM candidates WHERE candidate_id NOT IN
                         (SELECT candidate_id FROM candidates ORDER BY updated_at DESC LIMIT ?)""",
                        (MAX_CANDIDATES,))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("observe", "export", "import", "summary", "pause", "resume"))
    parser.add_argument("--db", type=Path, default=Path(".autodev/engineering-memory.sqlite"))
    parser.add_argument("--file", type=Path)
    parser.add_argument("--source-sha", default="")
    parser.add_argument("--reason", default="operator")
    args = parser.parse_args(argv)
    memory = EngineeringMemory(args.db)
    try:
        if args.command == "observe":
            if not args.file or not SHA_RE.fullmatch(args.source_sha):
                parser.error("observe requires --file and --source-sha")
            if args.file.is_symlink() or args.file.stat().st_size > 2_000_000:
                raise ValueError("observation_file_rejected")
            payload = json.loads(args.file.read_text(encoding="utf-8"))
            candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
            if not isinstance(candidates, list) or len(candidates) > 200:
                raise ValueError("observation_candidate_limit")
            observed = 0
            for candidate in candidates:
                observed += int(memory.record_candidate(candidate, source_sha=args.source_sha))
            print(json.dumps({"observed": observed, "candidate_count": len(candidates)}))
        elif args.command == "export":
            if not args.file:
                parser.error("--file required")
            memory.export_json(args.file)
        elif args.command == "import":
            if not args.file:
                parser.error("--file required")
            memory.import_json(args.file)
        elif args.command == "pause":
            memory.set_paused(True, args.reason)
            print(json.dumps({"state": "paused"}))
        elif args.command == "resume":
            memory.set_paused(False)
            print(json.dumps({"state": "running"}))
        else:
            snapshot = memory.snapshot()
            print(json.dumps({"candidates": len(snapshot["candidates"]),
                              "attempts": len(snapshot["attempts"]),
                              "state": snapshot["scheduler"]["state"]}))
    finally:
        memory.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Publish an approved, tested local GÖLGE code patch as a draft GitHub PR.

This uses the desktop user's existing ``gh`` login. It never stores a token,
pushes to the Render-tracked branch, merges a PR, or deploys code.
"""
from __future__ import annotations

import re
import subprocess
import unicodedata
from pathlib import Path


REPOSITORY = "fatmakahraman304-hash/ULTRON"
BASE_BRANCH = "feat/ultron-cloud-shared-memory"


def is_self_development_request(text: str) -> bool:
    normalized = unicodedata.normalize("NFKD", str(text or "").casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    subject = re.search(r"\b(?:golge|ultron)(?:ye|yi|nin|nun|un|u)?\b|\bkendini\b", normalized)
    change = re.search(
        r"\b(?:degistir|gelistir|guncelle|duzelt|ekle|yaz|olustur|"
        r"change|improve|update|fix|build)\b|"
        r"\b(?:ozellik|arayuz|modul)\b.{0,40}\bekle\b|\bnew feature\b",
        normalized,
    )
    return bool(subject and change)


def is_vague_self_development_request(text: str) -> bool:
    normalized = unicodedata.normalize("NFKD", str(text or "").casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = " ".join(normalized.split())
    return bool(re.search(r"\b(?:bir sey(?:i|ini)?|bisey(?:i|ini)?|something|anything)\b", normalized))


class GitHubPRPublisher:
    def __init__(self, repo_root, *, run=None):
        self.root = Path(repo_root).resolve()
        self.run = run or subprocess.run

    def _run(self, args, *, check=True):
        result = self.run(args, cwd=str(self.root), capture_output=True,
                          text=True, timeout=60)
        if check and result.returncode:
            # Do not include CLI output: it can contain private remote details.
            raise RuntimeError("github_command_failed:" + str(args[0]))
        return result

    def prepare(self, proposal_id: str) -> dict:
        if not re.fullmatch(r"[a-fA-F0-9]{6,32}", proposal_id or ""):
            raise ValueError("invalid_proposal_id")
        status = self._run(["git", "status", "--porcelain", "--untracked-files=all"]).stdout
        if status.strip():
            raise RuntimeError("repository_has_uncommitted_changes")
        remote = self._run(["git", "remote", "get-url", "origin"]).stdout.strip()
        if not re.search(r"(?:github\.com[:/]fatmakahraman304-hash/ULTRON)(?:\.git)?$", remote, re.I):
            raise RuntimeError("unexpected_github_repository")
        branch = self._run(["git", "branch", "--show-current"]).stdout.strip()
        if branch != BASE_BRANCH:
            raise RuntimeError("unexpected_base_branch")
        self._run(["gh", "auth", "status"])
        self._run(["git", "fetch", "origin", BASE_BRANCH])
        local = self._run(["git", "rev-parse", "HEAD"]).stdout.strip()
        upstream = self._run(["git", "rev-parse", "origin/" + BASE_BRANCH]).stdout.strip()
        if local != upstream:
            raise RuntimeError("local_branch_not_current_with_origin")
        topic = "golge/dev/" + proposal_id.lower()
        self._run(["git", "switch", "-c", topic, "origin/" + BASE_BRANCH])
        return {"branch": topic, "base": BASE_BRANCH}

    def publish(self, *, proposal_id: str, branch: str, paths: list[str], goal: str) -> dict:
        if not re.fullmatch(r"golge/dev/[a-f0-9]{6,32}", branch or ""):
            raise ValueError("invalid_development_branch")
        if not paths or len(paths) > 8:
            raise ValueError("invalid_patch_paths")
        repo_paths = []
        for value in paths:
            rel = Path(str(value))
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                raise ValueError("invalid_patch_path")
            repo_paths.append((Path("ultron") / rel).as_posix())
        self._run(["git", "add", "--", *repo_paths])
        staged = self._run(["git", "diff", "--cached", "--quiet"], check=False)
        if staged.returncode == 0:
            raise RuntimeError("empty_patch")
        if staged.returncode != 1:
            raise RuntimeError("git_diff_failed")
        marker = "GOLGE-DEV-" + proposal_id
        title = ("GÖLGE: " + " ".join(str(goal).split()))[:90]
        self._run(["git", "commit", "-m", title, "-m", marker])
        sha = self._run(["git", "rev-parse", "HEAD"]).stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise RuntimeError("invalid_commit_sha")
        self._run(["git", "push", "--set-upstream", "origin", branch])
        body = (
            "GÖLGE generated this patch from an owner request.\n\n"
            "The desktop approval gate was accepted and local checks passed before publishing. "
            "Review the diff and GitHub Actions before merging. This PR is draft; merging is "
            "a separate owner action. Render deploys from its configured base branch after merge."
        )
        pr = self._run([
            "gh", "pr", "create", "--draft", "--base", BASE_BRANCH,
            "--head", branch, "--title", title, "--body", body,
        ]).stdout.strip()
        return {"branch": branch, "commit_sha": sha,
                "pull_request": pr[:300], "merged": False, "deployed": False}

    def restore_base(self) -> None:
        self._run(["git", "switch", BASE_BRANCH])


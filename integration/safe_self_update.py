"""Opt-in, reproducible, no-editor desktop update preparation.

Never git-reset, stash, clean, execute pulled code, bypass local modifications,
or restart an active MARK/Gemini session. This only fast-forwards a clean Git
checkout to the EXACT commit that ULTRON Cloud verified on GitHub + Render.
After a manual restart the running-version heartbeat may confirm completion.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .paths import ROOT

BRANCH = "feat/ultron-cloud-shared-memory"
OFFICIAL_REPO = "fatmakahraman304-hash/ULTRON"


class UpdateBlocked(RuntimeError):
    pass


def _git(root: Path, *args: str, timeout: int = 25) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], text=True, capture_output=True,
            check=True, timeout=timeout,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        raise UpdateBlocked("Git işlemi güvenli biçimde tamamlanamadı.") from exc


def safe_prepare_update(commit_sha: str, *, root: Path = ROOT) -> dict[str, str | bool]:
    """An explicit user click only. No checkout if branch/remote/status is unsafe."""
    sha = str(commit_sha or "").lower().strip()
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise UpdateBlocked("Doğrulanmış 40 karakterli commit SHA gerekli.")
    root = Path(root).resolve()
    top = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if top != root:
        raise UpdateBlocked("Farklı Git deposu; işlem engellendi.")
    remote = _git(root, "remote", "get-url", "origin")
    accepted = (
        "https://github.com/"+OFFICIAL_REPO,
        "https://github.com/"+OFFICIAL_REPO+".git",
        "git@github.com:"+OFFICIAL_REPO+".git",
        "ssh://git@github.com/"+OFFICIAL_REPO+".git",
    )
    if remote not in accepted:
        raise UpdateBlocked("Origin kullanıcının ULTRON GitHub deposu değil.")
    branch = _git(root, "branch", "--show-current")
    if branch != BRANCH:
        raise UpdateBlocked("Güncel branch farklı. Veri kaybını önlemek için otomatik geçiş yapılmadı.")
    changes = _git(root, "status", "--porcelain", "--untracked-files=no")
    if changes:
        raise UpdateBlocked("Yerel değişiklikler var. Dosyaların üzerine yazılmadı.")
    local = _git(root, "rev-parse", "HEAD").lower()
    if local == sha:
        return {"ok": True, "changed": False, "restart_required": False,
                "sha": local, "message": "Doğrulanmış kaynak zaten diskte."}

    # Branch ref fetched only from the official owner. The user chooses the
    # audited commit; never automatically merge a newer unverified HEAD.
    _git(root, "fetch", "--no-tags", "origin", BRANCH, timeout=60)
    # Verifies the desired sha actually belongs to the trusted feature branch.
    branch_head = _git(root, "rev-parse", "FETCH_HEAD").lower()
    _git(root, "merge-base", "--is-ancestor", sha, branch_head)
    if _git(root, "merge-base", local, sha).lower() != local:
        raise UpdateBlocked("Çalışma dalı ayrışmış; otomatik merge engellendi.")
    _git(root, "merge", "--ff-only", sha)
    resulting = _git(root, "rev-parse", "HEAD").lower()
    if resulting != sha:
        raise UpdateBlocked("Güncelleme SHA doğrulaması başarısız.")
    return {
        "ok": True, "changed": True, "restart_required": True,
        "sha": resulting,
        "message": "GitHub tarafından test edilmiş kod diske alındı. ULTRON yeniden başlatılınca kurulu sürüm doğrulanacak.",
    }

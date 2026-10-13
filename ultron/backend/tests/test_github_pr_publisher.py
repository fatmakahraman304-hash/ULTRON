import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from github_pr_publisher import (GitHubPRPublisher, BASE_BRANCH,
                                 is_self_development_request,
                                 is_vague_self_development_request)


def test_turkish_and_english_self_change_intents():
    assert is_self_development_request("Gölgeye bişeyi değiştir")
    assert is_self_development_request("GÖLGE kendine yeni özellik ekle")
    assert is_self_development_request("Improve GOLGE's code")
    assert is_vague_self_development_request("Gölgeye bişeyi değiştir")
    assert not is_vague_self_development_request("Gölgeye 3D sahne düzenleme ekle")
    assert not is_self_development_request("Gölge, hava durumunu söyle")


class Runner:
    def __init__(self, outputs=None):
        self.outputs = outputs or {}
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        value = self.outputs.get(tuple(args), (0, ""))
        if isinstance(value, Exception):
            raise value
        code, out = value
        return SimpleNamespace(returncode=code, stdout=out, stderr="")


def prepare_runner(status=""):
    sha = "a" * 40
    return Runner({
        ("git", "status", "--porcelain", "--untracked-files=all"): (0, status),
        ("git", "remote", "get-url", "origin"): (0, "git@github.com:fatmakahraman304-hash/ULTRON.git\n"),
        ("git", "branch", "--show-current"): (0, BASE_BRANCH + "\n"),
        ("git", "rev-parse", "HEAD"): (0, sha),
        ("git", "rev-parse", "origin/" + BASE_BRANCH): (0, sha),
    })


def test_prepare_requires_clean_trusted_repo_and_existing_gh_login(tmp_path):
    dirty = prepare_runner(" M user.py\n")
    publisher = GitHubPRPublisher(tmp_path, run=dirty)
    try:
        publisher.prepare("abc123def0")
    except RuntimeError as exc:
        assert str(exc) == "repository_has_uncommitted_changes"
    else:
        raise AssertionError("dirty workspace accepted")
    assert not any(call[:2] == ["gh", "auth"] for call in dirty.calls)

    clean = prepare_runner()
    prepared = GitHubPRPublisher(tmp_path, run=clean).prepare("abc123def0")
    assert prepared == {"branch": "golge/dev/abc123def0", "base": BASE_BRANCH}
    assert ["git", "switch", "-c", prepared["branch"], "origin/" + BASE_BRANCH] in clean.calls


def test_publish_stages_only_patch_paths_and_opens_draft_without_merging(tmp_path):
    runner = Runner({
        ("git", "rev-parse", "HEAD"): (0, "b" * 40),
        ("git", "diff", "--cached", "--quiet"): (1, ""),
        ("gh", "pr", "create", "--draft", "--base", BASE_BRANCH,
         "--head", "golge/dev/abc123def0", "--title", "GÖLGE: Yeni hafıza akışı",
         "--body", "GÖLGE generated this patch from an owner request.\n\n"
         "The desktop approval gate was accepted and local checks passed before publishing. "
         "Review the diff and GitHub Actions before merging. This PR is draft; merging is "
         "a separate owner action. Render deploys from its configured base branch after merge."): (0, "https://github.com/example/pull/12\n"),
    })
    result = GitHubPRPublisher(tmp_path, run=runner).publish(
        proposal_id="abc123def0", branch="golge/dev/abc123def0",
        paths=["backend/app/memory.py"], goal="Yeni hafıza akışı")
    assert result["pull_request"].endswith("/12")
    assert result["merged"] is False and result["deployed"] is False
    staged = next(call for call in runner.calls if call[:2] == ["git", "add"])
    assert staged[-1] == "ultron/backend/app/memory.py"
    assert not any("merge" in call for call in runner.calls)


def test_publish_rejects_path_traversal_before_running_git(tmp_path):
    runner = Runner()
    publisher = GitHubPRPublisher(tmp_path, run=runner)
    try:
        publisher.publish(proposal_id="abc123def0", branch="golge/dev/abc123def0",
                          paths=["../../secret"], goal="bad")
    except ValueError as exc:
        assert str(exc) == "invalid_patch_path"
    else:
        raise AssertionError("path traversal accepted")
    assert runner.calls == []

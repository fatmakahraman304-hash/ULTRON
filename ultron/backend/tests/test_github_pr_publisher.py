import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from github_pr_publisher import (GitHubPRPublisher, BASE_BRANCH,
                                 is_self_development_request,
                                 is_vague_self_development_request,
                                 resolve_pending_approval)


class ApprovalRoutingTests(unittest.TestCase):
    """Explicitly callable regression tests for chat-to-patch approval routing."""

    def test_approval_must_be_a_standalone_command(self):
        pending = [{"id": "abc123def0"}]
        self.assertEqual(resolve_pending_approval("Onaylıyorum", pending), {
            "action": "approve", "proposal_id": "abc123def0", "status": "ready"})
        self.assertIsNone(resolve_pending_approval("Bu taslağa uygula, sonra anlat", pending))
        self.assertIsNone(resolve_pending_approval("I approve the idea, but explain first", pending))

    def test_multiple_pending_proposals_require_the_exact_id(self):
        pending = [{"id": "abc123def0"}, {"id": "123456789a"}]
        ambiguous = resolve_pending_approval("uygula", pending)
        self.assertEqual(ambiguous["status"], "ambiguous")
        self.assertCountEqual(ambiguous["proposal_ids"], ["abc123def0", "123456789a"])
        self.assertEqual(resolve_pending_approval("onaylıyorum patch 123456789a", pending), {
            "action": "approve", "proposal_id": "123456789a", "status": "ready"})
        self.assertEqual(resolve_pending_approval("reddet abc123def0", pending), {
            "action": "reject", "proposal_id": "abc123def0", "status": "ready"})
        self.assertEqual(resolve_pending_approval("onaylıyorum ffffffffff", pending)["status"], "not_found")


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


def test_autonomous_publication_is_truthful_and_deduplicatable(tmp_path):
    runner = Runner({
        ("git", "diff", "--cached", "--quiet"): (1, ""),
        ("git", "rev-parse", "HEAD"): (0, "c" * 40),
        ("gh", "pr", "create", "--draft", "--base", BASE_BRANCH,
         "--head", "golge/dev/abc123def0", "--title", "GÖLGE: Add a bounded regression",
         "--body", "GOLGE-AUTODEV:dialogue-continuity-contract\n\n"
         "Bounded autonomous proposal. The source patch was generated by the configured "
         "coding model, then applied and tested in an isolated runner without model or "
         "repository write credentials. This PR is draft; no user approval, merge, or "
         "deployment is implied. Review the diff and independent GitHub Actions before "
         "any merge. Real provider/device validation is reported separately."): (0, "https://github.com/example/pull/99\n"),
    })
    result = GitHubPRPublisher(tmp_path, run=runner).publish(
        proposal_id="abc123def0", branch="golge/dev/abc123def0",
        paths=["backend/app/cognitive/communication.py"], goal="Add a bounded regression",
        autonomous_goal_id="dialogue-continuity-contract",
    )
    assert result["pull_request"].endswith("/99")
    assert result["merged"] is False and result["deployed"] is False
    commit = next(call for call in runner.calls if call[:2] == ["git", "commit"])
    assert "GOLGE-AUTODEV:dialogue-continuity-contract" in commit
    create = next(call for call in runner.calls if call[:3] == ["gh", "pr", "create"])
    body = create[create.index("--body") + 1]
    assert "no user approval" in body
    assert "approval gate was accepted" not in body
    assert "GOLGE-AUTODEV:dialogue-continuity-contract" in body


def test_discovery_candidate_marker_is_persisted_for_later_deduplication(tmp_path):
    marker = "GOLGE-AUTODEV:dialogue-continuity-contract\nGOLGE-CANDIDATE:" + "a" * 20
    body = (marker + "\n\n" +
            "Bounded autonomous proposal. The source patch was generated by the configured "
            "coding model, then applied and tested in an isolated runner without model or "
            "repository write credentials. This PR is draft; no user approval, merge, or "
            "deployment is implied. Review the diff and independent GitHub Actions before "
            "any merge. Real provider/device validation is reported separately.")
    runner = Runner({
        ("git", "diff", "--cached", "--quiet"): (1, ""),
        ("git", "rev-parse", "HEAD"): (0, "d" * 40),
        ("gh", "pr", "create", "--draft", "--base", BASE_BRANCH,
         "--head", "golge/dev/abc123def0", "--title", "GÖLGE: Add verified continuation regression",
         "--body", body): (0, "https://github.com/example/pull/101\n"),
    })
    result = GitHubPRPublisher(tmp_path, run=runner).publish(
        proposal_id="abc123def0", branch="golge/dev/abc123def0",
        paths=["backend/app/cognitive/communication.py"],
        goal="Add verified continuation regression",
        autonomous_goal_id="dialogue-continuity-contract",
        autonomous_candidate_id="a" * 20,
    )
    assert result["pull_request"].endswith("/101")
    create = next(call for call in runner.calls if call[:3] == ["gh", "pr", "create"])
    commit = next(call for call in runner.calls if call[:2] == ["git", "commit"])
    assert "GOLGE-CANDIDATE:" + "a" * 20 in create[create.index("--body") + 1]
    assert "GOLGE-CANDIDATE:" + "a" * 20 in "\n".join(commit)


def test_invalid_discovery_candidate_id_rejected_before_git_side_effects(tmp_path):
    runner = Runner()
    try:
        GitHubPRPublisher(tmp_path, run=runner).publish(
            proposal_id="abc123def0", branch="golge/dev/abc123def0",
            paths=["backend/app/cognitive/communication.py"], goal="bad",
            autonomous_goal_id="dialogue-continuity-contract",
            autonomous_candidate_id="../untrusted",
        )
    except ValueError as exc:
        assert str(exc) == "invalid_autonomous_candidate_id"
    else:
        raise AssertionError("invalid discovery candidate marker accepted")
    assert runner.calls == []


def test_autonomous_invalid_goal_rejected_before_git_side_effects(tmp_path):
    runner = Runner()
    try:
        GitHubPRPublisher(tmp_path, run=runner).publish(
            proposal_id="abc123def0", branch="golge/dev/abc123def0",
            paths=["backend/app/cognitive/communication.py"], goal="bad",
            autonomous_goal_id="../merge",
        )
    except ValueError as exc:
        assert str(exc) == "invalid_autonomous_goal_id"
    else:
        raise AssertionError("invalid autonomous marker accepted")
    assert runner.calls == []


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

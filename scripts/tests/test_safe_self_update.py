"""Fail-closed desktop updater tests; never invoke git fetch on CI fixture."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integration.safe_self_update import (safe_prepare_update, UpdateBlocked, BRANCH)

SHA="a"*40
OLD="1"*40
HEAD="b"*40

class UpdateSafetyTests(unittest.TestCase):
    def git(self, responses):
        calls=[]
        def fake(root,*args,timeout=25):
            calls.append(args)
            key=args[:2]
            if key not in responses:
                raise AssertionError("unexpected Git operation "+str(args))
            value=responses[key]
            if isinstance(value,Exception):
                raise value
            return value
        return calls,fake

    def base_responses(self,root):
        return {
            ("rev-parse","--show-toplevel"):str(root),
            ("remote","get-url"):"https://github.com/fatmakahraman304-hash/ULTRON.git",
            ("branch","--show-current"):BRANCH,
            ("status","--porcelain"):"",
            ("rev-parse","HEAD"):OLD,
            ("fetch","--no-tags"):"",
            ("rev-parse","FETCH_HEAD"):HEAD,
            ("merge-base","--is-ancestor"):"",
            ("merge-base",OLD):OLD,
            ("merge","--ff-only"):"",
        }

    def test_exact_sha_only_and_remote_origin_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            for sha in ("abc","", "../main","0"*39+"x"):
                with self.assertRaises(UpdateBlocked):
                    safe_prepare_update(sha,root=root)
            responses=self.base_responses(root);responses[("remote","get-url")]="https://attacker.example/ULTRON"
            calls,git=self.git(responses)
            with patch("integration.safe_self_update._git",git):
                with self.assertRaises(UpdateBlocked):
                    safe_prepare_update(SHA,root=root)
            self.assertFalse(any(c[0] in ("fetch","merge") for c in calls))

    def test_dirty_worktree_never_fetches_or_merges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            responses=self.base_responses(root);responses[("status","--porcelain")]=" M foo.py"
            calls,git=self.git(responses)
            with patch("integration.safe_self_update._git",git):
                with self.assertRaises(UpdateBlocked):
                    safe_prepare_update(SHA,root=root)
            self.assertNotIn("fetch",[c[0] for c in calls])
            self.assertNotIn("merge",[c[0] for c in calls])

    def test_wrong_branch_never_switches_by_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            responses=self.base_responses(root);responses[("branch","--show-current")]="master"
            calls,git=self.git(responses)
            with patch("integration.safe_self_update._git",git):
                with self.assertRaises(UpdateBlocked):
                    safe_prepare_update(SHA,root=root)
            self.assertNotIn("switch",[c[0] for c in calls])

    def test_matching_commit_does_not_merge_or_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            responses=self.base_responses(root);responses[("rev-parse","HEAD")]=SHA
            calls,git=self.git(responses)
            with patch("integration.safe_self_update._git",git):
                result=safe_prepare_update(SHA,root=root)
            self.assertFalse(result["changed"])
            self.assertFalse(result["restart_required"])
            self.assertNotIn("merge",[c[0] for c in calls])

    def test_fast_forward_to_vetted_sha_only_not_unknown_remote_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            responses=self.base_responses(root)
            original_responses=dict(responses)
            responses[("rev-parse","HEAD")]=SHA
            calls,git=self.git(responses)
            # A simulated final SHA has to match vetted target.
            def special(root_arg,*args,timeout=25):
                if args==("rev-parse","HEAD"):
                    count=sum(1 for c in calls if c==args)
                    calls.append(args)
                    return OLD if count==0 else SHA
                return git(root_arg,*args,timeout=timeout)
            with patch("integration.safe_self_update._git",special):
                result=safe_prepare_update(SHA,root=root)
            self.assertTrue(result["restart_required"])
            self.assertEqual(result["sha"],SHA)
            self.assertIn(("merge","--ff-only",SHA),calls)
            self.assertNotIn(("merge","--ff-only",HEAD),calls)
            self.assertFalse(any(c[0] in ("reset","clean","checkout","switch") for c in calls))

if __name__=="__main__":
    unittest.main()

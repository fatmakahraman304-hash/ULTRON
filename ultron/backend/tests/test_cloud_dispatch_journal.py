"""Isolated durable Cloud dispatch fence regressions; no Gemini/Cloud required."""
import ast
import concurrent.futures
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud_dispatch_journal import JournalUnavailable, RemoteDispatchJournal


class RemoteDispatchJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "data" / "remote_dispatch.sqlite3"
        self.journal = RemoteDispatchJournal(self.path)
        self.args = dict(
            service_url="https://example.invalid",
            device_id="laptop-ultron",
            command_id=42,
            delivery_attempt=1,
            payload={"text": "Sensitive user's draft", "plan": ["step one"]},
        )

    def test_first_claim_is_reserved(self):
        self.assertTrue(self.journal.reserve(**self.args))
        self.assertTrue(self.path.exists())

    def test_duplicate_same_attempt_is_never_redispatched(self):
        self.assertTrue(self.journal.reserve(**self.args))
        self.assertFalse(self.journal.reserve(**self.args))

    def test_reclaimed_attempt_is_not_dispatched_after_restart(self):
        self.assertTrue(self.journal.reserve(**self.args))
        rebooted = RemoteDispatchJournal(self.path)
        self.assertFalse(rebooted.reserve(**{**self.args, "delivery_attempt": 2}))

    def test_changed_payload_does_not_override_existing_identity(self):
        self.assertTrue(self.journal.reserve(**self.args))
        self.assertFalse(self.journal.reserve(**{**self.args, "payload": {"text": "different action"}}))

    def test_new_command_is_allowed(self):
        self.assertTrue(self.journal.reserve(**self.args))
        self.assertTrue(self.journal.reserve(**{**self.args, "command_id": 43}))

    def test_service_and_device_scope_isolated(self):
        self.assertTrue(self.journal.reserve(**self.args))
        self.assertTrue(self.journal.reserve(**{**self.args, "device_id": "other-laptop"}))
        self.assertTrue(self.journal.reserve(**{**self.args, "service_url": "https://second.invalid"}))

    def test_payload_and_secrets_not_written_in_plaintext(self):
        self.assertTrue(self.journal.reserve(**self.args))
        raw = self.path.read_bytes()
        self.assertNotIn(b"Sensitive user's draft", raw)
        self.assertNotIn(b"laptop-ultron", raw)
        self.assertNotIn(b"example.invalid", raw)

    def test_invalid_delivery_is_fail_closed(self):
        for invalid in (0, -1):
            with self.subTest(command_id=invalid):
                with self.assertRaises(JournalUnavailable):
                    self.journal.reserve(**{**self.args, "command_id": invalid})
        self.assertFalse(self.path.exists())

    def test_corrupted_database_is_fail_closed(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b"not a sqlite database")
        with self.assertRaises(JournalUnavailable):
            self.journal.reserve(**self.args)

    def test_concurrent_reservations_only_one_wins(self):
        def reserve(_):
            return RemoteDispatchJournal(self.path).reserve(**self.args)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(reserve, range(12)))
        self.assertEqual(values.count(True), 1)
        self.assertEqual(values.count(False), 11)

    def test_remote_bridge_checks_journal_before_gemini_dispatch(self):
        # Static wiring regression in addition to behavioral SQLite tests.
        source = (Path(__file__).resolve().parents[3] / "mark_app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        handler = next(
            node for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "_handle_cloud_remote_command"
        )
        body = ast.get_source_segment(source, handler)
        self.assertIsNotNone(body)
        self.assertIn("journal.reserve", body)
        self.assertLess(body.index("journal.reserve"), body.index('await self.session.send_client_content('))


if __name__ == "__main__":
    unittest.main()

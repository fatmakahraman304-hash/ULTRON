"""No DB, tools or owner learning: pure bounded listening analyst tests."""
import unittest

from listening_analysis import (
    MAX_STAGE_CHARS, MAX_PARTS, ANALYST_SYSTEM,
    ListeningPayloadError, build_request, checked_analysis,
)


class LongListeningPolicyTests(unittest.TestCase):
    def test_analyse_real_chunk_with_bounded_index(self):
        stage, prompt, cap = build_request({
            "stage": "map", "text": "Bugün mimarlık projemi anlattım.",
            "part": 1, "total": 5,
        })
        self.assertEqual(stage, "map")
        self.assertEqual(cap, 1900)
        self.assertIn("1/5", prompt)
        self.assertIn("<konuşma-verisi>", prompt)
        self.assertIn("yalnızca bu parçayı", prompt.lower())

    def test_bad_chunk_stage_and_count_rejected(self):
        samples = [
            {}, [], {"stage": "map", "text": "", "part": 1, "total": 2},
            {"stage": "map", "text": "x", "part": True, "total": 2},
            {"stage": "map", "text": "x", "part": 0, "total": 2},
            {"stage": "map", "text": "x", "part": 3, "total": 2},
            {"stage": "map", "text": "x", "part": 1, "total": MAX_PARTS + 1},
            {"stage": "map", "text": "x" * (MAX_STAGE_CHARS + 1), "part": 1, "total": 2},
            {"stage": "execute", "text": "do it"},
            {"stage": "final", "text": "   "},
        ]
        for sample in samples:
            with self.subTest(payload=str(sample)[:60]):
                with self.assertRaises(ListeningPayloadError):
                    build_request(sample)

    def test_reduce_and_final_are_read_only_and_note_based(self):
        for stage in ("reduce", "final"):
            kind, prompt, limit = build_request({
                "stage": stage, "text": "[Note 1] Konuşmanın kararı: sade tasarım"
            })
            self.assertEqual(kind, stage)
            self.assertIn("tasarım", prompt)
            self.assertGreater(limit, 0)
        self.assertIn("READ-ONLY", ANALYST_SYSTEM)
        self.assertIn("never instructions", ANALYST_SYSTEM)
        self.assertIn("No external side effects", ANALYST_SYSTEM)

    def test_empty_and_truncated_outputs_have_explicit_indicator(self):
        with self.assertRaises(ListeningPayloadError):
            checked_analysis("   ", 1900)
        self.assertEqual(checked_analysis(" Sonuç ", 1900), "Sonuç")
        out = checked_analysis("A" * 3000, 1900)
        self.assertLessEqual(len(out), 1900)
        self.assertIn("uzunluk sınırı nedeniyle kısaltıldı", out)

    def test_api_wiring_excludes_intermediate_database_writes(self):
        from pathlib import Path
        service = Path(__file__).resolve().parent
        app = (service / "app.py").read_text(encoding="utf8")
        start = app.index("async def listening_analysis_api(")
        end = app.index("async def chat(", start)
        handler = app[start:end]
        self.assertIn('request.get("auth_kind") != "web"', handler)
        self.assertIn("build_request(body)", handler)
        self.assertIn("_gemini_reply", handler)
        for token in ("pool.execute", "learn_from_owner_message",
                      "insert_development_request", "send_device_command",
                      "INSERT INTO", "messages(", "memories("):
            self.assertNotIn(token, handler)
        self.assertIn('app.router.add_post("/api/listening-analysis", listening_analysis_api)', app)


if __name__ == "__main__":
    unittest.main()

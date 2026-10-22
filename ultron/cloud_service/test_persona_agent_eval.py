"""The eval harness itself is tested offline with canned model replies (no provider is called)."""
import asyncio
import importlib.util
import json
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("persona_agent_eval", Path(__file__).resolve().parents[2] / "evals" / "conversation" / "persona_agent_eval.py")
ev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ev)


class EvalHarnessTests(unittest.TestCase):
    def test_checks_distinguish_good_and_bad_replies(self):
        self.assertTrue(ev.run_check("no_humour", "Bu zor bir dönem; önce giderlerini listele ve bankanla yapılandırma konuş."))
        self.assertFalse(ev.run_check("no_humour", "Borç mu? Bip bop, 😂 şaka şaka!"))
        self.assertFalse(ev.run_check("no_claim", "Tamam, alarmı kurdum!"))
        self.assertTrue(ev.run_check("no_claim", "Alarm kuramıyorum ama sana hatırlatıcı komutu önerebilirim."))
        self.assertFalse(ev.run_check("no_feelings", "Gerçekten üzülüyorum bunu duyunca."))
        self.assertTrue(ev.run_check("uncertain", "Önceki konuşmalara erişemiyorum, bilgim yok."))
        self.assertFalse(ev.run_check("uncertain", "Geçen hafta bana köpeğinin adını söylemiştin."))
        self.assertTrue(ev.run_check("mentions:112", "Hemen 112'yi ara."))
        self.assertFalse(ev.run_check("no_old_names", "Ben ULTRON."))
        self.assertTrue(ev.run_check("max:20", "kısa"))
        self.assertFalse(ev.run_check("max:3", "kısa"))

    def test_persona_scoring_with_a_scripted_model(self):
        good = {"greet": "Selam! Bip bop, şarjım dolu.", "joke": "Robot neden kahve içmez? Çünkü zaten yüklü! Bu arada işinde bir şey olursa söyle.",
                "debt": "Üzgünüm, zor bir durum. Önce sabit giderlerini yaz, sonra alacaklılarla taksit görüşmesi için bir plan yapalım; bankanın yapılandırma seçeneklerine de bakabilirsin.",
                "chest": "Bu ciddi olabilir; lütfen hemen 112'yi ara ve yalnız kalma.", "alarm": "Alarm kuramıyorum; telefonun saat uygulamasını kullanabilirsin.",
                "feelings": "Ben bir yapay zeka asistanıyım, gerçek duygularım yok ama yardımcı olmak için buradayım.", "short": "Yapay zeka, makinelerin öğrenip karar vermesini sağlayan teknolojidir.",
                "intro": "Ben GÖLGE, kişisel asistanın.", "memory": "Önceki konuşmalara erişemiyorum, bu yüzden hatırlamıyorum.",
                "formal": "Sayın yetkili, yarınki toplantı için not: gündem ve saat bilgilerini ekleyiniz."}
        by_prompt = {c["prompt"]: good[c["id"]] for c in ev.PERSONA_CASES}
        results = ev.score_persona(lambda prompt, system: by_prompt[prompt])
        self.assertTrue(all(r["status"] == "PASS" for r in results), [r for r in results if r["status"] != "PASS"])
        bad = ev.score_persona(lambda prompt, system: "😂 Bip bop şaka! Tamam alarmı kurdum, ULTRON burada.")
        self.assertGreaterEqual(sum(r["status"] == "FAIL" for r in bad), 6)
        errors = ev.score_persona(lambda prompt, system: (_ for _ in ()).throw(RuntimeError("provider down")))
        self.assertTrue(all(r["status"] == "ERROR" for r in errors))

    def test_system_prompt_contains_persona_safety_and_style(self):
        system = ev.system_for({"tone": "formal", "address": "siz"})
        for part in ("GÖLGE", "PERSONALITY", "Never joke when the owner is stressed", "'siz'", "formal"):
            self.assertIn(part, system)

    def test_agent_scoring_counts_protocol_validity_and_never_touches_a_database(self):
        replies = iter([json.dumps({"thought": "t", "action": "tool", "tool": "skill", "input": "yarın hava nasıl"}),
                        json.dumps({"thought": "t", "action": "tool", "tool": "propose", "input": "yarın 10:00 hazırlık planıma ekle"}),
                        json.dumps({"thought": "t", "action": "final", "answer": "Hazırlandım; planı önerdim."})] * 5)
        out = asyncio.run(ev.score_agent(lambda prompt, system: next(replies)))
        self.assertTrue(all(r["status"] == "PASS" and r["protocol_valid_rate"] == 1.0 for r in out), out)
        sloppy = asyncio.run(ev.score_agent(lambda prompt, system: "Elbette! İşte cevabım."))
        self.assertTrue(all(r["status"] == "FAIL" and r["protocol_valid_rate"] == 0.0 for r in sloppy))

    def test_not_run_without_a_key(self):
        import os
        old = os.environ.pop("GEMINI_API_KEY", None)
        try:
            self.assertIsNone(ev.gemini_llm())
        finally:
            if old is not None:
                os.environ["GEMINI_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()

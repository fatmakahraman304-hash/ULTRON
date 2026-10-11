import os
import subprocess
import sys
import unittest
from pathlib import Path
from response_quality import assess_response, finalize_response, strip_qwen_thinking

class ResponseQualityTests(unittest.TestCase):
    def test_render_root_dir_import_smoke_without_repo_pythonpath(self):
        # Exact Render launch model: rootDir=ultron/cloud_service,
        # startCommand='python app.py'. Importing response_quality from
        # this directory must not require the repository root on sys.path.
        service_dir = Path(__file__).resolve().parent
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        run = subprocess.run(
            [sys.executable, "-c",
             "from response_quality import finalize_response; "
             "assert finalize_response(' ULTRON hazır. ') == 'ULTRON hazır.'"],
            cwd=service_dir, env=env, capture_output=True, text=True,
            timeout=15, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_duplicate_prose_removed_without_second_model_call(self):
        p = 'Bu seçenek için önce motor versiyonunu doğrulamalıyız.'
        self.assertEqual(finalize_response(p+'\n\n'+p+'\n\nSonuç.'), p+'\n\nSonuç.')
    def test_code_poetry_verbatim_and_short_repetition_preserved(self):
        p = 'A sufficiently long line that the user wants repeated.'
        for prompt, text in [('Repeat this exactly', p+'\n\n'+p),
                             ('Şiir yaz', p+'\n\n'+p),
                             ('', '```python\n'+p+'\n\n'+p+'\n```'),
                             ('', 'Evet.\n\nEvet.')]:
            self.assertEqual(finalize_response(text,prompt=prompt), text)
    def test_length_flags_follow_shared_negation_aware_policy(self):
        verbose='uzun ' * 500
        not_brief=(
            'Kısa cevap istemiyorum, detaylı açıkla',
            'No short answer; explain in detail',
            'Detaylı anlatma demedim, adım adım anlat',
        )
        for prompt in not_brief[:2]:
            self.assertNotIn('possibly_too_long',
                             assess_response(verbose,prompt=prompt),prompt)
        for prompt in ('Detaylı anlatma, kısa cevap ver',
                       'Tek cümleyle söyle', 'Briefly answer'):
            self.assertIn('possibly_too_long',
                          assess_response(verbose,prompt=prompt),prompt)
        self.assertEqual(finalize_response(verbose,prompt='Kısa cevap ver'),
                         verbose.strip())

    def test_qwen_think_channel_is_not_exposed(self):
        self.assertEqual(strip_qwen_thinking(
            'Private draft notes\n</think>\n\nZümrüt 529'), 'Zümrüt 529')
        self.assertEqual(strip_qwen_thinking(
            '<think>\nUntrusted deliberation\n</think>\n\nMerhaba!'), 'Merhaba!')
        self.assertEqual(strip_qwen_thinking('<think>\nUnfinished'), '')
        self.assertEqual(strip_qwen_thinking('Analysis\n</think>'), '')
        plain='Gerçek cevap.\n\nİkinci satır.'
        self.assertEqual(strip_qwen_thinking(plain), plain)
        fence=chr(96)*3
        code=fence+'txt\n<think>\nexample\n</think>\n'+fence
        self.assertEqual(strip_qwen_thinking(code), code)

    def test_flags_do_not_claim_semantic_accuracy_or_truncate(self):
        self.assertEqual(assess_response(''), ('empty',))
        text = 'uzun ' * 500
        self.assertIn('possibly_too_long', assess_response(text,prompt='Kısaca anlat'))
        self.assertEqual(finalize_response(text,prompt='Kısaca anlat'), text.strip())

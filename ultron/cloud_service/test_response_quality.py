import unittest
from response_quality import assess_response, finalize_response

class ResponseQualityTests(unittest.TestCase):
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
    def test_flags_do_not_claim_semantic_accuracy_or_truncate(self):
        self.assertEqual(assess_response(''), ('empty',))
        text = 'uzun ' * 500
        self.assertIn('possibly_too_long', assess_response(text,prompt='Kısaca anlat'))
        self.assertEqual(finalize_response(text,prompt='Kısaca anlat'), text.strip())

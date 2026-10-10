import unittest
from auto_learning import extract_owner_statement
from personal_context_focus import select_personal_context

class MemorySafetyTests(unittest.TestCase):
    def test_unlabelled_common_credentials_never_auto_learned(self):
        for value in ['sk-proj-'+'x'*24, 'ghp_'+'a'*30,
                      'AIza'+'a'*32, '-----BEGIN PRIVATE KEY-----',
                      'eyJabcdefghi.abcdefghijk.abcdefghijk']:
            self.assertIsNone(extract_owner_statement('Projem: '+value))
    def test_duplicate_case_space_and_final_punctuation(self):
        first = extract_owner_statement('Tercihim: Kısa cevaplar')
        second = extract_owner_statement('Tercihim:  kısa   cevaplar.')
        self.assertEqual(first[1], second[1])
    def test_newer_explicit_preference_wins_without_mutating_saved_rows(self):
        memories = [
            {'category':'PREFERENCE','key':'new','value':'Kısa Türkçe cevaplar'},
            {'category':'PREFERENCE','key':'old','value':'Detailed English replies'},
            {'category':'PROJECT','key':'project','value':'Architecture model'},
        ]
        before = repr(memories)
        result = select_personal_context(memories, [], 'English replies')
        self.assertIn('Kısa Türkçe', result)
        self.assertNotIn('Detailed English', result)
        self.assertIn('Architecture', result)
        self.assertEqual(repr(memories), before)
    def test_ambiguous_or_non_style_preferences_not_silently_resolved(self):
        from memory_safety import explicit_style_slots
        for value in ['Kısa cevap istemiyorum', 'Bazen kısa bazen detaylı cevap',
                      'English architecture books', 'Short and detailed replies',
                      'Kod için kısa cevaplar', 'Long replies only for architecture']:
            self.assertEqual(explicit_style_slots(value), {})

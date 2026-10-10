"""No-network contracts for owner reviewed chat-note preview and validation."""
import sys
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from conversation_notes import validate_note,_preview_text


class NoteUnitTests(unittest.TestCase):
    def test_reviewable_preview_is_excerpt_not_persistent_memory(self):
        rows=[
            {"role":"user","content":"2009 Mercedes bakımını konuşalım"},
            {"role":"assistant","content":"Bakım seçeneklerini gözden geçirelim"},
            {"role":"user","content":"Şifrem: very-secret"},
            {"role":"user","content":"Test maili user@example.com"},
            {"role":"assistant","content":"Mimarlık ödevini inceliyoruz"},
        ]
        result=_preview_text(rows)
        self.assertIn("Mercedes",result)
        self.assertIn("Mimarlık",result)
        self.assertNotIn("very-secret",result)
        self.assertNotIn("user@example.com",result)
        self.assertNotIn("Şifrem",result)
        self.assertLessEqual(len(result),3000)

    def test_invalid_control_character_and_length(self):
        self.assertEqual(validate_note({"title":" Düzenle ","body":" Maket "}),("Düzenle","Maket"))
        for data in [
            [],{},{"title":"Başlık","body":""},
            {"title":"","body":"İçerik"},
            {"title":"x"*141,"body":"not"},
            {"title":"başlık","body":"a"*3001},
            {"title":"abc\x00","body":"not"},
            {"title":"başlık","body":"not\x07"},
            {"title":3,"body":"not"},
        ]:
            with self.subTest(obj=str(data)[:35]),self.assertRaises(ValueError):
                validate_note(data)

    def test_notes_not_connected_to_model_context_or_unapproved_memory(self):
        content=(HERE/"conversation_notes.py").read_text(encoding="utf-8")
        app=(HERE/"app.py").read_text(encoding="utf-8")
        self.assertIn("register_conversation_note_routes(app)",app)
        self.assertIn('"saved":False',content)
        self.assertIn('"memory_saved":False',content)
        self.assertIn('user_id=$2',content)
        self.assertIn("WHERE id=$1 AND user_id=$2",content)
        start=app.index("async def _memory_context(")
        end=app.index("async def _recent_context(",start)
        self.assertNotIn("conversation_notes",app[start:end])
        self.assertNotIn("INSERT INTO memories",content)


if __name__=="__main__":
    unittest.main()

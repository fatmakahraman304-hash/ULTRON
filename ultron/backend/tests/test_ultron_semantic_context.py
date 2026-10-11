"""Long-term semantic retrieval must not treat ordinary dialogue as user facts."""
from app.memory.semantic_memory import SemanticMemory


class FakeMemory:
    def __init__(self, rows):
        self.rows = rows

    def recent(self, limit):
        return self.rows[:limit]


def test_current_user_message_is_not_repeated_as_a_long_term_fact():
    memory = FakeMemory([
        ("conversation", "USER: Sevdiğim kahve hangisi?", "2026-10-11"),
        ("PREFERENCE", "Sevdiğim kahve Türk kahvesi.", "2026-10-10"),
    ])
    retriever = SemanticMemory(memory)
    result = retriever.context("Sevdiğim kahve hangisi?")
    assert "[PREFERENCE]" in result
    assert "Türk kahvesi" in result
    assert "USER:" not in result


def test_explicit_search_can_still_find_conversation_history():
    memory = FakeMemory([
        ("conversation", "USER: Merhaba ULTRON", "2026-10-11"),
        ("FACT", "Araba modeli Mercedes", "2026-10-11"),
    ])
    hits = SemanticMemory(memory).search("Merhaba ULTRON", kinds=("conversation",))
    assert hits and hits[0][1] == "conversation"


def test_case_insensitive_kind_exclusion():
    rows = [("CONVERSATION", "USER: Bilgisayarım Lenovo", "2026-10-11"),
            ("DEVICE", "Bilgisayarım Lenovo LOQ", "2026-10-10")]
    text = SemanticMemory(FakeMemory(rows)).context("Bilgisayarım Lenovo")
    assert "[DEVICE]" in text
    assert "[CONVERSATION]" not in text

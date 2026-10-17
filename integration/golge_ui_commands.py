"""Exact, low-risk voice commands that must bypass model response latency."""
import re
import unicodedata


def is_stop_command(text: str) -> bool:
    value = unicodedata.normalize("NFD", str(text or "").casefold())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = value.replace("ı", "i").replace("’", "").replace("'", "")
    value = re.sub(r"[.!?,;:]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"^(?:golge)\s+", "", value)
    return value in {
        "dur", "sus", "kes", "konusmayi durdur", "konusmayi kes",
        "konusmayi sustur", "yaniti durdur", "cevabi durdur", "tts durdur",
    }

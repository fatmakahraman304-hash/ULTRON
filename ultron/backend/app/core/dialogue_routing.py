"""Conservative, deterministic model tier selection for live ULTRON dialogue.

Small talk may use an installed fast model, while code tasks go to the
coding model and substantive follow-ups retain the general model.
Unknown requests stay GENERAL; no remote service or model call is needed
to make this decision.
"""
import re

from app.core.model_router import TaskType


_CASUAL = frozenset({
    "selam", "merhaba", "günaydın", "iyi akşamlar",
    "nasılsın", "nasılsınız", "naber", "ne haber",
    "teşekkürler", "teşekkür ederim", "sağ ol", "sağ olun",
    "merhaba ultron", "selam ultron", "ultron merhaba", "ultron selam",
})

_CODE_RE = re.compile(
    r"(?<!\w)(?:python|javascript|typescript|react|git|github|"
    r"vscode|visual studio|terminal|powershell|kod|kodu|kodları|"
    r"kodlama|fonksiyon|derleme|programlama|pytest|bug|debug|"
    r"exception|traceback|api|endpoint|modül)(?!\w)",
    re.IGNORECASE,
)


def classify_dialogue(text: str) -> str:
    """Choose FAST only when no task/execution intent can be lost."""
    normalized = " ".join((text or "").strip().casefold().split())
    normalized = normalized.strip(" \t\n.,!?;:")
    if _CODE_RE.search(normalized):
        return TaskType.CODING
    if normalized in _CASUAL:
        return TaskType.FAST
    return TaskType.GENERAL

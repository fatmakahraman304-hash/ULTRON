"""Free read-only Qwen/Ollama chat serving a paired iPhone.

The request is from ULTRON Cloud's authenticated queue. Do not invoke the
Gemini Live session, desktop tool executor, shell, browser or approval gates.
Only requests to the local loopback Ollama API are made. The configured models
must already be installed; no automatic download or paid API fallback.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from ultron.backend.app.core.fast_brain import FastBrainPolicy, classify_text
from ultron.cloud_service.conversation_turns import ollama_messages, bounded_user_request
from ultron.cloud_service.response_quality import finalize_response, strip_qwen_thinking
from ultron.cloud_service.reply_policy import classify_reply_mode
from ultron.cloud_service.model_identity import is_qwen_model

_ROOT=Path(__file__).resolve().parents[1]
_SETTINGS=_ROOT/"ultron"/"backend"/"config"/"settings.json"
_OLLAMA="http://127.0.0.1:11434"
_MODELS_CACHE=(0.0, [])

# The remote mobile chat queue includes only text. There is no image,
# screenshot or attachment payload, so a blind vision model must not infer
# contents from a nonexistent picture.
_NO_IMAGE_REPLY_TR=(
    "Bu yerel sohbet bağlantısına görsel ulaşmadı; yalnızca metni "
    "görebiliyorum. Fotoğrafı veya ekran görüntüsünü görsel yüklemeyi "
    "destekleyen bir sohbet modunda gönderirsen inceleyebilirim."
)
_NO_IMAGE_REPLY_EN=(
    "This text-only chat hasn't received an image or screenshot. "
    "I can't inspect one without an actual attachment. "
    "Please use an image-capable chat mode to send it."
)
_ENGLISH_IMAGE_REQUEST=re.compile(
    r"\b(?:analy[sz]e|describe|inspect|read|look at)\s+"
    r"(?:this |the |my |an? )?(?:image|photo|picture|screenshot)\b"
    r"|\bwhat(?:'s| is) in (?:this|the|my) "
    r"(?:image|photo|picture|screenshot)\b",
    re.I,
)


_IMAGE_HOWTO=re.compile(
    r"^\s*(?:(?:bir|bu|şu)\s+)?"
    r"(?:fotoğrafı|resmi|görseli|ekran görüntüsünü)\s+"
    r"nasıl\s+(?:analiz|incele|oku|yorumla)|"
    r"^\s*how\s+(?:do|can|should)\s+i\b|"
    r"^\s*how\s+to\s+(?:analy[sz]e|inspect|describe|read)\s+"
    r"(?:an?\s+)?(?:image|photo|picture|screenshot)\b",
    re.I,
)


def _image_howto(text: str) -> bool:
    """A request to LEARN image analysis does not require an actual image."""
    return bool(_IMAGE_HOWTO.search(text))


def _text_only_image_request(text: str) -> bool:
    return not _image_howto(text) and (
        classify_text(text) == "VISION" or bool(
            _ENGLISH_IMAGE_REQUEST.search(text)
        )
    )


# Mentioning Python or React in a learning conversation is not an instruction
# to invoke the larger coding model. Explicit programming jobs still route to
# that model. This affects only the text-only local chat, not desktop tools.
_CONVERSATIONAL_TECH = re.compile(
    r"\b(?:öğreniyorum|öğrenmek|öğrenmeye|kurs(?:u)?|"
    r"nereden başlayayım|nasıl çalışmalıyım|"
    r"learning|learn|studying|beginner|getting started|"
    r"can you explain|what is)\b", re.I
)
_NO_CODE = re.compile(
    r"\b(?:kod yazma|kodu yazma|kod istemiyorum|"
    r"no code|do not write code|don't write code|"
    r"without (?:writing )?code)\b", re.I
)
_CODING_COMMAND = re.compile(
    r"\b(?:kod(?:u)? yaz(?:dır)?|örnek kod yaz|"
    r"script yaz|fonksiyon yaz|hata düzelt|"
    r"debug|refactor|implement|"
    r"write (?:some |a |the )?(?:code|script|function)|"
    r"fix (?:the |this )?(?:bug|code))\b", re.I
)
_CONTINUE_ONLY = re.compile(
    r"(?:kaldığın yerden devam et|aynı şekilde devam et|"
    r"devam et böyle|böyle devam et|devam et|devam|"
    r"continue like that|continue|keep going|go on)"
    r"(?:\s+(?:lütfen|lutfen|please))?[\s.!?]*",
    re.I,
)


def _last_substantive_owner_request(text: str, turns) -> str:
    """Only for a bare continuation; never interpret assistant/system as user.

    Already-scoped, recent history only. No additional DB/model call.
    """
    if not _CONTINUE_ONLY.fullmatch(text.strip()) or not isinstance(turns, list):
        return ""
    for turn in reversed(turns[-10:]):
        if not hasattr(turn, "get") or turn.get("role") != "user":
            continue
        prior = turn.get("content")
        if not isinstance(prior, str):
            continue
        prior = prior.strip()
        if prior and not _CONTINUE_ONLY.fullmatch(prior):
            return prior
    return ""


def _local_text_task(text: str, turns=None) -> str:
    # Keep the latest substantive coding/chat intent across a bare "continue".
    prior = _last_substantive_owner_request(text, turns)
    if prior:
        past_task = _local_text_task(prior)
        return "FAST" if past_task == "VISION" else past_task
    task = classify_text(text)
    if task == "CODING":
        if _NO_CODE.search(text) or (
            _CONVERSATIONAL_TECH.search(text) and
            not _CODING_COMMAND.search(text)
        ):
            return "FAST"
    return task


def _local_reply_mode(text: str, turns=None) -> str:
    """Preserve reply detail only for an explicit continuation of a user task."""
    prior = _last_substantive_owner_request(text, turns)
    return classify_reply_mode(prior if prior else text)


def _continuation_style_hint(text: str, turns=None) -> str:
    """Align the model's reply-length instruction with its token budget.

    The hint contains no previous user text and never promotes history to
    a system role. It is generated only for a bare, explicit continuation.
    """
    prior = _last_substantive_owner_request(text, turns)
    if not prior:
        return ""
    mode = classify_reply_mode(prior)
    if mode == "brief":
        return ("CONTINUATION REPLY LENGTH: The user requested a brief reply "
                "for this ongoing task. Continue concisely.")
    if mode == "detailed":
        return ("CONTINUATION REPLY LENGTH: The user requested a detailed "
                "explanation for this ongoing task. Continue with useful detail.")
    return ""


class LocalBrainUnavailable(RuntimeError):
    pass


def _get_json(path:str,payload:dict|None=None,*,timeout:float=8)->dict:
    if path not in ("/api/chat","/api/tags"):
        raise ValueError("non_local_ollama_path")
    req=urllib.request.Request(
        _OLLAMA+path,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload else None,
        method="POST" if payload else "GET",
        headers={"Content-Type":"application/json"},
    )
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            content=response.read(150_000)
            data=json.loads(content)
    except (urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
        raise LocalBrainUnavailable("Yerel Ollama yanıt vermiyor veya model çalıştırılamadı.") from exc
    if not isinstance(data,dict):
        raise LocalBrainUnavailable("Ollama yanıtı geçersiz.")
    return data


def installed_models()->list[str]:
    global _MODELS_CACHE
    stamp,models=_MODELS_CACHE
    if time.monotonic()-stamp<20 and models:
        return list(models)
    result=_get_json("/api/tags")
    names=[str(item.get("name")) for item in result.get("models",[])
           if isinstance(item,dict) and item.get("name")]
    _MODELS_CACHE=(time.monotonic(),names)
    return names


def local_chat_ready() -> bool:
    """Fresh loopback probe; online desktop or cached model names are not enough.

    This checks service/model availability, not successful future inference or
    available VRAM. No generation, warmup, download, tools or cloud requests.
    """
    try:
        result = _get_json("/api/tags", timeout=1.5)
        models = [item["name"] for item in result.get("models", [])
                  if isinstance(item, dict) and isinstance(item.get("name"), str)]
        chat_models = [name for name in models if is_qwen_model(name)]
        if not chat_models:
            # An installed LLaVA-only inventory is not a usable Qwen chat.
            return False
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))["llm"]
        policy = FastBrainPolicy(settings.get("fast_brain", {}))
        choice = policy.choose(task=classify_text("Merhaba"), installed=chat_models,
                               primary=settings.get("model", "qwen3:4b"))
        return choice.model in chat_models
    except (LocalBrainUnavailable, OSError, ValueError, TypeError, KeyError):
        return False


def local_chat(prompt:str,system:str,turns=None)->dict:
    text=bounded_user_request(prompt,3000)
    if not text:
        raise ValueError("empty_local_prompt")
    if _text_only_image_request(text):
        # The detection contains an English-only supplemental matcher;
        # ordinary Turkish and mixed voice commands keep a Turkish reply.
        language_english = bool(_ENGLISH_IMAGE_REQUEST.search(text))
        return {"reply":(_NO_IMAGE_REPLY_EN if language_english
                         else _NO_IMAGE_REPLY_TR),
                "model":"", "provider":"local-no-image"}
    settings=json.loads(_SETTINGS.read_text(encoding="utf-8"))["llm"]
    policy=FastBrainPolicy(settings.get("fast_brain",{}))
    models=installed_models()
    if not models:
        raise LocalBrainUnavailable("Ollama'da kurulu bir model bulunamadı.")
    chat_models=[name for name in models if is_qwen_model(name)]
    if not chat_models:
        # Never substitute a visual-only or unknown model for local Qwen chat.
        raise LocalBrainUnavailable("Yerel sohbet için kurulu Qwen modeli bulunamadı.")
    task=_local_text_task(text, turns)
    # A text-only how-to question about analysing images needs a language
    # model, not a vision-only model with no pixels supplied.
    if task == "VISION" and _image_howto(text):
        task = "FAST"
    choice=policy.choose(task=task,installed=chat_models,primary=settings.get("model","qwen3:4b"))
    if choice.model not in chat_models:
        raise LocalBrainUnavailable("Seçilen yerel model kurulu değil.")
    config=policy.runtime_options(choice.model,tools=False)
    # Conversational replies benefit from less deterministic sampling and enough
    # output tokens to finish a thought. Keep small-laptop bounds intact.
    runtime=dict(config.get("options") or {})
    mode=_local_reply_mode(text, turns)
    base=int(runtime.get("num_predict",192))
    # A negated "detaylı anlatma" is NOT a detailed-mode request.
    # Keep a lower output ceiling for explicit brief replies on the 4GB GPU.
    # These are safe maxima, not a claim about actual inference latency.
    if mode == "brief":
        runtime["num_predict"]=max(96,min(160,base))
    elif mode == "detailed":
        runtime["num_predict"]=min(420,max(base,360))
    else:
        runtime["num_predict"]=min(420,max(base,240))
    runtime["temperature"]=0.55
    runtime["top_p"]=0.9
    runtime["repeat_penalty"]=1.08
    config["options"]=runtime
    # The Cloud persona sees the bare "Devam et", so its generic reply-length
    # hint can otherwise contradict the model's inherited detailed/brief cap.
    # Preserve the original trusted system instructions intact: if it is
    # already at the wire limit, skip this optional hint rather than truncate.
    effective_system=str(system or "")
    style_hint=_continuation_style_hint(text, turns)
    if style_hint and len(effective_system)+len(style_hint)+1 <= 5400:
        effective_system += "\n" + style_hint
    # Ollama may finish slowly on CPU offload; Cloud worker renews the lease.
    # Keep the same prompt, model, privacy boundary and disabled-thinking
    # option for a bounded retry. Only a confirmed token-budget cutoff is
    # retryable: an interrupted/foreign-model response is never accepted.
    request={
        "model":choice.model,
        "messages":ollama_messages(effective_system, turns or [], text),
        **config,
    }
    result=_get_json("/api/chat",request,timeout=70)
    for attempt in range(2):
        # A malformed or interrupted Ollama response is not a successful answer.
        # Do not stringify arbitrary JSON as model-generated prose or trust
        # a reply labeled as an unexpected model.
        actual_model=result.get("model")
        if actual_model is not None and actual_model != choice.model:
            raise LocalBrainUnavailable("Ollama beklenmeyen modelden yanıt döndürdü.")
        if result.get("done") is False:
            raise LocalBrainUnavailable("Ollama tamamlanmamış yanıt döndürdü.")
        if result.get("done_reason") != "length":
            break
        # Ollama sets done=true for num_predict exhaustion, including short
        # user requests when the small first-pass budget runs out. Restart
        # inference at most once with a bounded larger token budget; do not
        # append the truncated model text to conversation history or report
        # a partial answer as completed.
        if attempt:
            raise LocalBrainUnavailable(
                "Yerel yanıt daha geniş uzunluk sınırında da kesildi; tamamlanmış sayılmadı."
            )
        expanded=min(768,max(512,int(runtime["num_predict"])*2))
        retry={**request,"options":{**runtime,"num_predict":expanded}}
        result=_get_json("/api/chat",retry,timeout=70)
    message=result.get("message")
    if not isinstance(message,dict) or not isinstance(message.get("content"),str):
        raise LocalBrainUnavailable("Ollama yanıtının metin biçimi geçersiz.")
    answer=strip_qwen_thinking(message["content"])
    if not answer:
        raise LocalBrainUnavailable(
            "Yerel model yalnızca tamamlanmamış düşünme metni döndürdü."
        )
    return {"reply":finalize_response(answer[:12000], prompt=text),"model":choice.model,"provider":"local-ollama"}

def local_listening_analysis(prompt: str, system: str, stage: str) -> dict:
    """Read-only Qwen summarization on the paired Windows computer.

    Caller-supplied speech is only untrusted text. This method cannot run
    tools, call cloud APIs, write files, or update memory.
    """
    if stage not in ("map", "reduce", "final"):
        raise ValueError("invalid_local_analysis_stage")
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 14500:
        raise ValueError("invalid_local_analysis_length")
    if not isinstance(system, str) or not 1 <= len(system) <= 2100:
        raise ValueError("invalid_local_analysis_system")
    installed = [name for name in installed_models() if is_qwen_model(name)]
    if not installed:
        raise LocalBrainUnavailable("Yerel analiz için kurulu Qwen modeli yok.")
    settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))["llm"]
    preferred = str(settings.get("model") or "qwen3:4b")
    selected = preferred if preferred in installed else (
        next((m for m in installed if m.startswith("qwen3:8b")), installed[0])
    )
    # Larger context than casual chat: 12k chars can be ~5k tokens.
    # This is bounded for consumer laptops, not a guarantee of speed.
    budgets = {"map": 700, "reduce": 750, "final": 1200}
    request = {
        "model": selected,
        "stream": False,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        "options": {"num_ctx": 8192, "num_predict": budgets[stage],
                    "temperature": 0.25, "top_p": 0.85},
    }
    result = _get_json("/api/chat", request, timeout=150)
    if result.get("model") not in (None, selected):
        raise LocalBrainUnavailable("Yerel analiz beklenmeyen Qwen modeli döndürdü.")
    if result.get("done") is False or result.get("done_reason") == "length":
        raise LocalBrainUnavailable("Qwen analizi tamamlanmadan kesildi.")
    message = result.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise LocalBrainUnavailable("Qwen analiz çıktısı geçersiz.")
    answer = strip_qwen_thinking(message["content"])
    if not answer:
        raise LocalBrainUnavailable("Qwen tamamlanmış analiz metni döndürmedi.")
    return {"analysis": answer[:9500], "model": selected, "provider": "local-ollama"}

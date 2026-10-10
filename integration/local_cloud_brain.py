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
from ultron.cloud_service.response_quality import finalize_response
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
    r"(?:devam et|devam|kaldığın yerden devam et|"
    r"aynı şekilde devam et|continue|keep going|go on)[\s.!?]*",
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
    # Ollama may finish slowly on CPU offload; Cloud worker renews the lease.
    result=_get_json("/api/chat",{
        "model":choice.model,
        "messages":ollama_messages(system, turns or [], text),
        **config,
    },timeout=70)
    answer=str((result.get("message") or {}).get("content") or "").strip()
    if not answer:
        raise LocalBrainUnavailable("Yerel model boş yanıt verdi.")
    return {"reply":finalize_response(answer[:12000], prompt=text),"model":choice.model,"provider":"local-ollama"}

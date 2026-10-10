"""Free read-only Qwen/Ollama chat serving a paired iPhone.

The request is from ULTRON Cloud's authenticated queue. Do not invoke the
Gemini Live session, desktop tool executor, shell, browser or approval gates.
Only requests to the local loopback Ollama API are made. The configured models
must already be installed; no automatic download or paid API fallback.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from ultron.backend.app.core.fast_brain import FastBrainPolicy, classify_text
from ultron.cloud_service.conversation_turns import ollama_messages

_ROOT=Path(__file__).resolve().parents[1]
_SETTINGS=_ROOT/"ultron"/"backend"/"config"/"settings.json"
_OLLAMA="http://127.0.0.1:11434"
_MODELS_CACHE=(0.0, [])


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


def local_chat(prompt:str,system:str,turns=None)->dict:
    text=str(prompt or "").strip()[:3000]
    if not text:
        raise ValueError("empty_local_prompt")
    settings=json.loads(_SETTINGS.read_text(encoding="utf-8"))["llm"]
    policy=FastBrainPolicy(settings.get("fast_brain",{}))
    models=installed_models()
    if not models:
        raise LocalBrainUnavailable("Ollama'da kurulu bir model bulunamadı.")
    task=classify_text(text)
    choice=policy.choose(task=task,installed=models,primary=settings.get("model","qwen3:4b"))
    if choice.model not in models:
        raise LocalBrainUnavailable("Seçilen yerel model kurulu değil.")
    config=policy.runtime_options(choice.model,tools=False)
    # Conversational replies benefit from less deterministic sampling and enough
    # output tokens to finish a thought. Keep small-laptop bounds intact.
    runtime=dict(config.get("options") or {})
    detailed=any(x in text.casefold() for x in
                 ("detaylı", "ayrıntılı", "adım adım", "uzun anlat",
                  "in detail", "step by step"))
    base=int(runtime.get("num_predict",192))
    runtime["num_predict"]=min(420,max(base,360 if detailed else 240))
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
    return {"reply":answer[:12000],"model":choice.model,"provider":"local-ollama"}

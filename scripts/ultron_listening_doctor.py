"""ULTRON listening release smoke: Windows-local real Ollama plus Render health.

This script performs ONE synthetic model request. It does not start the mic,
upload personal conversation data, touch credentials, or send remote commands.
It must be executed on the owner's paired Windows computer for real proof.
"""
from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"ultron/cloud_service"))

RESULTS=[]

def check(name,fn):
    start=time.monotonic()
    try:
        result=fn()
        print(f"[PASS] {name} ({time.monotonic()-start:.1f} saniye): {result}",flush=True)
        RESULTS.append((name,True))
    except Exception as exc:
        message=str(exc).splitlines()[0][:220]
        print(f"[FAIL] {name}: {type(exc).__name__}: {message}",flush=True)
        RESULTS.append((name,False))

def check_ollama_models():
    from integration.local_cloud_brain import installed_models,is_qwen_model
    models=[m for m in installed_models() if is_qwen_model(m)]
    if not models:
        raise RuntimeError("Ollama üzerinde Qwen modeli bulunamadı.")
    return ", ".join(models)

def check_real_qwen():
    from integration.local_cloud_brain import local_listening_analysis
    from ultron.cloud_service.listening_analysis import ANALYST_SYSTEM
    payload="KONUŞMA PARÇASI 1/1. Kullanıcı: Bugün evin planını çizdim. Sadece kısa bir karar özeti oluştur."
    result=local_listening_analysis(payload,ANALYST_SYSTEM,"map")
    if result.get("provider")!="local-ollama":
        raise RuntimeError("Doğrulanmış Qwen modeli yerine başka sağlayıcı döndü.")
    response=str(result.get("analysis") or "").strip()
    if len(response)<8:
        raise RuntimeError("Qwen kısa veya boş yanıt verdi.")
    return f"{result.get('model')} · {len(response)} karakterlik tamamlanmış yanıt"

def check_render():
    with urllib.request.urlopen("https://ultron-yubh.onrender.com/health",timeout=20) as response:
        if response.status!=200:
            raise RuntimeError("Bulut sunucusu HTTP "+str(response.status)+" döndürdü.")
        data=response.read(2048)
    return f"HTTP 200, {len(data)} byte yanıt"

def main():
    print("ULTRON · yerel Qwen dinleme kontrolü",flush=True)
    print("Uyarı: Bu kontrol gerçek iPhone mikrofonunu, Safari arka planını veya Render cihaz eşleşmesini sınamaz.",flush=True)
    print("Kişisel konuşma/şifre gönderilmez. Örnek metin sentetiktir.",flush=True)
    check("Ollama Qwen modelleri",check_ollama_models)
    check("Gerçek Qwen analiz yanıtı",check_real_qwen)
    check("Render sağlık adresi",check_render)
    passed=sum(ok for _,ok in RESULTS)
    print(f"\nSONUÇ: {passed}/{len(RESULTS)} kontrol başarılı",flush=True)
    if passed!=len(RESULTS):
        print("Sorunu gidermeden uzun konuşmayı gerçek cihazda doğrulanmış saymayın.",flush=True)
    return 0 if passed==len(RESULTS) else 1

if __name__=="__main__":
    raise SystemExit(main())

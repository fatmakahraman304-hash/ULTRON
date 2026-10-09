"""ULTRON FREE Fast Brain diagnostics for Windows and offline Linux.

Run at repo root:
    python scripts/ultron_fast_brain_doctor.py
    python scripts/ultron_fast_brain_doctor.py --benchmark

Uses localhost Ollama only, with zero API keys, no model downloads, no
model fabrication. Timing measures the actual local laptop when invoked there.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ultron" / "backend"))
from app.core.fast_brain import FastBrainPolicy

CONFIG = ROOT / "ultron" / "backend" / "config" / "settings.json"


def call_local(base: str, path: str, payload: dict | None = None, timeout: float = 8.0) -> dict:
    """No arbitrary endpoint, no bearer, no internet or cloud requests."""
    if base not in ("http://127.0.0.1:11434", "http://localhost:11434"):
        raise ValueError("Only localhost Ollama is supported by this doctor.")
    if path not in ("/api/tags", "/api/chat"):
        raise ValueError("Invalid Ollama diagnostic endpoint.")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    req = Request(base + path, method="POST" if body else "GET", data=body,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as res:
        data = json.loads(res.read(256_000))
    if not isinstance(data, dict):
        raise ValueError("Unexpected Ollama payload")
    return data


def report(*, benchmark=False, base="http://127.0.0.1:11434") -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))["llm"]
    policy = FastBrainPolicy(cfg.get("fast_brain", {}))
    try:
        models = call_local(base, "/api/tags")
    except (URLError, HTTPError, TimeoutError, ValueError, OSError) as exc:
        print("FAIL Ollama localhost yanıt vermiyor:", type(exc).__name__)
        print("Öneri: Ollama'yı başlat ve bu komutu yeniden çalıştır.")
        return 2
    installed = [str(row.get("name")) for row in models.get("models", [])
                 if isinstance(row, dict) and row.get("name")]
    print("ULTRON FAST BRAIN • ücretsiz yerel model kontrolü")
    print("Ollama:", "ÇALIŞIYOR")
    print("Kurulu:", ", ".join(installed) if installed else "Henüz model yüklü değil")
    chosen = {}
    for task, label in (
        ("FAST", "KONUŞMA"), ("GENERAL", "ZOR SORULAR"),
        ("CODING", "KODLAMA"), ("VISION", "GÖRSEL"),
    ):
        choice = policy.choose(task=task, installed=installed, primary=cfg["model"])
        chosen[task] = choice.model
        ok = choice.model in installed
        print(f"{label}: {choice.model} — " +
              ("KURULU" if ok else "KURULU DEĞİL; YENİ MODEL OTOMATİK İNDİRİLMEZ"))
    if not installed:
        print("Öneri: ollama pull qwen3:4b")
        return 1
    if "qwen3.5:4b" not in installed:
        print("İSTEĞE BAĞLI: Daha yeni 4B model için ollama pull qwen3.5:4b")
        print("RTX 2050 / 4 GB VRAM'de gerçek hız cihazına ve RAM kullanımına bağlı.")
    if not benchmark:
        print("Gerçek gecikmeyi ölçmek için --benchmark ile yeniden çalıştır.")
        return 0
    for task in ("FAST", "CODING"):
        model = chosen[task]
        if model not in installed:
            continue
        options = policy.runtime_options(model)
        options["options"]["num_predict"] = 55
        prompt = ("Kıbrıs hakkında tek cümle Türkçe bilgi ver."
                  if task == "FAST" else
                  "Python'da iki sayıyı toplayan fonksiyonu tek satırla yaz.")
        now = time.perf_counter()
        try:
            response = call_local(base, "/api/chat", {
                "model": model, "messages": [
                    {"role": "system", "content": "Sen ULTRON'sun. Türkçe ve doğru cevap ver."},
                    {"role": "user", "content": prompt},
                ], **options,
            }, timeout=90)
            content = ((response.get("message") or {}).get("content") or "").strip()
            seconds = time.perf_counter() - now
            if not content:
                print("WARN", task, "model boş içerik döndürdü.")
                continue
            print(f"PASS {task}: {model} • {seconds:.2f} saniye (test tek sorgu; gerçek konuşma farklı olabilir)")
            print("  Yanıt:", content[:160].replace("\n", " "))
        except (URLError, HTTPError, TimeoutError, ValueError, OSError) as exc:
            print("WARN", task, model, "benchmark başarısız:", type(exc).__name__)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true", help="Mevcut iki yerel modele gerçek kısa sorgu gönder")
    args = parser.parse_args()
    raise SystemExit(report(benchmark=args.benchmark))

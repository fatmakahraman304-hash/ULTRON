# ULTRON — Hızlı Başlangıç

## İlk Kurulum (bir kere yapılır)

```
scripts\install_windows.bat
```

Bu script:
1. Python sanal ortamı oluşturur (`.venv`)
2. Tüm Python bağımlılıklarını kurar
3. Frontend (React) bağımlılıklarını kurar
4. Ollama'yı kontrol eder, eksik modelleri indirir
5. Güvenlik kurallarını mühürler
6. Sağlık taraması yapar

**Gereksinimler:**
- Python 3.11+ → https://python.org
- Node.js LTS → https://nodejs.org
- Ollama → https://ollama.com
- (Opsiyonel) Tesseract OCR → https://github.com/UB-Mannheim/tesseract/wiki
- (Opsiyonel) eSpeak-ng → https://github.com/espeak-ng/espeak-ng/releases
- (Opsiyonel) Piper TTS → https://github.com/rhasspy/piper/releases

---

## Her Gün Kullanım

Sadece çift tıkla:

```
ULTRON.bat
```

Tarayıcı otomatik açılır → `http://127.0.0.1:5173`

---

## Ollama Modelleri

```bash
# Zorunlu (ana model)
ollama pull qwen2.5-coder:7b

# Vision (ekran analizi için)
ollama pull llava:7b

# Hızlı model (basit sorular)
ollama pull qwen3:4b
```

---

## Ses Desteği

### Türkçe TTS (Piper)
1. https://github.com/rhasspy/piper/releases adresinden `piper_windows_amd64.zip` indir
2. `backend/data/voice/piper/` klasörüne çıkar
3. Türkçe model: `tr_TR-fahrettin-medium.onnx` indir, aynı klasöre koy

### STT (Konuşma tanıma)
```bash
pip install faster-whisper sounddevice soundfile
```

---

## Yapılan Düzeltmeler (v19)

| # | Dosya | Sorun | Düzeltme |
|---|-------|-------|----------|
| 1 | `app/voice/wake.py` | Porcupine hata mesajı yanlış sırada | `status()` öncelik sırası düzeltildi |
| 2 | `app/memory/store_v3.py` | SQLite WAL bypass (read-only sessizce geçiyordu) | `stat` bazlı `_is_read_only()` kontrolü |
| 3 | `app/events/bus.py` | Aynı WAL bypass sorunu | Aynı düzeltme |
| 4 | `app/core/runtime.py` | Tek bir bileşen crash → tüm sistem duruyordu | Her bileşen ayrı `try/except`, null-safe |
| 5 | `app/automation/gui.py` | `gui_click` vb. standalone fonksiyonlar yoktu | Module-level wrapper'lar eklendi |
| 6 | `app/skills/__init__.py` | `SkillEngine` adı yok, `SkillRunner` var | Import ve args düzeltildi |
| 7 | `app/connectors/__init__.py` | `ConnectorError` eksikti | Eklendi |
| 8 | `health.py` | None-safe değildi, crash edebiliyordu | Sıfırdan None-safe yazıldı |
| 9 | `ULTRON.bat` | Yoktu | Backend sağlık bekleyerek tek tıkla başlatıcı |
| 10 | `scripts/install_windows.bat` | Hata yönetimi zayıftı | Adım adım doğrulama ile yeniden yazıldı |

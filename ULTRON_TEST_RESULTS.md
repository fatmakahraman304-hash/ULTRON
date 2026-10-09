# ULTRON — Gerçek Test Kayıtları

## 2026-10-09
**Başlangıç HEAD:** `0638b116c30d221f4167a4df35381a5697237668`.  
**Son kod/CI referansı:** `34b80e43abe023e58a8f65c87688aa104d6d55e7`.

### GitHub Actions: PASS
- Workflow: `ULTRON Scene Build Check`
- Run: `37893780863`
- GitHub commit: `a010726149f7a1352933a2e45af51f9b1a985662`
- Görülen başarılı adımlar:
  - Python 3.12 değişen kaynakların `py_compile` kontrolü.
  - `test_earth_watch_config.py` saf backend state regresyonları.
  - `test_ultron_dev_resume.py` read-only devam raporu regresyonları.
  - `python scripts/ultron_dev_resume.py --json`.
  - `npm ci`, `tsc --noEmit`, Vite üretim derlemesi.
  - `npm run test:earth`: geospatial, input wrapping, equinox/solstice ve UTC güneş testleri.
- Önceki kod HEAD `7f89ba130485536fa6e655ef942a782a39b44632`: `ULTRON Scene Build Check` PASS.

### Çalıştırılmamış / dış ortam bağımlı
- Windows 11 cihazında `START.bat` ve gerçek masaüstü UI etkileşim smoke testi: **NOT RUN**.
- RTX 2050 üzerinde FPS/VRAM benchmark: **NOT RUN**.
- Gerçek mikrofon, hoparlör, wake-word ve Gemini Live/Cloud uçtan uca: **NOT RUN**.
- Gerçek ISS API erişimi: **NOT RUN** (hata durumunda UI fallback kodlandı).
- Tüm Python pytest suite: **NOT RUN**.
- Render deployment SHA doğrulaması: **NOT CHECKED**.
- Testler derleme ve saf mantık sözleşmesini doğrular; gerçek cihazdaki başarının yerine geçmez.

## Sonraki turda
Yeni testler/CI sonuçları için run ID ve tam commit SHA yaz. Olmayan testi PASS gösterme.

### Cloud task queue regresyonu — PASS
- Workflow: `ULTRON Scene Build Check`, run `37894840971`.
- Kod HEAD: `34b80e43abe023e58a8f65c87688aa104d6d55e7`.
- `python -m unittest discover -s ultron/cloud_service -p 'test_device_queue_contract.py' -v`: **6 tests PASS** (`Ran 6 tests in 0.135s, OK`).
- Senaryolar: parallel claim, direction guard, late duplicate completion, inactive command statuses, retry limit, SQL atomic status checks.
- Aynı run: Python syntax, Earth backend, resume tests, Node/npm install, TypeScript/Vite build, Earth math test: PASS.
- Hatalı test harness ilk aşamalar: `37894708692` (source path) ve `37894774521` (fake aiohttp exception constructor) FAILED; düzeltildi.
- **Kapsam sınırı:** AST-extracted gerçek handler fonksiyonları fake DB ile çalıştırıldı; gerçek PostgreSQL advisory lock semantiği, Render deploy, telefon-laptop runtime ve Windows smoke **NOT RUN**.


### 2026-10-09 — Cloud attempt fencing: verified PASS
- **Final code SHA:** `9d577a993f78aa7393c83c22b52c83d5c7d7dfac`.
- **Scene Build Check:** `37897505788` — **PASS**.
  - Python syntax/py_compile: Cloud app, laptop `mark_app.py`, `cloud_client.py`, Earth/backend.
  - `test_earth_watch_config.py`: **5 PASS**.
  - `test_device_queue_contract.py`: **14 PASS**.
  - `test_ultron_dev_resume.py`: **3 PASS**.
  - Frontend TypeScript/Vite production build: **PASS**.
  - Earth geographic regression: **6 PASS**.
- **Cloud Queue PostgreSQL Integration:** `37897505793` — **PASS**, **4 tests** on disposable PostgreSQL 16 service.
  - Parallel claim single-agent lane; retry/reclaim increments fencing generation.
  - Old worker cannot complete a new delivery; current worker can.
  - Old worker cannot renew lease or write progress/checkpoint.
  - Legacy one-shot wake completion remains accepted.
- **Fixed failures honestly recorded:** early integration CI `37897241297` failed due to SQL `$3` type ambiguity plus raw JSONB response; `37897368506` failed due to test-side JSONB string parsing. Both corrected before final PASS.
- **Limitations:** Real Render production deployment/phone/Windows/RTX microphone/Gemini Live end-to-end **NOT RUN**. Disposable real PostgreSQL is not a production deployment test. Cloud callback fencing does not prove exactly-once local tool side effects.

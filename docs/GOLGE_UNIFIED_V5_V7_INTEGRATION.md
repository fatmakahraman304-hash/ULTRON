# GÖLGE — birleşik V5 arayüz + V7 otonom mühendislik adayı

Tarih: 15 Ekim 2026. DURUM: **ENTEGRE EDİLMEK ÜZERE HAZIRLANMIŞ TASLAK**. Canlı Render sürümü değildir.

## Kaynak ve sürüm kökeni

- Üretim ortak tabanı: `6ef3f5d207fc9430cbbd552988935995529e87f5` (`feat/ultron-cloud-shared-memory`).
- GÖLGE V5 arayüzü: `e0d5458800117dba3cd15b8df73c35206e932c0b` (PR #44).
- Otonom mühendis V7: `ae4f515ccd01a359b3be34cf7d08d82bc84d3cc4` (PR #46; V4/V5/V6 geçmişini içerir).
- Birleşik commit'in iki ebeveyni V7 ve V5 UI'dır. Her iki geliştirme hattının geçmişini korur.
- Dört çakışan ilerleme dosyasında V7'deki güncel sürümler korunmuştur: ULTRON_NEXT_TASKS.md, ULTRON_PROGRESS.md, ULTRON_ROADMAP.md, ULTRON_TEST_RESULTS.md. V5 arayüz kanıtları `docs/ui-v5/` ve `docs/GOLGE_V5_VISUAL_REVIEW.md` içindedir. Eski V5 günlükleri bu dört dosyada V7 kayıtlarının üzerine yazılmamıştır.

## Tek ürün, farklı yürütme ortamları

- **Windows masaüstü**: `START.bat` ve yerel backend; cihaz izinleri, Ollama/Qwen, mikrofon, ekran ve bilgisayar araçları.
- **Render Cloud ve telefon PWA**: `ultron/cloud_service/`; kullanıcı hesabına bağlı hafıza ve konuşma, onaylı uzaktan cihaz kuyruğu. Bilgisayar çevrimdışıyken uzaktan masaüstü komutu çalışmış gibi gösterilmez.
- **Tek arayüz / kontrol merkezi**: `ultron/frontend/` içerisindeki V5 sohbet ve 3D CORE; yerel backend ile mevcut HTTP/WebSocket sözleşmelerini kullanır.
- **V7 kod geliştirme**: `scripts/golge_autodev/`; izole doğrulama ve taslak PR adımları. Kendiliğinden kodu production'a merge etmez, Render'ı deploy etmez.

## Entegrasyon kabul sınırları

Bu commit kaynakları birleştirir; tek başına fiziksel cihazda çalışan uçtan uca sistemi KANITLAMAZ.

1. Birleşik SHA'da yeni Unified Integration Gate ve mevcut responsive/cloud/scene/autodev kontrolleri başarılı olmalı. Test geçmeden birleştirme yapılmamalı.
2. Windows cihazında: GÖLGE başlangıcı, Qwen konuşma, wake/STT/TTS, ekran algılama, onaylı dosya/tarayıcı işlemi, geri alma ve bir örnek kod-onarım→test→taslak PR zinciri gerçek donanımda çalıştırılıp kaydedilmeli.
3. iPhone'da: PWA giriş→sohbet→ortak hafıza→Cloud kuyruk→Windows yerel ajan→sonuç akışı, çevrimdışı hata durumları ve mikrofon sahipliği doğrulanmalı.
4. V7 Qwen3 8B son bağımsız canlı ölçüm **5/8 (%62,5)**, önceki `ae4f515ccd01a359b3be34cf7d08d82bc84d3cc4` öncesindeki head'e aittir; güncel V7 ölçümü henüz yok. Test model kalitesini kanıtlamadan hazır/başarılı denmemeli.
5. Render'da uygulama canlı sürümü `6ef3f5d207fc9430cbbd552988935995529e87f5` idi. Yalnızca başarılı kapılar ve kullanıcı incelemesinden sonra üretim dalına birleştirilir; otomatik deploy sonrası Render `/health`, yayımlanan SHA ve günlükler yeniden doğrulanır.

## Kırmızı çizgiler

Onay kapıları, günlükleme, yetki sınırları, gizli anahtarların korunması, provider bütçe kapıları ve offline/UNAVAILABLE durumları korunur. Otomatik paid model isteği, veri silme, otomatik merge ve production deploy bu entegrasyon işleminden yapılmaz.

## Windows startup regression — 16 Ekim 2026

Owner Windows device evidence: the first V5/V7 launch built the frontend successfully and copied seven Cloud memory records, but fell back to offline desktop because `ultron/backend/merged_api.py` could not import `ultron.cloud_service.conversation_persona` (ModuleNotFoundError: ultron). Bootstrap exported only the backend folder to PYTHONPATH; child process CWD is `ultron/backend`.

Draft fix `fix/golge-unified-windows-pythonpath-20261016`: include **both repository root and backend path** in Windows bootstrap and in `integration.launcher.Services.start` child environment, preserving inherited PYTHONPATH. Test `python -m unittest discover -s tests -p 'test_launcher_pythonpath.py' -v`. On Windows, then validate `START.bat` with PYTHONPATH unset, verify backend `/api/merged/health`, and test a real Qwen chat. Passing CI is not evidence of physical Windows audio or Render production deployment.

## Windows desktop memory-name collision (same owner diagnosis)

After backend health passed (`ULTRON hazır; masaüstü açılıyor`), the desktop child exited: `ModuleNotFoundError: No module named 'memory.memory_manager'; 'memory' is not a package`. This is a distinct import namespace from the backend problem: backend has `ultron/backend/memory.py` while the native UI uses root `memory/memory_manager.py` and `memory/config_manager.py`. Both are named top-level `memory`.

The launcher must provide different search order to subprocesses: backend `[BACKEND, ROOT]` and native desktop `[ROOT, BACKEND]`, preserving non-GÖLGE inherited paths. In `mark_app.py`, explicitly import the native memory package before Qt UI to avoid accidentally caching the homonymous backend module. CI tests cover both real import paths in subprocesses, import priority, and UI import order. Windows audio/Qt actual launch remains to be confirmed by the owner.

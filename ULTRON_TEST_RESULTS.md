# ULTRON — Gerçek Test Kayıtları

## 2026-10-09
**Başlangıç HEAD:** `0638b116c30d221f4167a4df35381a5697237668`.  
**Son kod/CI referansı:** `afe9f5b6855fc4742e384a4d298b71ee6c6feb18`.

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


### 2026-10-09 — Desktop Cloud ownership loss + stale worker guard: VERIFIED CI PASS
- **Kod commit:** `d96638e1ecaad7d0b800e20fb22580ade555e777`.
- **Workflow:** `ULTRON Scene Build Check`, run `37914696238` — **SUCCESS**.
- Python `py_compile` (backend/Cloud/client/mark_app): **PASS**.
- `test_earth_watch_config.py`: **5 PASS**.
- `test_cloud_delivery_guard.py`: **10 PASS** (6 RemoteLeaseGuard davranışı + 4 CloudClient HTTP sınıflaması).
- `test_device_queue_contract.py`: **14 PASS**.
- `test_ultron_dev_resume.py`: **3 PASS**.
- `npm run build`: **PASS** (Vite 3.28s); `npm run test:earth`: CI step **PASS**.
- **NOT RUN:** gerçek Windows üzerinde `START.bat`, Gemini Live sesli agent ve telefon görev uçtan uca testi; Render deploy SHA ve kullanıcı hesabı; gerçek enjekte edilmiş ağ kopmasıyla side-effect kontrolü.
- **Gerçek kapsam:** Cloud HTTP status handling ve lease monitor unit/regression testleri; `mark_app.py` import/syntax ve CI bağlantısı. Gerçek harici tool side-effect exactly-once **kanıtlanmadı**.


### 2026-10-09 — Durable desktop dispatch fence (CI SUCCESS)
- Yeni `cloud_dispatch_journal.py` ve `test_cloud_dispatch_journal.py`, `mark_app.py` entegrasyonu ve Scene CI adımı eklendi.
- `ULTRON Scene Build Check` run `37915768918` **SUCCESS** @ kod SHA `afe9f5b6855fc4742e384a4d298b71ee6c6feb18`; GitHub Actions job `verify` SUCCESS. Gerçek Windows/Cloud/Gemini Live E2E **NOT RUN**.
- Doğrulanması gereken: ilk claim, yeniden claim, restart, corrupt DB fail-close, concurrency, plaintext gizliliği, pre-dispatch wiring ve Approval Gate etkilenmemesi.

- **CI logları:** 11 durable dispatch journal testi PASS (first/duplicate/restart/changed-payload/different command/scope, no plaintext, invalid/corrupt fail-closed, concurrent reserve, pre-dispatch wiring). Diğer saf Python test grupları: 10 lease, 14 Cloud contract, 5 Earth backend, 3 resume = toplam 43 PASS. Python compile ve frontend TypeScript/Vite production build PASS; Earth math test step PASS.
- **Bilinen sınır:** `RemoteDispatchJournal` aynı yerel sqlite'ı paylaşan masaüstü komutları için at-most-once Gemini dispatch sağlar. Tool-level exactly-once, Cloud-prod deploy/Windows/telefon gerçek cihaz doğrulaması değildir; crash sonucu belirsiz görevleri manuel kontrol gerektirir.


### 2026-10-09 — Native iPhone Siri task / iOS Bridge (CI PENDING)
- Native XcodeGen/iOS Simulator/unsigned device derleme sonucu henüz doğrulanmadı; gerçek iPhone Siri, kilit ekranı, Cloud-login, Kestirmeler ve Windows laptop uçtan uca **NOT RUN**.


### Native iPhone v0.3 — CI PASS (2026-10-09)
- Kod commit: `0b4751a5d7c5f6ceb4642af4eb413f6fb0ca16b9`.
- Native iOS Build: [GitHub Actions 37917812910](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37917812910), **SUCCESS**.
- Yeni Siri/Shortcuts native sözleşme testleri: **5 PASS** (authenticated desktop queue, explicit user tap/allowlist, handled WS events, bounded Siri HTTP/status route, Keychain storage).
- XcodeGen: **PASS**; iOS Simulator compile: **BUILD SUCCEEDED**; unsigned iPhone compile: **BUILD SUCCEEDED**; unsigned IPA 178K ve Xcode project zip artifacts: **upload PASS**.
- Önceki hata açık kaydı: iOS 18 deployment'da kullanılamayan `IntentModes` (iOS 26+) compile ERROR; `openAppWhenRun = false` iOS18-uyumlu yöntemle düzeltildi ve PASS alındı.
- Bu statik kontrat testleri runtime Siri, locked-screen/Apple Shortcuts ve gerçek cihaz onaylarının doğru çalıştığını kanıtlamaz; gerçek iPhone/Windows/Render/prod deployment **NOT RUN**. İmzasız IPA cihaza doğrudan kurulamaz.


### 2026-10-09 — TestFlight workflow (implementation only, NOT PUBLISHED)
- `.github/workflows/ios-testflight.yml`: opt-in manual-only protected environment; Apple certificate import, provisioning profile download, signed iPhone archive/export, TestFlight upload; ULTRON SVG source to AppIcon render.
- `ios/ULTRONMobile/tests/test_testflight_release_contract.py`: 4 static checks; `Native iOS Build` CI result pending.
- Apple Developer membership, certificates, App Store Connect app record/API key, TestFlight publication/invitation, real device install: **NOT RUN**.


### 2026-10-09 — TestFlight hazırlığı native CI doğrulandı
- TestFlight yayın hattı `.github/workflows/ios-testflight.yml` **yalnız elle** ve **sadece main** dalından çalışır; protected `testflight` environment ve Apple signing secrets/variables şarttır. Apple'a yükleme bu ortamda **NOT RUN**.
- Kod SHA `076e9962959c7ce091dec440d2ec1a54673f4d10` için [Native iOS Build run 37919528795](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37919528795): **SUCCESS**. Native iOS regresyon/sözleşme testleri, Simulator build, unsigned iPhone build, unsigned IPA ve Xcode projesi artifacts başarılı. Bu *imzalı TestFlight IPA* veya gerçek cihaz doğrulaması değildir.
- Apple Developer Program üyelik, App Store Connect app record, distribution certificate .p12, provisioning profile ve p8 App Store API key henüz sağlanmadı; gerçek TestFlight upload, processing, invitation veya kablosuz kurulum yapılmadı.

## 2026-10-09 — Ücretsiz iPhone PWA komut onayı ve canlı görev göstergesi (CI PASS)
- iPhone ana ekrana eklenen ücretsiz Cloud PWA geliştirildi; ücretli TestFlight gerektirmez. `static/mobile-action-guard.js`: yalnız `ULTRON Bridge` ve `set_focus`, `set_volume`, `set_brightness`, `bluetooth`, `wifi`, `compose_message` allowlist'i; URL/JSON manipülasyonu, keyfi shortcut isimleri ve bilinmeyen eylemler engelleniyor.
- `static/index.html`: Cloud Live'dan gelen `ios_action`/`ios_shortcut` komutları artık otomatik URL açmak yerine iPhone üzerinde `KESTİRMELERİ AÇ / VAZGEÇ` onay ekranını bekler. İkinci komut önceki onayı sessizce değiştirmez. `UZAKTAN` sekmesinde Cloud queue'daki aktif laptop görev badge'i ve kuyruk/çalışıyor/başarısız özetleri var.
- `static/sw.js`: offline shell `ultron-shell-v37`, guard script precache ve HTTP error response caching engeli. Mikrofon/Gemini Live, laptop Approval Gate ve Cloud queue koruması değiştirilmedi.
- Test dosyası `ultron/cloud_service/test_mobile_action_guard.cjs`: 8 gerçek Node test (komut parse/allowlist, unsafe bypass, onay bileşeni, inline JS sözdizimi, badge), `.github/workflows/scene-check.yml` adımlarına eklendi.
- **Gerçek CI:** Kod SHA `dd839dd5bdf1ee5ff93ad066d57eacc26d380917`; Scene build [37922721093](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37922721093) **SUCCESS** (8 PWA Node PASS, diğer backend/Cloud regresyonları, TS/Vite build ve Earth tests); gerçek PostgreSQL [37922721027](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37922721027) **SUCCESS**.
- **Henüz doğrulanmadı:** Render üretim SHA ve otomatik deploy, iPhone Safari ana ekran PWA UI testi, kilit ekranı/bildirim arka plan davranışı. Browser PWA iOS sandbox'ı aşmaz, kapalı uygulamada 7/24 mikrofon veya APNs push vaat edilmez. Yeni özellikler Render'ın bu branch'i deploy etmesiyle görünür.

## 2026-10-09 — CORE küçük animasyon + ULTRON WORLD (kod ve canlı kaynaklar doğrulandı)
- CORE içi animasyon: kuş / yörünge / nabız presetleri, React/CSS boyuta duyarlı panel, oynat/duraklat/kapat; animation_show backend + stage tool + Türkçe metin komutları. Rastgele Python/Pygame çıktısı henüz otomatik gömülmüyor.
- Yerel frontend ve masaüstü backend CORE animasyon aşaması: SHA cfacb7355b87af174182b37b635152bd2c204729, frontend build 37925291261 SUCCESS, Scene build 37925291379 SUCCESS.
- WORLD: iPhone ana ekran PWA DÜNYA sekmesi ve Windows CenterStage içi world_map modu; Leaflet OSM sokak haritası (zoom 19 ve atıf), Three.js WebGL küre, adres/koordinat arama, favoris, izinli geolocation.
- Gerçek REST sağlayıcıları: Open-Meteo / MET Norway (Render IP Open-Meteo 429 olduğunda resmî MET Norway tahmin yedeği), adsb.lol / adsb.fi v3 (ADS-B uçak konumu), USGS depremler, Open-Meteo Air Quality, Photon OSM geocoding. Kısa süreli bounded cache, sabit upstream URL, açık kaynak atfı, 502 durumunda sahte veri üretmeme.
- Uydu, Street View, trafik, yağış radarı, rüzgâr, gemiler işaretli harici servis bağlantılarıdır; ULTRON içinde native entegre canlı veri katmanı gibi sunulmaz. 3D her evin detaylı fotogrametrik modeli değildir.
- SHA 5c0b8781f0303ae8351dc772d9df3dbcee57f6f9: Scene build 37927499485 SUCCESS, PostgreSQL 37927499348 SUCCESS, public production WORLD live smoke 37927499312 SUCCESS. 5/5 gerçek API kategorisi JSON kaynak doğrulama PASS (hava MET Norway, uçak adsb.lol, AQI Open-Meteo, deprem USGS, Photon adres). Sağlayıcı erişimi değişebilir.
- Render autoDeploy yes, feat/ultron-cloud-shared-memory dalı. Son live SHA ayrıca Render panelinden doğrulanmalı. Windows bilgisayarda git pull/START.bat gerekir.
- NOT RUN: gerçek iPhone Safari WORLD 2D/3D görsel ve harici harita tile/CDN testi; Windows Qt içinde CORE animasyon fiziksel testi; keyfi Pygame animasyonu gömme, harici trafik/uydu/gemi native katmanları.

### ULTRON WORLD sesli ve yazılı telefon komutları — 2026-10-09
- PWA index.html worldVoiceIntent: kullanıcı tarafından konuşulan/yazılan Dünya, 2D/3D, Gazimağusa, Lefkoşa, Kıbrıs, İstanbul, uçaklar/deprem/hava durumu görüntüle komutlarını DÜNYA sekmesine iletir. Harita iframe'i yalnız aynı origin ve kendi parent kaynağının postMessage komutlarını; tip, koordinat, mod ve katman allowlist guard'ını geçirse işler. Lazy-load sırasında en fazla dört komut bekletilir. Sesli sohbet motoru/Gemini reply Cloud oturumuyla devam eder.
- Cache PWA v40. Sesli komut güvenliği ve WORLD sözleşme testleri Scene Build Check 37928165355 SUCCESS; Cloud PostgreSQL 37928165548 SUCCESS. Kod SHA b473a4bfd28835aefae0472fb07a15442e7e383f. Önceki 37928109729 Scene FAIL sebebi test regex'i; düzeltme sonrası PASS. Üretim WORLD real-provider smoke 37928109603 SUCCESS (bu smoke bir önceki sesli komut kodunun commit'inde tetiklendi; sesli komut cihaz testi değildir).
- NOT RUN: fiziksel iPhone Safari PWA sesli komut → iframe görsel etkileşim, WebGL/CDN texture, Windows Qt CORE. Render AutoDeploy canlı HEAD ayrıca doğrulanmalı.

## 2026-10-09 — Original MARK-LV native video engine restored INSIDE ULTRON CORE
- Investigation of actual original MARK files actions/video_player.py and ui.py: the player was a QMediaPlayer with a QGraphicsVideoItem mounted in the avatar/camera/video stack. It supports local files, HTTP direct media, optional yt-dlp YouTube resolution with separate synchronized audio/video, initially muted sound, stop/mute. The merged integration/web_panel.py had MOVED _video_cont to a separate QDialog (user's pop-out regression).
- New integration/video_dock.py MarkVideoDock reparents the SAME original _video_cont into the actual QWebEngineView. It positions the native QWidget according to .reactor-panel .center-stage DOM bounds, scaled by viewport, clamped so as not to cover surrounding telemetry/chat. Rechecks while open and calls Qt _fit_video on size changes. No new QMediaPlayer engine or video_dialog is created.
- integration/web_panel.py NativeBridge.videoRequest forwards explicit typed video commands to actions.video_player, and MARK native voice tools continue using old video_player directly. React Dashboard.tsx adds deterministic typed media routing irrespective of chosen model; CORE adds MARK VIDEO native-only button. Unknown or source-less voice 'video oynat' asks Qt native file picker (instead of generating a fabricated animation). Preset CORE bird/orbit/pulse animations remain separate.
- ui.py now retains native/QGraphicsVideoItem support after reparenting, QMediaPlayer pause/resume signal & button, correct sound output selection for mic protection, auto-closes the dock after EndOfMedia/decoder failure rather than leaving a black box. Opening a different clip cancels stale asynchronous YouTube requests.
- Headless GUI smoke scripts/tests/test_mark_video_dock_qt.py explicitly instantiated real PyQt6 QMediaPlayer, QGraphicsVideoItem, QAudioOutput, and verified QWidget signals/placement/resizing; 5 tests PASS with QT_QPA_PLATFORM=offscreen and Ubuntu EGL/PulseAudio dependencies. Pure geometry/plugin/contract tests scripts/tests/test_mark_video_dock.py 12 PASS.
- Exact tested code SHA 54a2f2408c54385fc53bc69f7cf944a7a22b1637, GitHub Actions Scene Build Check https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931870709 SUCCESS. Prior frontend build https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931231558 SUCCESS (no frontend changes since).
- Honest NOT RUN: real Windows GPU/QtWebEngine+QGraphicsVideoItem rendered video frame screenshot, real MP4 decoder and split audio through Windows speakers, live YouTube (yt-dlp/network), complete desktop voice Gemini route. The CI Qt smoke verifies Qt object creation and QWidget behavior, not actual codec playback on a Windows PC.
- This is a Windows-native MARK feature in a GitHub branch; Render is the Cloud Python host and does not execute or install a Windows Qt video widget. Laptop must git pull and START.bat; user might need INSTALL.bat once if dependencies are not present.


## 2026-10-09 — ULTRON Fast Brain ücretsiz yerel modül (CI PASS)
- ultron/backend/app/core/fast_brain.py: FAST/GENERAL/CODING/VISION sınıflaması. Sadece gerçekten kurulu Ollama modelleri seçilir; ücretsiz Qwen3.5:4b varsa günlük sohbet, yoksa qwen3:4b. qwen3:8b daha kapsamlı sorulara, qwen2.5-coder:7b kod isteklerine, llava:7b görsele. Model otomatik indirilmez.
- ultron/backend/app/core/model_router.py: önce model çalıştırıp ikinci aşamada ekstra paralel 2-model race + judge çağıran gecikme kaldırıldı (Fast Brain interaktif yolunda). Manuel local evaluation korunuyor. Orijinal Approval Gate ve izin/araç akışı korunur; tek model yanıtı veya yalnız hata üzerine fallback.
- ultron/backend/app/core/brain.py: Qwen3/3.5 için think:false, kısa yanıt num_predict, sınırlı bağlam ve 10m sıcak model ayarı. Basit selamlaşmalarda ağır araç şeması atlanır; gerçek görevlerde araç erişimi korunur.
- ultron/backend/config/settings.json: fast_brain etkin ve tercih listeleri; mevcut kurulu modellerle ücretsiz çalışır. scripts/ultron_fast_brain_doctor.py yerel /api/tags ve opsiyonel gerçek yanıt zamanı --benchmark; kılavuz ultron/FAST_BRAIN_README_TR.md.
- Gerçek GitHub CI: code SHA 2d0eb712347cf98e100ea89b05c51751bc7c75d1, run https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37940137389 SUCCESS; 15 test_fast_brain.py PASS, Python compile, TypeScript/Vite ve mevcut regresyonlar PASS.
- Fiziksel Lenovo/Ollama/GPU hızı ve mikrofon gecikmesi NOT RUN. MARK Gemini Live & iPhone Cloud Live hiç değiştirilmedi; bu modül provider ücretsiz plan/sınırlarını otomatik değiştirmez. Model qwen3.5:4b indirme kullanıcı tercihi olup birkaç GB disk/indirme ve cihazda olası CPU offload gerektirir.


## 2026-10-09 — Hybrid Free-First Brain (Qwen primary, Gemini optional)
- iPhone web PWA chat defaults to YEREL QWEN ÜCRETSİZ; separate GEMINI İSTEĞE BAĞLI selector. POST /api/local-chat, GET /api/local-chat/{id} polls real completion. Offline laptop responds 409 rather than silently using Gemini. Gemini Live microphone remains a separately disclosed opt-in service.
- Cloud local_brain_bridge.py: authenticated web-only and owner-scoped chat queue with limited concurrent jobs, context from shared Cloud memory, exactly-once PostgreSQL assistant persistence via local_chat_requests. Render never runs Ollama nor exposes a user-supplied Ollama URL.
- Windows MARK bridge: integration/local_cloud_brain.py chooses only installed Qwen/llava models via FastBrainPolicy, Ollama fixed localhost 127.0.0.1:11434, no Gemini and no desktop tool execution in read-only chat mode; mark_app.py handles mode=local_brain agent_task using lease renewal and checked completion.
- Native iOS CloudSession.askULTRON Siri defaults to local laptop Ollama; ContentView Siri metin beyni selection can explicitly choose Gemini; bounded task polls, no silent Gemini fallback. Continuous native voice is still Gemini Live, not free offline local audio.
- GitHub code SHA 98b5902ab5cc793aa3d16c4a3ac55f993bc15ceb: Scene Build Check 37942388982 SUCCESS, Real Cloud Queue PostgreSQL Integration 37942388970 SUCCESS. iOS code SHA ed82517cf03264d29e04bc5b2fcc414382ba91ac: Native iOS Build 37942797049 SUCCESS (simulator and unsigned iPhone; static contracts). Render 98b5902a deployed live. No real iPhone/Windows visual/audio or local Ollama hardware round-trip benchmarks.
- Windows requires user git pull and START.bat restart; Ollama must run with an installed model. Laptop offline -> free phone chat unavailable. Paid/limited Gemini deliberately remains optional. Camera, PDF, and Live audio paths still use Gemini. Existing approval and desktop automation unchanged.

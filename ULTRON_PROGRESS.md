# ULTRON — Kalıcı Geliştirme Günlüğü

Bu belge geçmişteki gerçek kod değişikliklerini ve doğrulamayı kaydeder. Kendiliğinden arka plan çalışan bir süreç değildir.

## 2026-10-09 — Otonom geliştirme oturumu

**Repo:** `fatmakahraman304-hash/ULTRON`  
**Branch:** `feat/ultron-cloud-shared-memory`  
**Başlangıç HEAD:** `0638b116c30d221f4167a4df35381a5697237668`

### Döngü 1 — Earth Watch etkileşim
- `CenterStage.tsx` içinde kamera position/target ve Dünya orientation durumunu layer değişikliklerinde koruma.
- Focus hedefine yumuşak geçiş; drag hareketini gerçek nokta tıklamasından ayırma.
- `earthMath.ts` ile deterministik coğrafi koordinat matematiği.
- `earthMath.test.mjs` ve `npm run test:earth` ile regresyonlar.

### Döngü 2 — Backend state doğrulama
- Yeni `ultron/backend/earth_watch.py`: JSON veri normalizasyonu, doğru bool yorumlama, nonfinite koruması, longitude wrapping, renk/label/id/marker sınırları.
- `server.py` Earth Watch komutları ve diskten yükleme bu katmanı kullanıyor.
- Focus durumunda otomatik dönüş durur; GLOBAL seçimi dönüşü yeniden açar.
- Yeni `test_earth_watch_config.py`, CI'da bağımsız stdlib testleri.

### Döngü 3 — Gerçek dünya aydınlatma + ISS güvenilirliği
- Yaklaşık UTC Güneş pozisyonu ve dinamik ışıklandırma; manuel `UTC SUN` düğmesi ve sesli kontrol.
- Ekinoks/gündönümü/UTC farkı için testler.
- ISS kaynağı doğrulanmadan konum pini gösterilmiyor; request timeout, tek aktif request ve cleanup uygulanıyor.
- Bu, ISS kaynağının her ortamda erişilebilir olduğu anlamına gelmez.

### Döngü 4 — Geliştirme oturumları arası devam
- Root `AGENTS.md` Codex çalışma kuralları; riskli işlemlerde onayı korur.
- `scripts/ultron_dev_resume.py`: dört devam belgesini, branch/HEAD/git durumunu ve sıradaki işleri read-only raporlar.
- `scripts/tests/test_ultron_dev_resume.py` ve CI doğrulaması.
- Dört devam belgesi oluşturuldu, bu oturum sonunda gerçek kayıtlarla güncellendi.

### Doğrulama
- Son tam kod/CI referansı: `a010726149f7a1352933a2e45af51f9b1a985662`.
- `ULTRON Scene Build Check` run `37893780863`: PASS. Python syntax, backend Earth tests, resume tests/command, TypeScript/Vite ve Earth math tests geçti.
- Tam Python test suite, Windows `START.bat`, gerçek RTX 2050 FPS, mikrofon ve gerçek ISS bağlantısı: **bu oturumda çalıştırılmadı**.
- Cloud/Render otomatik deploy edildiği iddia edilmemiştir.

## Sonraki kesin iş
`ULTRON_NEXT_TASKS.md` içindeki Windows smoke doğrulaması ve Cloud queue idempotence regresyonları.

### Döngü 5 — Cloud queue atomik task teslimi ve completion koruması
- `ultron/cloud_service/app.py`: aynı `user_id:target` için `pg_advisory_xact_lock` ile eşzamanlı claim sorgularını seri hale getirme; yalnızca `status='delivered'` halinde retry/completion yapılması; eski/tekrarlanan completion için 409.
- `ultron/cloud_service/test_device_queue_contract.py`: gerçek handler AST ile çalıştırılan izole stub/mock veritabanında duplicate completion, inactive task, retry limiti, direction guard, iki paralel claim ve SQL state guard testleri.
- `.github/workflows/scene-check.yml` queue testlerini çalıştırıyor.
- İlk CI test denemeleri `37894708692` ve `37894774521` test harness hatalarıyla FAILED; source path ve HTTP stub düzeltildikten sonra `37894840971` SUCCESS.
- **Doğrulanmış son kod SHA:** `34b80e43abe023e58a8f65c87688aa104d6d55e7`.
- Başarılı CI adımları: Python compile, Earth backend test, 6 Cloud queue test, resume test/command, frontend TypeScript/Vite build, Earth math test.
- **Henüz doğrulanmayan:** gerçek PostgreSQL paralel transaction, Render deploy SHA, eski worker'ın yeniden teslim edilmiş task'a karşı attempt fencing'i, gerçek Windows/Gemini/Cloud uçtan uca test.


### Döngü 6 — Cloud delivery generation ve gerçek PostgreSQL doğrulaması
- `ultron/cloud_service/schema.sql`: teslim nesli `delivery_attempt` eklendi.
- `ultron/cloud_service/app.py`: claim nesli artırır; completion/retry, heartbeat/progress ve checkpoint kayıtlarında teslim nesli atomic SQL guard ile kontrol edilir. Tamamlanma/checkpoint JSONB yanıtları normalize edilir. PostgreSQL'in `jsonb_build_object` parametre belirsizliği `$3::integer` ile giderildi.
- `ultron/backend/cloud_client.py`, `mark_app.py`: masaüstü komutunun claim nesli tüm ilgili çağrılara eklenir; `agent_task` dışındaki legacy kontroller korunur.
- `ultron/cloud_service/test_device_queue_contract.py`: eksik/eski attempt, yarışan completion ve gerçek progress/lease/checkpoint handler testleri.
- `ultron/cloud_service/test_device_queue_postgres.py`: disposable PostgreSQL üzerinde paralel claim, retry/reclaim, stale completion, stale progress/lease/checkpoint ve legacy wake kontrolü testleri.
- `.github/workflows/cloud-queue-postgres.yml`: GitHub Actions PostgreSQL 16 disposable DB entegrasyonu. `scene-check.yml` masaüstü istemci/worker py_compile kontrolü de yapar.
- İlk PostgreSQL denemeleri `37897241297` ve `37897368506` FAIL oldu. Tespit edilen gerçek SQL tipi ve test JSONB dönüş sorunları giderildi.
- **Kod SHA:** `9d577a993f78aa7393c83c22b52c83d5c7d7dfac`.
- **CI PASS:** `37897505788` (Python compile, 5 Earth, 14 Cloud contract, 3 resume, TypeScript/Vite, 6 Earth math); `37897505793` (4 gerçek PostgreSQL 16 testi).
- **NOT RUN:** Render üretim deploy, gerçek Windows masaüstü/Gemini/telefon uçtan uca testleri, yerel eylemlerde exact-once garanti analizi.


### Döngü 7 — Masaüstü Cloud lease fencing ve görev serileştirme
- `ultron/backend/cloud_client.py` yanıtı 404/409 olan `/api/device-commands/*` işlemlerini `CloudDeliveryRejected` olarak sınıflandırıyor. 503/diğer URL yanıtları stale fence sayılmıyor.
- Yeni `ultron/backend/cloud_delivery.py` yenilemeyi kısa timeout'la yapıyor; belirgin lease reddi ve 15 sn boyunca doğrulanamama durumunda `lost` sinyali veriyor.
- `mark_app.py` görev çalıştırmadan önce ve Gemini bekleme döngüsünde lease'i kontrol ediyor; kayıp tespitinde best-effort `interrupt()` çağırıyor, eski teslimi completed olarak göndermiyor. Aynı process'teki agent görevleri artık ortak oturumda üst üste binmiyor.
- Yeni `ultron/backend/tests/test_cloud_delivery_guard.py`: 6 lease guard + 4 HTTP hata senaryosu, **10 PASS**.
- `.github/workflows/scene-check.yml` yeni regresyonları zorunlu kılıyor.
- **Kod SHA**: `d96638e1ecaad7d0b800e20fb22580ade555e777`; **CI** `37914696238` — PASS (5 Earth backend, 10 lease/client, 14 Cloud contract, 3 devam aracı testi; TypeScript/Vite PASS).
- **Sınır:** Cihaz üzerinde sesli/Gemini gerçek workflow ve Render ortamı doğrulanmadı; geriye dönük yan etkiler iptal edilemez.


## 2026-10-09 — Desktop durable dispatch fence (CI PASS)
- Cloud `agent_task` Gemini Live'a gönderilmeden önce `data/cloud_remote_dispatch.sqlite3` dosyasında `(Cloud URL, device, command_id)` için atomik kalıcı kayıt ayrılır. Yeniden claim/retry veya süreç yeniden başladıktan sonra aynı komut otomatik tekrar gönderilmez. DB açılamıyorsa fail-closed; telefon sonucuna inceleme gerektiren hata gönderilir.
- Görev metni, API anahtarı veya yanıtlar veritabanında saklanmaz; sadece scope/payload özetleri ve komut/attempt kimlikleri.
- Approval Gate, mic ownership ve diğer kontroller değiştirilmedi. `test_cloud_dispatch_journal.py` testleri CI'a eklendi.
- **Gerçek doğrulama:** kod commit `afe9f5b6855fc4742e384a4d298b71ee6c6feb18`; `ULTRON Scene Build Check` run `37915768918` **SUCCESS**. `test_cloud_dispatch_journal.py` 11 PASS, lease 10 PASS, Cloud contract 14 PASS, Earth 5 PASS, resume 3 PASS; frontend TypeScript/Vite build ve Earth math PASS.
- **Sınır:** Bu komut seviyesinde at-most-once *dispatch* korumasıdır, per-tool exactly-once değildir. Aynı komutun farklı masaüstüne yönlenmesi, tek turn içi tool tekrarları veya rezervasyondan önce yapılmış yerel işlemler için garanti vermez. Crash rezervasyon-sonrası dispatch-öncesi olsa bile inceleme gerekir.


## 2026-10-09 — iPhone Siri / Native Cloud görev köprüsü (CI BEKLENİYOR)
- Native iPhone 0.3: Siri App Intent arka planda tek HTTP isteği ile laptop `agent_task` kuyruğa ekler; web oturumu ve Keychain kullanılır, masaüstü Approval Gate korunur.
- Native ekranda yazılı laptop görev alanı eklendi. Cloud Live `ios_action` ve `ios_shortcut` olayları sadece kullanıcı onaylı `ULTRON Bridge` Kestirmesiyle çalıştırılabilir. Otomatik sistem ayarı değiştirme yok.
- Xcode derleme sonucu ve gerçek iPhone/Siri kilit ekranı, Cloud deploy ile Windows uçtan uca sonuçları henüz doğrulanmadı.


## 2026-10-09 — Native iPhone v0.3 son doğrulama
- **Kod SHA:** 0b4751a5d7c5f6ceb4642af4eb413f6fb0ca16b9; **CI:** Native iOS Build run `37917812910` **SUCCESS**. `test_siri_bridge_contract.py` **5 PASS** (kaynak/sözleşme testleri), XcodeGen proje üretimi, iOS Simulator build **PASS**, unsigned iPhone build **PASS**, unsigned IPA/Xcode project paketleme/upload **PASS**.
- Yeni native App Intents: `AskULTRONIntent` (Cloud sohbet), `SendULTRONDesktopTaskIntent` (desktop queue), `CheckULTRONDesktopTaskIntent` (görev durumu). Siri'den çalıştırılabilir kısa Cloud HTTP istekleri; canlı ses WebSocket bağımlılığı yok.
- Native `ContentView` laptop görev yazma/gönderme/durum sor ve `BackgroundVoiceController` ios_action, ios_shortcut, laptop_task event desteği.
- PhoneActionRouter'da izinli sistem komutları sadece `ULTRON Bridge` üzerinden ve kullanıcı `DEVAM ET` onayıyla yönlendirilir; otomatik foreground/background ayar değiştirme yok. Bekleyen hassas komutlar UserDefaults'tan cihaz Keychain'ine taşındı. Masaüstü Approval Gate ve durable queue koruması değiştirilmedi.
- **NOT RUN:** gerçek iPhone/Siri/telefon kilidi, Xcode signing/install, canlı Cloud/Render deploy, gerçek Mac/Windows laptop uçtan uca eylem, iOS sistem tarafından sonlandırma sonrası mikrofon/arka plan devamı. Kodun derlenmesi bu cihaz davranışlarını ispatlamaz.


## 2026-10-09 — USB'siz TestFlight hattı hazırlandı (release NOT RUN)
- `.github/workflows/ios-testflight.yml` yalnız `workflow_dispatch` ile manuel imzalı App Store archive/export ve Apple-Actions TestFlight upload hattını hazırlıyor; push/PR otomatik yayın YOK. `testflight` environment'da Apple Developer/App Store Connect API signing değişken ve sırları gerekiyor; fail-closed preflight eklendi.
- `ios/ULTRONMobile/TESTFLIGHT_KABLOSUZ_TR.md` Windows/iPhone cihaz-bazlı rehber. Mevcut ULTRON SVG'den App Store 1024x1024 icon build sırasında oluşturulacak. Apple Developer Program ve sertifika yoksa TestFlight yüklemesi yapılamaz. Workflow `main` default branch üzerinde bulunmadan GitHub UI'da manuel çalıştırma seçeneği açılmaz.
- `test_testflight_release_contract.py` 4 statik release guard testi eklendi. GitHub Native iOS Build doğrulaması bekleniyor; kod-signing/App Store upload gerçek hesabı olmadan NOT RUN.


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

## 2026-10-09 • ULTRON Hybrid Brain — local Qwen primary, Gemini optional
- Existing owner-authenticated iPhone Cloud /api/local-chat → paired Windows Ollama/Qwen remains free default text chat. Phone/Render do not themselves host Qwen; Windows laptop and Ollama must be online.
- Added ultron/cloud_service/static/local-voice.js: explicit tap-to-talk in Turkish via browser SpeechRecognition (when available), free Windows Qwen via the existing queue, and browser speechSynthesis for Turkish response. No browser Gemini fallback or automatic background microphone.
- PWA static/index.html: Qwen mic button now calls local recognition; Gemini Live mic starts only after explicit Gemini mode selection plus mic tap. App boot/pageshow/visibility will not silently initiate Gemini anymore. Service worker v43.
- Browser speech recognition may be unsupported in iOS Home Screen PWA and may use the browser vendor's network service. This is not guaranteed fully offline STT, no native iOS Siri entitlement, and does not establish guaranteed speech latency.
- Original Windows Fast Brain via installed Ollama models already exists; Windows MARK live-voice engine still Gemini separately and was NOT switched automatically to local Whisper/Piper.
- Code SHA f33bc81f9bdfdb4d5644c7beeaa7c061f8e63cbf: Scene Build Check #37989333207 SUCCESS, PostgreSQL #37989333208 SUCCESS and Render this code SHA observed live. Physical iPhone Safari microphone and Windows actual GPU latency NOT RUN. Further documentation: ultron/HYBRID_BRAIN_TR.md.

## 2026-10-10 — Warm ULTRON persona across devices
- Created ultron/cloud_service/conversation_persona.py plus eight stdlib regression tests.
- Integrated policy into local_brain_bridge.py and Cloud app.py for Gemini text, image, PDF, camera and Live audio. Local Qwen still requires Windows and cannot execute device tools.
- Added standalone CI persona-policy job independent of Postgres. Prior Cloud queue runs failed during GitHub runner Postgres container initialization, before checkout or Python tests; not a code failure.
- No real device or Render deployment validation completed at authoring time.

## 2026-10-10 — Shared persona verification
- GitHub Actions Cloud Queue PostgreSQL Integration run #37992572797 SUCCESS at commit 015ed652a03fd67caaf1118ff6707cc55e3b6f30. The separate persona-policy job passed all eight tests; the postgres-fencing job also passed its persona test and real PostgreSQL queue, local-brain memory/reply and dev-request integration steps.
- Docker Hub rate limit was the cause of earlier CI setup failures; replaced postgres:16 with public.ecr.aws/docker/library/postgres:16 to restore integration tests.
- ULTRON Scene Build Check run #37992487672 SUCCESS for persona fix commit 2e424e9c6da7eb2efecff50b8737f18532e36a67. No runtime files changed since that run, only workflow/docs.
- Real iPhone/Windows/Gemini sessions and Render deployment remain NOT VERIFIED.

## 2026-10-10 — Windows assistant persona refinement / verified
- Desktop Agent persona_guard.py now uses respectful ULTRON guidance rather than mocking the owner; no longer penalizes ordinary replies for lacking 'Boss'. agent.py no longer forces 'Boss' after reframing and removes the harsh rewrite cue.
- Added ultron/backend/tests/test_persona_warmth.py: 4 stdlib tests covering kind anchor, ordinary direct response, genuine apology and desktop postprocessor.
- GitHub Actions Cloud Queue PostgreSQL Integration #37992833637 on SHA 433617f77b669fbe30526705faccbe6532ccd545 SUCCESS: persona-policy (Cloud 8 + Windows 4 tests), real PostgreSQL queue/memory/development-request integrations all passed.
- ULTRON Scene Build Check #37992774370 SUCCESS at Windows agent postprocessor SHA 93f921f266a37bf01f565b9c8c32880854f3f372.
- No Windows local checkout, microphone/audio, physical phone or current Render deploy verified.


## 2026-10-10 — Personal owner briefing API
- Previous capability-readiness implementation and five tests passed CI (Cloud Queue PostgreSQL Integration #37995713894 success; scene build #37995706268 success on adjacent code commit).
- New pure Python personal_briefing.py reads only user-saved memory rows, deduplicates entries, bounds all outputs, and labels every item owner_saved_memory; it never invents deadlines, reminders, appointments, email access or executed actions.
- app.py now offers authenticated GET /api/personal-briefing with user-scoped memory query; no automatic polling or data gathering.
- Four new tests in test_personal_briefing.py wired into the standalone persona-policy CI job. CI / physical iPhone / Windows / Render current deployment should be checked separately; do not claim they are verified without passing results.


## 2026-10-10 — iPhone personal overview implementation
- Confirmed previous briefing API CI #37995893863 SUCCESS and Render successfully deployed briefing test SHA ba3c46df.
- Added /static/personal-panel.js with on-demand personal-memory and ten-capability panels, linked into mobile HAFIZA tab; loaded scripts via PWA cache v44.
- Node test contracts added: test_personal_panel.cjs (6), wired to scene-check.yml. CI initially red because test_local_voice.cjs pinned cache v43; patched version regex and new asset assertion in c1c641f67cf7a8627609b02df2996072a88489d6.
- This is code + automated contract validation, not yet physical iPhone Safari screenshot testing or confirmation of latest Render HEAD.


## 2026-10-10 — Personal dated plans and Cloud API
- Added personal_plans.py owner-browser-authenticated GET/POST/PATCH/DELETE /api/owner-plans with validation, owner-scoped parameterized queries and cross-site request checks.
- Added owner_plans table and index. Every write needs a direct user action; no automatic alerts or external account changes.
- /api/personal-briefing shows pending owner plans; _memory_context includes only plan titles, dates and times, deliberately omitting private notes.
- iPhone HAFIZA create/list/done/undo/delete UI, confirmation-gated delete, separate refresh; PWA static asset cache v45.
- Added offline, real PostgreSQL tenant-isolation and Node UI regressions, wired into both GitHub Actions workflows; final CI and Render must be verified separately before announcing success.


## 2026-10-10 — Life planner reschedule/edit increment
- Implemented plan PUT endpoint with shared strict field validation and user_id-bound SQL. Existing done/delete paths unchanged; missing or other-owner plan returns 404.
- iPhone owner's existing plan now offers DÜZENLE, DEĞİŞİKLİKLERİ KAYDET and DÜZENLEMEYİ İPTAL ET, preserving entries on failed network save. PWA cache v46.
- Extended Python offline and disposable PostgreSQL lifecycle tests and Node UI regression contracts. CI / Render current commit confirmation required; actual devices not tested.


## 2026-10-10 — Delivered opt-in .ics export
- Added ultron/cloud_service/personal_calendar_ics.py with bounded RFC5545 UTF-8 folding, reserved-char escaping, opaque stable UID, calendar timestamps and explicit DST-safe UTC conversion. Private owner notes excluded.
- Registered authenticated, no-store GET /api/owner-plans/calendar.ics in personal_plans.py with user_id-scoped SQL and a strict IANA timezone allowlist, only outstanding plans.
- HAFIZA owner-plans.js and index.html now expose timezone selector (Europe/Istanbul / Asia/Nicosia / UTC) plus explicit download button. No background export and no third-party calendar authorization. No push notifications.
- Automated Python offline test_personal_calendar_ics.py, extended disposable PostgreSQL test_personal_plans_postgres.py, and Node test_owner_plans_ui.cjs. Cloud Queue PostgreSQL Integration #38034057983 SUCCESS, Scene Build Check #38034046409 SUCCESS (code/test SHA 74162f6). Render confirmed export UI SHA 74162f6 live. Current docs-only or workflow-only HEAD can be ahead; distinguish deployment proof of working code from HEAD deployment proof.
- This session had no access to the user's real iPhone/Windows hardware, so Safari file-download/import and native Apple Calendar appearance are not verified.

## 2026-10-10 — Reviewable ULTRON learning / memory deletion
- Added approved_learning.py, learning_proposals PostgreSQL table with pending-only unique index, and web-session-only owner-scoped APIs for create/list/review/delete. Explicit approval uses an atomic PostgreSQL transaction and INSERT memories ON CONFLICT DO NOTHING (existing memories are not silently overwritten). Rejection never saves memory.
- iPhone HAFIZA now shows İZİNLİ ÖĞRENME panel for user-proposed preference/goal/project/fact/device records. No automatic extraction, polling or hidden memory writes; only the owner tapping ONAYLA can approve.
- Added a separate confirmation-gated HAFIZADAN SİL control to shared memory entries to revoke learned information; deleting the proposal itself does not delete a previously approved memory.
- Tests: offline validators, disposable PostgreSQL cross-owner consent/privacy/duplicate/conflict scenarios, and mobile Node safe DOM/explicit-click tests wired to Cloud and Scene CI. No native device or LLM quality claims.
- The ten-capability readiness API now reports available reviewed learning but honestly marks general autonomous learning only partial.

## 2026-10-10 — Opt-in auto-learning implementation
- Implemented auto_learning.py with default-off owner_auto_learning PostgreSQL table and authenticated GET/PUT /api/auto-learning (JSON + same-origin write). An atomic FOR UPDATE check guards writes against switch-off races.
- Supports deterministic high-confidence owner-declared preference/goal/project chat statements, normalizes and hashes per-value key, and INSERT ... ON CONFLICT DO NOTHING so existing memories are never silently overwritten. Excludes common secrets, sensitive phrases, emails, long numbers, URLs, control chars and multiline requests.
- Attached to accepted /api/chat (Gemini) and /api/local-chat (Windows Qwen bridge). No network model extractor, background observer, assistant-message learning or unrestricted continuous retraining.
- Added HAFIZA one-click status fetch followed by explicit confirmation to enable, reversible OFF and honest scope/exclusions text; PWA shell v48.
- Added offline Python extraction/owner-scope tests, disposable PostgreSQL on/off/cross-owner/no-overwrite tests and Node manual-toggle tests. Wired GitHub CI; statuses verified separately. iPhone/Windows real hardware not tested.


## 2026-10-10 — Command-first mobile + laptop UX
- Added pure mobile static/panel-intents.js and React panelIntent.ts with Turkish/English recognized requests and strict standalone command verbs; normal questions like "Dünya kaç yaşında?" must stay in chat.
- PWA index.html: original WORLD map remains in iframe but never prominently exposed. All five/six tab buttons only appear via tiny ⋯ menu; natural speech transcripts and typed messages routed through handlePanelIntent. New optional Hologram Lab screen-only CSS 3D ring energy preview; no third-party assets.
- Desktop Dashboard: voice-first class hides large nav/footer/system rail/redundant right panels by default, retains chat+CenterStage+mic+Menu. React HologramLab and Earth accessible by exact command; handles new native voice-log commands.
- CI tests added for iOS typed/Live words and no accidental question interception, desktop command parser and minimalist CSS; existing WORLD legacy test updated for new handlePanelIntent chain. Focus on low-cost GPU.
- Old scene CI failing because tests assumed direct worldVoiceIntent(heard) and naive "aç" substring matched "kaç"; patched actual intent routing/whole-word grammar. Need confirm exact final CI SHA and Render deployed code before reporting verified.


## 2026-10-10 — Implemented fully automatic brain route in minimal mobile UI
- Added static/auto-brain.js (select devices, safeToFallback verified 409 desktop_offline only) and PWA service worker cache v50.
- index.html removes the entire brain-picker row, unused CSS and old saved manual model preference; reads authenticated device presence on login, before chat submission, on voice tap, via existing 5s laptop heartbeat and on reactivation. Keeps a short re-check cache / deduplicated in-flight check; no extra microphone permission prompts on load.
- A connected, heartbeat-online Windows ULTRON gets first chance at local Ollama/Qwen. Otherwise Gemini Cloud chat. Local /api/local-chat rechecks heartbeat before creating queue task; only pre-queue desktop_offline permits resending to Gemini. If queued local later times out, the error is shown rather than risking double answer. Current live voice session is not automatically interrupted to switch providers.
- Kept microphone, attachment, message send controls; replaced provider text with generic speech status. If browser STT unsupported, Gemini Live can be offered after a direct microphone tap (existing permission requirements still apply). No silent mic start.
- Updated old local voice and bridge tests to new auto selection contract. Added test_auto_brain.cjs in Scene CI for owner-scoped heartbeat, safe fallback, no picker, JS syntax, privacy conditions. Must still verify final exact HEAD GitHub CI/Render; real device test not possible here.


## 2026-10-10 — More natural ULTRON personality and real turn history
- Added conversation_turns.py: strict user_id + conversation_id query, prior-only id exclusion, latest-first bounded turns (14–20 max) and explicit Ollama/Gemini role mapping that never promotes saved history to the system role.
- app.py /api/chat: current message id returned and excluded from history; Gemini gets structured Content user/model turns; read-only status prevents false tool claims. Shared /api/live-voice request initializes history only for the relevant voice session.
- local_brain_bridge.py: user-scoped thread history in queued, read-only local_brain payload; conversation owner-bound INSERT ON CONFLICT ... WHERE ..., preventing malicious reused UUID. mark_app.py passes only the text turns to local_cloud_brain.local_chat; no desktop dangerous tools or extra network providers.
- integration/local_cloud_brain.py uses conversation_turns.ollama_messages and moderate bounded sampling for less robotic Qwen replies while retaining configured provider and installed-model selection.
- conversation_persona.py now specifically instructs pronoun resolution, short casual tone and fewer formulaic honorifics, no repetitive follow-up questions, transparent limitations and respectful correction.
- Regression suite test_conversation_turns.py, test_conversation_turns_postgres.py and test_local_dialogue_runtime.py added to Cloud CI. Latest code SHA dddbb7338c0689aa20fc0d708abfd5433d6646c6 is awaiting final Scene/Render verification. Native hardware and live model sample dialogues still NOT tested here.


## 2026-10-10 — Natural dialogue continued, Windows deferred
- Added classify_reply_mode, classify_dialogue_act and dialogue_guidance to conversation_persona.py. Dynamic response hints now match explicit request for short vs detailed explanations, same-topic followups, or corrected misunderstanding.
- Changed Cloud Gemini /api/chat and local Qwen bridge to set has_prior_turns=bool(real_thread_turns), not truthy placeholder strings; Gemini Live uses existing session-scoped recent context presence. No new data source or cross-session tracking.
- Hardening in conversation_turns.py ignores malformed/non-text history records instead of permitting invalid roles/content to derail conversation generation. Maintains bounded newest-first user/assistant turn history.
- Added offline test_conversation_style.py with realistic Turkish/English user utterances, history/no-history followups, seriousness/corrections and malicious history structure checks. Wired into Cloud Queue PostgreSQL Integration persona-policy job. Native Windows installation deliberately deferred.
- Cloud CI/Render must be confirmed on exact functional code SHA. Real Qwen/Gemini model subjective quality tests and Windows local updates remain outstanding.


## 2026-10-10 — Delivered topic-aware contextual recall
- Added _topic_terms, select_contextual_turns, load_contextual_thread_turns in conversation_turns.py. Directly stated salient topics can retrieve a small set of older messages within the exact same owner/conversation; pronoun-only turns use normal latest history.
- Updated app.py /api/chat and local_brain_bridge.py /api/local-chat to use this bounded selection. More natural continuity for very long threads without introducing another model call, autonomous memory writes or new platform dependencies.
- Changed old thread-contract checks to assert the new helper. Added test_contextual_recall.py and expanded disposable PostgreSQL test_conversation_turns_postgres.py for earlier same-thread recall, no current-turn duplication and cross-owner/cross-conversation denial. Cloud CI workflow runs the new tests.
- After code/test commit 8c25b3db4186d7e62bac465b6bbe8693af55a298: Cloud Queue PostgreSQL Integration 38057407803 SUCCESS, ULTRON Scene Build Check 38057407812 SUCCESS, Render deployment dep-db546815efls73a9o7cg LIVE. Real Gemini/Qwen spoken quality and iPhone/Windows device acceptance NOT independently verified.
- Requested persistent hourly development automation now enabled with explicit instructions not to install/download Windows files until the user chooses a final release; each hourly execution must still independently verify permissions and CI.


## 2026-10-10 — Read-only conversation recap for natural dialogues
- Added is_thread_recap_request() and select_recap_turns() in conversation_turns.py. Exact owner request only; samples from start / midpoint / latest messages in order with capped char and role budgets. load_contextual_thread_turns() detects recap commands and fetches at most 80 scoped prior user/assistant messages, honoring before_id, instead of only recent history.
- conversation_persona.py adds THREAD RECAP guidance to avoid hallucinating omitted discussion, and to state when thread has no prior messages.
- Both Gemini Cloud and queued Windows Qwen already use load_contextual_thread_turns; no new dispatch, model provider, microphone behavior, API endpoint, file write, database table, or visible UI change.
- Added test_thread_recap.py: exact command detection vs incidental summarization, chronological beginning-middle-end, caps, invalid/system-role rejection, no missing-context invention, scoped SQL and current-message exclusion.
- Expanded real PostgreSQL test_conversation_turns_postgres.py with cross-owner/cross-thread privacy and older-summary detection. CI wired in cloud-queue-postgres.yml.
- Code da9f6e76049953e88ae91b17104018bb9bdc6613 verified Render live; tests 8ffd9983cc1fc077745f3c5ed257b9f224553b8f verified Scene+PostgreSQL CI successes; workflow-only commit ef474b66ad9009871aa4dae7126223ee363ebe6c Cloud CI success. Actual mobile Safari / Gemini and local Qwen live answers not tested in this session.


## 2026-10-10 — Conversation-notes implementation and verification
- Added ultron/cloud_service/conversation_notes.py with explicit owner-only preview/list/create/edit/delete REST endpoints. Preview uses bounded same-thread excerpts, avoids common secrets and never saves; actual persistence requires direct Save from owner.
- Added conversation_notes table in schema.sql (conversation FK ON DELETE CASCADE, owner indexes). Registered routes in app.py. The notes table is intentionally NOT read by _memory_context or sent to Gemini/Qwen prompts.
- New static/conversation-notes.js creates a safe textContent-based editor/list under HAFIZA. Typed or voice "Sohbet notu hazırla" opens editable preview on demand; "Notlarımı göster" opens current conversation's notes. No extra home controls. sw.js v51 precaches the module.
- Added Python validators and preview safety tests (test_conversation_notes.py), disposable PostgreSQL consent/ACL/edit/delete/no-memory tests (test_conversation_notes_postgres.py), Node mobile preview/save/edit/safe-DOM tests (test_conversation_notes_ui.cjs). Wired GitHub Cloud Queue and Scene workflows.
- Fixed stale test_auto_brain.cjs PWA-version assertion after v51 cache bump (pinning v50 previously caused Scene CI failure).
- Final functional/test SHA a1afc4befbdfbd84fc52e3b0511aebdba675bed8: Cloud Queue PostgreSQL Integration #38061837383 SUCCESS, Scene Build Check #38061837381 SUCCESS, Render deploy dep-db555toae00c739bvqn0 LIVE. No real iPhone Safari, microphone or Windows hardware tests completed.


## 2026-10-10 — Fixed mobile Gemini Live end-of-answer clipping
- Created static/live-playback.js with generation-scoped pending audio counters, turnComplete() (drain rather than cut), enqueue()/idempotent finish() and cancel() invalidating stale completion events.
- index.html player registers every AudioBufferSourceNode with queue; audio onended removes and retires its entry, while normal turn_complete keeps already scheduled buffers running. Listening status returns after the last chunk. stopPlayback for real barge-in, server-interrupted, microphone stop, socket close and single-speaker desktop handoff still cancels immediately.
- service worker moved to v52 to precache Live playback helper. No additional home UI button or audible double TTS, no new account/provider/storage.
- New test_live_playback.cjs verifies normal end -> full drain, interruption -> invalidation, empty response -> no audio lock, late duplicate ended event safety, server/UI hook correctness, and microphone owner protection. Added to ULTRON Scene Build Check.
- Intermediate Scene workflow #38065262849 failed because UMD helper used a module variable shadowing Node's module.exports; fixed in final code commit b431b82314c4b27fee7c1cf7b2d96e5b27a51acf. Final Cloud Queue PostgreSQL Integration #38065354266 SUCCESS, Scene Build Check #38065354265 SUCCESS, Render dep-db55ubl9mjac73899sl0 LIVE at same SHA.
- No real iPhone Safari microphone, real-time Gemini audio API or paired Windows physical tests have been conducted. Laptop installation remains deferred.


## 2026-10-10 — One speaker per ULTRON voice turn
- Added static/speaker-policy.js pure decision functions for desktop eligibility and phone Live/local Qwen mic priority; only genuine boolean heartbeat fields grant desktop output.
- PWA index.html now blocks speakRemoteResult browser TTS while desktop is speaker leader; setDesktopVoiceLeader cancels WebAudio/browser TTS and clears remoteResultSpeaking after output handoff. watchDesktopPresence uses monotonic sequence to ignore stale out-of-order async responses and includes localVoiceController.active() as phone priority. Local voice onState takes phone priority immediately on explicit tap.
- PWA service worker cache advanced to v53 to precache speaker-policy.js; main minimal UI untouched.
- Added test_speaker_policy.cjs with no provider: online/unmuted actual speaker, invalid/stale statuses, phone Live or local microphone priority, no duplicate TTS, handoff cancellation, out-of-order presence safety and inline JS/PWA registration.
- Updated old test_live_playback.cjs to accept versioned PWA service-worker names and wired new Node speaker tests to Scene Build Check. Latest code/test SHA 4952ea5a6a44c041aebf5d87e21ce2184ad3e48d; Cloud CI and Scene CI SUCCESS (see tests doc).
- Windows laptop installation deferred at user request. Latest Render deployment must be checked for live separately. Real physical iPhone/Windows sound ownership NOT verified by browser/static CI.


## 2026-10-10 — Tap-to-interrupt stale phone Qwen voice reply
- Added static/voice-turn-guard.js, a tiny generation-token gate for browser local speech recognition completions and later model replies. A second explicit mic tap, typed new turn, voice mute, pagehide or app background invalidates the prior token.
- Mobile index.html now cancels browser SpeechSynthesis BEFORE starting/restarting a local mic; onTranscript associates a distinct token with send(true,voiceToken). The local/cloud response is still appended to chat, but audio is only played when the original voice turn remains current and the app is visible. No automatic cancellation or unsafe replay of an accepted desktop queue task.
- sw.js advanced v53 -> v54 to precache voice-turn-guard.js; no new visible panels, model picker, or automatic mic startup.
- test_voice_turn_guard.cjs checks cancellation and new-generation fencing, invalid tokens, pending text-vs-audio separation, mute/background cleanup, and PWA JavaScript syntax. Scene Build Check runs this module. A stale old test_local_voice.cjs assertion expected await send(true) without the new voice token; fixed to assert await send(true,voiceToken).
- Final code/test commit 70991ff6610e2cac631a2c1ec91d856588aa0cab: Cloud Queue PostgreSQL Integration #38066919827 SUCCESS and Scene Build Check #38066919837 SUCCESS. Render deploy dep-db5697jhu5js73djph4g was update_in_progress when checked; confirm live before saying deployed. No physical iPhone or Windows voice tests performed; Windows install remains deferred.


## 2026-10-10 — Relevant owner memory and higher-quality text routing
- Added ultron/cloud_service/personal_context_focus.py with select_personal_context and async load_focused_owner_context; owner-scoped PostgreSQL query fetches only saved memories and unfinished plans (never private plan notes or separate conversation-notes table). Plan and preference information survives long unrelated fact histories, with topical overlap ranking and 3400-character cap.
- app.py _memory_context delegates to helper, Gemini /api/chat passes current user text, and local_brain_bridge.py passes current Qwen prompt to the same helper. No manual brain picker or visible new UI; both models retain the established role-separated turns.
- Extended ultron/backend/app/core/fast_brain.py complexity recognition for explicitly detailed comparisons, logical reasoning and in-depth analyses; chooses already-installed 8B reasoning over 4B conversation model when requested, preserving low-cost FAST on ordinary chat and existing installed-model validation.
- Offline test_personal_context_focus.py covers 96 irrelevant facts plus one old C180 project, persistent Turkish reply preference, dated plan priority, owner note exclusion and strict 64–3400 char caps; routing tests verify deep request selects 8B and greetings 4B when available.
- Disposable PostgreSQL test_personal_context_focus_postgres.py verifies actual owner-scoped memory + event retrieval; foreign user memories, private notes and other-account plans stay excluded.
- Updated refactor-aware test_personal_plans.py and test_approved_learning.py to verify actual standalone helper, not obsolete SQL source positions. Latest functional/test commit a6ce694ff35423f93a386140c7e1938a374ad162 passed Cloud Queue PostgreSQL Integration #38068020642 and Scene Build Check #38068020631. Exact Render promotion still needs checking; no actual live Gemini model conversational rating or Windows 8B speed measured.


## 2026-10-10 — Conversational intelligence regression cycle 1
- Explicit first-topic return now retrieves the actual opening of the same owner/thread, including conversations beyond the 80-message recall window. Named recall includes adjacent question/answer evidence; very small context/turn budgets no longer overflow. Three new regressions first FAILED on the old code, then PASSED after fixes.
- Shared lightweight response quality checks remove only adjacent identical long prose paragraphs, preserve code/verbatim text, and flag excessive length without another model call. This is not semantic truth verification.
- Added versioned `evals/conversation`: 100 distinct scenarios (50 TR/50 EN), ten categories, scenario-specific acceptance plus five review dimensions. Real production provider adapters, transcript/latency capture, independent review and honest missing-run handling.
- Local verification: conversation tests 30 PASS / 6 PostgreSQL tests SKIPPED (no local disposable DB), response-quality 3 PASS, local runtime 3 PASS, reference-return 3 PASS, contextual recall 5 PASS, recap 6 PASS, local brain 5 PASS; backend Earth 5 PASS; Python compile PASS; npm ci/build PASS and Earth JS 6 PASS. PostgreSQL extension awaits real CI.
- Real model attempts: Gemini unavailable (no configured GEMINI_API_KEY in this environment); local Qwen unavailable (no reachable local Ollama). Each report has 100 NOT_RUN, zero captured transcripts, null quality score. **100/100 model quality NOT established.** No production personal chat accessed; no Windows install/model download.
- Prior functional Render SHA a6ce694ff35423f93a386140c7e1938a374ad162 verified LIVE (dep-db56gpmoq3os73c5cicg). This cycle's CI and Render pending commit/push.


## 2026-10-10 — Conversational intelligence cycle 2: real readiness and bounded memory
- Local-first routing now requires a fresh desktop heartbeat AND boolean local_chat_ready from a 1.5-second live loopback Ollama tags/model probe. Dedicated readiness executor preserves Cloud heartbeat independence from voice executors. Browser and server both reject missing/false/string readiness. Pre-queue 409 fallback remains the only safe retry route; accepted/ambiguous requests are never replayed.
- Older Windows builds do not advertise readiness and therefore safely use Gemini until the single final Windows update. No Windows install or model download performed. A readiness probe proves reachable service/installed model, not future inference or VRAM success.
- Auto-learning rejects common unlabelled API/private-key/JWT formats; canonical normalization deduplicates whitespace/case/final punctuation. No deletion or rewrite of existing owner memory. Explicit unambiguous reply-language/length conflicts use the newest saved preference in model context; scoped, negated, ambiguous and other factual conflicts are not automatically resolved. Owner CRUD/approval remains intact.
- Indexed PostgreSQL full-text retrieval combines 100 recent entries, 20 standing preferences and 40 lexical matches (at most 160 records) within unchanged prompt caps. Actual integration test retrieves an old C180 memory beyond 130 newer records while excluding another owner's matching keyword. This is bounded lexical retrieval, not universal semantic recall.
- Removed desktop queue payload logging to avoid exposing prompt/history/memory text. No changes to Approval Gate, device task permissions or UI controls; PWA cache v55 refreshes automatic routing.
- Evaluation scoring additionally checks exact suite hash, unique known scenario IDs, category and full matching transcripts before accepting reviews. Missing/error/unreviewed cases cannot establish 100/100.
- Actual local validation: ALL Cloud Python tests **152 PASS**, including **28 real disposable PostgreSQL tests**; mobile Node **86 PASS**; local-brain tests **6 PASS**; py_compile PASS. Frontend TypeScript/Vite and Earth 6 tests passed in cycle 1; no frontend TypeScript changed afterward.
- Cycle 1 SHA 27abf3c4fb53ecd0ce4bb70d89ca59146b56e289: GitHub Cloud/PostgreSQL 38069553694 SUCCESS, Scene 38069553682 SUCCESS, Render dep-db56rfou01pc73echpjg LIVE. Cycle 2 exact CI/Render awaits commit/push.
- Real model quality remains UNMEASURED: no configured Gemini credential or reachable Qwen/Ollama here. Common-secret filters and style heuristics are deliberately limited; no perfect privacy classification, semantic truth oracle, latency or 100/100 model quality claim.


## 2026-10-10 — Final bounded-evidence regression
- Long recalled assistant answers could still evict their corresponding question within the older-evidence character budget. A new regression FAILED before the fix; each selected role now reserves a bounded share, preserving both question and answer. Reference-return tests 4 PASS and actual conversation PostgreSQL tests 4 PASS.
- Final full local Cloud run: **153 PASS**, no skips, including 28 disposable PostgreSQL tests. `evals/conversation/LATEST_RESULTS.md` separately records all 100 TR/EN scenarios as NOT_RUN for both live providers and no quality score.
- Cycle 2 SHA 06acb933f9568c7548ec0d62631fcdb6f65a1811 verified: Cloud PostgreSQL run 38069902423 SUCCESS, Scene run 38069902369 SUCCESS; Render dep-db56tv7avr4c73eqm5lg LIVE. Final bounded-evidence commit CI/Render is checked after push.
- Continuation document now exposes current priorities under the resume script's supported `Next tasks` heading. No Windows changes, downloads or installations.

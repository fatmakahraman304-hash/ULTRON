# ULTRON — Teknik Yol Haritası

Bu belge `MARK-ULTRON-MERGED` kaynak ağacına dayanır. **Test edilmemiş özellik tamamlanmış sayılmaz.**

## Korunacak mevcut sistemler
- Python 3.12/aiohttp backend; React/TypeScript + Three.js UI; Ollama ve SQLite.
- Telefon Gemini Live → Cloud device queue → desktop agent → yerel tool → Cloud result → telefon.
- Scene Lab, Earth Watch, 3D video, GLB Asset Library, Mission Sequences, Trigger Engine, Snapshot Vault.
- Approval Gate, sandbox, izin denetimi ve audit logları.

## Doğrulanmış ilk geliştirme dalgası (2026-10-09)
- [x] P0 Earth Watch: Kamera orbit/zoom konumu ayar değişiminde korunuyor; sürükleme yanlışlıkla koordinat tıklaması olarak işlenmiyor.
- [x] P0 Geospatial tests: `earthMath.ts` ile koordinat round-trip, Greenwich, boylam wrapping, UTC subsolar nokta, ekinoks ve gündönümü testleri.
- [x] P1 Backend state validation: `earth_watch.py` persisted ayarları, bool string, finite sayılar, enlem/boylam, renk ve pinleri normalize ediyor.
- [x] P1 ISS safety: Geçerli yanıt gelmeden sahte ISS pini yok; timeout, non-overlapping poll ve cleanup var.
- [x] P1 UTC light: Yaklaşık NOAA tabanlı UTC Sun synchronisation, UI ve sesli araç kontrolü.
- [x] P1 Development continuity: `AGENTS.md`, dört kalıcı belge, `scripts/ultron_dev_resume.py` ve regresyon testleri.
- CI referansı: `a010726149f7a1352933a2e45af51f9b1a985662` — `ULTRON Scene Build Check` PASS, run `37893780863`.

## Sonraki öncelikler
| Öncelik | Alan | Kabul ölçütü |
| --- | --- | --- |
| P0 | Windows gerçek test | `START.bat`, üç Earth Watch mod kontrolü, zoom/orbit persistence, ISS çevrimdışı fallback, gerçek mikrofon ve 3D GPU akışı doğrulanır. |
| P1 | Earth offline kalite | İnternetsiz gerçekçi/kullanım hakkı açık texture varlığı; fallback geometrisi; GPU yaşam döngüsü ölçümü. |
| P1 | Cloud queue idempotence | **İlk koruma tamamlandı:** eşzamanlı claim'i PostgreSQL advisory transaction lock ile seri hale getirme; terminal olmayan görevlerde atomic completion/retry; 6 izolasyon/SQL sözleşme testi CI PASS (34b80e4). **Tamamlandı:** disposable PostgreSQL üzerinde delivery_attempt fencing; masaüstü lease guard. **Açık:** Render/telefon/Windows gerçek cihaz doğrulaması ve per-tool idempotency journal. |
| P1 | Güvenlik kontratı | Approval Gate, audit ve riskli tool işlemleri için güvenli regresyonlar. |
| P2 | Ses ve AI router | Wake-word, barge-in, STT/TTS hata dayanımı; yok model için fallback ve timeout testleri. |
| P2 | Scene Studio | Büyük sahne FPS/VRAM benchmark; GLB proje/export round-trip. |
| P3 | Agent sürekliliği | Alt görev state ve safe checkpoint; güvenli hata sonrası devam; sessiz background çalışma iddiası yok. |

## İş akışı
1. `AGENTS.md` ve dört devam belgesini oku.
2. `python scripts/ultron_dev_resume.py` ile HEAD/branch/kirlilik/sonraki iş durumunu gör.
3. Kod değişikliği, gerçek test, CI sonucu, açıklayıcı commit, dört belge güncellemesi.
4. Repo dışına yazma, secret ifşa etme, izinsiz destructive işlem ya da Approval Gate bypass yapma.
5. Bir oturum bitince `ULTRON_NEXT_TASKS.md` içinde tekrar üretilebilir kesin sonraki adımı bırak.

## 2026-10-09 — Cloud Queue P1 ara doğrulama
- `ultron/cloud_service/app.py`: aynı kullanıcı/hedef için claim transaction advisory lock; yalnızca `delivered` görevden completed/failed/retry state geçişi; duplicate veya late callback'e 409.
- `ultron/cloud_service/test_device_queue_contract.py`: handler fonksiyonlarını AST üzerinden gerçek kaynakta çalıştıran dependency-free simülasyon; 6 test geçti.
- `.github/workflows/scene-check.yml`: queue regresyonları zorunlu.
- **GitHub Actions PASS:** kod SHA `34b80e43abe023e58a8f65c87688aa104d6d55e7`, run `37894840971`; Python compile, frontend build ve diğer mevcut regresyonlar da geçti.
- **Sınır:** fake DB testi gerçek PostgreSQL lock/Cloud deployment sonucunu doğrulamaz; attempt ID olmadan eski worker'ın yeni claim döngüsüne yazması ayrıca ele alınmalı.


## 2026-10-09 — Cloud queue P1 delivery fencing (gerçek DB ile doğrulandı)
- [x] Cloud schema migration: `device_commands.delivery_attempt INTEGER NOT NULL DEFAULT 0`; her claim atomik olarak nesli artırır ve desktop'a döndürür.
- [x] Ajan görevleri tamamlanırken, lease yenilerken, progress gönderirken ve checkpoint yazarken `status='delivered'` **ve aynı delivery_attempt** şartı SQL'de uygulanır. Eski worker'a 409/404 verilir.
- [x] `ultron/backend/cloud_client.py` ve `mark_app.py` bu nesli Cloud çağrılarına taşır. Tek seferlik kontrol komutları geriye uyumludur.
- [x] Cloud kuyruk için 14 izole regresyon testi; gerçek PostgreSQL 16 üzerinde 4 ek entegrasyon testi. TypeScript/Vite ve diğer testler PASS.
- **Kod SHA:** `9d577a993f78aa7393c83c22b52c83d5c7d7dfac`
- **CI:** Scene `37897505788` PASS; PostgreSQL `37897505793` PASS.
- **Açık:** Render deploy SHA; masaüstü/telefon gerçek cihaz testleri; canlı kullanıcı hesabı ve ağ kopması dayanım testi; istenirse çoklu worker/failover ve DLQ yük testi.
- **Önemli:** Veritabanı fencing, bir worker'ın daha önce gerçekleştirdiği yerel yan etkileri geri almaz. Tam exactly-once masaüstü eylemi için permission-aware idempotency journal ayrıca gereklidir.


## 2026-10-09 — CloudRemote desktop lease loss protection (PASS)
- [x] `cloud_client.py`: device command 404/409 yanıtlarını `CloudDeliveryRejected` ile HTTP ağ/geçici hatalardan ayırma.
- [x] `cloud_delivery.py`: lease'i 5 saniyede yenileme; Cloud reddederse hemen işaretleme; 8s HTTP timeout, yaklaşık 15s yenilenememe halinde konservatif durdurma. Kısa kopmada anında iptal etmez.
- [x] `mark_app.py`: Gemini görevi dispatch öncesi ve yürütme sırasında lease kaybını denetleme; stale attempt'a completion raporu vermeme; eskimiş turn'ü best-effort interrupt etme ve aynı laptop içindeki agent_task'ları serileştirme.
- [x] `test_cloud_delivery_guard.py` ve `scene-check.yml`: 10 test, gerçek CloudClient HTTP hata sınıflaması ve lease yarışları CI'da PASS.
- **CI/commit:** `d96638e1ecaad7d0b800e20fb22580ade555e777`, run `37914696238`, Python+Frontend PASS.
- **Önemli sınır:** Çalışmaya başlamış harici/geri alınamaz eylemlerin exactly-once veya otomatik geri alındığı kanıtlanmamıştır. Bu katman bir teslim öncesi ve devam denetimidir; tam per-tool idempotency journal halen açık.


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

## 2026-10-10 — Personal ULTRON conversation parity
- Implemented shared conversation_persona.py for local Qwen and Cloud Gemini (text/image/PDF/camera/Live), with adaptive light humour versus serious tone, consistent name and consent-aware claims.
- Memory and history injected as untrusted bounded context; phone Qwen is explicitly read-only and never claims saved memory or local actions.
- Follow-up: real phone/Windows speech quality, configurable owner address/humour, personal daily brief only with opt-in, proof of live Render deployment.

## 2026-10-10 — Windows assistant persona refinement / verified
- Desktop Agent persona_guard.py now uses respectful ULTRON guidance rather than mocking the owner; no longer penalizes ordinary replies for lacking 'Boss'. agent.py no longer forces 'Boss' after reframing and removes the harsh rewrite cue.
- Added ultron/backend/tests/test_persona_warmth.py: 4 stdlib tests covering kind anchor, ordinary direct response, genuine apology and desktop postprocessor.
- GitHub Actions Cloud Queue PostgreSQL Integration #37992833637 on SHA 433617f77b669fbe30526705faccbe6532ccd545 SUCCESS: persona-policy (Cloud 8 + Windows 4 tests), real PostgreSQL queue/memory/development-request integrations all passed.
- ULTRON Scene Build Check #37992774370 SUCCESS at Windows agent postprocessor SHA 93f921f266a37bf01f565b9c8c32880854f3f372.
- No Windows local checkout, microphone/audio, physical phone or current Render deploy verified.


## 2026-10-10 — Owner personal-briefing mobile interface
- iPhone HAFIZA tab now exposes opt-in button for /api/personal-briefing and separate opt-in button for /api/capability-readiness (ten realistic JARVIS gap statuses).
- New static/personal-panel.js uses textContent-only rendering, no background fetches, no automatic account access or memory edits. PWA v44 precaches the script.
- Six Node UI tests in test_personal_panel.cjs cover no automatic network fetch, output provenance, status labels, safe DOM, error recovery and HTML wiring; scene CI runs them.
- Priorities remain verified iPhone hardware UX, consent-based calendar/email provider linking, and voice testing without disabling approval gates.


## 2026-10-10 — Owner Manual Calendar (ULTRON Life v1)
- Implemented: signed-in owner-created dated plans in PostgreSQL with create/list/mark done/undo/delete and strict title, time/date and note validation, owner-scoped SQL.
- iPhone HAFIZA tab has the plan editor; on-demand daily brief shows open plans and saved memory. Local/cloud assistant context receives plan titles and date/time, not private notes.
- NOT complete: Apple/Google Calendar OAuth syncing, scheduled background notifications, timezone controls, rescheduling, repeating events, physical iOS proof. Manual plans are not third-party calendar integration.


## 2026-10-10 — ULTRON Life v1 plan editor
- Add authenticated owner-only PUT /api/owner-plans/{id} to edit title/date/time/notes atomically, preserving plan id and completion. Avoid any external calendar sync or fake notification claims. iPhone HAFIZA includes explicit EDIT / SAVE / CANCEL, with draft preserved after network errors.
- CI acceptance: real PostgreSQL cross-owner edit forbidden and persistent update; Node UI confirms no write until click, cancel discards unsaved draft and errors retain it. No physical iPhone or Windows test inferred.


## 2026-10-10 — Personal calendar file export (no OAuth required)
- Implemented explicit owner-requested iCalendar (.ics) export from ULTRON HAFIZA.
- Browser-session-protected GET /api/owner-plans/calendar.ics accepts only Europe/Istanbul, Asia/Nicosia or UTC, converts timed events to true UTC instants and emits all-day dates without invented hours. Rejects ambiguous/nonexistent DST times instead of silently changing schedules.
- The file contains only outstanding plan titles and dates/times (not notes), uses stable opaque event identifiers and RFC5545 escaping/UTF-8 folding, and has no VALARM or subscription/provider side effects.
- The user explicitly chooses timezone and taps .ICS TAKVİM DOSYASINI İNDİR. Import into Apple/Google calendar must be user-initiated; export is not provider OAuth, syncing, notifications, calendar import verification or an automatic reminder.


## 2026-10-10 — Ten JARVIS capabilities implementation truth table
1. Expressive conversation: ULTRON persona, safety-aware humour and owner preferences carried through explicit saved memory; real human feelings/consciousness do not exist.
2. Personal memory/life: owner-scoped Cloud saved memory, daily briefing, manual dated plans, editing, completion and .ics export; real Gmail/Calendar provider authorization remains absent.
3. Learning with consent (NEW): owner-supplied fact/preferences inbox, approve/reject/delete proposal; only approved inserts into memories and older key is not replaced without review. No silent surveillance or continuous model retraining.
4. Offline powered-off computer: Cloud task queue exists, but actually powered-off PC control requires a separately powered authenticated device and compatible Wake-on-LAN configuration; unavailable here.
5. iPhone Siri: native source and explicit Shortcut approval bridge exist; full iOS app installation, Apple entitlements and device tests required.
6. Hologram: 3D scene on a screen exists; volumetric free-air hologram requires display hardware.
7. Humanlike voice: Whisper/Piper Windows path and optional Gemini Live/Qwen browser paths exist; live phone/Windows hardware speed and audio quality not measured here.
8. Self-updating: repository development queue, GitHub CI, Render autoDeploy exist; owner approval, tested desktop installation and rollback are mandatory before claiming fully self-updated.
9. Calendar/email: manual plans and .ics export exist; email and calendar OAuth provider connections, permissions and delivery receipts absent.
10. Smart home: connector concepts/adapters only; actual user-owned devices, authenticated LAN/cloud adapters and explicit device-change approval required.
All ten are *workstream requirements*; not all are implemented or physically achievable through software alone.

## 2026-10-10 — Optional automatic personal learning (bounded, user-controlled)
- Distinguish ordinary owner-approved inbox from opt-in auto-learning of explicit *owner-written* chat statements. Per-user database setting DEFAULT OFF, explicit browser toggle and reversible disable.
- Eligible exact-prefix expressions: "Tercihim:", "Hedefim:", "Projem:" and simple English equivalents. Stores only preference/goal/project value as owner-scoped memories; no model retraining, hidden scraping or app/microphone surveillance.
- Sensitive-pattern, email, long-number, URL and multiline rejects; bounded single message length/value and duplicate-key hash. No arbitrary "infinite storage" promise; actual storage and server resources are finite.
- Both Gemini Cloud and free paired Windows Qwen text chats can learn accepted owner messages after enabled, without weakening Approval Gate. Non-owner messages, replies and tool results must not be sources.
- Actual model-side autonomous omniscient learning, OS control while PC is powered off, unrestricted iOS Siri, free-air hologram and unpaired smart-home physical control remain unsupported.


## 2026-10-10 — One clean ULTRON interface, reveal workspaces on demand
- User wants mobile and desktop to show minimal cockpit/chat/voice by default. No permanently visible DÜNYA/Hologram/Tools grids; controls should appear only after user speech/text request (e.g. "Dünyayı aç", "Hologram Lab'i aç", "Hafızamı göster", "Ana ekrana dön").
- Mobile Cloud PWA: bottom multi-tab strip visually hidden except when ⋯ menu is explicitly opened; natural-language text and Gemini Live transcript routing to existing WORLD/HAFIZA/UZAKTAN/GELİŞTİR and new mobile screen-only Hologram Lab preview. PWA service worker shell caches panel-intents.js (v49). Menu remains for accessibility/no microphone.
- Windows: simplified voice-first React Dashboard hides top nav, footbar, system rail, redundant cards, retains CenterStage/ULTRON chat, small mic and one Menu. Desktop HologramLab opens on demand via dynamic component, Earth opens via existing stage backend, tools available in dialog.
- Safety: panel commands change visual UI only (except authenticated preexisting stage modes). No microphone auto-start, approval bypass, file operations, continuous recording or operating-system tool execution introduced.
- Mobile hologram is an animated *screen preview*, not full Windows 3D editor or a volumetric free-air hologram. Real devices still require manual acceptance.


## 2026-10-10 — Invisible local-first brain, clean mobile composer
- Requested simplified Cloud PWA removes visible "ULTRON BEYİN" title, Qwen/Gemini picker, cloud-limit explanations and duplicate technical guidance. Only voice button, attachment, message composer and send remain; existing hidden on-demand workspace menu is preserved.
- Browser Cloud /api/device-presence yields per-owner Windows desktop heartbeat: online within existing 15s window -> choose local Qwen; otherwise -> Gemini Cloud. No stale localStorage selector override. The choice re-checks before every text send and when the user taps microphone; background presence update is only for routing and must not start microphones.
- Browser transient source failures route to Gemini. Once a local request has entered the queue, uncertain timeout/failure is NOT blindly replayed to Gemini, avoiding duplicate command/message and surprise billing. Explicit 409 desktop_offline rejection before insert is safe for cloud fallback.
- Existing owner auth, browser microphone permission, live audio owner, queue fencing and local dangerous-tool isolation unchanged. Real provider subscription/quotas still apply, whether or not provider UI is hidden. Real iPhone/laptop manual verification remains required.

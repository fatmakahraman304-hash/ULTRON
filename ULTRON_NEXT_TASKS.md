# ULTRON — Sonraki Kesin Görevler / Kesinti Devam Kaydı

**Repo:** `fatmakahraman304-hash/ULTRON`  
**Branch:** `feat/ultron-cloud-shared-memory`  
**Doğrulanmış kod HEAD:** `afe9f5b6855fc4742e384a4d298b71ee6c6feb18` (ardından yalnızca doküman commit'i gelebilir).  
**CI:** `ULTRON Scene Build Check` run `37915768918` — PASS.

## Hemen yapılacak
1. `git status` ve `python scripts/ultron_dev_resume.py` ile yeni oturumun durumunu oku.
2. Windows 11 cihazında son branch'i pull ederek `START.bat` çalıştır; Earth Watch kamera/zoom kaybı, drag seçimi, Türkiye/Kıbrıs focus ve UTC SUN düğmesini manuel test et. Başarı gözlemi olmadan PASS yazma.
3. İnternetsiz durumdayken Earth Watch fallback, ISS WAIT durumu, network request ve UI cleanup davranışını gözle.
4. **Cloud P1 devam:** `ultron/cloud_service/app.py` için gerçek PostgreSQL üzerinden eşzamanlı claim/ack/retry integration testi yaz ve CI'da opsiyonel servisle koş; `mark_app.py` worker yeniden teslim/retry davranışını incele. Attempt token/fencing (eski worker sonraki claim'i bitiremesin) eklemeden tam idempotence PASS yazma.
5. Yeni kod için `npm run build`, `npm run test:earth`, backend pure unittests ve uygun CI workflow'u çalıştır; 4 geliştirme belgesine gerçek sonuçları yaz.

## Test komutları
```bash
python -m unittest discover -s ultron/backend/tests -p 'test_earth_watch_config.py' -v
python -m unittest discover -s scripts/tests -p 'test_ultron_dev_resume.py' -v
python scripts/ultron_dev_resume.py
python -m unittest discover -s ultron/cloud_service -p 'test_device_queue_contract.py' -v
cd ultron/frontend
npm ci
npm run build
npm run test:earth
```

## Sonraki öncelikler
- Kullanım hakkı açık offline texture + gerçek GPU memory/texture cleanup testi.
- Audio owner, wake-word, Türkçe STT/TTS ve barge-in regresyonları.
- Ollama local/cloud provider düşüşü ve memory persistence testleri.
- Agent görev logları için bounded retry ve state/checkpoint mekanizması.

## Kesinti koşulları
GitHub erişimi, izin veya güvenlik engeli çıkarsa burada gerçek başarısız adımı belirt. Bir oturum kendiliğinden arka planda devam etmez; sonraki Codex oturumunda `AGENTS.md` ve bu dosya üzerinden başlanır.

## 2026-10-09 doğrulanan Cloud queue altyapısı
- SHA: `34b80e43abe023e58a8f65c87688aa104d6d55e7`; Actions `37894840971` PASS.
- Eşzamanlı claim advisory lock, inactive completion reddi, retry limit ve guard için 6 izolasyon testi.
- Sonraki agent kesin adım: live/ephemeral Postgres ile claim/fencing integration tests; Render deploy/telefon testini kullanıcı ortamında ayrı doğrula.


## 2026-10-09 — Cloud P1 delivery fencing tamamlanan aşama
- En güncel doğrulanmış **kod SHA**: `9d577a993f78aa7393c83c22b52c83d5c7d7dfac`.
- Scene/Cloud contract build: `37897505788` **PASS** (14 Cloud contract testi).
- Disposable PostgreSQL integration: `37897505793` **PASS** (4 test).
- Bütün eski worker callback'leri (completion, lease/progress, checkpoint) yalnızca o claim'e ait `delivery_attempt` ile kabul edilir. Control command geriye uyumludur.

## Sonraki kesin görev
1. Render uygulamasında `/health` üzerinden **deploy.commit** doğrula; branch commit ile birebir eşleşmeden yeni protokolün canlıda çalıştığını iddia etme.
2. Son branch'i Windows 11'e `git pull --ff-only origin feat/ultron-cloud-shared-memory` ile al ve `START.bat` smoke testi yap.
3. Telefon → Cloud → desktop gerçek `agent_task` gönder; delivery attempt >0, lease 20 saniye korunuyor mu, sonuç telefona geliyor mu? Telefon/laptop araçları çalışmıyorsa gerçek hatayı kaydet.
4. Yerel irreversible eylemler için permission-aware idempotency journal tasarla ve test et: re-delivery, duplicate action ve approval gate güvenli kalmalı. DB fencing sadece Cloud callback'lerini sınırlar.
5. Cloud queue load/reconnection ve DLQ/expired cleanup stres senaryoları; gerçek microhone/Gemini Live ve RTX GPU canlı testleri ayrı sürdür.
6. Test/CI sonucunu ve dört devam dosyasını aynı SHA ile güncelle; sıradaki işi kodlamaya geç.

**Dağıtım uyumu:** Yeni Cloud sunucusu eski agent_task istemcisinden `delivery_attempt` gelmediğinde güvenli biçimde callback'i reddeder. Masaüstü branch'inin de güncellendiğini ve server migration tamamlandığını doğrula.


## 2026-10-09 — Güncel kesin sonraki iş (Döngü 7 sonrası)
- **Güncel doğrulanmış kod SHA:** `d96638e1ecaad7d0b800e20fb22580ade555e777`.
- **CI:** `ULTRON Scene Build Check` `37914696238` PASS (5 Earth, 10 masaüstü lease/client, 14 Cloud contract, 3 resume, frontend build).
1. Render `/health` üzerinden sunucunun deploy commit'ini kontrol et; Cloud migration ile desktop branch aynı protokol neslinde değilse canlı görev testi iddia etme.
2. Windows üzerinde yeni branch'i al, `START.bat` smoke testi, gerçek Gemini Live ve telefon görevini dene. `CloudDeliveryRejected` geçersiz claim'i kesiyor mu, normal 5s lease refresh çalışıyor mu? Kullanıcı cihazında gözlemlenmeden PASS kaydetme.
3. **En yüksek P1 kalan risk:** Onay mekanizmasını ihlal etmeyen ve yalnız izinli yerel eylemlerde çalışan durable action-level idempotency/checkpoint journal tasarla. Duplicate task sonrası aynı geri döndürülemez tool çağrısını tekrar çalıştırmama semantiği ve crash recovery testleri ekle. Cloud fencing'in already-executed tools'u geri alamadığını belirt.
4. Çoklu worker yeniden bağlanma ve deadline/lease stres testi; mümkünse disposable PostgreSQL 16 senaryosunu çoğalt. Memory/performance etkisini ölç.
5. `ULTRON_ROADMAP.md`, `ULTRON_PROGRESS.md`, `ULTRON_NEXT_TASKS.md` ve `ULTRON_TEST_RESULTS.md` dosyalarını her doğrulama sonrası eşleştir.


## Döngü 8 sonrası kesin adımlar (CI doğrulandı)
1. Kod `afe9f5b6855fc4742e384a4d298b71ee6c6feb18` GitHub Actions `37915768918` PASS: 11 yeni dispatch testinin yanında 10 lease, 14 Cloud contract, 5 Earth backend, 3 resume testi, TypeScript/Vite ve Earth math PASS. Yeni kod değişikliği yapılınca aynı kontrolleri tekrar çalıştır.
2. Gerçek Windows 11 üzerinde telefon → Cloud → desktop agent_task, yeniden deneme ve süreç kapanma/kurtarma senaryolarını gözle; canlı eylem ve onay testini PASS saymadan kaydet.
3. Komut-seviyesi fence'den sonra *per-tool* permission-aware journal: tool çağrı kimliği, onay öncesi/sonrası durum ve crash 'uncertain' kararı; reset/manual audit akışı tasarla. Tam exactly-once vaadi verme.
4. Render `/health` deploy.commit, Windows START.bat, Gemini Live, Earth Watch ve RTX GPU hâlâ cihaz testine bağımlı.

### Windows tekrarlama testi için güvenli kılavuz
- Testi geri alınabilir/yalnız okuma eylemiyle yap; gerçek belge silme, ödeme, kapatma veya sistem ayarı gibi işlemlerle duplicate/retry testi yapma.
- Tek bir `agent_task` komut ID'sinin Cloud tarafından ikinci attempt ile verilmesini kontrollü test ortamında doğrula. İkinci otomatik Gemini dispatch olmamalı; telefon manuel kontrol mesajı görmeli.
- `data/cloud_remote_dispatch.sqlite3` yerel, kalıcı ve `.gitignore` kapsamındadır. Dosyayı temizlemek önceki güvenlik kayıtlarını kaybettirir; otomatik temizleme önerilmez.
- Render, canlı Cloud deploy ve gerçek Windows/telefon/RTX/mikrofon smoke testleri **NOT RUN**.


## Native iPhone Siri (v0.3) doğrulama ve devam
1. `Native iOS Build` workflow'u exact HEAD için XcodeGen, Simulator ve unsigned device build çıktısına bak; FAIL varsa derleme hatasını gider.
2. Mac/Xcode'da imzalı iPhone kurulum; Cloud parolasını gir; Siri'den `ULTRON bilgisayara görev gönder` ile kuyruğa ID ekle; Windows masaüstü agent Cloud claim ve Approval Gate'i gözle.
3. ULTRON Bridge kestirmesini Kestirmeler'de elle hazırla. Kullanıcı **DEVAM ET** demeden `ios_action` sistem ayarları çalışmamalı. Ekran kilidi/suspend davranışı ve izin reddini ayrı test et.
4. Cloud görev durumunu sorgulama ve izinli APNs bildirimlerini geliştirmeye devam et; tam telefon sandbox erişimi vaat etme.


## 2026-10-09 — Native v0.3 doğrulama sonrası kesin devam
- Kod SHA `0b4751a5d7c5f6ceb4642af4eb413f6fb0ca16b9`; `Native iOS Build` run `37917812910` SUCCESS. 5 statik güvenlik testi, Simulator/unsigned iPhone build, unsigned IPA/Xcode artifact paketleme/upload PASS.
1. Mac/Xcode ve uygun Apple signing ile native iPhone'a yükle; Cloud password/Keychain oturumu aç, Siri Ask/Send/Status komutlarını gerçek kilit ekranı ve arka plan koşullarında test et, logla.
2. ULTRON Bridge kestirmesini Kestirmeler'de yapılandır, supported action izinlerini doğrula; telefon sistem ayarı kullanıcı DEVAM ET dokunuşu olmadan değişmemeli.
3. Gerçek telefon→Cloud→Windows ULTRON `agent_task` oluştur, Cloud ID, lease, masaüstü Approval Gate, durum sorgusu ve yeniden deneme korumasını gözle. Render `/health` deploy SHA'yı doğrulamadan production ready deme.
4. Sistem izniyle APNs görev sonucu bildirimleri, Shortcuts ek eylemleri ve kullanıcının açık izniyle iOS entegrasyonunu geliştirmeyi sürdür. Üçüncü taraf uygulamanın gizli ekran kontrolünü veya 7/24 mikrofonu vaat etme.


## TestFlight (kablosuz) — sonraki adımlar
1. Apple Developer Program aktif üyelik, tekil Bundle ID, App Store Connect app record, App Store API (Issuer+Key+p8), Apple Distribution private-key içeren p12 ve App Store provisioning profile sağlanmasını **kullanıcı kendi hesabından** yapmalı. Secret veya parola sohbet/repo/commit içinde paylaşılmamalı.
2. `.github/workflows/ios-testflight.yml` dosyasını inceleyip default `main` dalına PR/merge yap (UI Run workflow default branch gerektiriyor); GitHub `testflight` environment koruması, 5 vars + 3 secrets ayarla.
3. Kullanıcı workflow'u manuel başlatsın, signed archive/export ve TestFlight upload sonuçlarını CI loglarıyla doğrula. Yayın yaptık iddiasında bulunma; Apple beta processing, metadata, encryption questions, AppIcon ve TestFlight internal invitation ihtiyaçlarını kontrol et.
4. iPhone TestFlight daveti ile kablosuz kurulum, Cloud password, Siri App Intents, kilit ekranı, arka plan, desktop queue/Approval Gate uca kadar test et.


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
### Kesin sonraki mobil adımlar
1. Render dashboard üzerinden `ultron-yubh.onrender.com` servisinin canlı commit/branch durumunu kontrol et. **Sadece bu branch deploy edildiyse** `/static/mobile-action-guard.js` HTTP 200 ve yeni `index.html` UI'sını doğrula; değilse prod deploy politikası/branch'i kullanıcının kendi Render hesabında kontrollü güncelle.
2. Gerçek iPhone 14 Pro Max Safari PWA'da (ana ekran simgesinden) ULTRON Bridge kurulu iken Gemini Live'dan `set_brightness=35` iste; izin modalı çıkmalı, otomatik Shortcuts geçişi olmamalı, kullanıcı VAZGEÇ sonrası ayar değişmemeli. Sonra KEStİRMELERİ AÇ'a basıp iOS izin davranışını test et.
3. Arbitrary `ios_shortcut` adı veya kötü formatlı action geldiğinde PWA girişini reddetmeli; `UZAKTAN` sekmesinde queued/delivered sayılarını, görev sonrası badge sıfırlanmasını, offline/reconnect durumunu fiziksel cihazla kontrol et.
4. Apple'ın sistem kısıtları altında izinli PWA voice UX, foreground reconnect ve bildirim seçeneklerini geliştir. Masaüstü Approval Gate veya Cloud lease/idempotency korumasını aşma.

## 2026-10-09 — CORE küçük animasyon + ULTRON WORLD (kod ve canlı kaynaklar doğrulandı)
- CORE içi animasyon: kuş / yörünge / nabız presetleri, React/CSS boyuta duyarlı panel, oynat/duraklat/kapat; animation_show backend + stage tool + Türkçe metin komutları. Rastgele Python/Pygame çıktısı henüz otomatik gömülmüyor.
- Yerel frontend ve masaüstü backend CORE animasyon aşaması: SHA cfacb7355b87af174182b37b635152bd2c204729, frontend build 37925291261 SUCCESS, Scene build 37925291379 SUCCESS.
- WORLD: iPhone ana ekran PWA DÜNYA sekmesi ve Windows CenterStage içi world_map modu; Leaflet OSM sokak haritası (zoom 19 ve atıf), Three.js WebGL küre, adres/koordinat arama, favoris, izinli geolocation.
- Gerçek REST sağlayıcıları: Open-Meteo / MET Norway (Render IP Open-Meteo 429 olduğunda resmî MET Norway tahmin yedeği), adsb.lol / adsb.fi v3 (ADS-B uçak konumu), USGS depremler, Open-Meteo Air Quality, Photon OSM geocoding. Kısa süreli bounded cache, sabit upstream URL, açık kaynak atfı, 502 durumunda sahte veri üretmeme.
- Uydu, Street View, trafik, yağış radarı, rüzgâr, gemiler işaretli harici servis bağlantılarıdır; ULTRON içinde native entegre canlı veri katmanı gibi sunulmaz. 3D her evin detaylı fotogrametrik modeli değildir.
- SHA 5c0b8781f0303ae8351dc772d9df3dbcee57f6f9: Scene build 37927499485 SUCCESS, PostgreSQL 37927499348 SUCCESS, public production WORLD live smoke 37927499312 SUCCESS. 5/5 gerçek API kategorisi JSON kaynak doğrulama PASS (hava MET Norway, uçak adsb.lol, AQI Open-Meteo, deprem USGS, Photon adres). Sağlayıcı erişimi değişebilir.
- Render autoDeploy yes, feat/ultron-cloud-shared-memory dalı. Son live SHA ayrıca Render panelinden doğrulanmalı. Windows bilgisayarda git pull/START.bat gerekir.
- NOT RUN: gerçek iPhone Safari WORLD 2D/3D görsel ve harici harita tile/CDN testi; Windows Qt içinde CORE animasyon fiziksel testi; keyfi Pygame animasyonu gömme, harici trafik/uydu/gemi native katmanları.

### Sonraki WORLD ve CORE görevleri
1. Render live SHA kontrolü, iPhone Safari DÜNYA menüsü 2D/3D ve adres/POI/gerçek uçak/hava/deprem/AQI gerçek cihaz kullanıcı testi.
2. Windows güncel branch git pull + START.bat, sesli küçük kuş animasyonunu ULTRON CORE'da başlat; boyut/oynatma/kapama davranışını fiziksel test et. Yeni masaüstü sürümü Windows yereline otomatik yüklenmez.
3. Harici traffic/satellite/Street View/RainViewer/MET provider lisanslarına uyarak ve erişim anahtarı varsa ayrı sürümde gelişmiş bina 3D tiles; mevcut dış bağlantıları yerleşik native özellik PASS yazma.
4. Keyfi Pygame animasyonunu güvenli MIME/size sınırı ve izinli içerikle CORE'da oynatmaya dönüştüren sonraki modül; mevcut 3 hazır animasyonla karıştırma.
5. Sağlayıcı 429/502 için circuit breaker/backoff/normalization testleri, uygun harita CDN bağımlılığı ve gerçek iPhone WebGL testi.

### ULTRON WORLD sesli ve yazılı telefon komutları — 2026-10-09
- PWA index.html worldVoiceIntent: kullanıcı tarafından konuşulan/yazılan Dünya, 2D/3D, Gazimağusa, Lefkoşa, Kıbrıs, İstanbul, uçaklar/deprem/hava durumu görüntüle komutlarını DÜNYA sekmesine iletir. Harita iframe'i yalnız aynı origin ve kendi parent kaynağının postMessage komutlarını; tip, koordinat, mod ve katman allowlist guard'ını geçirse işler. Lazy-load sırasında en fazla dört komut bekletilir. Sesli sohbet motoru/Gemini reply Cloud oturumuyla devam eder.
- Cache PWA v40. Sesli komut güvenliği ve WORLD sözleşme testleri Scene Build Check 37928165355 SUCCESS; Cloud PostgreSQL 37928165548 SUCCESS. Kod SHA b473a4bfd28835aefae0472fb07a15442e7e383f. Önceki 37928109729 Scene FAIL sebebi test regex'i; düzeltme sonrası PASS. Üretim WORLD real-provider smoke 37928109603 SUCCESS (bu smoke bir önceki sesli komut kodunun commit'inde tetiklendi; sesli komut cihaz testi değildir).
- NOT RUN: fiziksel iPhone Safari PWA sesli komut → iframe görsel etkileşim, WebGL/CDN texture, Windows Qt CORE. Render AutoDeploy canlı HEAD ayrıca doğrulanmalı.

Somut sonraki doğrulama: iPhone Safari ULTRON → DÜNYA; sesle “Gazimağusa'yı haritada göster”, “3D Dünya'yı aç”, “yakındaki uçakları göster”; iframe yüklenene kadar komut kuyruğunu, OSM zoom/MapLibre yerine Leaflet içerik yüklendiğini, kaynak hatalarında gerçek durumu kontrol et. Windows desktop git pull/START.bat ve CORE preset animasyonun ayrı Bird Flap penceresi açmadan görünmesini test et.

## 2026-10-09 — Original MARK-LV native video engine restored INSIDE ULTRON CORE
- Investigation of actual original MARK files actions/video_player.py and ui.py: the player was a QMediaPlayer with a QGraphicsVideoItem mounted in the avatar/camera/video stack. It supports local files, HTTP direct media, optional yt-dlp YouTube resolution with separate synchronized audio/video, initially muted sound, stop/mute. The merged integration/web_panel.py had MOVED _video_cont to a separate QDialog (user's pop-out regression).
- New integration/video_dock.py MarkVideoDock reparents the SAME original _video_cont into the actual QWebEngineView. It positions the native QWidget according to .reactor-panel .center-stage DOM bounds, scaled by viewport, clamped so as not to cover surrounding telemetry/chat. Rechecks while open and calls Qt _fit_video on size changes. No new QMediaPlayer engine or video_dialog is created.
- integration/web_panel.py NativeBridge.videoRequest forwards explicit typed video commands to actions.video_player, and MARK native voice tools continue using old video_player directly. React Dashboard.tsx adds deterministic typed media routing irrespective of chosen model; CORE adds MARK VIDEO native-only button. Unknown or source-less voice 'video oynat' asks Qt native file picker (instead of generating a fabricated animation). Preset CORE bird/orbit/pulse animations remain separate.
- ui.py now retains native/QGraphicsVideoItem support after reparenting, QMediaPlayer pause/resume signal & button, correct sound output selection for mic protection, auto-closes the dock after EndOfMedia/decoder failure rather than leaving a black box. Opening a different clip cancels stale asynchronous YouTube requests.
- Headless GUI smoke scripts/tests/test_mark_video_dock_qt.py explicitly instantiated real PyQt6 QMediaPlayer, QGraphicsVideoItem, QAudioOutput, and verified QWidget signals/placement/resizing; 5 tests PASS with QT_QPA_PLATFORM=offscreen and Ubuntu EGL/PulseAudio dependencies. Pure geometry/plugin/contract tests scripts/tests/test_mark_video_dock.py 12 PASS.
- Exact tested code SHA 54a2f2408c54385fc53bc69f7cf944a7a22b1637, GitHub Actions Scene Build Check https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931870709 SUCCESS. Prior frontend build https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931231558 SUCCESS (no frontend changes since).
- Honest NOT RUN: real Windows GPU/QtWebEngine+QGraphicsVideoItem rendered video frame screenshot, real MP4 decoder and split audio through Windows speakers, live YouTube (yt-dlp/network), complete desktop voice Gemini route. The CI Qt smoke verifies Qt object creation and QWidget behavior, not actual codec playback on a Windows PC.
- This is a Windows-native MARK feature in a GitHub branch; Render is the Cloud Python host and does not execute or install a Windows Qt video widget. Laptop must git pull and START.bat; user might need INSTALL.bat once if dependencies are not present.

### MARK-LV native video: physical verification
1. On Windows laptop: git pull origin feat/ultron-cloud-shared-memory; START.bat. Say 'ULTRON, video oynat' (native voice) or type it / press MARK VIDEO. Native file picker should open; choose a REAL MP4/WebM clip. Assert picture and mute/play/pause/close appear INSIDE CORE, not a Windows video dialog. Confirm dashboard side rails remain interactive.
2. Resize the Windows ULTRON window, switch display scaling/DPI: native QGraphicsVideoItem should refit inside CenterStage with aspect ratio and should never cover the activity/file panels.
3. Test YouTube URL/description resolution with yt-dlp and separate audio; initially muted. Enable sound and check mic echo protection, pause/resume synchrony, close and end/error returns to CORE. CI tests do not assert these real Windows codec/network conditions.
4. Do not represent native Qt video dock as shipped via Render or as an iPhone-PWA playback feature. This path is for local Windows MARK-ULTRON instance. If device video window remains blank, collect runtime logs and codec availability for a targeted fix.


## 2026-10-09 — ULTRON Fast Brain ücretsiz yerel modül (CI PASS)
- ultron/backend/app/core/fast_brain.py: FAST/GENERAL/CODING/VISION sınıflaması. Sadece gerçekten kurulu Ollama modelleri seçilir; ücretsiz Qwen3.5:4b varsa günlük sohbet, yoksa qwen3:4b. qwen3:8b daha kapsamlı sorulara, qwen2.5-coder:7b kod isteklerine, llava:7b görsele. Model otomatik indirilmez.
- ultron/backend/app/core/model_router.py: önce model çalıştırıp ikinci aşamada ekstra paralel 2-model race + judge çağıran gecikme kaldırıldı (Fast Brain interaktif yolunda). Manuel local evaluation korunuyor. Orijinal Approval Gate ve izin/araç akışı korunur; tek model yanıtı veya yalnız hata üzerine fallback.
- ultron/backend/app/core/brain.py: Qwen3/3.5 için think:false, kısa yanıt num_predict, sınırlı bağlam ve 10m sıcak model ayarı. Basit selamlaşmalarda ağır araç şeması atlanır; gerçek görevlerde araç erişimi korunur.
- ultron/backend/config/settings.json: fast_brain etkin ve tercih listeleri; mevcut kurulu modellerle ücretsiz çalışır. scripts/ultron_fast_brain_doctor.py yerel /api/tags ve opsiyonel gerçek yanıt zamanı --benchmark; kılavuz ultron/FAST_BRAIN_README_TR.md.
- Gerçek GitHub CI: code SHA 2d0eb712347cf98e100ea89b05c51751bc7c75d1, run https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37940137389 SUCCESS; 15 test_fast_brain.py PASS, Python compile, TypeScript/Vite ve mevcut regresyonlar PASS.
- Fiziksel Lenovo/Ollama/GPU hızı ve mikrofon gecikmesi NOT RUN. MARK Gemini Live & iPhone Cloud Live hiç değiştirilmedi; bu modül provider ücretsiz plan/sınırlarını otomatik değiştirmez. Model qwen3.5:4b indirme kullanıcı tercihi olup birkaç GB disk/indirme ve cihazda olası CPU offload gerektirir.

### FAST BRAIN kesin sonraki Windows kontrolleri
1. Doğru Git dalında 'git status', 'git pull origin feat/ultron-cloud-shared-memory'; START.bat restart. Proje kökünden .venv/Scripts/python.exe scripts/ultron_fast_brain_doctor.py --benchmark ile gerçekten kurulu modellerin gecikmelerini ölç; kod testlerini gerçek laptop hız testi sayma.
2. İsteğe bağlı kullanıcı onayıyla 'ollama pull qwen3.5:4b', gerekirse resmî Ollama sürüm güncellemesi; benchmark before/after, RTX2050 4GB VRAM ve 24GB RAM taşma riskini değerlendir.
3. Offline local voice Whisper -> Fast Brain -> Piper ve mevcut Gemini Live sesli çağrılarını fiziksel Windows cihazında ayrı ayrı dene; Gemini ücret/limit durumu değişmedi. Approval Gate ve Cloud görev araçlarını regress etme.


## 2026-10-09 — Hybrid Free-First Brain (Qwen primary, Gemini optional)
- iPhone web PWA chat defaults to YEREL QWEN ÜCRETSİZ; separate GEMINI İSTEĞE BAĞLI selector. POST /api/local-chat, GET /api/local-chat/{id} polls real completion. Offline laptop responds 409 rather than silently using Gemini. Gemini Live microphone remains a separately disclosed opt-in service.
- Cloud local_brain_bridge.py: authenticated web-only and owner-scoped chat queue with limited concurrent jobs, context from shared Cloud memory, exactly-once PostgreSQL assistant persistence via local_chat_requests. Render never runs Ollama nor exposes a user-supplied Ollama URL.
- Windows MARK bridge: integration/local_cloud_brain.py chooses only installed Qwen/llava models via FastBrainPolicy, Ollama fixed localhost 127.0.0.1:11434, no Gemini and no desktop tool execution in read-only chat mode; mark_app.py handles mode=local_brain agent_task using lease renewal and checked completion.
- Native iOS CloudSession.askULTRON Siri defaults to local laptop Ollama; ContentView Siri metin beyni selection can explicitly choose Gemini; bounded task polls, no silent Gemini fallback. Continuous native voice is still Gemini Live, not free offline local audio.
- GitHub code SHA 98b5902ab5cc793aa3d16c4a3ac55f993bc15ceb: Scene Build Check 37942388982 SUCCESS, Real Cloud Queue PostgreSQL Integration 37942388970 SUCCESS. iOS code SHA ed82517cf03264d29e04bc5b2fcc414382ba91ac: Native iOS Build 37942797049 SUCCESS (simulator and unsigned iPhone; static contracts). Render 98b5902a deployed live. No real iPhone/Windows visual/audio or local Ollama hardware round-trip benchmarks.
- Windows requires user git pull and START.bat restart; Ollama must run with an installed model. Laptop offline -> free phone chat unavailable. Paid/limited Gemini deliberately remains optional. Camera, PDF, and Live audio paths still use Gemini. Existing approval and desktop automation unchanged.

### Next hardware verification: free-first hybrid
1. Windows laptop: verify clean branch and pull feat/ultron-cloud-shared-memory, restart START.bat. Check ollama list shows qwen3:4b; optional qwen3.5:4b requires separate voluntary download.
2. iPhone Safari ULTRON: choose YEREL QWEN, send Merhaba, test actual round trip. Disconnect laptop and confirm truthful offline error rather than Gemini fallback. Select Gemini manually to compare.
3. Native signed iOS Siri Ask ULTRON on-device test, inspect local/Gemini selection and App Intents lifetime. Continuous Gemini Live remains separate.
4. Windows local latency benchmark: python scripts/ultron_fast_brain_doctor.py --benchmark. Do not assert fixed ms speed from unit CI tests.

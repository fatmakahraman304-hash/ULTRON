# Current priority — conversation acceptance (2026-10-10)

- **Latest verified functional code:** `066b7b982a19c97297a2d74ee4cf68a4a9c4d336`. Long-thread recaps now sample the actual beginning, midpoint and end, even after 80+ prior turns, rather than sampling only the latest 80.
- **Verified CI:** Cloud Queue PostgreSQL Integration [38070614904](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070614904) SUCCESS; ULTRON Scene Build Check [38070614899](https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/38070614899) SUCCESS. New offline synthetic-long-thread and disposable PostgreSQL 120+ history/tenant-boundary tests are covered.
- **Next:** Obtain authorized real Gemini and local Ollama/Qwen evaluations without extracting secrets or connecting production private conversations. Run frozen 100-scenario suite for each available provider and independent human review before any quality score. Measure latency and context losses before increasing prompt budgets.
- **Do not yet:** call natural conversation 100/100; deploy a Windows update; claim new Render deployment LIVE without exact SHA confirmation. Preserve sparse UI, Cloud approval gate, owner isolation, and conservative model fallback.

---

# Current priority — conversational intelligence (2026-10-10)

## Next tasks

1. Latest functional SHA 78930a44f40835917337b3d7f494435a500cd94e passed Cloud/PostgreSQL CI 38070103017 and Scene CI 38070103005. Local evidence: 155 Cloud Python (28 real PG), 86 Node, 6 local-brain tests passed. Render dep-db56v7vmphoc739fq12g is LIVE at that exact functional SHA (17:03:37 UTC). Read the final verification record before new work.
2. Real quality remains NOT MEASURED. Run `python evals/conversation/run.py --provider gemini --output /tmp/gemini-eval.json` where an authorized Gemini credential is configured, and Qwen equivalent only on an available Ollama host. Independently review all 100 transcripts per provider against README criteria; report model identity limitations and latency. No Windows setup before final handoff.
3. Important compatibility: old Windows versions without `local_chat_ready` now use Gemini. Final single Windows update must include mark_app.py and integration/local_cloud_brain.py, then test Ollama reachable/unreachable transitions and no duplicate queued request fallback.
4. Remaining quality work: general semantic factual contradictions are not automatically resolved; only explicit reply language/length preferences are. Common secret patterns are not exhaustive classification. Measure long multi-turn dialogue and inference truncation before increasing context/model budgets. Current additional response checks are presentation-only, not semantic fact verification.
5. Preserve all approval/privacy controls and minimal UI. A CI pass is never a live-model 100/100 score. No further JARVIS features or Windows downloads until conversational acceptance.

---
Historical task records below; the priorities above supersede older Windows-install or non-conversation tasks.

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

## 2026-10-09 • ULTRON Hybrid Brain — local Qwen primary, Gemini optional
- Existing owner-authenticated iPhone Cloud /api/local-chat → paired Windows Ollama/Qwen remains free default text chat. Phone/Render do not themselves host Qwen; Windows laptop and Ollama must be online.
- Added ultron/cloud_service/static/local-voice.js: explicit tap-to-talk in Turkish via browser SpeechRecognition (when available), free Windows Qwen via the existing queue, and browser speechSynthesis for Turkish response. No browser Gemini fallback or automatic background microphone.
- PWA static/index.html: Qwen mic button now calls local recognition; Gemini Live mic starts only after explicit Gemini mode selection plus mic tap. App boot/pageshow/visibility will not silently initiate Gemini anymore. Service worker v43.
- Browser speech recognition may be unsupported in iOS Home Screen PWA and may use the browser vendor's network service. This is not guaranteed fully offline STT, no native iOS Siri entitlement, and does not establish guaranteed speech latency.
- Original Windows Fast Brain via installed Ollama models already exists; Windows MARK live-voice engine still Gemini separately and was NOT switched automatically to local Whisper/Piper.
- Code SHA f33bc81f9bdfdb4d5644c7beeaa7c061f8e63cbf: Scene Build Check #37989333207 SUCCESS, PostgreSQL #37989333208 SUCCESS and Render this code SHA observed live. Physical iPhone Safari microphone and Windows actual GPU latency NOT RUN. Further documentation: ultron/HYBRID_BRAIN_TR.md.
### Hybrid Brain next physical tests
1. iPhone ULTRON: select YEREL QWEN, manually tap mic, grant browser mic permission if supported, verify transcript, Cloud/Windows local answer and Turkish TTS. Confirm no Gemini connection or automatic restart on opening page.
2. Manually select GEMINI, tap mic and confirm original Live native audio works. Return to Qwen; Gemini must never be an unapproved fallback.
3. Windows: run Ollama, paired ULTRON Cloud worker and scripts/ultron_fast_brain_doctor.py --benchmark; measure actual response. Existing MARK voice Gemini Live is a separate audio path.
4. If browser STT is unsupported or requires third-party processing, consider opt-in audio capture relayed securely to Windows Whisper with retention/size/security testing; do not claim done.

## 2026-10-10 — Next concrete ULTRON steps
1. Confirm new standalone persona-policy CI job on b982019a0afe61cb4d1a39740e3fb9eccb9b3c8c. If red, inspect job steps/log and fix.
2. Retry Cloud Postgres runner integration when service initialization recovers; do not call its failure a regression without logs.
3. Check Render /health deployed commit, then physical iPhone Gemini Live and local Qwen conversations using jokes, personal memory and an emergency statement.
4. On Windows pull feat/ultron-cloud-shared-memory, START.bat; check microphone/approval gates still work. This connector cannot write to C:.
5. Explore user-controlled tone/humour preferences, opt-in briefings and preference sync to desktop agent; never claim true consciousness.

## 2026-10-10 — Next after verified CI
- CI proof: https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37992572797 succeeded (persona + actual PostgreSQL). Scene Build Check #37992487672 also succeeded.
- Outstanding: check Render release SHA, owner iPhone free-Qwen/Gemini mode behaviour and device voice; sync local Windows branch and start with START.bat; do not call the remote-only GitHub changes locally installed.
- Improve user-configurable style, humour, life reminders and secure opt-in calendar integrations with tests. Maintain permissions and user override.

## 2026-10-10 — Post-persona CI follow-up
- Latest passing Cloud+desktop persona/real DB CI: https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37992833637
- Next: verify Render /health active deployed SHA and actual Live voice/local Qwen on user devices. Sync Windows folder from feat/ultron-cloud-shared-memory; only GitHub was modified here.
- Add opt-in personal briefing, calendar/email integrations, adjustable wit and preference memory with explicit consent; keep Approval Gate active.


## 2026-10-10 — Owner request: complete 10 JARVIS-gap categories (realistic plan)
Scope and boundary: feature requests are accepted as a roadmap, NOT a claim that all 10 are implemented. Never represent sentience, unlimited iOS entitlements, physical holograms, powered-off PC control, or universal physical device access as available.

1. **Emotion / humour:** shared conversation policy now includes user-requested serious mode and warm personal style. More adaptive style preferences must be saved only after explicit consent and verified end-to-end.
2. **Personal life memory:** cloud/local shared history is available. Opt-in daily briefing is guided by real saved memory; next build source-authorized Calendar/Email integrations, data minimization, edit/delete controls and device tests.
3. **Learning:** user-approved preferences, task outcomes and corrections only; no silent surveillance, account crawling or unapproved collection. Add reviewable learned-facts dashboard.
4. **Powered-off laptop:** Cloud can hold requests but Windows-specific work cannot execute until an authenticated Windows worker comes online. Consider only user-owned, separately powered always-on worker; never promise power-on/control without suitable hardware or Wake-on-LAN network configuration and testing.
5. **iPhone Siri:** installable PWA with explicit Shortcut Bridge approval; native Swift source exists. Full Siri/background access requires signed installed iOS app, entitlements and Apple constraints. TestFlight has not been published.
6. **Hologram:** 3D Scene Lab on monitor is implemented. Genuine free-air volumetric hologram requires external display hardware not present.
7. **Human-like continuous voice:** Whisper/Piper local and optional Gemini Live already exist; test real Windows devices, speech interruption, latency, voice quality and phone/browser capability gaps. No perfect latency or unrestricted always-on phone microphone promise.
8. **Self-updating:** development request queue, GitHub CI and safe desktop update preparation exist. Require explicit owner permission, verified commit, clean worktree, tests, rollback and restart before announcing installed success. Never self-approve.
9. **Daily life apps:** add OAuth least-privilege, per-action authorization, calendar/email adapters, provider-reported delivery receipts, opt-in briefings, and integration tests before claiming complete management.
10. **Physical device control:** use only authorized supported IoT/Home Assistant HTTP devices, require confirmation for changes and report disconnected/missing devices honestly.

**Implemented this pass:** shared persona now adds explicit opt-in grounded daily-brief rules, per-request disable-jokes instruction, and no implicit personal learning or cross-device access claims. Four offline tests added in test_conversation_persona.py (12 tests total). Check Cloud Queue PostgreSQL Integration CI for these commits; physical devices and Render deploy remain unverified.


## 2026-10-10 — After owner briefing UI
1. Verify scene-check CI at c1c641f67cf7a8627609b02df2996072a88489d6, especially personal panel Node tests and older local voice tests.
2. Inspect Render service srv-db20lmei0phs73crgujg until live deployment matches current branch. Render autoDeploy=yes: do not trigger duplicate deploy.
3. On user's iPhone log into PWA, open HAFIZA, explicitly tap ÖZETİ GÖSTER and DURUMU KONTROL ET. Verify owner-scoped memory, no extra permissions, errors and empty state.
4. Install latest branch on Windows only with clean worktree and user-controlled update, then run START.bat. Test actual desktop and optional Qwen voice.
5. Next functionality: consent-based calendar/email connections with strict read scopes and no speculative appointments, editable learning preferences, verified device support and safe releases.


## 2026-10-10 — Next steps for life assistant
1. Verify final Cloud Queue PostgreSQL Integration + Scene Build Check CI green and Render service deployment SHA matches branch HEAD.
2. Test manually on iPhone Safari: create, list, complete/undo, confirm-delete; reopen tab and check persisted changes.
3. Confirm daily briefing displays owner-created plans. Query Qwen and opt-in Gemini, ensuring no fabricated appointments or reminders.
4. Add owner-selected timezone, edit/reschedule and optional consent-based notification channel with actual delivery acknowledgement.
5. Integrate third-party Calendar/Email only with scoped OAuth and explicit account connection and protect tokens; distinguish external providers from ULTRON's plan notebook.
6. Continue remaining ten JARVIS gaps with physical-device and safe self-update verification.


## After ULTRON Life plan rescheduling
1. Verify Cloud Queue PostgreSQL Integration and Scene Build Check for commit adding PUT/edit UI. If red, inspect failed GitHub logs and fix before continuing.
2. Verify Render autoDeploy latest code SHA live without manually triggering an unnecessary deploy.
3. On real iPhone: HAFIZA > KİŞİSEL TAKVİM > PLANLARI GÖSTER > DÜZENLE; change date and time; KAYDET; refresh and verify persisted. Check cancel, failed save, done state and cross-user isolation.
4. Next opt-in capabilities: user-selected timezone, optional verified calendar .ics export or provider OAuth, repeat plans; do not promise phone push alerts until actual provider and permissions configured.


## Next ULTRON Life acceptance and follow-ups
1. On a logged-in iPhone, open HAFIZA > KİŞİSEL TAKVİM VE PLANLAR, select Türkiye or Kıbrıs timezone and tap .ICS TAKVİM DOSYASINI İNDİR. Import the downloaded file in Apple Calendar only with user consent; verify timed plan and all-day plan timestamps. iOS browser/PWA download support and real import have not been tested.
2. Verify no private notes or automatic alarms appear in downloaded .ics; verify export does not mark a plan complete or update Cloud records.
3. Confirm Render live commit corresponds to latest code/test SHA and CI Cloud PostgreSQL + Scene Build Check succeeded; inspect new failures before changing more code.
4. For real two-way calendar integration require explicit provider OAuth authorization, least-privilege scopes and token security. For alerts require deliberate user opt-in and verified delivery; no alerts exist now.
5. Consider per-owner saved timezone default with versioned preference and no implicit location tracking; continue actual phone/Windows Gemini/Qwen voice tests and safe updates.

## After approved learning review (current)
1. Check latest Cloud Queue PostgreSQL Integration and Scene Build Check on exact HEAD; if failing, inspect job step and fix first. Check Render live hash separately. No hardware test claim.
2. On real iPhone Safari: HAFIZA > İZİNLİ ÖĞRENME. Propose "PREFERENCE / İletişim tarzım / Kısa Türkçe yanıtları seviyorum", tap ÖNERİLERİ GÖSTER, then REDDET or ONAYLA. Confirm pending facts do not appear in ORTAK HAFIZA, approved facts do. Confirm HAFIZADAN SİL really clears the key. Reopen app and verify persistence.
3. Connect model to *strictly validated* user-selected tone without treating untrusted saved memory as executable system instructions; optional playful/serious mode and test no humour in serious situations.
4. Add an optional explicitly consented language-model suggestion extraction step for review inbox (never auto-approve); bound privacy, prompt injection, rate and data retention.
5. For remaining capabilities: Apple/Google OAuth with minimum scopes, true reminder delivery receipts, iPhone native entitlements/hardware, local voice latency, powered-off computer wake hardware, optional IoT device adapters and safe updates/rollbacks. Never invent real hologram hardware or human consciousness.

## Next after optional auto-learning
1. Inspect GitHub Cloud Queue PostgreSQL Integration + Scene Build Check on latest auto-learning HEAD, fix any failing test, verify Render live commit. Do not mark successful without evidence.
2. iPhone Safari HAFIZA > SOHBETTEN OTOMATİK ÖĞRENME: tap status, explicitly enable, switch to chat and type "Tercihim: Kısa Türkçe yanıt". Check ORTAK HAFIZA, then disable and verify new phrases no longer save. Delete saved item using HAFIZADAN SİL.
3. Confirm account A's opt-in and stored facts are not accessible by B. Confirm direct Gemini and free Qwen text accepted. Verify no background audio/camera/email/calendar collection.
4. For smarter extraction beyond direct statements: separate approval inbox for low-confidence AI-suggested memories with source excerpts and PII redaction, no silent automatic approval. Add preferences for retention/export and limits; no unlimited database promise.
5. Other JARVIS goals: least-privilege calendar/email OAuth, native iOS entitlements/device build, Wake-on-LAN hardware, real smart-home enrollment, measured local Whisper/Piper voice and safe desktop self-updating, external holo hardware.


## Next after command-first UI
1. Verify exact HEAD Cloud Queue PostgreSQL Integration, Frontend Build Check and ULTRON Scene Build Check including NEW minimal intent tests. On failure inspect logs and patch, don't handwave.
2. Verify Render live deployed commit SHA. Do not trigger redundant manual deploy (autoDeploy enabled).
3. Real iPhone Safari/PWA: ensure chat input+mic visible, bottom DÜNYA/HAFIZA/UZAKTAN/GELİŞTİR buttons not exposed by default, ⋯ menu expands and closes, typing or speaking "Dünyayı aç"/"Hologram Lab'i aç"/"Ana ekrana dön" changes view. Verify World real map/3D render and Safari browser permission restrictions.
4. Real Windows START.bat: ensure native audio still owned by existing system; CenterStage+chat+small mic appear, old menu/footer hidden, "Hologram Lab'i aç" opens actual HologramLab, "Dünyayı aç" opens Earth stage, "Hafızayı göster" opens ToolPanel, Escape closes modal, menu button provides fallback.
5. Mobile screen-preview hologram is NOT same as full Windows 3D lab. If user wants full parity, ship prebuilt interactive Three.js mobile lab with verified performance/permissions and then test on hardware.
6. Continue truthful capability gaps and avoid real background/PC powered-off or native iOS feature claims without hardware/provider access.


## Next user acceptance: automatic Qwen/Gemini without a manual selector
1. Confirm latest Cloud Queue PostgreSQL Integration and ULTRON Scene Build Check on exact code SHA, inspect failures and fix before calling done. Confirm latest Render deploy status and code SHA (not merely repository commit).
2. Real iPhone: sign in to https://ultron-yubh.onrender.com, refresh PWA/Safari cache. Ensure no large "ULTRON BEYİN", Qwen/Gemini select, rate limit explanation row. Chat composer with microphone, attachment and send must remain.
3. With Windows ULTRON + CloudRemote queue + Ollama running, verify desktop device heartbeat is ONLINE, send ordinary text and test local Qwen answer returns with shared conversation. Tap mic with browser permission and test local speech turn.
4. Shut Windows ULTRON down, wait >15s for heartbeat to expire, send text and check real Gemini reply; try tap-to-speak and Gemini Live only after user tap. On reconnect, send next text and check automatic local selection. Do not claim actual laptop hardware powered-down detection beyond heartbeat.
5. Simulate laptop going offline between presence check and local queue submit: a confirmed 409 desktop_offline must trigger Gemini once; 429 busy, network ambiguity, queued timeouts and permission errors must NOT silently duplicate/replay message.
6. Verify Cloud API key quota failures are reported truthfully; model limits are not removed by hiding labels. No fully unbounded free model claims.


## Next — ULTRON humanlike conversational experience acceptance
1. Verify Cloud Queue PostgreSQL Integration and ULTRON Scene Build Check for exact code SHA dddbb7338c0689aa20fc0d708abfd5433d6646c6; fix any failed tests. Confirm Render deploy of this SHA live, do not infer from commit.
2. iPhone Cloud Gemini test with one conversation id: "2009 Mercedes C180'e bakalım" → "Yakıt tüketimi nasıl?" → "Peki onunla 2016 E220d'yi karşılaştır." Verify multi-turn 'onun' resolution and no stale different-topic bleed; request independent new conversation to ensure isolation.
3. Laptop with Ollama Qwen and running CloudRemote: repeat multi-turn chat, check queued local_brain payload contains bounded ordered turns, no duplicated current user prompt, and actual local Qwen follow-up coherence.
4. On real iPhone Gemini Live voice: speak several follow-ups and verify session_id-scoped history and interruption, no microphone capture without tap and no unproven tool actions.
5. Manually evaluate naturalness for 20 diverse Turkish dialogues (greetings, follow-ups, ambiguity, serious situations, humour requested, corrections, long/short requests). Track latency and provider model names. Do not claim human-level conversation without hardware/provider evidence.
6. For deeper conversational memory consider user-approved summaries of older conversation threads with explicit retention limits, never automatic sensitive facts or cross-user history mixing. Keep minimal mobile/desktop UX.


## Next ULTRON natural conversation tasks before final Windows update
1. Verify all Cloud Queue PostgreSQL Integration jobs including test_conversation_style.py and full Scene Build Check pass for latest functional commit; verify Render latest functional SHA LIVE. If failed, inspect exact logs and fix before new changes.
2. Run real conversational acceptance dialogues on deployed mobile Gemini: "Merhaba" -> natural short chat; "Mercedes C180 2009" -> "Peki onun yakıtı?" -> "Kısa cevap ver" -> "Hayır, 2016 E220d'yi kastettim" -> "Adım adım karşılaştır". Check no invented earlier context when starting a new conversation.
3. Preserve safety of native device approval gates and Cloud text/voice session scoping. Retest phone mic handoff without claiming physical hardware was tested.
4. Later add optional user-controlled advanced conversation presets or explicit feedback scores, keeping the mobile UI uncluttered and avoiding automatic personal-sensitive learning.
5. Only AFTER iterative GitHub+Render development is complete, guide user through a single Windows update of latest clean branch with START.bat/DOCTOR and real local Qwen tests. Do NOT attempt a Windows download or claim local installation now.


## Next ULTRON JARVIS-like capabilities — develop first, install Windows last
1. On the deployed mobile Cloud account, run a real 30-turn conversation: discuss Mercedes C180, switch to design/English for 20 turns, then explicitly ask "Mercedes C180 hakkında ne konuşmuştuk?" and verify selected old context is reflected without inventing facts; then ask "Peki?" and ensure it follows the immediate topic rather than jumping back. Repeat in a brand-new conversation ID to verify topic isolation.
2. On a running Windows Ollama/Qwen desktop after the user eventually installs the finalized build, test the same long thread; confirm acceptable latency on RTX 2050 and adequate context caps (2600 characters).
3. Maintain automated CI and Render proof for every changeset; treat physical iPhone voice latency, iOS PWA, Windows START.bat, local STT/Piper, IoT, calendar/email OAuth, true hologram hardware and powered-off PC interactions as separate unverified goals.
4. Next candidate: opt-in per-conversation "summary of older dialogue" feature with explicit, editable review and deletion. Never auto-save sensitive personal information or let LLM-authored summaries become system instructions; prefer deterministic bounded sources and preserve all owner approval/security gates.
5. Update user only with actual verified code/test/deployment outcomes, not a promise of nonstop autonomous work beyond the scheduled hourly task. Laptop installation remains deferred until the user requests it.


## Next ULTRON steps after scoped whole-chat recap
1. Run real iPhone Cloud Gemini conversation: discuss a car, then 20 messages on architecture, then a recent voice topic. Ask "Bu sohbeti özetle" and verify the recap covers the early, middle and latest *known* portions without fabricating facts or claiming exhaustiveness. No UI changes needed: type or speak normally.
2. Test a brand-new empty chat: same command should explicitly say there is no prior thread. Ask "Kitabı özetle" and verify normal book summary task is NOT misrouted to whole-conversation recap.
3. On real iPhone/Windows when approved and available, test Gemini Live multi-turn and local Qwen with shorter context; verify correctness and latency. Do not trigger a Windows download or installation until owner explicitly requests the final package.
4. Consider next: user-requested editable, local-only conversation notes and a review-before-saving mechanism; no automatic sensitive learning or unapproved external cloud sync. Keep UI minimal and voice-first.
5. Recheck GitHub CI + Render on each code SHA; never treat CI unit tests as live subjective conversation quality proof. Physically powered-off control, Apple entitlements, external Calendar/Email OAuth, actual volumetric holograms and hardware tests remain separate.


## Next after owner-reviewed chat notes
1. On a real iPhone Safari/PWA sign in to deployed ULTRON, have a multi-turn conversation, type/speak "Sohbet notu hazırla", inspect HAFIZA draft title and excerpt. Verify it is NOT saved before tapping NOTU KAYDET. Edit content, save, reopen, edit and delete with confirmation.
2. Start another conversation and verify the first conversation's notes do not appear there; check an unrelated user cannot access previews/notes. Verify ordinary "Kitabı özetle" stays a chat request, not a note preview.
3. Test privacy limits with genuinely sensitive-looking user messages; deterministic common-secret filters are NOT a substitute for guaranteed PII classification, so owner must review all excerpts before saving.
4. For Windows Qwen/Cloud Gemini continue improving real conversational and voice response quality; on actual hardware measure Turkish latency and interruption after user authorizes final Windows update. No local laptop install/download until the owner explicitly requests final package.
5. Investigate chat notes export/import or semantic overview only on specific request and with permission; never promote notes to model system instructions or automatic permanent personal memory. Preserve clean command-first interface.


## Next user-requested ULTRON development after safer Live audio playback
1. Test on real iPhone Safari/PWA, with microphone permission after user tap: ask for a two-sentence response; verify its last word is fully audible, UI does not say 'listening' while final WebAudio buffers are still queued, and no second browser SpeechSynthesis voice runs over Gemini Live.
2. Speak during a long Gemini Live response and verify Gemini's server interrupt or local RMS gate immediately stops playback, does not resume old chunks and recognizes the new user turn. Then mute/stop/close browser mid-playback and ensure no audio leak.
3. Test laptop single-speaker leader switching: phone output stops when desktop leads; on reconnect it should not replay stale audio. Check session-scoped transcript and approval-gated device tools remain intact.
4. Evaluate voice echo cancellation/threshold under real room noise and headphones. Consider exposing a private calibration diagnostic only after real recordings/tests; don't hardcode risky mic thresholds or claim flawless full-duplex conversation.
5. Continue safer real user tasks, per-chat edit/review and privacy tests while keeping the clean on-command UI. Windows laptop update/download only once the user explicitly requests final handoff.


## Next: single-speaker ownership hardware acceptance
1. Verify GitHub HEAD Cloud Queue PostgreSQL Integration and Scene Build Check at 4952ea5a6a44c041aebf5d87e21ce2184ad3e48d, verify Render LIVE at same code SHA.
2. User-authorized actual hardware testing later: with Windows desktop genuinely online and audible, phone receives a remote laptop task result and does NOT read it simultaneously via iOS TTS; it still shows the result in chat.
3. During phone Gemini Live with desktop reporting speaking=true, phone retains voice priority in UI; listen for actual duplicate desktop audio and debug Windows-side owner heartbeat if needed. Current phone-side policy cannot mute Windows physical speakers by itself.
4. Phone local Qwen one-tap microphone should take immediate UI priority even if earlier desktop speaker was leading. After stopping local voice, desktop presence refresh can regain speaker role without old WebAudio chunk replay or stale callback interference.
5. Stress overlapping /api/device-presence responses: only newest request should update phone speaker; server and user permission constraints still apply.
6. Real iPhone Safari, Gemini Live permissions, Windows microphone/speaker, Ollama performance and task replay are not verified. Do not install/update user's Windows files until they explicitly request final combined package.


## Next after tap-to-interrupt guarded local voice
1. Check the latest Render deployment dep-db5697jhu5js73djph4g for status live at code 70991ff6610e2cac631a2c1ec91d856588aa0cab; do not infer from GitHub success alone. Verify both Cloud/Scene jobs green, fixed old test.
2. Real iPhone Safari PWA + paired active Windows Qwen (when owner approves the final Windows update): tap mic, speak a long question, tap mic again while response is queued, confirm the old answer appears as text but does NOT begin speaking. Starting a new mic must stop old browser TTS immediately.
3. Test toggling speaker mute, sending typed chat while voice in-flight, hiding PWA and reopening; ensure no late local voice audio and no microphone use when backgrounded. Check desktop one-speaker handoff unaffected.
4. Keep the present deliberate Cloud local_chat queue behavior: tapping mic off is an audio stop, NOT a request to delete or cancel a real worker task; do not duplicate prompts via uncertain Gemini fallback. If user requests task cancellation, design a separately authenticated explicit cancel with approval and idempotent result semantics.
5. For genuine JARVIS quality, perform real latency, Turkish transcript accuracy and interrupt/reconnect measurements on owner devices when available; don't claim full-duplex natural human speech from CI-only tests. Continue advancing real features without installing Windows until requested.


## Next steps — make natural conversation measurably stronger, BEFORE other ULTRON features
1. Confirm Render latest deploy for functional code a6ce694ff35423f93a386140c7e1938a374ad162 is LIVE and inspect any deploy failure. Cloud/PostgreSQL and Scene CI are successful at exact SHA; no Windows installation.
2. Run 30–50 actual phone Gemini dialogues scored on Turkish naturalness, context continuity, corrections, hallucination avoidance and response time. Ask multiple referent follow-ups, abrupt topic shifts, explicit old-topic recall, concise/detailed mode, and "Bu sohbeti özetle"; keep all ratings reproducible and anonymized.
3. When owner requests final Windows installation, test actual Qwen4B FAST vs Qwen8B complex request inference latency and real answer quality on RTX2050 4GB/24GB RAM; 8B likely CPU offload and must not degrade everyday latency. Consider transparent opt-in detailed reasoning if too slow, without showing provider picker in normal UI.
4. Strengthen automatic contradictions / correction prioritization within the SAME conversation without treating old assistant guesses as confirmed owner facts. All untrusted chat/memory remains data, never tool instructions or elevated system role. No new sensitive auto-learning.
5. Avoid claiming JARVIS-level 100% or raising numerical readiness without measured provider/hardware quality. Keep user-requested focus on conversation intelligence; no hologram or UI changes and no Windows local download until final delivery.

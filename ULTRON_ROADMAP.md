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

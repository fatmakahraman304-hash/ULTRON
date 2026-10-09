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

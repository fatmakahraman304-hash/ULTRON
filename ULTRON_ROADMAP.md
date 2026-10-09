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

# MARK LV + ULTRON V22 birleştirme raporu

Tarih: 1 Ekim 2026. Teslim dizini: `outputs/MARK-ULTRON-MERGED`.

## Kaynak ve mimari

MARK LV çalışan ana uygulama olarak korundu. Özgün giriş noktası `mark_app.py` adıyla durur; `main.py`, süreçleri yöneten `integration/launcher.py` üzerinden açılır. MARK'ın Qt arayüzü, Gemini Live, avatar/lip-sync, ses aygıtları, aksiyonlar, tarayıcı ve masaüstü işlevleri korunmuştur. `ui.py` değiştirilmedi. Mevcut kişisel MARK yapılandırması taşındı; anahtar değeri rapora veya Git'e alınmadı.

ULTRON için `ULTRON-v22-ULTRON-WAKEWORD-READY.zip` temel alındı. `ULTRON-v22-final.zip` karşılaştırma kaynağıdır; ona özgü ek dosya bulunmadı. Özgün ZIP'ler değiştirilmedi. Kaynak karşılaştırması `SOURCE_DIFF.json` içinde yer alır.

ULTRON backend; planner, supervisor, uzun görevler, yerel LLM/model router, kod araçları, görev hafızası, scheduler, audit, sandbox, vault, OCR, connectors ve skills bileşenlerini sağlar. MARK içindeki dock ve `plugins/ultron_capability.py`, `integration/bridge.py` aracılığıyla aynı backend'e erişir. Bütün kaynak modüllerinin her harici hizmetiyle uçtan uca çalıştığı iddia edilmez; aşağıdaki testler doğrulanan kapsamı belirtir.

Backend yalnız loopback üzerinde dinamik port kullanır. Her başlatmada üretilen oturum anahtarı HTTP ve WebSocket sınırında doğrulanır. Web paneli, URL fragment'ındaki anahtarı sunucu günlüklerine göndermeden HttpOnly/SameSite oturum çerezine dönüştürür. Çerezli yazma isteklerinde Origin doğrulanır. Desktop ve mobile frontend aynı backend'den sunulur. MARK ana ekran olmaya devam eder.

## Düzeltilen sorunlar

- `OpenWakeWordEngine` içindeki erişilemeyen model başlatma kodu düzeltildi; `self.models` her durumda tanımlı. Eksik model çökme yaratmaz.
- Özel ULTRON uyandırma modeli sağlanmalıdır; başka kelimeye ait model kullanılmaz. Model yokken manuel uyandırma kullanılabilir.
- Mikrofon, hoparlör ve canlı wake-word sahibi MARK'tır. Birleşik kipte ULTRON otomatik dinleme/proaktif başlangıcı ve ikinci canlı ses/PTT açılması engellenir.
- Model router yalnız mevcut listeden model seçer; eksik primary/config modeli kurulu modele düşer. Çoklu model seçimi de kurulu listeyle sınırlanır. Çevrimdışı durumda sınırlı deneme ve görünür hata vardır.
- Faster-Whisper CUDA DLL/yükleme başarısızlığında CPU int8 kullanır; gerçek tiny model ve transcribe çalıştırması doğrulandı.
- Kaldırılmış Piper model URL'si yerine mevcut Türkçe `tr_TR-dfki-medium` modeli/metadata kullanıldı. Gerçek WAV sentezi yapıldı. Model kaynağı: https://huggingface.co/rhasspy/piper-voices/tree/main/tr/tr_TR/dfki/medium
- Windows SQLite bağlantıları işlem sonrasında kapanır. Kalıcı bağlantılar test finalizer'ında kapatılır; zorla kesilen WAL yazıcısı sonrası geçici disk I/O hatası sınırlı yeniden denemeyle ele alınır. WAL dosyaları silinmez.
- Shell araçları doğru venv Python'unu PATH üzerinden bulur. Görevlerde otomatik güvenlik onayı verilmez; `approved=true` gönderen istemcinin yazma isteği gerçek testte reddedildi.
- Connector HTTP/yerel ICS yardımcıları uygulandı. Geçerli HTTP fixture'larıyla hava durumu ve takvim ayrıştırması test edildi.
- Qt worker arayüz kapandıktan sonra sinyal gönderimini güvenle sonlandırır; gerçek köprü hatası kullanıcıya gösterilir.
- Vite yapılandırması `runner` ile yüklenir; sınırlı Windows ortamında disk köküne gereksiz config taraması önlenir. Mobil asset yolları göreli hale getirildi.
- Desktop HUD, backend'in `label/detail` alanlarını `name/description` alanlarına eşler. Boş görünen yetenek adları düzeltildi; READY sayısı gerçek backend durumundan hesaplanır.

## Kurulum ve süreç yönetimi

Python **3.12.14**, tek `.venv` içinde kullanıldı. Çalışan runtime keşfedildi; Windows `py` launcher'ının kurulu Python bulamaması engel olmaktan çıkarıldı. Başlatıcıda kullanıcıya özel mutlak Python yolu yoktur. `scripts/bootstrap.ps1` venv, proje runtime'ı, PATH ve yaygın kullanıcı kurulumlarını kontrol eder; Python yoksa resmi imzalı 3.12 kurulumu proje içine yapılabilir.

MARK gereksinimleri yanında `requirements-local-ai.txt`, `requirements-voice.txt`, `requirements-dev.txt` vardır. Wake model eğitimi günlük kurulumdan ayrılmıştır. Windows native uyumluluğu için numpy 2.2.6, scipy 1.15.3, scikit-learn 1.6.1, av 16.1.0 ve charset-normalizer 3.4.4 seçildi. `pip check` başarılıdır. npm lock dosyalarıyla `npm ci` kullanılır; npm/pip/Chromium önbellekleri proje içinde tutulur.

`INSTALL.bat` tekrar çalıştırılabilir; zorunlu bir adım başarısızsa çıkış kodu 1 ve FAIL sonucu üretir. Optional model/tarayıcı sorunu WARN olarak kalır. Mevcut model dosyaları tekrar indirilmeden yüklenerek doğrulanır.

`START.bat` backend health için süre sınırlı bekler, gerçek MARK penceresini açar. Windows dosya kilidi ikinci örneği engeller. Graceful shutdown, gerektiğinde yalnız başlatıcının kendi child süreçlerini sonlandırma ve Windows Job Object ile süreç ağacını temizleme vardır. ULTRON açılamazsa normal kullanımda MARK uyarıyla degraded açılabilir. Günlüklerde boyut sınırlı döndürme uygulanır.

Eski ULTRON başlangıç/kurulum batch dosyaları birleşik giriş noktalarına yönlendirilmiştir. Eski Electron build/autostart yardımcıları kaynak olarak korunur; bu teslimde çalıştırılmadı ve birleşik kurulum için kullanılmaz.

## Doğrulama kapsamı

Son tam regresyon: **974 PASS, 3 SKIP, 0 FAIL**, 78,67 saniye. Son kurulum sırasında entegrasyon paketi: **20 PASS**. Paket anlık görüntüsü `requirements-resolved-windows.txt` içinde; otomatik test çıktısı `logs/pytest-release.txt` içindedir.

Atlanan üç kaynak testi: deterministik parser'ın tanımadığı örnek; kullanıcı Picovoice anahtarının bulunmaması; ekranın olmadığı varsayımına dayanan testin gerçek ekran bulunan ortamda uygulanmaması. Gerçek uygulama exception'ları bu nedenlerle gizlenmedi.

Gerçek backend süreciyle HTTP, WebSocket, core bileşenler, MARK köprüsü, bellek ekleme/okuma/silme, hesaplama aracı, onaysız yazmanın reddi, yanlış token'ın reddi, çift örnek engeli ve child cleanup doğrulandı. Web panelinin cookie, CSRF ve her iki frontend asset erişimleri gerçek HTTP ile test edildi. Ayrıca Chromium'da her iki panel açıldı, boş olmayan yetenek etiketleri ve oturumlu health erişimi doğrulandı; **0 JavaScript hatası**. Kanıt: `logs/browser-release.json`, `logs/frontend-desktop.png`, `logs/frontend-mobile.png`.

Desktop ve mobile frontend için son `npm ci` + `npm run build` başarılı. Desktop bundle boyutu uyarısı vardır; build hatası yok. Compileall, core imports ve pip check başarılı.

Ollama API şu modelleri bildirdi: `qwen2.5-coder:7b`, `qwen3:4b`, `qwen3:8b`, `llava:7b`. Metin sorgusu gerçek MARK→ULTRON→Ollama yolundan çalıştırıldı. Vision testi gerçek görüntüyü llava'ya gönderir; sonucu final DOCTOR kaydındadır.

## Sınırlar

- Özel ULTRON uyandırma modeli sağlanmalıdır; başka kelimeye ait model kullanılmaz. Model yokken manuel uyandırma kullanılabilir.
- Gemini yapılandırması ve Live modülleri doğrulandı; insanla canlı konuşma, fiziksel mikrofon/hoparlör ses kalitesi ve lip-sync görüşmesi uçtan uca doğrulanmadı.
- Startup smoke kipinde gerçek Qt penceresi açılır; bu test Gemini oturumunu başlatmaz. Normal START aynı kısıtlamayı uygulamaz.
- Masaüstü ekran yakalama ve kamera erişimi bu otomasyon oturumunda kısıtlı olabilir; cihaz bulunması görüntü/ses kalitesi testi değildir. OCR bilinen bir görsel üzerinde gerçekten çalıştırıldı.
- Harici servis anahtarları gerektiren connector'lar ayrıca yapılandırma ister. Hiçbir eksik credential/model varmış gibi gösterilmedi.
- Önceki sandbox dışı DOCTOR çalıştırma isteği otomatik izin denetimi tarafından reddedildi. İzin verilen yerel kontroller tamamlandı; ekran erişim sınırı PASS sayılmadı.
- Bu oturumda Ollama CLI dosyasına erişim kısıtlıdır; çalışan API ve gerçek metin/görüntü inference başarılıdır. Önceki aşamada `ollama --version` ve `ollama list` de çalıştırılmıştır.
- WebSocket'li tarayıcı kapanışında Windows asyncio, bir kez `ConnectionResetError 10054` callback günlüğü üretti. Tarayıcı testinin temizlenmesi ve backend kapanışı başarılıydı; bu kayıt startup fatal hatası değildir. Geçmiş denemelerin günlükleri audit amacıyla korunur.

## Final sonuç

| Kontrol | Sonuç |
|---|---|
| INSTALL.bat tekrar kurulum | PASS, exit 0; optional Ollama CLI erişim WARN |
| Python compile / core imports | 0 hata |
| pip check | 0 conflict |
| Pytest | 974 PASS / 3 SKIP / 0 FAIL |
| Desktop build / mobile build | PASS / PASS |
| Chromium desktop / mobile | PASS / PASS; 0 JavaScript hatası |
| Config JSON parse | 7 dosya PASS |
| İlk START.bat -Smoke | PASS, exit 0; gerçek Qt UI + backend health |
| İkinci START.bat -Smoke | PASS, exit 0; stale process/port yok |
| Başlangıç fatal traceback | 0 |
| İki çevrim sonrası backend PID | İkisi de sonlanmış |
| DOCTOR.bat | **32 PASS / 2 WARN / 0 FAIL**, exit 0; metin ve görüntü inference PASS |

Başlangıç kanıtları `logs/startup-cycle-1.json`, `logs/startup-cycle-2.json`, `logs/start-cycle-1.txt`, `logs/start-cycle-2.txt` ve `logs/mark-ui-cycle-2.png` içinde. Makine tarafından üretilen kurulum sonucu `logs/install-result.json` içindedir. Kurulum günlüğü geçmiş başarısız denemeleri de içerir; son çıkış ve sonuç JSON'u nihai durumu belirtir.

Günlük kullanım için **START.bat** dosyasına çift tıklayın. Ayrıntılı kullanım: `QUICK_START_TR.md`.

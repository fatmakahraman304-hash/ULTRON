# ULTRON Native iPhone Companion

Bu proje, web/PWA sürümünün yapamadığı uzun süreli ses oturumunu native iOS uygulamasına taşır.

## Şu an eklenenler

- ULTRON Cloud parola girişi ve Keychain saklama.
- Aynı Cloud `/api/live` WebSocket hattına bağlanma.
- Kalıcı native ses oturumu kimliği; reconnect sonrası konuşma bağlamı korunur.
- Mikrofonu 16 kHz PCM16 olarak Cloud/Gemini Live hattına gönderme.
- 24 kHz ULTRON sesini native olarak oynatma.
- `AVAudioSession.playAndRecord` + `UIBackgroundModes=audio`.
- Uygulama arka plandayken aktif ses oturumunu koruma.
- Ağ/WebSocket kopunca otomatik yeniden bağlanma ve ping.
- Cloud'a native iPhone presence heartbeat gönderme.
- Ses kesintileri ve kulaklık/Bluetooth route değişimlerinden sonra toparlanma.
- Arka planda gelen telefon komutunu güvenli kuyruğa alma.
- Komut arka planda çalıştırılamıyorsa yerel bildirim oluşturma; ULTRON öne gelince devam etme.
- YouTube, Spotify, WhatsApp, Instagram, Chrome, Haritalar ve desteklenen URL intentleri.
- Siri/App Shortcuts:
  - “ULTRON dinlemeye başla”
  - “ULTRON dinlemeyi durdur”
- Özel URL şeması:
  - `ultron://start`
  - `ultron://stop`
  - `ultron://app?name=youtube`
  - `ultron://youtube?q=...`
  - `ultron://spotify?q=...`
  - `ultron://whatsapp?text=...`

## iPhone'a kurulum

1. Bir Mac'te Xcode ve XcodeGen kur.
2. Terminal:
   ```bash
   cd ios/ULTRONMobile
   xcodegen generate
   open ULTRONMobile.xcodeproj
   ```
3. Xcode > Signing & Capabilities bölümünde kendi Apple Team hesabını seç.
4. Bundle Identifier çakışırsa `com.ultron.mobile` değerini kendi benzersiz identifier'ınla değiştir.
5. Background Modes içinde Audio açık olduğunu doğrula.
6. iPhone'u bağla, hedef cihaz olarak iPhone'u seç ve Run'a bas.
7. İlk açılışta mikrofon ve bildirim izinlerini ver.
8. ULTRON Cloud parolanı bir kez gir.
9. **SÜREKLİ DİNLEMEYİ BAŞLAT** düğmesine bas.

Parola Keychain'de saklanır; kaynak koda veya repoya yazılmaz.

## Otomatik build kontrolü

Repo içindeki iOS workflow'u XcodeGen ile projeyi üretip iOS Simulator hedefinde kod imzasız derleme kontrolü yapar. Bu test compile hatalarını yakalamak içindir; gerçek iPhone IPA'sı için Apple signing gerekir.

## Arka planda davranış

Dinleme açıkken native ULTRON aktif bir audio session kullanır. iOS uygulamayı arka plana aldığında sesli bağlantının sürmesi hedeflenir. Bağlantı koparsa uygulama artan gecikmeyle otomatik reconnect dener.

Cloud'dan başka bir uygulamayı açma komutu ULTRON arka plandayken gelirse iOS üçüncü taraf uygulamanın kendiliğinden başka uygulamayı öne getirmesine izin vermeyebilir. Böyle durumda komut kaydedilir ve bildirim gösterilir; ULTRON yeniden aktif olduğunda bekleyen komut devam eder.

## iOS sınırları

Native uygulama web sürümünden çok daha güçlüdür ama iOS sandbox sınırlarını aşmaz:

- YouTube uygulamasındaki **Reklamı Atla** düğmesine ULTRON otomatik dokunamaz.
- WhatsApp'ın kendi ekranındaki **Gönder** düğmesine kullanıcı etkileşimi olmadan basamaz.
- Başka bir uygulamanın ekranını gizlice okuyamaz veya kontrol edemez.
- Arka plandaki bir üçüncü taraf uygulama başka bir uygulamayı her durumda sessizce öne getiremez.

ULTRON; sesi arka planda sürdürebilir, mesaj/arama hedefini hazırlayabilir, desteklenen deep link/App Intent/Shortcuts işlemlerini çalıştırabilir ve izin verilen otomasyonları cihazlar arasında devam ettirebilir.

## 0.3 — Siri'den bilgisayar görevi ve iPhone Kestirmeler köprüsü

- App Intent: Siri/Kestirmeler içindeki **ULTRON Bilgisayara Görev Gönder**, Cloud'a kimlik doğrulamalı agent_task kaydı açar. Örnek: **Hey Siri, ULTRON bilgisayara görev gönder**. Siri görev metnini sorabilir.
- Native ekrandaki **BİLGİSAYARA GÖNDER** bölümü aynı köprüyü kullanır. Kuyruk ID'si görevin işlendiği anlamına GELMEZ.
- Cloud parolası ilk kez uygulama içinden girilir, Keychain'de saklanır. Siri komutu login yoksa güvenle hata verir.
- Native iOS, Cloud Live üzerinden gelen ios_action ve ios_shortcut olaylarını yalnızca **ULTRON Bridge** adlı Kestirmeye yönlendirebilir. Manuel **DEVAM ET** düğmesi ve iOS izinleri gereklidir; modelin istediği keyfi kestirme otomatik çalışmaz.
- Kestirmeler uygulamasında ULTRON Bridge adında kestirme oluştur. Gelen text girdisini JSON/Sözlük olarak çöz. Güvenilir action, target, value alanlarını denetleyerek sistemin izin verdiği eylemleri bağla.
- iOS farklı uygulamaların ekranına sınırsız erişim, genel açık mikrofon veya zorla kapatıldıktan sonra sonsuz arka plan çalışmayı garanti etmez.
- Simulator/unsigned Xcode build CI doğrulanmalı; gerçek Siri/iPhone/Cloud-laptop çalışması ayrıca gerçek cihaz gerektirir.

## Siri komutları — native v0.3 (09.10.2026)

- **Hey Siri, ULTRON soru sor**: ULTRON'un ortak Cloud sohbet/hafızasından metin cevabı döndürür (iOS App Intent, mikrofon oturumu bağımsız).
- **Hey Siri, ULTRON bilgisayara görev gönder**: Senden görev metni ister; onu Windows ULTRON'un onay mekanizmasını koruyarak Cloud kuyruğuna bırakır.
- **Hey Siri, ULTRON son görev ne durumda**: Cloud kuyruğundaki son masaüstü görevinin kaydedilmiş durumunu söyler. Kuyruğa alındı veya masaüstüne teslim edildi bildirimleri, işin tamamlandığı anlamına gelmez.
- Native ULTRON içinde aynı görevi yazıyla gönderme ve son durumunu öğrenme düğmeleri vardır.
- Cloud Live üzerinden gelen iPhone sistem komutları yalnızca adı ULTRON Bridge olan kullanıcı tarafından hazırlanmış Kestirmeler akışına gider. İşlem, iPhone ekranında DEVAM ET onayı verilmedikçe başlamaz.
- Bekleyen komutun metni artık UserDefaults yerine cihazın kendi Keychain'inde AfterFirstUnlockThisDeviceOnly erişim kuralıyla tutulur; eski kayıt taşınır.
- Siri arka plan tetikleyicisi sistemin izin verdiği kısa App Intent işlemidir. Mikrofonun sürekli çalışması, sistemin Force Quit veya askıya alma durumları ve üçüncü taraf uygulama ekranları için sınırsız erişim vaat edilmez.
- Native iOS build doğrulaması: kod commit 0b4751a5d7c5f6ceb4642af4eb413f6fb0ca16b9 için GitHub Actions run 37917812910 SUCCESS. Beş statik güvenlik/regresyon testi, iOS Simulator ve imzasız iPhone derlemesi, paketleme/artifact upload başarılı. Statik testler gerçek iPhone çalışmasını doğrulamaz.
- Gerçek iPhone'a kurulum için Mac/Xcode, Apple signing ve Cloud login gereklidir. İşletim sistemi ve cihaz izinlerini otomatik aşmaz.

## TestFlight ile kablosuz kurulum (2026-10-09)

**Windows laptop + iPhone, USB kablo gerekmiyor.** GitHub'da yeni `.github/workflows/ios-testflight.yml` *sadece manuel tetiklemeyle* Apple Developer hesabının imzalı IPA'sını hazırlayıp TestFlight'a göndermek üzere eklendi. Apple Developer Program üyeliği, App Store Connect API key, App Store distribution .p12 ve provisioning profile olmadan çalışmaz; bu gizli bilgiler yalnızca GitHub `testflight` environment secrets içinde tutulur. Workflow varsayılan dala alınıp manuel çalıştırılabilmelidir. **Kurulum ve kayıt adımları:** [TESTFLIGHT_KABLOSUZ_TR.md](TESTFLIGHT_KABLOSUZ_TR.md). Bu yol canlı Apple hesabında henüz denenmedi; önce üyelik ve sertifikalar hazır olmalı.

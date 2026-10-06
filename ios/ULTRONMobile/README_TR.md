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

# ULTRON Native iPhone Companion

Bu klasör PWA'nın yapamadığı arka plan ses oturumunu native iOS uygulamasına taşımak için başlangıç projesidir.

## Ne yapar?

- ULTRON Cloud'a giriş yapar ve oturum çerezini saklar.
- `/api/live` WebSocket hattına bağlanır.
- Mikrofonu 16 kHz PCM16 olarak Gemini Live hattına yollar.
- 24 kHz ULTRON sesini oynatır.
- `UIBackgroundModes = audio` ve `AVAudioSession.playAndRecord` kullanarak uygulama arka plana geçtiğinde ses oturumunun devam etmesine uygun şekilde yapılandırılmıştır.
- Ön plandayken Cloud'dan gelen uygulama açma / arama intentlerini çalıştırabilir.

## Kurulum

1. Mac'te Xcode ve XcodeGen kur.
2. Bu klasörde `xcodegen generate` çalıştır.
3. Oluşan `ULTRONMobile.xcodeproj` dosyasını Xcode ile aç.
4. Signing & Capabilities altında kendi Apple Team hesabını seç.
5. Background Modes > Audio, AirPlay, and Picture in Picture açık olmalı.
6. Uygulamayı iPhone'a kur.
7. ULTRON Cloud parolasını bir kez gir ve Sürekli Dinlemeyi Başlat.

## iOS sınırları

Native uygulama arka planda mikrofon/ses oturumunu sürdürebilir; ancak iOS üçüncü taraf uygulamaların başka bir uygulamanın ekranına dokunmasına izin vermez. Bu nedenle:

- YouTube uygulamasındaki “Reklamı atla” düğmesine otomatik basılamaz.
- WhatsApp ekranındaki Gönder düğmesine ULTRON tarafından sessizce basılamaz.
- Arka plandaki ULTRON başka bir uygulamayı kendiliğinden öne getiremez.

ULTRON mesaj metnini hazırlayabilir, arama ekranını açabilir ve iOS'un izin verdiği App Intents / Shortcuts yollarını kullanabilir.

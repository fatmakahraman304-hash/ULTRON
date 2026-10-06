# Windows'tan iPhone'a ULTRON Kurulumu

Bu proje için GitHub Actions artık gerçek iPhone hedefi için **unsigned IPA** üretir.

## 1. IPA'yı indir

GitHub reposunda:

1. **Actions** sekmesini aç.
2. **Native iOS Build** workflow'unu aç.
3. Son başarılı run'ı aç.
4. **Artifacts** bölümünden `ULTRONMobile-unsigned-IPA` paketini indir.
5. ZIP'i aç; içinde `ULTRONMobile-unsigned.ipa` bulunur.

## 2. IPA'yı kendi Apple hesabınla imzala ve kur

Windows'ta unsigned IPA doğrudan iPhone'a kurulamaz. IPA'nın kendi Apple hesabınla yeniden imzalanması gerekir.

Bunu Sideloadly veya AltStore/AltServer gibi bir iOS sideload aracıyla kendi bilgisayarında yapabilirsin.

Genel akış:

1. iPhone'u USB ile bilgisayara bağla.
2. iPhone'da bilgisayara **Güven** de.
3. Seçtiğin sideload aracını aç.
4. `ULTRONMobile-unsigned.ipa` dosyasını seç.
5. Kendi Apple hesabınla cihaz için imzala.
6. Uygulamayı iPhone'a yükle.
7. iPhone gerekiyorsa geliştirici uygulamasına güvenmeni ister; Ayarlar'daki ilgili geliştirici/gizlilik ekranından onayla.

**Apple hesabı parolanı veya doğrulama kodunu ChatGPT'ye, GitHub reposuna veya ULTRON kaynak koduna yazma.** İmzalama işlemini yalnızca kendi bilgisayarındaki güvenilir araçta yap.

## 3. İlk açılış

1. ULTRON'u aç.
2. Mikrofon iznine izin ver.
3. Bildirim iznine izin ver.
4. ULTRON Cloud parolasını gir.
5. **SÜREKLİ DİNLEMEYİ BAŞLAT** düğmesine bas.
6. ULTRON'u arka plana alıp ses oturumunu test et.

## 4. Beklenen davranış

- ULTRON native uygulama arka plandayken aktif ses oturumunu korumaya çalışır.
- Cloud bağlantısı koparsa otomatik yeniden bağlanır.
- ULTRON konuşabilir ve mikrofondan ses almaya devam edebilir.
- Arka planda iOS'un izin vermediği bir uygulama açma komutu gelirse komut kuyruğa alınır ve bildirim gösterilir.
- ULTRON tekrar öne geldiğinde bekleyen komut devam eder.

## iOS sınırı

Bu native sürüm bile iOS sandbox'ını aşmaz. YouTube'daki **Reklamı Atla** düğmesine otomatik dokunamaz veya WhatsApp'ın kendi arayüzünde kullanıcı etkileşimi olmadan **Gönder** düğmesine basamaz.

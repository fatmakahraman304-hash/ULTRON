# ULTRON'u iPhone'a kablosuz TestFlight ile kurma (2026-10-09)

**Bu yol için USB kablosu gerekmez.** App Store Connect/TestFlight yayını Apple Developer Program üyeliğine (yıllık 99 USD veya yerel eşdeğeri), Apple imzalama kimlik bilgilerine ve Apple beta işleme sürecine bağlıdır. GitHub'da kodun başarılı *imzasız* derlenmesi, uygulamanın TestFlight'a yüklendiği anlamına gelmez.

## Aşama A — Apple hesabı (cihaz: iPhone veya Windows tarayıcısı)

1. https://developer.apple.com/programs/enroll/ adresinden Apple Developer Program üyeliğini kontrol et. Ücretli üyelik yoksa TestFlight yayınlayamazsın. Üyelik ödeme ve doğrulamasını sadece Apple üzerinde yap.
2. https://developer.apple.com/account/resources/identifiers/list üzerinden tekil, sana ait bir uygulama kimliği (Bundle ID) kaydet (örnek: `com.seninhesabin.ultron.mobile`; bu sadece örnektir). **Kaydedilen Bundle ID, bütün adımlarda aynı olmalı.**
3. https://appstoreconnect.apple.com/ → **Apps → + → New App**; platform **iOS**, ad **ULTRON**, dil ve SKU seç; kaydettiğin Bundle ID'yi seç. İlk sürüm için Apple sözleşmelerinin kabul edilmiş olması gerekir.
4. App Store Connect → **Users and Access → Integrations → App Store Connect API**. Yetkin varsa Team API anahtarı üret (uygun en az izinli rol, genellikle **App Manager**); `.p8` anahtarını *bir kez* indir. **Issuer ID** ve **Key ID** bilgisini ayrı not al. Anahtarı sohbete, repoya, GitHub issue'ya ya da commit'e koyma.
5. Apple Developer portalında **Apple Distribution** sertifikası ve bu sertifikaya/Bundle ID'ye bağlı **App Store Connect** provisioning profili gerekir. Sertifikanın **özel anahtarıyla birlikte** `.p12` dosyası olarak dışa aktarılmış olması zorunludur; yalnızca `.cer` dosyası imzalama için yeterli değildir. Gerekiyorsa bir Mac'te Keychain Access veya Apple'ın resmi/Apple-Actions kurulum yardımcılarıyla bir kerelik hazırlanır.

## Aşama B — GitHub ayarları (cihaz: Windows laptop)

1. https://github.com/fatmakahraman304-hash/ULTRON adresini aç.
2. Bu TestFlight workflow'u önce `feat/ultron-cloud-shared-memory` dalında hazırlanmıştır. **GitHub Actions üzerindeki Run workflow düğmesi için workflow dosyasının ayrıca varsayılan dalda (`main`) bulunması gerekir.** Güvenlik ve diğer değişiklikleri inceleyip bir pull request/merge ile varsayılan dala eklemeden yayını başlatmayı deneme.
3. Repository → **Settings → Environments → New environment** → `testflight` oluştur. Mümkünse gerekli onay veren kişi/branch koruması ekle. En azından bu ortamı sadece bilerek elle başlatılan yayınlar için kullan.
4. Ortamın **Variables** bölümüne şu 5 değişkeni koy:
   - `APPSTORE_TEAM_ID`: Apple Developer Team ID.
   - `APPSTORE_BUNDLE_ID`: adım A'da seçtiğin tekil Bundle ID.
   - `APPSTORE_PROFILE_NAME`: App Store provisioning profilinin **tam adı**.
   - `APPSTORE_ISSUER_ID`: App Store Connect API Issuer ID.
   - `APPSTORE_API_KEY_ID`: App Store Connect API Key ID.
5. **Secrets** bölümüne (hiçbirini public variable yapma):
   - `APPSTORE_API_PRIVATE_KEY`: `AuthKey_XXXX.p8` dosyasının **tam içeriği**.
   - `APPSTORE_CERTIFICATES_FILE_BASE64`: Apple Distribution özel anahtarıyla birlikte verilmiş `.p12` dosyasının Base64 içeriği.
   - `APPSTORE_CERTIFICATES_PASSWORD`: `.p12` dışa aktarma parolası.
6. Windows PowerShell'de kendi bilgisayarında `.p12` Base64 üretmek için, dosyanın yolunu kendi dosyanla değiştir:
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\Users\<kullanici>\Downloads\ultron-distribution.p12"))
   ```
   Çıktıyı **yalnızca** GitHub secret alanına yapıştır. PowerShell çıktısını, özel anahtarı veya parolayı buraya gönderme.

## Aşama C — TestFlight beta yayını (cihaz: Windows tarayıcısı)

1. Yukarıdaki bilgiler hazır ve workflow varsayılan daldaysa repo → **Actions → ULTRON iPhone TestFlight → Run workflow**.
2. `testflight` ortamı onay istiyorsa kendi GitHub onay ekranında kontrol et.
3. Workflow önce gereksinimleri kontrol eder. Eksik credential varsa güvenli biçimde **FAIL** olur ve Apple'a yayın yapmaz.
4. Daha sonra Swift/XcodeGen testleri, Apple Distribution sertifikasını içe alma, provisioning profili indirme, Apple'ın şartlarına göre **imzalı IPA arşivleme**, App Store Connect'e yükleme adımlarını yürütür. Kaynak olarak mevcut ULTRON ikonunu işler. Hata olursa logları incele; sonuç başarılı olmadan 'TestFlight yayınlandı' deme.
5. Apple işlemeyi tamamladıktan sonra https://appstoreconnect.apple.com/ → **Apps → ULTRON → TestFlight**. Apple'ın istediği beta açıklaması, test bilgileri, uygun şifreleme beyanları ve diğer metadata alanlarını doldur.
6. **Internal Testing** grubu oluşturup kendi Apple hesabını gerekli App Store Connect rolüyle testçi olarak ekle. Harici testçi davetinde Beta App Review gerekebilir.

## Aşama D — iPhone'a kablosuz yükle (cihaz: iPhone 14 Pro Max)

1. App Store'dan **TestFlight** uygulamasını yükle.
2. Apple'ın e-posta daveti veya TestFlight davet bağlantısını aç ve beta davetini kabul et.
3. TestFlight → ULTRON → **Yükle**.
4. ULTRON'u açıp Cloud parolasıyla giriş yap; mikrofon/bildirim izinlerini ver; önce normal sesli konuşmayı, sonra Siri App Shortcuts, en son iOS arka plan davranışını test et.
5. ULTRON'un Windows görevi alabilmesi için dizüstündeki yerel ULTRON'un Cloud'a bağlanması gerekir; iPhone ve Windows izinleri ayrı ayrı geçerlidir.

## Sınırlar ve bekleyen doğrulamalar

- Mevcut `Native iOS Build` workflow'u unsigned IPA üretir; **o IPA'yı TestFlight'a yüklemek yeterli değildir**.
- TestFlight yüklemesi için Apple üyeliği, signing materyali ve App Store Connect app kaydı olmadan release workflow'unu başarılı çalıştırmak mümkün değil.
- Apple'ın beta işlemeyi/uygunluğu onaylaması gerekebilir. Bu depoda gerçek Apple hesabı, kod imzalama, TestFlight yüklemesi veya fiziksel iPhone testi henüz yapılmadı.
- iOS üçüncü taraf uygulamaların tüm ekranlarını veya sürekli mikrofonu kontrol etmeye sınırsız izin vermez. ULTRON yalnızca kullanıcı izinlerinin ve iOS App Intents/Kestirmeler/arka plan ses kurallarının desteklediği eylemleri sunar.

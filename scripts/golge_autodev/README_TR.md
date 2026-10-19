# GÖLGE Autonomous Development V1 — gerçek durum

Bu aşama **otomatik, sınırlı kod değişikliği teklifi** altyapısıdır. Tam güvenli
kendi kendine yazılım dağıtımı değildir; asla öyle gösterilmemelidir.

## Uçtan uca akış

1. Zamanlanmış GitHub Actions görevi, Render'a bağlı
   `feat/ultron-cloud-shared-memory` dalındaki **son SHA'yı sabitler**.
2. `goals.json` içindeki bilinen eksiklerden birini seçer; mevcut başka bir
   `GOLGE-AUTODEV:` PR'sı açıksa yinelenen PR oluşturmaz.
3. Yapılandırılmış Gemini modeline yalnızca seçilmiş iki Python dosyasının
   sınırlı kaynak bağlamını verir. Başka dosya/komut/izin isteği modele geçmez.
4. Yalnızca kayıtlı iki yolu değiştirebilen tam dosya önerisi alır. Geçersiz
   JSON, gizli bilgi, symlink, dış dizin, güvenlik dosyası veya test eksikse reddeder.
5. Üretilen kod **model anahtarının olmadığı ve yazma yetkisi bulunmayan**
   bağımsız CI işinde uygulanır, derlenir ve test edilir.
6. Testler geçerse ayrı bir iş yalnızca sınırlandırılmış dosyaları commit ederek
   bir **taslak** GitHub PR açmayı dener. Bu iş model çıktısını çalıştırmaz.
7. **Birleştirme, Render dağıtımı, Windows cihazına yükleme veya kendiliğinden
   izin genişletme yoktur.** Bunlar tamamlandı diye raporlanmaz.

## İlk defa etkinleştirme

- Üretim PR'ını inceleyip gerekli testleri geçirdikten sonra uygulayın.
- GitHub `schedule` sadece **varsayılan dalda** (bu repoda `main`) bulunan
  workflow dosyasıyla tetiklenir. Dolayısıyla üretim dalındaki PR tek başına
  zamanlayıcıyı etkinleştirmez. Onaylı workflow'un ayrıca `main` dalına
  güvenli şekilde alınması gerekir; `main` ve üretim dalının diğer kodlarını
  birbirine karıştırmayın.
- GitHub > Settings > Secrets and variables > Actions altına
  `GOLGE_AUTODEV_GEMINI_API_KEY` repository secret'ı girilir. Mevcut Render
  `GEMINI_API_KEY` otomatik olarak GitHub'a kopyalanmaz. Gizli anahtarı
  workflow YAML'ına veya sohbete yapıştırmayın.
- İsteğe bağlı repository variable: `GOLGE_AUTODEV_MODEL`.
  Kodda `gemini-2.5-flash` başlangıç değeri vardır; sağlayıcının o an
  gerçekten desteklediği bir model seçilmesi gerekir.
- GitHub Actions izinleri otomasyonun ayrı bir dal oluşturmasına ve PR açmasına
  izin vermelidir. Bu izin yoksa otomasyon başarısızdır, `success` değildir.
- Üretim/varsayılan dal aktivasyonuna kadar `workflow_dispatch` veya
  `schedule` çalıştırılmış gibi iddia edilmez. Otomatik PR açıldıktan sonra
  `GITHUB_TOKEN` kaynaklı PR'ların başka CI akışlarını kendiliğinden
  başlatmayabileceğini dikkate alın; bağımsız CI ayrıca doğrulanmalıdır.

## Laptopta mevcut ücretsiz Qwen ile kullanım

Sadece **temiz, yetkilendirilmiş geliştirici checkout'unda** ve proje kökünde:

```powershell
python scripts/golge_autodev/engine.py plan --base-sha <EXACT_40_CHAR_SHA>
python scripts/golge_autodev/engine.py generate --provider ollama
python scripts/golge_autodev/engine.py validate
```

Bu komutlar `golge-autodev-proposal.json` üretir; çalışır uygulamayı
değiştirmez. `apply` yalnızca izole test checkout'unda kullanılmalıdır.
Ollama `127.0.0.1:11434` üstünden erişilemezse veya model kurulu değilse
gerçek hata döner. Laptop kapalıyken yerel model işlemi yapıldığı iddia edilmez.

## Dürüst sınırlar / V2 backlog

- Henüz kendiliğinden yeni görev keşfeden genel-yetenek motoru değildir;
  `goals.json` içindeki güvenli, sınırlı iş kuyruğunu kullanır.
- Gerçek model kalite değerlendirmesi, Windows/iPhone/TTS/Render canary,
  üretime otomatik birleştirme ve otomatik geri alma **NOT_RUN / NOT_IMPLEMENTED**.
- Değişen ses/multimodal kodları gerçek mikrofon veya model üretimini kesmeyi
  kanıtlamaz. İzole deterministik testler bu iddia için yeterli değildir.
- İkinci aşama: CI arızaları ve doğrulanmış capability gap'lerinden güvenli
  görev keşfi, kaynak başına daha güçlü gerçek testler, başarısız önerilerde
  en fazla iki deneme, testten geçmiş ve insan onaylı politika paketlerinin
  kısıtlı otomatik dağıtımı ve Rollback Canary.
- Mevcut approval gate, audit log, risk sınıflandırma, güvenlik çekirdeği,
  iPhone PWA sade arayüz ve cihaz sahipliği korunur.

## Model hizmeti ve ücret

GitHub Models API artık kullanılamadığı için model sağlayıcısı olarak
tasarlanmamıştır. Gemini erişimi sağlayıcı kota ve maliyet koşullarına bağlıdır.
GitHub Actions'ın çalışması gerçek kod üretildiği anlamına gelmez.

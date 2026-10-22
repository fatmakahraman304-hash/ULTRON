# GÖLGE'nin kendi kodunu geliştirmesi

GÖLGE'ye sohbette “Gölgeye bir şeyini değiştir” veya istediğin özelliği açıkça söyle. İstek eşleşmiş Windows laptop çevrimiçiyse yerel Qwen ile sınırlı bir patch taslağı üretir. Diff'i gösterir; sen `onaylıyorum` demeden dosyalara dokunmaz.

Onaydan sonra laptop şu kontrolleri çalıştırır: TypeScript, üretim derlemesi, Python derlemesi, backend testleri ve mevcut servis sağlık kontrolleri. Hepsi geçerse mevcut GitHub CLI oturumunla ayrı bir `golge/dev/<id>` dalına yalnızca patch dosyalarını commit eder ve taslak PR açar. PR inceleme ve GitHub Actions içindir. PR birleştirilmez ve Render dağıtımı başlatılmaz. PR, `feat/ultron-cloud-shared-memory` dalına birleştirildikten sonra Render'ın mevcut otomatik dağıtımı çalışır.

Bu akış kişisel erişim anahtarını GÖLGE sohbetine veya Render'a koymaz. Windows GÖLGE kurulumu tamamlandığında laptopta şunlar gerekir:

1. ULTRON deposu `feat/ultron-cloud-shared-memory` dalında olmalı; uzak `origin` `fatmakahraman304-hash/ULTRON` deposuna gitmeli.
2. GitHub CLI kurulu ve `gh auth status` başarılı olmalı. GitHub hesabının bu depoda dal gönderme ve PR açma yetkisi olmalı.
3. Çalışma ağacı temiz ve uzak dal ile eşit olmalı. GÖLGE kullanıcı değişikliklerini ezmemek için kirli veya geride kalmış checkout'ta durur.
4. Render servisi bu taban dalı izlemeli. Birleştirme sonrasında Render sağlık/SHA doğrulaması ayrıca yapılır.

GitHub CLI oturumu yoksa GÖLGE kodu değiştirmeden durur. Anahtarları sesli sohbete, hafızaya veya isteğe yapıştırma.

## Eksik listesi: yapamadığını kendisi not alır, sen onaylarsın (2026-10-21)
Yeni telefon/Cloud akışı (`gap_skills.py`, tablo `capability_gaps`):

1. **Not alma:** Model bir isteği yapamadığını söylerse isteğin otomatik olarak "eksik" listesine yazılır ve cevabın sonuna tek satırlık bir ipucu eklenir. Kendin de ekleyebilirsin: `eksik: rehberden kişi bulabilsin`. Gizli bilgiler (şifre/anahtar) listeye yazılmaz.
2. **Liste:** `eksiklerim` / `geliştirme listem`. Vazgeçmek için `eksik 3'ü vazgeç`.
3. **Geliştirme isteği:** `eksik 3'ü geliştir` → mevcut geliştirme isteği tablosuna (`dev_requests`) AGENTS.md kurallarını içeren bir istek yazılır (ChatGPT/Codex hand-off). Laptop çevrimiçiyse ayrıca laptopa **yalnızca patch TASLAĞI hazırlaması** için görev gider: "diff'i göster, kullanıcı onaylamadan hiçbir dosyaya yazma". Laptop çevrimdışıysa hiçbir görev kuyruğa alınmaz.
4. **Sesle:** eksik eklenebilir ve listelenebilir; geliştirme başlatma **yalnızca yazarak** yapılır.

Değişmeyenler: Approval Gate, denetim kaydı, `SelfCodeBoundary`, yedek → uygula → test → geri alma, taslak PR, birleştirme ve Render deploy yalnızca senin kararınla. GÖLGE kendi kodunu sessizce değiştirmez ve "değiştirdim" demez.

Doğrulanan: cloud tarafı (kayıt, liste, istek oluşturma, çevrimdışı/çevrimiçi laptop, ses kısıtı) gerçek PostgreSQL testiyle. **Doğrulanmayan:** laptop ajanının gelen taslak görevini gerçekten "yalnız taslak" olarak işlemesi, yerel Qwen'in patch kalitesi, PR açma (Windows + `gh` oturumu gerekir).

### Zekâ düzeyi: model seçimi senin maliyet kararın
Sohbet zekâsı ağırlıkla arkadaki modele bağlıdır. Cloud servisi varsayılan olarak hızlı/ucuz modeli kullanır (`GEMINI_MODEL`). Kod ve derin düşünme isteklerinde daha güçlü model kullanması için Render ortam değişkenlerine şunları **sen** ekleyebilirsin (maliyeti artırabilir, bu yüzden otomatik açılmadı):
- `GEMINI_TASK_MODELS_APPROVED=true`
- `GEMINI_CODING_MODEL=<kod için daha güçlü model>` ve `GEMINI_GENERAL_MODEL=<derin düşünme için daha güçlü model>`

Sistem talimatına eklenen "düşünme rehberi" (adım adım akıl yürütme, varsayımları belirtme, çalışır kod, dürüst sınırlar) model değişmeden de cevap kalitesini artırmayı hedefler; etkisi gerçek modelle **ölçülmedi**.

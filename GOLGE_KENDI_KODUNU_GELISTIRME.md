# GÖLGE'nin kendi kodunu geliştirmesi

GÖLGE'ye sohbette “Gölgeye bir şeyini değiştir” veya istediğin özelliği açıkça söyle. İstek eşleşmiş Windows laptop çevrimiçiyse yerel Qwen ile sınırlı bir patch taslağı üretir. Diff'i gösterir; sen `onaylıyorum` demeden dosyalara dokunmaz.

Onaydan sonra laptop şu kontrolleri çalıştırır: TypeScript, üretim derlemesi, Python derlemesi, backend testleri ve mevcut servis sağlık kontrolleri. Hepsi geçerse mevcut GitHub CLI oturumunla ayrı bir `golge/dev/<id>` dalına yalnızca patch dosyalarını commit eder ve taslak PR açar. PR inceleme ve GitHub Actions içindir. PR birleştirilmez ve Render dağıtımı başlatılmaz. PR, `feat/ultron-cloud-shared-memory` dalına birleştirildikten sonra Render'ın mevcut otomatik dağıtımı çalışır.

Bu akış kişisel erişim anahtarını GÖLGE sohbetine veya Render'a koymaz. Windows GÖLGE kurulumu tamamlandığında laptopta şunlar gerekir:

1. ULTRON deposu `feat/ultron-cloud-shared-memory` dalında olmalı; uzak `origin` `fatmakahraman304-hash/ULTRON` deposuna gitmeli.
2. GitHub CLI kurulu ve `gh auth status` başarılı olmalı. GitHub hesabının bu depoda dal gönderme ve PR açma yetkisi olmalı.
3. Çalışma ağacı temiz ve uzak dal ile eşit olmalı. GÖLGE kullanıcı değişikliklerini ezmemek için kirli veya geride kalmış checkout'ta durur.
4. Render servisi bu taban dalı izlemeli. Birleştirme sonrasında Render sağlık/SHA doğrulaması ayrıca yapılır.

GitHub CLI oturumu yoksa GÖLGE kodu değiştirmeden durur. Anahtarları sesli sohbete, hafızaya veya isteğe yapıştırma.

# GÖLGE Autonomous Development V2 — sınırlı taslak PR döngüsü

Bu sistem modelin doğrudan çalışan GÖLGE kurulumuna yazmasına izin vermez.
Sadece kayıtlı ve yol listesi sınırlandırılmış bir geliştirme görevini önerir;
değişiklikler incelenebilir bir taslak PR olarak kalır. Otomatik merge, Render
dağıtımı, cihaz kurulumu ve kendi kendine izin yükseltme yoktur.

## İş akışı

1. `goals.json` görevleri kanıt, etkilenen dosya, beklenen iyileşme, risk,
   test kapsamı, başarı ölçütü ve öncelik taşır. Önce yüksek öncelik seçilir.
2. Başka bir açık PR aynı dosyaları değiştiriyorsa o görev atlanır. Açık bir
   `GOLGE-AUTODEV:` PR varsa ikinci bir otomatik öneri üretilmez. Birleştirilen
   hedef etiketi tekrar kuyruğa alınmaz.
3. Var olan `CodeAgent` yalnızca sınırlı kaynak dosyalarını okuyup öneri üretir.
   Gemini kullanımı için repository secret gerekir; model yükü 6.000 çıktı
   tokenıyla, kaynak bağlamı 18.000 karakterle sınırlandırılmıştır.
4. Öneri; sabit hedef kimliği ve SHA, dosya listesi, boyut, kimlik bilgisi,
   symlink, güvenlik yolu ve test varlığı açısından doğrulanır. Mevcut regresyon
   testleri aynen korunur; yeni testler bunlara eklenir.
5. Kaynak ve model anahtarı olmayan ayrı Actions job’ı öneriyi geçici checkout’a
   uygular, Python derler ve üretilen regresyon dosyasını Pytest ile çalıştırır.
6. Normal assertion/regresyon hatasında en fazla **bir** düzeltme modeli çağrısı
   yapılır. Sağlayıcı kesintisi, eksik test bağımlılığı ve zaman aşımında ikinci
   model çağrısı yapılmaz. Hata kanıtı anahtar desenlerinden arındırılır ve en
   fazla 6.000 karakter olarak modele verilir.
7. Başarılı doğrulama sonrası `GitHubPRPublisher` yalnızca allowlist yollarını
   yeni dala commit edip taslak PR açar. Yazma token’ı kodu çalıştıran job’da
   yoktur. PR gövdesi kullanıcı onayı alınmış gibi davranmaz.
8. PR birleştirilmez ve Render’a dağıtılmaz. `GITHUB_TOKEN` ile açılan PR yeni
   Actions kontrollerini otomatik başlatmayabilir; merge öncesi bağımsız CI ve
   insan incelemesi gerekir.

Her workflow çalıştırmasında en fazla iki Gemini isteği ve her istekte en çok
6.000 çıktı tokenı bütçelenir. API anahtarı yoksa gerçek model üretimi
**NOT_RUN** olur. Yalnızca sabit/sahte modelle test geçmesi, gerçek modelin kod
kalitesini doğrulamaz.

`workflow_dispatch` varsayılan olarak `contracts_only` modundadır ve provider
çağrısı yapmaz. Gerçek model/PR akışı ancak secrets ve repository izinleri
yetkili biri tarafından kontrol edildikten sonra açıkça `pipeline` seçilerek
başlatılmalıdır. Zamanlanmış çalışma `pipeline` yolunu kullanır.

## Zamanlayıcı

GitHub `schedule` yalnızca varsayılan `main` dalındaki workflow üzerinden
çalışır. Bu depodaki `feat/ultron-cloud-shared-memory` üretim dalındaki dosya
tek başına zamanlayıcıyı etkinleştirmez. V2 kodu üretim dalına alındıktan sonra
aynı workflow için ayrı, incelemeye açık bir aktivasyon PR’ı `main` dalına
gerekebilir. Bu aktivasyon PR’ı merge edilmeden düzenli çalışma iddia edilmez.
Otomatik çalışma sırasında Actions kota sınırı, tekil concurrency grubu ve
başına iki model çağrısı uygulanır.

## Yerel Ollama

Yalnızca açık ve yetkili geliştirme checkout’unda, laptop açıkken:

```powershell
python scripts/golge_autodev/engine.py plan --base-sha <EXACT_40_CHAR_SHA>
python scripts/golge_autodev/engine.py generate --provider ollama
python scripts/golge_autodev/engine.py validate
```

Bu adımlar öneri dosyası üretir. `verify` ve `apply` komutlarını canlı çalışma
checkout’unda kullanmayın; Actions bunları geçici, yazma yetkisi olmayan test
checkout’unda çalıştırır. Yerel model erişilemiyorsa Gemini’ye sessiz fallback
yapılmaz.

## Bilinçli sınırlar

- Güncel V2 gerçek, harici Gemini/Qwen çağrısı ve GitHub’a yazma gerektirir.
  Repository secrets ve repository settings erişimi olmayan yerel doğrulama bu
  entegrasyonu `NOT_RUN` olarak raporlamalıdır.
- Otomatik hata keşfi şu an kayıtlı backlog, açık PR dosya çakışmaları ve
  birleştirilmiş hedef geçmişiyle sınırlıdır. Actions başarısızlıkları, Render
  hata kayıtları, üretim performans metrikleri, capability probe’ları ve açık
  GitHub issue’larından otomatik yeni görev çıkarmak sıradaki geliştirmedir.
- Test runner ayrı ve anahtar/token içermeyen job’dır; üretilen Python kodu bu
  job’da çalıştırılır. Bu nedenle dosya allowlist’i, süre sınırı, dar izinler ve
  yeni PR için bağımsız inceleme korunur.
- Bu deterministic sözleşmeler Gemini/Qwen doğruluğu, gerçek Windows/iPhone,
  mikrofon/TTS davranışı, fiziksel model iptali veya üretim kalitesi ölçümü
  değildir.

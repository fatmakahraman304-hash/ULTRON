# GÖLGE Autonomous Engineer V5 — gerçek görev ölçümü ve sınırlı, güvenli doğrulama

V5, V4 keşif/SQLite mühendislik hafızası hattını korur ve şu doğrulanabilir
katmanları ekler:

- `coding_bench.py` sekiz bağımsız Python/TypeScript kodlama görevini, modelin
  prompt'una eklenmeyen test oracles ile değerlendirir. Her görev en çok iki
  üretim/onarım çağrısı alır. Gerçek provider belirtilmezse sonuç **NOT_RUN**,
  başarı puanı `null` olur. Sahte provider testleri `simulated=true` olarak
  ayrılır; gerçek Qwen/Gemini puanına eklenmez.
- Test çalıştırıcısı digest ile sabitlenmiş Ubuntu Docker imajında ağsız,
  salt okunur rootfs, capabilities kapalı, sınırlı PID/CPU/RAM alanında çalışır.
  Checkout varsayılan olarak salt okunurdur; `/tmp` 64 MiB geçicidir, kişisel
  home ve gizli environment değerleri sandbox'a aktarılmaz. Docker daemon veya
  imaj yoksa test **BLOCKED/NOT_RUN** kalır. Windows üzerinde güvenli yerel
  test için doğrulanmış bir sandbox henüz yoktur.
- V5 kalite kapıları syntax, type, unit, integration, secret, dependency,
  security boundary, API uyumluluğu, performans ve rollback durumlarını ayrı
  kaydeder. Zorunlu bir kapı `PASS` veya açık `NOT_APPLICABLE` değilse taslak
  PR yayımlama yolu başarılı sayılmaz. Performans tabanı yoksa ölçülmüş başarı
  değil, `NOT_APPLICABLE` raporlanır.
- Engineering Memory V4 snapshot'ları V5 zarfında repo/workflow/branch/run/SHA
  kökeniyle taşınır. Eski V4 snapshot yalnızca GitHub artefakt/run metaverisi
  doğrulandıktan sonra içe alınabilir. Artefaktın 90 günlük ömrü kalıcı depolama
  değildir; eksik, eski veya uyuşmayan artefakt proposal akışını durdurur.
- İlk kurulumda `main` dalından yalnızca açık `initialize_memory` workflow
  dispatch'i boş snapshot üretir. Operatör ayrıca boş başlangıcı onaylamalı ve
  tam artefakt listesinde daha önceki bir hafıza artefaktı bulunmamalıdır.
  Eski/süresi dolmuş kayıt veya kayıp hafıza bu yolla sıfırlanmaz; o durumda
  iş akışı durur ve kayıt kurtarma/incelemesi gerekir.
- İzole sahte-model E2E gerçek pytest hatası → bir onarım → yeniden test → var
  olan `GitHubPRPublisher` sözleşmesini ağ çağrıları taklit edilerek çalıştırır
  ve SQLite hafızasında tekrar seçilmeme durumunu doğrular. Bu, gerçek model
  çıkarımı veya GÖLGE'nin gerçek GitHub'a otomatik PR açması değildir.

Benchmark güvenli, izole Linux ortamında ve provider erişimi olduğunda örneğin:

```bash
python scripts/golge_autodev/coding_bench.py --provider ollama --max-cases 8 --max-calls 16
```

Gemini için ayrıca `--confirm-cloud-budget`, açık `GOLGE_AUTODEV_CLOUD_MODEL_BUDGET_APPROVED=true`,
API anahtarı, pozitif maliyet tavanı ve kullanıcı tarafından belirtilen çağrı
limiti gerekir. Bu kontroller API faturalamasını bağımsız doğrulamaz; gerçek
kota/maliyet incelemesi yine yetkili operatörün sorumluluğundadır.

V5 bu oturumda gerçek model çağrısı yapmadı: GitHub secret/settings envanteri
403 ile kapalıydı ve yerel Ollama endpoint'i erişilemiyordu. Bu nedenle 8
benchmark görevinin gerçek başarı puanı **NOT_RUN**'dur. Windows/iPhone ve
Render doğrulaması da ayrıca raporlanır; commit veya draft PR bunların yerine
geçmez.

---

# GÖLGE Autonomous Development V3 — kanıta dayalı keşif ve sınırlı taslak PR döngüsü

Bu sistem modelin doğrudan çalışan GÖLGE kurulumuna yazmasına izin vermez.
Sadece kayıtlı ve yol listesi sınırlandırılmış bir geliştirme görevini önerir;
değişiklikler incelenebilir bir taslak PR olarak kalır. Otomatik merge, Render
dağıtımı, cihaz kurulumu ve kendi kendine izin yükseltme yoktur.

## İş akışı

1. `goals.json` görevleri kanıt, etkilenen dosya, beklenen iyileşme, risk,
   test kapsamı, başarı ölçütü ve öncelik taşır. V3 ayrıca salt okunur ve
   deterministik bir keşif adımıyla doğrulanmış bulguları bu sabit kapsamla
   eşleştirir; model kendi başına yeni dosya veya izin kapsamı açamaz.
2. Başka bir açık PR aynı dosyaları değiştiriyorsa o görev atlanır. Açık bir
   `GOLGE-AUTODEV:` PR varsa ikinci bir otomatik öneri üretilmez. Birleştirilen
   hedef ve `GOLGE-CANDIDATE:<20 hex>` işareti tekrar kuyruğa alınmaz. Yeni,
   farklı kanıt aynı kayıtlı hedefi yeniden gündeme getirebilir.
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
çağrısı yapmaz. `discovery_only`, Actions/issue/PR metaverisi, aktif roadmap
kontrol listeleri ve yerel statik incelemeyi toplar; hiç model çağırmaz.
Üretim Actions hatası ancak başarısız adım adı tam bir kayıtlı regresyon testini
işaret ederse otomatik aday olur. Issue içeriği okunmaz; yalnızca `autodev:verified`
ve desteklenen `component:voice` / `component:conversation` etiketleri otomatik
hedef eşlemesi sağlayabilir. Diğer bulgular insan incelemesi bekler.
`pipeline` planlaması ayrıca `--require-discovery` kullanır; mevcut sabit görev
listesindeki genel bir hedef, uygun keşif kanıtı bulunmadan modele gönderilmez.
Gerçek model/PR akışı için secret ve
repository izinlerinin yanında sağlayıcı kotası/maliyeti yetkili biri tarafından
kontrol edilmeli ve `GOLGE_AUTODEV_CLOUD_MODEL_BUDGET_APPROVED=true` repository
variable'ı açıkça ayarlanmalıdır. Değişken yoksa veya `true` değilse scheduled
çalışma da dahil ilk üretim ve tek onarım çağrısı yapılmaz. `pipeline` seçimi tek
başına maliyet politikasını geçemez.

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

- Tam V3 uçtan uca modda gerçek, harici Gemini/Qwen çağrısı ve GitHub’a yazma gerektirir.
  Repository secrets ve repository settings erişimi olmayan yerel doğrulama bu
  entegrasyonu `NOT_RUN` olarak raporlamalıdır.
- Self-discovery sources: production-branch Actions failure/job-step metadata,
  maintainer-labelled open issues, deterministic CodeIntel error/high findings,
  `ULTRON_NEXT_TASKS.md` / `ULTRON_ROADMAP.md` active checklist items, and
  open-PR path conflicts. Application error logs, health snapshots and measured
  performance reports are accepted only as bounded operator-supplied JSON/JSONL
  inputs; no Render log API is configured or queried here. Personal transcripts,
  issue bodies, raw logs, stack traces and exception messages are excluded from
  model evidence. Unmapped/high-risk findings are review-only.
- The priority score is a transparent source-based heuristic, not a measured
  user-impact metric. Current workflow discovery saw no eligible candidates;
  static findings and failed run metadata remained review-only. The engine has a
  merged-PR candidate marker for successful-task deduplication, but it does not
  yet keep a durable attempt-by-attempt engineering journal across failed runs.
- Test runner ayrı ve anahtar/token içermeyen job’dır; üretilen Python kodu bu
  job’da çalıştırılır. Bu nedenle dosya allowlist’i, süre sınırı, dar izinler ve
  yeni PR için bağımsız inceleme korunur.
- Bu deterministic sözleşmeler Gemini/Qwen doğruluğu, gerçek Windows/iPhone,
  mikrofon/TTS davranışı, fiziksel model iptali veya üretim kalitesi ölçümü
  değildir.


## V6 taslak: gerçek Qwen3 bulgularından çıkarılan sınırlandırılmış onarım

V6, V5'in bağımsız testlerini, Docker yalıtımını, model çağrı ve çıktı bütçelerini,
GitHub/Render üretim sınırlarını değiştirmez. Temel farklar:

- Yerel `qwen3*` Ollama modellerinde `think: false` istenir. Bu seçenek,
  düşünme tokenlarının kısa JSON kod yaması bütçesini tüketmesini engellemeye
  yardımcı olur. Qwen2.5 ve Gemini istekleri aynı kalır.
- Benchmark modeli yanıtının JSON/şema veya gerekli dosya listesi eksikliği
  nedeniyle reddedilmesi halinde en fazla **bir** ek biçim düzeltmesi ister.
  Gizli kabul testleri modele açıklanmaz. İzin dışı yol, tekrar eden yol,
  büyük dosya veya sır benzeri içerik yine **ilk denemede engellenir**.
- Başarısız bağımsız testten sonraki üretim, değişen dosya içeriklerini
  hiç değiştirmediyse ikinci test koşusu yapılmaz; açık
  `unchanged_patch_after_repair` hatası raporlanır.
- Genel kodlama talimatları tam JSON, tam dosya içeriği, kamuya açık API
  uyumluluğu ve ham girdi / türetilmiş değer ayrımı ister. Hazır benchmark
  çözümleri, gizli testler ve sabit görev yanıtları eklenmez.
- Regresyon testleri format düzeltme, ikinci biçim hatası, tehlikeli dosya yolu
  engeli, değişmeyen yamalar ve Qwen3 / Qwen2.5 taşıma davranışını kapsar.

**Kanıt sınırı:** V5'in yerel kullanıcının Qwen3 8B ile paylaştığı önceki tam
koşularında 8 görevden 6'sı geçmiştir. V6 için gerçek-model benchmark sonucu
henüz bulunmamaktadır. CI sözleşme testleri yerel model başarısı anlamına
gelmez. Render veya mevcut üretim dalı otomatik güncellenmez.

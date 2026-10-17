# GÖLGE — kaynaklı araştırma, 17 Ekim 2026

## Durum ve referans

[Taslak PR #59](https://github.com/fatmakahraman304-hash/ULTRON/pull/59). Bu sürüm geliştirme dalıdır; üretime alınmadı, Render dağıtımı yapılmadı. Başlangıç üretim SHA'sı `b486f13b5f70092bbf9e5a0dce4afac301573058`. PR #56'nın bekleyen ses kesme, uydu/hava durumu ve dosya seçme düzeltmeleri bu **geliştirme dalına** alındı (`48a688a`); PR #56 veya üretim birleştirilmedi. Diğer açık PR'lar değiştirilmedi.

JARVIS 4.6.2'nin [resmî sürüm notlarındaki](https://github.com/alpunlu12-commits/jarvis/releases/tag/v4.6.2) güncel bilgi için Google Search ve model yedeği fikirleri bağımsız olarak uygulandı. JARVIS çalıştırılmadı; konuşma kalitesi karşılaştırması **NOT_RUN**. Yüklenen exe indirme sınırını aştığından resmî release kopyası salt statik incelendi: 73.534.559 bayt, PE32; SHA-256 `582558101b379580be715f1159a11c3f84ca441e27f7bbc70214340abf2ae2c4` verilen digest ile eşleşti. Kurulum, decompile, özel kod/anahtar kopyalama yapılmadı; exe repoya eklenmedi.

## Çalışan kod yolu

1. Mevcut `conversation_persona` yönlendiricisi güncel fiyat, döviz, haber, spor ve teknoloji sorularını araştırmaya ayırır. “Bugün yoruldum”, kavram soruları ve sıradan sohbet web başlatmaz. Programlama hakkında öğrenme sorusu kod üretiminden ayrılır. Yönlendirme ikinci model çağrısı yapmaz.
2. Mevcut `ResearchEngine` içinde isteğe bağlı resmî `google-genai` **GenerateContent / google_search** adaptörü çalışır. Ayrı sohbet motoru kurulmadı. Aramaya yalnızca mevcut açık sorgu, sınırlı araştırma takip sorusunda aynı kullanıcı/konuşmadaki önceki sorgu gider; profil, kişisel hafıza ve asistan metni eklenmez.
3. Gemini `groundingChunks` ve `groundingSupports` işlenir; Türkçe UTF-8 byte aralıkları gerçek yanıt bölümüyle eşleştirilir. Kaynakla ilişkilendirilmeyen uydurma URL'ler kaynak diye sunulmaz. En fazla beş kaynak, başlık, erişim zamanı ve desteklenen **yanıt bölümü** gösterilir. Bu bölüm özgün sayfadan alınmış alıntı değildir.
4. Google atfı **bağımsız iddia doğrulaması değildir**. Yayın tarihi metadata'da yoksa bilinmiyor yazılır. Sayfa bizzat okunmuş gibi etiketlenmez. Modelin desteklenmeyen her iddiasını semantik olarak yakalama garantisi verilmez.
5. Google kapalı/erişilemez/kanıtsız ise mevcut güvenli arama ve sayfa okuyucu kullanılır. DNS pinning, özel IP/port, redirect ve boyut sınırları korunur. Aynı/kopya kaynak ve olası sayısal çelişki kontrolleri mevcut Evidence Engine'dedir. Google kaynaklarının bağımsızlığı ayrıca doğrulanmış sayılmaz.
6. Kaynak yoksa güncel bilgi uydurmak yerine açık hata döner; kaynak var ama Cloud model anahtarı yoksa gerçek sayfa bölümleri sunulur. Tam grounding yanıtı için ikinci Gemini çağrısı yapılmaz.
7. Windows React ve iPhone PWA kaynakları tıklanabilir, `noopener noreferrer` bağlantılarıyla gösterir. Google Search önerileri betiksiz, ayrı sandbox iframe/CSP içinde gösterilir. Kaynak metadata'sı mesajla **tek INSERT** içinde saklanır; yenilemede geri gelir ve owner filtresini korur. Migration nullable/additive `research_metadata JSONB` ekler; mevcut hafızayı silmez.
8. Bekleyen araştırma iptal edilirse geç gelen yanıt/kaynak kaydedilmez. Gemini üretiminin fiziksel olarak durdurulduğu iddia edilmez: `output_suppressed`, `provider_stopped=false`.

### Yüzeyler ve sınırlar

| Yüzey | Yeni davranış |
|---|---|
| iPhone/Cloud metin sohbeti ve metin endpoint'ine aktarılan ses transkripti | Onaylı Google grounding → güvenli sayfa okuma → dürüst erişilemiyor yanıtı |
| Windows React, paylaşılan Cloud yolu | Aynı yanıt/kaynak/widget metadata'sı |
| Windows React, Cloud erişilemiyor | Aynı araştırma adaptörü; açıkça yerel model seçilmişse Google kapalı, mevcut Qwen ile okunan sayfa özeti |
| Windows native ses / `actions.web_search` / agent | Mevcut güvenli okuyucu ve kaynak listesi. Google öneri widget'ını gösteremeyen native yüzeyde Google grounding özellikle açılmaz. |
| Gemini Live doğrudan ses oturumu | Mevcut ses araçları korunur; bu sürümde yeni Google grounding bağlanmadı. Fiziksel ses doğrulaması yapılmadı. |

Telefon otomatik model seçiminde araştırma, **kuyruğa hiçbir iş eklenmeden** `research_requires_cloud` ile Cloud'a yönlendirilir. Önceden kabul edilmiş request tekrarları önce mevcut görev kimliğini döndürür; kabul edilen iş ikinci kez çalıştırılmaz. Açıkça yerel mod kullanan kullanıcıya sessiz ücretli geçiş yapılmaz.

## Model politikası ve maliyet

- Normal Cloud sohbeti mevcut `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL` ayarlarını korur. Yeni ağır model otomatik seçilmez veya indirilmez.
- `GEMINI_TASK_MODELS_APPROVED=true` açıkça yapılandırılmışsa isteğe bağlı `GEMINI_FAST_MODEL`, `GEMINI_GENERAL_MODEL`, `GEMINI_CODING_MODEL`, `GEMINI_RESEARCH_MODEL` geçerlidir. Görsel yükleme ve Gemini Live ayrı mevcut yollarında kalır.
- Qwen seçimi mevcut kurulu model envanteri ve ModelRouter/FastBrainPolicy ile yapılır; bu ortamda kullanıcının laptop envanteri erişilebilir değildir.
- Cloud model başına SDK denemesi bir; toplam en fazla iki farklı model. 401/403/geçersiz istek için model dolaşımı yapılmaz. Kota, timeout, ağ, servis, model bulunamaması ayrı sınıflandırılır. Konuşma geçmişi/persona yedek modele aynı biçimde geçer. Bilgisayar araçları retry zincirine katılmaz.
- Normal üretim isteğinde transport timeout 15 sn; Google varsayılan 12 sn, yapılandırılabilir 1–15 sn. Bunlar provider transport sınırlarıdır; bütün araştırma için toplam SLA veya gerçek üretim iptali değildir. Kaynak okuyucunun mevcut sınırlı timeout'ları ayrıca geçerlidir.
- Yanıt token tavanı sıradan sohbette 4096, ayrıntılı/kod sorusunda 8192, grounding'de 4096. Model düşünme token'ları tüketebilir; gerçek kalite/gecikme testi yapılmadı.
- Google'ın arama sayısı sağlayıcı kontrolündedir. Çağrı sayısı/token sınırı parasal harcama garantisi değildir; sağlayıcı projesinde kota/harcama sınırı ayrıca kontrol edilmelidir. [Güncel fiyat sayfası](https://ai.google.dev/gemini-api/docs/pricing) ve [kullanım koşulları](https://ai.google.dev/gemini-api/terms) esas alınır; ücretsiz kullanım varsayılmaz.

Google **varsayılan kapalıdır**. Etkinlik için tümü gereklidir:

| Sunucu değişkeni | Gereklilik |
|---|---|
| `GEMINI_API_KEY` | Mevcut güvenli sunucu anahtarı; frontend'e veya Git'e yazılmaz |
| `GEMINI_SEARCH_MODEL` | Hesaba erişilebilir ve Google Search destekleyen doğrulanmış model; bu adaptörde sabit varsayılan yok |
| `GOLGE_GOOGLE_SEARCH_ENABLED` | `true` |
| `GOLGE_GOOGLE_SEARCH_BUDGET_APPROVED` | Kullanıcının ayrıca onayladığı bütçe/kota sonrası `true` |
| `GEMINI_SEARCH_FALLBACK_MODEL` | İsteğe bağlı, aynı onay/kota kapsamındaki yedek; en fazla bir deneme |

Bu oturumda hiçbir bayrak/anahtar üretimde değiştirilmedi ve ücretli çağrı yapılmadı. `python scripts/golge_research_doctor.py` yalnızca yapılandırma varlığını gösterir. `--list-models` sadece resmî model metadata'sını sorgular; üretim yapmaz, anahtar yazdırmaz. Listeleme başarısı grounding desteği/kota/kalite kanıtı değildir. Ortam raporu [environment-readiness.json](research-grounding/environment-readiness.json).

## Ölçüm ve testlerin anlamı

Yeni açıklamalı 16 yönlendirme senaryosu aynı ortamda üretim başlangıç kodu ve yeni kodla çalıştırıldı: **8/16 → 16/16**. Yalnızca bu deterministik yönlendirme vakalarıdır; gerçek sohbet zekâsı başarı yüzdesi değildir. Medyan süre **0,00583 → 0,00714 ms**, p95 **0,01241 → 0,01660 ms** (senaryo başına 100 tekrar). Yeni kuralın küçük ek maliyeti vardır; uçtan uca hızlanma iddiası yoktur. [Önce](research-grounding/routes-before.json), [sonra](research-grounding/routes-after.json), tekrar: `python evals/research/grounding_routes.py`. Mevcut bağımsız 100 TR/EN niyet regresyonu her iki sürümde 100/100 geçti; gerçek ilk token/yanıt gecikmesi **NOT_RUN**.

Otomatik testler SDK fixture'ları, gerçek geçici PostgreSQL ve gerçek Chromium kullanır; canlı Gemini veya fiziksel iPhone/Windows testi sayılmaz. Başlangıçta güncel soru yönlendirme/mahremiyet regresyonları başarısızdı; yeni kodla düzeldi. Eski research_meta testi üretim başlangıç kodunda da kısa/kopya kaynak fixture'ı nedeniyle başarısızdı; kaynak kalitesi assertion'ı gevşetilmeden fixture yeterli gerçek metin biçimine getirildi.

- Gerçek Google/Gemini: **BLOCKED**, API anahtarı ve ayrı maliyet onayı yok.
- Gerçek Qwen: **BLOCKED**, bu çalışma ortamında localhost:11434 erişilemiyor; kullanıcının Windows cihazına erişim yok.
- Model kalitesi/JARVIS karşılaştırması/gerçek ses: **NOT_RUN**.
- Canlı güvenli sayfa okuyucu denemesi (`ai.google.dev`): **BLOCKED**, mevcut DNS-pinned transport bu ortamdan içerik alamadı (`request_failed`, 5,23 sn). SSRF kontrolü/proxy sınırı gevşetilmedi. Resmî belgeler erişilebilir web okuma aracıyla incelendi.
- Render `/health`: bu oturumda 15 sn timeout; **BLOCKED**. Üretim canlı SHA'sı doğrulanmadı. GitHub üretim SHA'sı Render SHA'sı yerine sunulmaz.
- Mahremiyet filtresi bilinen şifre/token/e-posta/telefon/yerel kullanıcı yolu kalıplarıdır; her türlü kişisel metni tespit eden genel DLP sistemi değildir. Özel profil hiçbir zaman otomatik arama bağlamına eklenmez.
- Google arama widget'ı gerçek servis çıktısıyla görsel kabul görmedi; fixture güvenlik/gösterim testleri geçti. Canlı açmadan önce Google'ın görüntüleme kuralları ve gerçek örnek birlikte denetlenmeli.

## Güvenli kullanım ve sonraki adım

Bu kod henüz `START.bat` ile mevcut üretim kurulumuna gelmez. Taslak PR inceleme bekler. Üretime dağıtım ve maliyet için ayrıca kullanıcı onayı gerekir.

İzole laptop incelemesi istenirse önce GÖLGE'yi kapat, mevcut dizinde `git status --short` ile kullanıcı değişikliklerini kontrol et. Değişiklikleri ezmeden ayrı worktree oluştur:

```bat
cd /d "%USERPROFILE%\ULTRON-3a6f489"
git fetch origin
git worktree add "%USERPROFILE%\GOLGE-research-review" origin/feat/golge-grounded-research-20261017
cd /d "%USERPROFILE%\GOLGE-research-review"
INSTALL.bat
.venv\Scripts\python.exe scripts\golge_research_doctor.py
```

Bu ayrı test kurulumudur; mevcut kullanıcının hafızası, anahtarları ve eşleştirmesi otomatik taşınmaz. Üretimle aynı anda yerel portu kullanma. Gizli dosyaları Git'e ekleme. Google'ı bütçe/model doğrulamasından önce açma. Anahtar varsa `--list-models` ile salt okunur envanter kontrolü yapılabilir. Fiziksel doğrulama: sıradan sohbet → güncel soru/kaynak → takip sorusu → konu değişimi → iptal → yenilemede kaynak → aynı yetkili hesapta telefon/Windows. Hesap Makinesi UIA ve onaylı araçlar ayrıca gerçek Windows'ta sınanmalı.

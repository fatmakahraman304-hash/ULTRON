# GÖLGE — CORE / Dünya çalışma alanı

Bu geliştirme PR #44 içindedir. Üretime birleştirme veya Render dağıtımı içermez.
Referans, konuşmadaki üçlü GÖLGE görselidir. Bu oturumda erişilebilir bir JARVIS
video dosyası bulunmadığından videonun izlendiği iddia edilmez. Teknik test geçişi
kullanıcının görsel kabulü sayılmaz.

## Gerçek davranış

- Normal sohbetin merkezinde CORE ve Dünya aynı çalışma alanını kullanır.
  `CoreEarthStage` geçiş sırasında iki gerçek GPU sahnesini en fazla yaklaşık
  1,4 saniye tutar; sonra çıkan sahneyi kaldırır. CORE parçacıkları vertex shader
  ile dağılır, halkalar hızlanır ve sahne ölçeği değişir. Dünya'nın görünürlüğü
  ve ölçeği GPU sahnesinde değişir. Reduced-motion geçişi kısaltır.
- `GolgeOrb`: yazılım / sınırlı GPU yolunda 1.400, uygun WebGL aygıtında 2.200
  nokta. Bu seçim gerçek WebGL renderer adı ve CPU concurrency bilgisini kullanır;
  VRAM miktarını tespit ettiği iddia edilmez. Yakın komşu ağı, turuncu noktalar,
  bağımsız halkalar ve projeksiyon korunur. Ses genliği mevcut native RMS
  köprüsünden gelir. Sessizlikte sahte RMS üretilmez.
- `EarthWatch`: tek renderer, paketli yüzey/gece/bulut dokuları, UTC Güneş
  yönü, shader terminatörü, gece ışıkları, atmosfer, yıldızlar ve isteğe bağlı
  koordinat ızgarası. Küre katmanı veya koordinat değişiminde WebGL renderer yeniden
  kurulmaz. Harita ile küre arasında geçerken GPU kaynakları bırakılır.
- Kamera odaklaması gerçek geçen zamana göre yaklaşık 1,2 saniyedir. Aynı
  koordinata tekrar gitmek de yeni bir odak olayıdır (`focus_revision`). Kamera
  ekseni kullanıcı fareyle döndürdükten sonra da hedefe hizalanır. İzole testte
  bu hata önce yeniden üretildi, sonra düzeltildi.
- Küresel doku sokak ayrıntısı gibi büyütülmez. Yakınlık sınırı vardır. Şehir
  seçiminde ayrı, lazy-loaded Leaflet katmanı gerçek sokak döşemelerine geçer.
  Bu raster sokak haritasıdır; uydu veya 3D bina değildir.
- Normal mod ve kontrol merkezi aynı `stage.earth` durumunu, oturum kapsamlı
  kamera kaydını ve komut işleyicisini paylaşır. Ayrı kullanıcı/geçmiş belleği
  kurulmaz. Telefon CORE/Dünya/kontrol merkezini açmaz.

## Komutlar

`GÖLGE, Dünya’yı göster.` → `Kıbrıs’a git.` → `Lefkoşa’yı göster.`

Konumlar mevcut Photon/OSM adaptöründen gelir. Kıbrıs/Türkiye gibi ülke adları
sorgu eşanlamlarıyla çözülür; koordinat hardcode edilmez. Birden fazla sonuçta
panel üzerinden seçim gerekir. Kaynak erişilemiyorsa mevcut görünüm korunur.

`Haritayı aç.` · `Uydu moduna geç.` · `3D görünümü aç.` · `Dünyayı döndür.`
`Biraz daha yakınlaş.` · `Uzaklaş.` · `Dünya’nın gece tarafını göster.`
`Uçakları göster.` · `Hava durumunu göster.` · `Kayıtlı konumları göster.`
`CORE’a dön.` · `Kontrol merkezini aç.` · `Normal moda dön.`

Yazılı komut ve mevcut köprüden gelen ses transkripti aynı yönlendirmeyi kullanır.
Bu, fiziksel mikrofon/ASR başarısı kanıtı değildir. Araç/model çağrısı gerektirmeyen
Dünya komutları ikinci bir modele gönderilmez.

## Kaynak ve lisans sınırları

| Katman | Kaynak / durum |
| --- | --- |
| GLOBAL / NIGHT | Paketli statik Dünya dokuları; canlı uydu değildir. Doku kökenleri `ultron/frontend/src/assets/earth/SOURCES.md`. |
| MAP | OpenStreetMap standart raster sokak döşemeleri; gereken görünür attribution ve copyright bağlantısı. Yalnız kullanıcı isteğinde, prefetch/offline toplu indirme yok. |
| SATELLITE | Varsayılan kapalı. Operatöre ait lisanslı, CORS destekli public XYZ endpoint gerekir. |
| TERRAIN | Yükselti ve bina verisi yapılandırılmadı; kullanılamıyor. |
| WEATHER | Mevcut Open-Meteo / MET Norway adaptörü. Gerçek yanıt, kaynak ve sağlanan tarih; tahmin varsa etiketli. |
| FLIGHTS | Mevcut adsb.lol / adsb.fi adaptörü. Yalnız bildirilen koordinatlar; kapsam dışı uçak uydurulmaz. |
| ISS | Mevcut Where the ISS at kaynağı; açık komutla, 10 saniye aralıkla. Veri gelmeden işaret çizilmez. |
| LOCATIONS | Mevcut sahnenin kullanıcı tarafından eklenen pinleri. Otomatik konum izleme yok. |

Leaflet 1.9.4 BSD-2-Clause lisanslıdır; tam lisans dağıtımda
`public/licenses/leaflet.txt` içindedir. MapLibre/Cesium; vektör/terrain için uygun
seçeneklerdir, ancak doğrulanmış veri lisansı ve ihtiyacı olmadan ikinci bir
WebGL motoru ve büyük bağımlılık eklenmemiştir. Topluluk servislerinin kota ve
kullanım politikaları geçerlidir; yüksek trafik için sözleşmeli/öz barındırılan
kaynak gerekir. Bu uygulama izin veya SLA garantisi vermez.

Uydu için yalnız operatörün güvenli sunucu ortamında şu ayarlar değerlendirilebilir:
`GOLGE_SATELLITE_TILE_URL`, `GOLGE_SATELLITE_ATTRIBUTION`,
`GOLGE_SATELLITE_LICENSE_APPROVED=1`. URL public HTTPS XYZ resim şablonu olmalı;
query string, userinfo, özel IP veya frontend'e taşınan API secret kabul edilmez.
Bu ayarlar lisans satın almaz ve hiçbir servisi otomatik etkinleştirmez.
Anahtar gerektiren sağlayıcı için sağlayıcının izin verdiği ayrı bir sunucu
entegrasyonu gerekir; frontend'e gizli anahtar koyulmaz.

## Güvenlik ve veri korunumu

Desktop kaynak API'leri mevcut MARK token/HttpOnly cookie ve Origin sınırının
arkasındadır. Cloud'da mevcut public, salt-okunur kaynak rotaları genişletilir;
özel hafıza veya cihaz kimliği bu yanıtlara eklenmez. Backend yalnız sabit public
sağlayıcı URL'lerini okur; yönlendirme, timeout, boyut ve koordinat sınırları
korunur. Proxy ayarı `.netrc` kimlik bilgilerini kaynaklara taşımadan kullanılır.
Tarayıcıya sınırsız shell veya yeni OS aracı verilmez. Approval Gate, audit,
model yönlendirme, uzun dinleme ve özel hafıza kodu değiştirilmez.

## Doğrulama ve kanıt

`golge_earth_acceptance.py` yalnız izole loopback backend'i kabul eder. Token
`GOLGE_UI_QA_TOKEN` ortam değişkeninden okunur; dosyaya/rapora yazılmaz. Gerçek
sahne komutları, gerçek backend/telemetri, WebSocket, auth/Origin, kamera,
Photon sonuçları, OSM tile yanıtları ve model sonucunu ayrı raporlar. Sohbeti
model cevaplarıyla doldurmak için sentetik yanıt eklemez.

`golge_audio_visual_contract.py` ayrı ve görünür etiketli fake-QWebChannel /
yapay ses seviyesi testidir. Dinleme/konuşma/sessizlik ve transkript yönlendirme
sözleşmesini sınar; mikrofon, ASR, TTS veya fiziksel Qt testi değildir.

Ekranlar ve kayıtlar `docs/ui-v7/` altında tutulur. Ortam Chromium SwiftShader
ve CPU compositor'dür; Windows/RTX 60 FPS kanıtı değildir. Önceki headless GPU
compositor yeniden boyutlandırma sınırlaması sürer. Fiziksel iPhone klavyesi,
Windows mikrofon/TTS ve gerçek Qwen/Gemini çıkarımı ayrı cihaz/servis doğrulaması
ister. Tasarım kabulü REVIEW_REQUIRED kalır.

## Bu oturumun sonuçları

- Frontend / niyet / coğrafya / bağlantı / CORE: 24 test PASS.
- Lazy bundle: 1 test PASS. Backend Dünya / katman / geocoding: 11 test PASS.
- Cloud WORLD ve mobil tasarım sözleşmeleri: 16 test PASS.
- Gerçek Chromium mevcut sahne-yükleme ve mobil kompozisyon: 2 test PASS.
- Toplam bu odaklı otomatik set: **54 PASS, 0 FAIL**. Build, Python compile,
  minimal UI kontrolü, YAML ve diff kontrolleri ayrıca PASS. npm audit: 0 zafiyet.
- Gerçek izole backend ile 10 uçtan uca kontrol PASS. Kimlik/Origin reddi,
  gerçek WebSocket, dönüş/zoom, Kıbrıs'a doğru kamera, Lefkoşa sokak döşemeleri,
  lisanssız uydu reddi, görünüm geçişinde sohbet ve tek soket, tekrar sahne temizliği,
  mobil sabit arka plan / azaltılmış klavye yüksekliği ve shader hataları sınandı.
  Fiziksel iPhone klavyesi ve GPU bellek kullanımı bu test değildir.
- Photon/OSM: gerçek Kıbrıs ve Lefkoşa sonuçları alındı. Kıbrıs ülke merkezi
  34.9823018°, 33.1451285°; seçilen Lefkoşa şehir kaydı yaklaşık
  35.1853773°, 33.3610135°. Birden çok şehir sonucu UI'den seçildi.
- Ek gerçek UI kontrolü: hava paneli, uçuş paneli ve kontrol merkezinden doğrudan CORE dönüşü **3 PASS**; `ui-v7/additional-acceptance.json`.
- Gerçek OSM raster tile HTTP 200 yanıtları alındı. Uydu ve terrain **BLOCKED**:
  lisanslı kaynak yok. Uydu isteği mevcut katmanı değiştirmedi.
- Gerçek hava ve uçuş API'leri HTTP 200: Open-Meteo 0,771 sn, adsb.lol 0,681 sn
  (tek gözlem; genel performans garantisi değildir). O okumada 12 uçak vardı;
  daha sonraki UI kaydı 9 uçak gösterdi. Bunlar farklı erişim zamanlarıdır.
- İzole gerçek `/api/merged/invoke`: `ok=false`, `UNAVAILABLE`. Qwen/Gemini
  **BLOCKED**; laptop/VPN/Ollama veya Cloud model kimliği bu ortamda yok.
- Ayrı sentetik native köprü testinde dört sözleşme PASS: dinleme RMS (sıfır
  dahil), konuşma RMS (sıfır dahil), idle dönüşü, ses transkriptinden Dünya/CORE
  yönlendirme. Video üstünde SIMÜLASYON etiketi vardır. Gerçek mikrofon ve TTS
  **NOT RUN**.
- Kayıt sırasında SwiftShader RAF p50 178,2 ms, p95 198,0 ms ölçüldü. Bu yazılım
  render ortamında 60 FPS elde edilmedi. Windows/RTX için FPS **NOT RUN**.
  Bu değerler gerçek donanım ölçümüyle değiştirilmeden hedef başarısı sayılmaz.

İlk testler; yanlış ülke sonucu, düşük FPS'te uzayan kamera animasyonu,
aynı koordinata yeniden odaklanmama ve aşırı büyütülen düşük çözünürlüklü küre
sorunlarını ortaya çıkardı. Kod düzeltildi. Test sürücüsünde eski sahne durumunu
başlangıç kabul etme, eksik Origin ve React geçişinin ortasında örnek alma
hataları da düzeltildi; auth veya assertion sınırları kapatılmadı.

## Görsel / video galerisi

| Görünüm | 1366×768 | 1920×1080 |
| --- | --- | --- |
| CORE | [Ekran](ui-v7/core-desktop1366.webp) | [Ekran](ui-v7/core-desktop1920.webp) |
| Normal sohbette Dünya | [Ekran](ui-v7/earth-desktop1366.webp) | [Ekran](ui-v7/earth-desktop1920.webp) |
| Kontrol merkezi | [Ekran](ui-v7/control-desktop1366.webp) | [Ekran](ui-v7/control-desktop1920.webp) |

[390×844 mobil](ui-v7/mobile390.webp) · [Kıbrıs](ui-v7/cyprus-focus.webp) ·
[Lefkoşa gerçek sokak haritası](ui-v7/nicosia-street-map.webp) ·
[Gerçek hava verisi](ui-v7/weather-real.webp) · [Gerçek uçuş verisi](ui-v7/flights-real.webp) ·
[Gerçek model isteğinin hata sonucu](ui-v7/actual-provider-result.webp).

Bu ekranlardaki sohbet metni gerçek sahne komutlarının uygulama cevapları ve
sağlayıcı hatasıdır; Qwen/Gemini yanıtı veya sentetik dolgu sohbeti değildir.
Sistem telemetrisi gerçek Linux QA ortamından gelir; Windows laptop değildir.

[CORE idle](ui-v7/core-idle.webm) ·
[CORE → Dünya](ui-v7/core-earth-transition.webm) ·
[Döndürme / Kıbrıs / Lefkoşa](ui-v7/earth-cyprus-nicosia.webm) ·
[Kontrol merkezi ve CORE'a dönüş](ui-v7/control-and-core-return.webm) ·
[Açık etiketli sentetik ses / transkript sözleşmesi](ui-v7/synthetic-audio-and-voice-contract.webm).

Videolar gerçek ekran kaydından kısa kesitlerdir; oynatma hızı değiştirilmedi,
ara kare üretilmedi. Ana ham kayıt dış QA çalışma alanında 94,68 saniyedir.
Sesli kesit sahte köprüyle yapıldığından gerçek ses donanımı kanıtı değildir.
[Makine raporu](ui-v7/earth-acceptance.json) ·
[Gerçek veri sağlayıcıları](ui-v7/real-data-providers.json) ·
[Sentetik ses raporu](ui-v7/synthetic-audio-contract.json).

## Fiziksel kabul için kalanlar

1. Windows'ta mevcut yetkili bridge, Ollama/Qwen ve Cloud kimliğiyle tek gerçek
   sohbet turu; ardından ses RMS/TTS kesilmesi ve mikrofon sahipliği.
2. RTX 2050'de 1366/1920 çözünürlüklerinde FPS/VRAM ve tekrarlı geçiş.
3. iPhone Safari'de gerçek klavye, güvenli alan, mic izni, uzun dinleme/PWA.
4. İsteniyorsa operatörün lisanslı uydu / terrain kaynağı; ücretli servis kendiliğinden açılmaz.
5. Kullanıcının görsel incelemesi ve ayrı üretim onayı. Taslak PR otomatik merge/deploy edilmez.

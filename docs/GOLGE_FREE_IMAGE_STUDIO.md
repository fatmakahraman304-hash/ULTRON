# GÖLGE ücretsiz yerel Image Studio — 18 Ekim 2026

Bu çalışma PR #60'ın `d690c74b841f25c408cde955c02ac6900dd1bde0` commit'inden ayrı
`feat/golge-free-comfyui-20261018` dalında hazırlanmıştır. PR #59, PR #60 ve üretim
değiştirilmez. Render dağıtımı, ücretli API çağrısı veya model indirmesi yapılmaz.

## Çalışan kod yolu

Windows React / iPhone PWA → mevcut yetkili `/api/image/generate` → PostgreSQL
`image_requests` + mevcut `device_commands` kuyruğu → eşleşmiş laptopun CloudRemote
worker'ı → yalnızca loopback ComfyUI → özel görsel + mesajların atomik kaydı →
mevcut yetkili görsel URL'si ve sohbet geçmişi.

Yeni bir sohbet motoru veya depolama sistemi yoktur. Masaüstü de mevcut kimlik
doğrulamalı Cloud bridge'i kullanır; bu sürüm Cloud olmadan bağımsız bir masaüstü
görsel deposu sunmaz. Aynı yetkili kullanıcının telefon/laptop geçmişi mevcut
senkronizasyonu kullanır. Masaüstündeki geçmiş hâlâ mevcut birleştirilmiş owner
listesidir; yeni bir sohbet seçici değildir.

## Ücretsiz mod ve ücretli API sınırı

`GOLGE_IMAGE_PROVIDER` varsayılanı **comfyui_local**. Yerel yapılandırma eksik,
laptop çevrimdışı veya sağlayıcı adı bilinmiyorsa hata döner; Gemini'ye fallback
**yoktur**. Eski Gemini anahtar/bütçe bayraklarının ortamda bulunması bu davranışı
değiştirmez. `_gemini_generate_image` de ücretsiz modda SDK oluşturulmadan reddeder.
Ücretli eski yol ancak sunucuda ayrıca `GOLGE_IMAGE_PROVIDER=gemini` seçilirse ve
PR #60'taki bütün maliyet/onay kapıları geçerse kullanılabilir; bu çalışmada seçilmedi.
Araştırma, mevcut görsel analiz ve ses sağlayıcıları değiştirilmedi.

Yerel görsel üretiminin harici model API ücreti yoktur. Mevcut Cloud barındırma,
trafik, elektrik ve donanım giderlerinin sıfır olduğu iddia edilmez.

## SD 1.5 / RTX 2050 profili

- Batch 1, Euler/normal, 20 adım, CFG 6.5; request UUID'den sabit seed.
- Kare **512×512**, dikey **384×640**, yatay **640×384**. Oran etiketleri mevcut
  kullanıcı niyetlerini ifade eder; bu düşük VRAM ölçüleri matematiksel tam 9:16
  veya 16:9 değildir. Gerçek çıktı boyutları kaydedilir; 1K/4K vaat edilmez.
- Stock `CheckpointLoaderSimple`, `CLIPTextEncode`, `EmptyLatentImage`, `KSampler`,
  `VAEDecodeTiled` (tile 256, overlap 64), `SaveImage`. İstemci workflow/node,
  checkpoint yolu veya endpoint gönderemez. `.safetensors` dosya adı yapılandırılır.
- Önceden kurulmuş ComfyUI için `START_LOCAL_IMAGE.bat` / `scripts/golge_comfyui_start.py`:
  loopback 127.0.0.1:8188, `--disable-dynamic-vram --lowvram --reserve-vram 1
  --cpu-vae --preview-method none --disable-all-custom-nodes`.
- ComfyUI/PyTorch bağımlılıkları ayrı ComfyUI Python ortamında kalır. GÖLGE
  ortamına CUDA/Torch yüklenmez. Script paket/model indirmez ve Windows ayarı değiştirmez.
- Readiness, kurulu checkpoint listesini ve CUDA cihaz metadatasını gerçek ComfyUI
  API'sinden kontrol eder. Checkpoint dosyasının gerçekten SD 1.5 olduğu operatörün
  güvenilir model kurulumuna bağlıdır; yalnız dosya adından ağırlık doğrulaması yapılmaz.
- Qwen otomatik kapatılmaz/VRAM'den atılmaz. Eşzamanlı Qwen/SD bellek kullanımı,
  gerçek VRAM tepe değeri, hız ve görsel kalitesi **NOT RUN**; OOM başarı sayılmaz.

Resmî kaynak doğrulaması: [ComfyUI kaynak kodu](https://github.com/Comfy-Org/ComfyUI/tree/c06bf5f569d268b80076e5f44126f87cdf835869),
[CLI seçenekleri](https://github.com/Comfy-Org/ComfyUI/blob/c06bf5f569d268b80076e5f44126f87cdf835869/comfy/cli_args.py),
[API örneği](https://github.com/Comfy-Org/ComfyUI/blob/c06bf5f569d268b80076e5f44126f87cdf835869/script_examples/basic_api_example.py),
[SD 1.5 model kartı](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5).
18 Ekim'de incelendi. Model kartı 512 eğitim çözünürlüğünü, daha az VRAM kullanan
`v1-5-pruned-emaonly.safetensors` ağırlığını ve CreativeML OpenRAIL-M lisansını belirtir.
Ağırlık indirme/lisans kabulü ve gerçek inference sonraki cihaz doğrulamasındadır.

## Sonraki cihaz doğrulaması için yapılandırma

Bunlar henüz uygulanmadı; bu aşamada kullanıcıdan laptop komutu çalıştırması istenmez.

Cloud ortamı:
```dotenv
GOLGE_IMAGE_PROVIDER=comfyui_local
GOLGE_LOCAL_IMAGE_ENABLED=true
```

Eşleşmiş Windows laptopun mevcut güvenli ortamına eklenecek değerler:
```dotenv
GOLGE_COMFYUI_ENABLED=true
GOLGE_COMFYUI_URL=http://127.0.0.1:8188
GOLGE_SD15_CHECKPOINT=v1-5-pruned-emaonly.safetensors
GOLGE_COMFYUI_HOME=C:\ComfyUI
GOLGE_COMFYUI_PYTHON=C:\ComfyUI\.venv\Scripts\python.exe
```
Mevcut Cloud URL/cihaz anahtarı eşleşmesi korunur; ComfyUI internete açılmaz.
Python yolu mevcut ComfyUI kurulumuna göre seçilir. Kod arayüz üzerinden key,
shell veya özel node çalıştırma izni vermez. Yapılandırılmış model kurulu değilse
hazır göstermez. Türkçe istekler doğru yönlendirilir; SD 1.5'in Türkçe görsel kalitesi
bu sahte sağlayıcı testlerinden çıkarılamaz. Ücretli çeviri çağrısı eklenmedi.

## Güvenlik, kuyruk ve iptal

- Mevcut auth, kullanıcı/sohbet sınırı, Origin/CSRF ve tek agent görev şeridi korunur.
  Son 15 saniyedeki **aynı kullanıcı** laptop heartbeat'i `local_image_ready=true`
  demeden yeni istek kabul edilmez. Çevrimdışı durumda dürüst 503 döner.
- Kullanıcı başına bir aktif görsel ve günde 20 kabul edilmiş istek; max_retries=0.
  Aynı request UUID / içerik tekrar teslimde yeniden kuyruklanmaz; farklı içerik 409.
- Mevcut `delivery_attempt` fencing, lease yenileme ve worker kaybı sınırları korunur.
  İstemci 270 sn, Comfy üretim döngüsü 240 sn + sınırlı HTTP zaman aşımı, Cloud
  kuyruk kaydı en geç 10 dk sonra sorguda sona erer. Yeniden başlatma otomatik
  üretim tekrarı yapmaz. Kaybolan sonuç başarı olarak bildirilmez.
- Sonuç yalnız cihaz kimliği + aktif eşleşen teslim nesliyle kabul edilir. Görsel,
  gerçek Pillow decode/MIME/boyut/profil kontrolünü geçtikten sonra mesajlar,
  dosya ve queue ACK aynı PostgreSQL transaction'ında kaydedilir. Queue result'a
  base64 görsel veya ham provider hata logu yazılmaz; prompt bitince scrub edilir.
- İptal tombstone'u ve kuyruğun iptal durumu aynı kilit altında yazılır; geç sonuç
  kaydedilmez. ComfyUI'de yalnız ilgili prompt_id bekleme kuyruğundan silinir.
  **Global `/interrupt` çağrılmaz**: çalışan başka işleri durdurmaz. Başlamış GPU
  işi için gerçek compute iptali iddia edilmez; `output_suppressed` doğru durumdur.
- HTTP proxy/redirect yok; yalnız numeric loopback, sabit API yolları. Çıktı dosyası
  `golge-local*` ve güvenli dosya adı olmalı; path traversal/subfolder reddedilir.
  Yanıtlar byte sınırıyla sonuna kadar okunur; bölünmüş ağ yanıtları test edildi.
- Mevcut özel görüntü erişimi ve son 12 / 30 gün byte saklama korunur. ComfyUI'nin
  yerel output klasörünü GÖLGE otomatik temizlemez; yerel saklama operatörce yönetilir.
  UUID ledger geçmişi silinmez. Kullanıcı verisi veya üretim DB'si testte kullanılmadı.

## Doğrulama

- **474 PASS**: Cloud tüm testleri + yeni Comfy transport testleri, gerçek geçici
  PostgreSQL; 0 FAIL/0 SKIP, 368 ek subtest. Bu toplam içinde 7 yeni Cloud queue ve
  8 yerel transport/profil testi bulunur.
- **1307 PASS, 3 SKIP** backend regresyonu; altı ek subtest. Atlananlar mevcut
  parser kapsamı, Picovoice anahtarı ve fiziksel Windows/mikrofon E2E.
- **59 PASS** frontend Node, **169 PASS** PWA Node; build ve Python compile PASS.
- **10 PASS** gerçek Chromium Image Studio: 7 mevcut regresyon + 3 ücretsiz kuyruk,
  onaysız/ücretsiz yönlendirme ve iptal. **2 PASS** araştırma renderer regresyonu.
- Ek ayrı komutlar: Earth JS 6 PASS (59'a dahildir), Earth Python 6 PASS,
  native download policy 1 PASS. Örtüşen sayılar bağımsız toplam diye toplanmaz.
- Kontrollü E2E: telefon cookie/Origin HTTP → gerçek DB kuyruğu → cihaz claim →
  sahte ComfyUI HTTP /prompt /history /view → gerçek decode → fenced ACK → özel
  dosya/sohbet geçmişi. Sahte CUDA metadatası/PNG, gerçek model başarısı değildir.
- **NOT RUN**: fiziksel laptop/RTX 2050, gerçek SD 1.5 inference ve VRAM/FPS/gecikme,
  fiziksel iPhone, mikrofon/TTS, gerçek iki cihaz arası aktarım.
- Ücretli Gemini görsel çağrısı **yapılmadı**; ücretsiz modda SDK engeli PASS.
- Son commit'in GitHub Actions durumu yeni taslak PR'da doğrulanır; merge/deploy yok.

Tarayıcı kanıtları sentetiktir: [Windows düzeni](free-image-studio/free-image-desktop-fixture.png),
[iPhone düzeni](free-image-studio/free-image-phone-fixture.png). Sade sohbet/CORE korunur.

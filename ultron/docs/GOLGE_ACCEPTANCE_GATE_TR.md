# GÖLGE — 10 çekirdek yetenek kabul kapısı (V1)

Tarih: 2026-10-16 · Üretim Render son doğrulanan commit: `c554d640` · Geliştirme başlangıcı: `b4086aac`.

## İlke ve sonuç türleri

**Kodun bulunması, testlerin yeşil olması ve gerçek kullanıcı cihazında çalışması farklı kanıtlardır.**
Bir yetenek yalnızca otomatik test + ilgili gerçek cihaz/sağlayıcı smoke testi + beklenen çıktı
kanıtlandığında **DOĞRULANDI** kabul edilir. Log veya ekranda sadece "success" yazması
işlemin gerçekten gerçekleştiğini kanıtlamaz. Desteklenmeyen cihaz/model için yalancı
başarı yerine **DOĞRULANMADI / ERİŞİLEMİYOR** kullanılır.

Durumlar: `CODE` (uygulama kodu mevcut), `CI` (otomatik doğrulama kanıtı var),
`DEVICE_PENDING` (gerçek cihaz testi eksik), `BLOCKED` (önkoşul yok),
`VERIFIED` (uçtan uca kanıt tamam). Bu liste rapor tarihindeki kabul değerlendirmesidir;
test adları ileride değişirse yeniden doğrulanmalıdır.

## On temel yetenek için gerçek kabul ölçütleri

| # | Yetenek | Otomatik kapı / kanıt | Gerçek dünya kabul senaryosu | Mevcut kabul |
|---|---|---|---|---|
| 1 | Bulut API + oturum güvenliği | `cloud-queue-postgres.yml`; `test_provider_error_privacy.py` | Render `/health` HTTP 200 ve `ok=true`; yetkisiz `/api/session` 401; geçerli giriş ve çıkış çalışır, sır sızmaz | CI tekrar doğrulanacak |
| 2 | Kullanıcıya özel kalıcı hafıza | `test_memory_history_v3.py`, `test_episodic_memory_v4.py` ve PostgreSQL kapsamı | İzinli anı kaydet → düzelt → yeni oturumda geri çağır → sil → tekrar çağırınca yok; başka kullanıcıya sızmaz | CODE / DEVICE_PENDING |
| 3 | Uzun konuşma ve hedefi hatırlama | `test_continuation_paging.py`, `test_golge_memory_focus_continuity.py` | Uzun sohbet sonrası önceki hedefi ve son düzeltmeyi doğru, kaynaklı ve uydurmadan aktarır | CODE / DEVICE_PENDING |
| 4 | Gerçek yerel Qwen ve bulut köprüsü | `test_local_brain_postgres.py`, `test_local_dialogue_runtime.py` | Windows Ollama çevrimiçiyken telefondaki yerel model isteği gerçek yanıt döner; PC kapalıyken başarı uydurmaz | CODE / DEVICE_PENDING |
| 5 | Kesintisiz/elle başlatılan ses | `test_voice_stack_state_machine.py`, `test_voice_vad.py` | Gerçek Windows mikrofonu ve hoparlörle konuşma → doğru STT → yanıt → TTS; wake modeli kuruluysa uyandırma ve araya girme çalışır | CODE / DEVICE_PENDING |
| 6 | Güvenli bilgisayar ve tarayıcı kontrolü | `test_cloud_delivery_guard.py`, `test_wave4_browser.py`, `test_risk_engine.py` | İzinli ve geri alınabilir uygulama açma görevi gerçek Windows'ta sonuç verir; riskli işlemler ayrı kullanıcı onayı olmadan yürütülmez | CODE / DEVICE_PENDING |
| 7 | Telefon → masaüstü görev kuyruğu | `test_device_queue_postgres.py`, `test_local_brain_bridge.py` | Eşleştirilmiş PC heartbeat görünür; telefondan verilen tek bir güvenli görev bir kere çalışır, kesinti/iptal durumunda çift işlem oluşmaz | CODE / DEVICE_PENDING |
| 8 | iPhone PWA sohbet ve geçmiş | `test_mobile_chat_flow.cjs`, `test_mobile_action_guard.cjs` | Fiziksel iPhone Safari'de oturum, yazışma, geçmiş, ekran güvenli alanları ve ağ kesintisinden dönüş doğrulanır | CODE / DEVICE_PENDING |
| 9 | Dünya/veri/görsel araştırma | `test_world_contract.cjs`; WORLD read-only smoke | Gerçek sağlayıcıdan veri, 2D/3D dünya ekranı ve açıkça izin verilmiş kamera/görsel girdisi doğrulanır; sağlayıcı hatasında sahte veri gösterilmez | CI kısmi / DEVICE_PENDING |
| 10 | Planlı ajan ve güvenli kod iyileştirme | `test_self_coding_loop.py`, `test_task_engine.py`, `test_shell_policy.py` | Yalıtılmış test dalında planla → güvenlik onayı → değiştir → test → geri al / PR aç; ana dala veya kullanıcı dosyalarına izinsiz yazma yok | CODE / DEVICE_PENDING |

**Kapsam dışı/engelli:** Fiziksel havada hologram, tam native iOS/Siri izinleri,
bilgisayar kapalıyken bilgisayarı kontrol etme ve gerçek bağlı IoT cihazları ayrı donanım/
izin projeleridir. Ekrandaki 3D sahne, fiziksel hologram olarak raporlanmaz.

## Sıralı kontrol akışı

### G0 — CI sağlığı (ilk blokaj)
- Aynı commit için Cloud Queue PostgreSQL Integration iki işinin de PASS olması:
  `persona-policy` ve gerçek PostgreSQL'li `postgres-fencing`.
- 2026-10-16 üretim SHA `c554d640` için `postgres-fencing`, testler başlamadan
  `public.ecr.aws/docker/library/postgres:16` indirilirken
  `toomanyrequests: Data limit exceeded` yüzünden durdu. Bu uygulama test başarısızlığı
  olarak etiketlenmemelidir; ama yeşil kabul kapısı da değildir.
- İmaj resmi `postgres:16` ile değiştirilen PR'ın kendi GitHub Actions koşusu
  tamamlanmalı. Bunun da pull sınırına takılması halinde başka kanıtlanmış bir
  registry/cache çözümü değerlendirilmeli. Hiçbir test job'ı kaldırılmayacak,
  `continue-on-error` kullanılmayacak.

### G1 — Bulut oturumu ve hafıza
- `/health` sadece yapılandırma bayrakları ve deploy SHA'sını gösterir; canlı
  model doğruluğunu veya masaüstü varlığını ispatlamaz.
- Üretim API'yı yalnızca sahip oturumuyla, gerçek ama test amaçlı veriyle dene.
  Test notunu sonra sil; kişisel sırları test verisi yapma.

### G2 — Windows ve yerel model
- Bilgisayarda mevcut giriş yöntemiyle `DOCTOR.bat` çalıştır; raporunu incele.
- `START.bat` ile UI ve backend açıldıktan sonra gerçek bir Qwen sorusu, sonra
  güvenli bir araç işlemi deneyip *araç sonucunu* gözle.
- Mikrofon/PortAudio, wake-word modeli, TTS ve Windows ekranı yoksa ilgili test
  `DEVICE_PENDING` kalır; birim testinden dolayı tamamlanmış sayılmaz.

### G3 — iPhone ve cihaz köprüsü
- Aynı sahip hesabıyla PWA giriş/çıkış, geçmiş, telefondan yerel Qwen, çevrimdışı
  hata, yeniden bağlantı ve iptal akışını gerçek iPhone'da doğrula.
- iOS Kestirmeleri için kullanıcı onayını atlama. iOS arka planında sürekli ses/
  bildirim veya Siri yetkisi varsayma.

### G4 — Kontrol edilen ajan ve sürüm kapısı
- Yalnızca geri alınabilir, izinli görevler ve test deposu kullan.
- Önce dry-run/onay, sonra tek kontrollü işlem, log/çıktı, olumsuz durum ve
  rollback doğrula. Kendini onaylama veya production auto-deploy yok.
- GitHub testleri + Render health + gerçek cihaz kanıtları aynı sürüm için kayıt
  altına alınmadan **VERIFIED** yazma ve otomatik deploy'a geçme.

## Kayıt şablonu

Her deneme için şu alanları sakla: UTC zaman, commit SHA, ortam (GitHub/Render/Windows/
iPhone), kontrol adı, beklenen sonuç, gözlenen sonuç, PASS/FAIL/SKIP, log veya
ekran kanıtının sır içermeyen referansı, hata açıklaması. Gizli token, ses kaydı,
kişisel sohbet veya kullanıcı dosyalarını GitHub issue/PR'a kopyalama.

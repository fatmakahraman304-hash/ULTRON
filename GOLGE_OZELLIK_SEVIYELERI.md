# GÖLGE — telefon ve laptop özellikleri, seviyeye göre (2026-10-21)

Bu liste **dürüstlük için** yazıldı: yüzde değil, kanıta dayalı seviye kullanır. "JARVIS yüzdesi" ölçülebilir bir şey değildir (ROADMAP'te de böyle kayıtlı); aşağıdaki seviyeler yalnızca *ne kanıtlandığını* söyler.

## Seviye ölçeği
| Seviye | Anlamı |
|---|---|
| **S4 — Test'li, veritabanıyla doğrulanmış** | Kod + birim testi + gerçek PostgreSQL 16 testi + CI yeşil. Gerçek telefonda/laptopta henüz denenmedi. |
| **S3 — Test'li, dış bağımlılık doğrulanmadı** | Kod + birim testi (sahte sağlayıcıyla) yeşil. Canlı API / gerçek cihaz / gerçek Gemini ile denenmedi. |
| **S2 — Var, bu oturumda doğrulanmadı** | Depoda eski/mevcut özellik; bu oturumda değiştirilmedi ve çalıştırılmadı (Windows/donanım gerekir). |
| **S1 — Kısmi / zayıf** | Çalışır ama sınırlı; bilinen eksikler var. |
| **S0 — Yok** | Henüz yazılmadı. |

Hiçbir özellik için "gerçek cihazda doğrulandı" iddiası yoktur. Laptop kapalıydı; iPhone ve Windows'ta hiçbir şey çalıştırılmadı.

---

## TELEFON (GÖLGE PWA + Cloud)

### Konuşma ve zekâ
| Özellik | Seviye | Not |
|---|---|---|
| Doğal sohbet (Gemini) | S3 | Üslup talimatı (kısa/samimi/sen-siz/isim/emoji) eklendi; gerçek model davranışı ölçülmedi |
| Kalıcı üslup tercihleri | S4 | "kısa cevap ver", "bana Murat diye hitap et" … cihazlar arası |
| Canlı sesli konuşma (Gemini Live) | S3 | `golge_skill` aracı + ses kuralları eklendi; modelin aracı gerçekten çağırıp çağırmadığı denenmedi |
| Sesle yetenek kullanımı | S4 (kod) / S3 (canlı) | Yazma yetenekleri sınırlı; silme/iptal/akıllı ev sesle kapalı |
| Konuşma geçmişi hatırlama | S4 | "dün ne konuştuk", "nerede kalmıştık", "X hakkında ne konuşmuştuk" |
| Görsel / PDF / kamera analizi | S2 | Mevcut; bu oturumda değişmedi |
| YouTube özetleme | S3 | Gemini gerekir, denenmedi |
| Çok adımlı görev ("görev: …") | S3 | Gerçek Gemini ile plan kalitesi ölçülmedi |

### Hafıza ve kendini geliştirme
| Özellik | Seviye | Not |
|---|---|---|
| Hafıza kaydet/unut/listele | S4 | Açık komut gerekir; sırlar reddedilir |
| Hafıza düzeltme + sürüm geçmişi | S4 | `düzelt: x => y`, "hafızada x notumun geçmişi" |
| Hafıza arama / son notlar / özet | S4 | Sahibe özel |
| Geri bildirim (👍/👎, "yanlış anladın") | S4 (kod) / S2 (arayüz) | Butonların iPhone görünümü doğrulanmadı |
| Kullanım sayacı + günlük tek öneri | S4 | |
| Rutin yönlendirme kalite kapısı | S4 | 479 etiketli cümle, sıradan sohbet hiç yakalanmıyor (0/187) |

### Hazır yetenekler (model çağırmadan)
| Özellik | Seviye | Not |
|---|---|---|
| Saat/tarih/dünya saatleri, geri sayım | S4 | |
| Hesap, birim çevirme, yüzde | S4 | |
| Pratik: yazı-tura, zar, rastgele, seç, tarih aritmetiği, yaş, VKİ, bahşiş/hesap bölme | S4 | |
| Hava durumu (konumlu) | S3 | Open-Meteo yanıt biçimi canlı doğrulanmadı |
| Döviz, kripto | S3 | Frankfurter / CoinGecko canlı doğrulanmadı |
| Haberler, namaz vakti, deprem, gün doğumu, Vikipedi | S3 | Canlı sağlayıcılar denenmedi |
| Uçuş arama bağlantısı | S3 | Fiyat çekmez, yalnızca bağlantı |
| Yol tarifi / yakınımda / trafik (bağlantı) | S3 | Apple/Google Maps bağlantıları |

### Kişisel düzen
| Özellik | Seviye | Not |
|---|---|---|
| Hatırlatıcılar (tekrarlı, zamanlayıcı, erteleme) | S4 | |
| Plan/takvim, çakışma uyarısı, boş zaman bulma | S4 | iCal okuma salt-okunur, https + izinli sunucular |
| Doğum günleri (yıllık hatırlatıcı + geri sayım) | S4 | |
| Alışkanlıklar (su/uyku/spor/adım/kilo/mod) + seriler | S4 | Tıbbi tavsiye vermez |
| Harcamalar + aylık bütçe uyarısı | S4 | Yalnızca TL |
| Listeler (alışveriş vb.) | S4 | |
| Günlük (private) | S4 | |
| Rutinler (adım listeleri + adım başına hatırlatıcı) | S4 | |
| Pomodoro / odak | S4 | |
| Haftalık özet (+ isteğe bağlı pazar bildirimi) | S4 | |
| Sabah özeti (isim, dün özeti, hava, gündem, kur) | S4 (kod) / S3 (canlı veriler) | |

### Bildirim ve proaktiflik
| Özellik | Seviye | Not |
|---|---|---|
| Web Push (kilitli telefonda) | S3 | RFC 8291/8292 test vektörüyle doğrulandı; **gerçek iPhone'da denenmedi** |
| Yaklaşan etkinlik / yağmur / deprem / fiyat uyarıları | S3 | Sağlayıcılar canlı denenmedi |
| Sessiz saatler, uyarı anahtarları | S4 | |

### Hologram (telefon + laptop ortak)
| Özellik | Seviye | Not |
|---|---|---|
| İstenen şekli hazır kütüphaneden üretme (45 şekil, sayı ve birleşim) | S4 (kod) / S2 (ekran) | Gerçek three.js ile 30 şekil görsel kontrol edildi; telefon/laptop arayüzünde denenmedi |
| Bilinmeyen şekil → Gemini tarifinden | S3 | Gemini denenmedi; renk şemada yok |
| İnternetten CC0 model bulma (Poly Haven) | S2 | Mevcut |
| Dönüş/ölçek/taşıma/yok etme komutları | S2 | Mevcut |

### Sonradan eklenenler (2026-10-21, aynı oturum)
| Özellik | Seviye | Not |
|---|---|---|
| Hesap kutusu: kredi taksiti, bileşik faiz, KDV, indirim, % değişim, yakıt maliyeti, liste istatistikleri, asal/faktöriyel/EBOB-EKOK/Fibonacci, sayı yazıyla, Roma rakamı, ikilik/onaltılık | S4 | 30+ komut, çevrimdışı, sınır testli |
| Metin/kod araçları: Türkçe büyük-küçük harf, ters çevir, say, palindrom, Base64, Mors, hex↔rgb | S4 | |
| Yaşam hesapları: uyku saati, burç/Çin burcu, tempo, kalori tahmini (tavsiye değil), tarif ölçekleme, mutfak ölçüleri, saat dilimi, iş günü, sabit resmî tatiller, artık yıl, yıl ilerlemesi | S4 | Dinî bayram tarihleri YOK |
| Defterler: rehber, borç/alacak, hedefler, kronometre/zaman kaydı, yakıt kaydı | S4 | Silme yalnızca yazıyla |
| Eğlence/iyi oluş: motivasyon, atasözü/deyim, espri, doğrulanmış bilgiler, günün kelimesi, bilmece, taş-kağıt-makas, 8 top, yemek fikri, nefes/göz/esneme (tavsiye değil) | S4 | İçerik sabit listeden; yaratıcı istekler modele gider |
| Akıllı planlama: "şu işleri sığdır" önerisi → "planı onayla", kalan süre, sıradaki plan, erteleme | S4 | Onaysız hiçbir şey yazılmaz |
| Hazır listeler (13 şablon, deprem çantası dahil) | S4 | |
| Gün/hafta özeti (yalnız kayıtlı veriden) | S4 | |
| Eksik listesi + onaylı geliştirme isteği (kendini geliştirme) | S4 (bulut) / S3 (laptop tarafı) | Laptop ajanının "yalnız taslak" talimatına uyması doğrulanmadı |
| Sesle hologram, sesle yetenek kullanımı | S3 | Canlı oturumda denenmedi |

### Büyük bileşenler (2026-10-22)
| Özellik | Seviye | Not |
|---|---|---|
| **Ajan** ("ajan: <hedef>", sesle `start_agent`): düşün → araç kullan → gözlemle döngüsü; araçlar: hazır yetenekler (salt-okunur), hafıza/geçmiş arama, bilgi tabanı, web araştırması; laptop yalnız öneri | S4 (döngü, güvenlik sınırları, kalıcılık; sahte modelle) / **S2 (gerçek Gemini ile denenmedi)** | JSON protokolüne gerçek modelin uyup uymadığı bilinmiyor |
| **Onay kuyruğu**: ajan/öneriler yalnızca "bekleyen işlem" olur; yazarak `onayla N` ya da PWA kartındaki ONAYLA/REDDET ile uygulanır; yalnızca güvenli yazma yetenekleri çalışır; sesle onay yok | S4 | Silme, iptal, akıllı ev, hafıza, sırlar kapalı |
| **Kişisel bilgi tabanı**: not/belge ekleme (son analiz edilen belge/fotoğraf dahil), tam metin arama, "notlarıma göre: …" ile cevap bağlamı, bulamazsa tahmin etmez | S4 | Arayüz yok (komut + `/api/kb`); çok büyük PDF'ler denenmedi |
| **Durumsal farkındalık** (opt-in "akıllı öneriler aç"): yarın erken etkinlik → uyku saati + onaylı hatırlatıcı önerisi, yoğun gün, su, bütçe temposu, seri uyarısı | S4 (kurallar) / S3 (bildirim iletimi gerçek cihazda denenmedi) | |

### Cihaz bağlantıları
| Özellik | Seviye | Not |
|---|---|---|
| Telefondan laptopa görev ("laptop: …", "ekran analizi yap") | S3 | Kuyruk + sonuç dönüşü testli; gerçek laptopla denenmedi, laptop kapalıyken sıraya almaz |
| Akıllı ev (Home Assistant) | S3 | Kapı kilidi açmaz, garajı açmaz; gerçek HA yok |
| iOS Kestirmeler / telefon eylemleri | S2 | Mevcut |
| Eksik: yerel iOS uygulaması | S0 | Mac derlemesi gerekir |

### Altyapı / güvenlik
| Özellik | Seviye | Not |
|---|---|---|
| Giriş kilitleme, hız sınırı, güvenlik başlıkları, güvenli 500 | S4 | |
| Derin sağlık, tanılama, bakım/saklama, veri dışa aktarma | S4 | Sohbet geçmişi ve sırlar dışa aktarmaya girmez |
| CI (9 kontrol, gerçek PostgreSQL) | S4 | Son kontrol: 9/9 yeşil (b28e928) |
| Bağımsız hata incelemesi | S4 | 20 bulgu çıktı, çoğu düzeltildi |

---

## LAPTOP (Windows kokpiti + masaüstü ajanı)

Bu bölümdeki her şey **mevcut kod**; bu oturumda Linux'ta çalıştırılamadığı için S2'dir. Kök testlerde 5 masaüstü/ortam testi Linux'ta kırmızı (Windows gerektiriyor).

| Özellik | Dosya | Seviye |
|---|---|---|
| Ana kokpit (PyQt6 + React/Three.js) | `main.py`, `ultron/frontend` | S2 |
| **Çift tıkla açılış (yeni): `GOLGE.vbs` + `GOLGE_KISAYOL_KUR.vbs`** | kökte | S3 (dosya içeriği testli; **Windows'ta çalıştırılmadı**) |
| Sesli uyandırma, STT, TTS | `core/wake_word.py`, `stt.py`, `tts.py` | S2 |
| Ekran analizi | `actions/screen_processor.py` | S2 |
| Uygulama açma | `actions/open_app.py` | S2 (1 test Linux'ta kırmızı) |
| Tarayıcı / web otomasyonu | `actions/browser_control.py`, `web_search.py` | S2 |
| Fare-klavye kontrolü, bilgisayar ayarları | `computer_control.py`, `computer_settings.py` | S2 |
| Dosya yönetimi / işleme | `file_controller.py`, `file_processor.py` | S2 |
| Kod yardımcısı / geliştirme ajanı | `code_helper.py`, `dev_agent.py` | S2 |
| Mesaj gönderme (WhatsApp çekirdeği) | `send_message.py`, `plugins/_whatsapp_core.py` | S2 |
| Sistem izleme, arka plan izleme | `system_monitor.py`, `background_monitor.py` | S2 |
| Video / YouTube | `video_player.py`, `youtube_video.py` | S2 |
| Hava, uçuş, oyun güncelleme | `weather_report.py`, `flight_finder.py`, `game_updater.py` | S2 |
| Hologram çalışma alanı (GLB, parçalama, el hareketleri) | `ultron/frontend/src/hologram` | S2 |
| **Hologram: istenen şekli üretme (yeni)** | `shape_library.py` + `scene_design_api.py` | S4 kod / S2 ekran (çevrimdışı çalışır) |
| Yerel beyin (Qwen/Ollama), yerel görsel üretim | `integration/local_cloud_brain.py`, `comfyui_image.py` | S2 |
| Cloud ↔ laptop köprüsü, bellek eşitleme | `integration/cloud_memory_sync.py`, `ultron/backend/cloud_*` | S3 |
| Onay kapısı, geri alma, denetim kaydı | `core/confirm.py`, `core/undo.py` | S2 (kapatılmadı) |
| Güvenli kendini güncelleme | `integration/safe_self_update.py` | S2 |
| Dünya/Earth izleme | `ultron/backend/earth_watch.py` | S2 |

---

## En zayıf yerler (dürüst özet)
1. **Gerçek cihaz kanıtı yok:** iPhone push, canlı sesli oturum, laptop köprüsü ve Windows başlatıcı denenmedi.
2. **Canlı veri sağlayıcıları** (hava, kur, haber, namaz, deprem) yalnızca sahte yanıtlarla test edildi; yanıt biçimi değişmişse "ulaşamadım" der.
3. **Konuşma kalitesi** (Gemini/Qwen) ölçülmedi; üslup talimatının etkisi bilinmiyor.
4. **Renk, malzeme, animasyon** hologram şemasında yok; şekiller tek renk.
5. **Yerel iOS uygulaması** yok; PWA'nın iOS sınırları geçerli (bildirim için Ana Ekrana eklemek şart).
6. PR #62 **birleştirilmedi, Render'a deploy edilmedi**; bu yüzden telefon tarafı canlı değil.

## Sonraki adım için denenecekler
`ULTRON_NEXT_TASKS.md` içinde adım adım yazılı.

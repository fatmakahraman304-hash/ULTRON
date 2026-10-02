# ULTRON arayüzü — 2 Ekim 2026

Mevcut MARK + ULTRON projesi güncellendi. Başlatmak için START.bat kullanılır.

- Kırmızı/siyah masaüstü paneli: hareketli enerji küresi, yörüngeler ve ışıklı kaide.
- Gerçek CPU, RAM, GPU, sıcaklık, depolama ve model durumları.
- Sohbet, PDF/metin ekleme (8 MB), dosya özeti ve kalıcı not kaydetme.
- Ayarlar ve kişiselleştirme: isim, renk, parlaklık, animasyon, tema, robot avatarı ve konuşma geçmişi.
- Telefon ekranlarına uyumlu yerleşim; ayarlar ve dosya yükleme erişilebilir.
- Windows içindeki ses denetimleri mevcut MARK çalışma zamanına bağlıdır. Tarayıcıda ses Windows uygulamasından yönetilir.
- Ayarlar > MARK araçları / Gelişmiş ULTRON araçları önceki özellikleri açar.

Robot avatarı SVG ile çizilmiştir; hareketli küre canvas ile oluşturulur. Görsellerdeki tasarım esas alınmıştır; fotoğraf gerçekliğinde bir 3B yüz değildir. Bakış hareketi işaretçiyi izler; kamera yüz takibi eklenmemiştir.

Doğrulama: masaüstü ve mobil üretim derlemeleri; tarayıcı etkileşim testi (dosya, not, tercihler, avatar, 375/820/1280 px taşma kontrolü, sıfır JavaScript hatası); gerçek Windows Qt açılışı ve ekran görüntüsü. Test görselleri logs/design altındadır. Sesli Gemini oturumu bu arayüz testinde başlatılmamıştır.

Önceden oluşturulan MARK-ULTRON-MERGED-TAM.zip bu tasarım güncellemesinden öncedir. Güncel uygulama bu klasördedir.

Entegrasyon regresyonu: 25 test geçti. Görsel kontrolü tekrar çalıştırmak için `.venv\Scripts\python.exe scripts\verify_cockpit.py` kullanılır (Playwright Chromium gerekir).

# ULTRON masaüstü

START.bat tek ana pencereyi açar: PyQt6 içinde React/TypeScript dashboard ve gerçek Three.js Core. Ana ekranlar arasında seçim veya eski dashboarda dönüş yoktur. Hologram Çalışma Alanı (Ctrl+H), GLB/parça/el kontrolü için ayrı uzman araçtır.

1920×1080 tasarım alanı pencereye orantılı ölçeklenir; 1366×768 de desteklenir. Merkez sahne, mekanik halkalar, parçacıklar, oda ve platform tamamen geometridir; arka plan resmi/video kullanılmaz. Sistem kartları gerçek backend ölçümlerini gösterir; eksik veri N/A olur.

Üst menü ayarları, ses kontrollerini, dosyaları, araç ve eklenti kayıtlarını açar. Alt menü mevcut browser, dosya, terminal, ekran, OCR, görev ve kod araçlarını kullanır. Terminal ve dosya işlemleri mevcut sandbox/onay sisteminden geçer. Model seçimi Ayarlar içindedir ve kurulu Ollama modellerinden gelir. Canlı ses motoru native STT/TTS akışını kullanır; mikrofon düğmesi ve ESC mevcut ses kontrolüne bağlıdır.

Kurulum: INSTALL.bat. Tanılama: DOCTOR.bat. Uygulama kapalıyken START.bat -Smoke ile otomatik masaüstü açılışı denenebilir. Frontend değişirse ultron/frontend klasöründe npm ci ve npm run build çalıştırın.

Yerel model yanıtları mevcut backend sözleşmesine göre tamamlanmış yanıt olarak gelir; sahte token akışı gösterilmez. Backend kapalıysa ULTRON BACKEND OFFLINE, model yoksa MODEL NOT AVAILABLE görünür.

Özel sesle uyandırma için gerçek ultron.onnx modeli gerekir; henüz kurulu değildir. Elle mikrofon/bas konuş kullanılabilir. config/api_keys.json kişiseldir ve Git'e dahil edilmez.

Doğrulama: scripts/verify_dashboard.py gerçek backend/model ile tarayıcıyı; scripts/verify_native_dashboard.py Qt ses seviyesi ve hologram köprüsünü kontrol eder. Son ekranlar logs/final-ultron-1920x1080.png ve logs/final-ultron-1366x768.png dosyalarındadır. Test ekranları/cache/backups Git'e eklenmez.

# ULTRON — Orijinal MARK masaüstü

START.bat dosyasını açın. Tek ana ekran, MARK'ın orijinal masaüstü arayüzüdür; asistan adı ULTRON'dur. Yeni web kokpitleri, mobil alternatif ve arayüz değiştirme düğmeleri devre dışıdır. Bu ekranların kaynakları henüz fiziksel olarak silinmemiştir.

Orijinal avatar, ses, kamera ve araç kontrolleri korunur. Ctrl+L ile açılan Yerel AI / Görevler bölümünde Ollama, kod, agent ve uzun görev seçenekleri bulunur. Kurulum INSTALL.bat; tanılama DOCTOR.bat. Hologram aracının kurulumu için Node/npm gerekir; INSTALL.bat yalnız hologram sayfasını derler.

Sesle uyandırma için gerçek ultron.onnx modeli gerekir. Model henüz mevcut değildir. Eğitim hazırlığı: ultron/tools/ultron_wakeword/README.md. Normal sesli görüşme ve elle kontrol kullanılabilir.

Kişisel API ayarları config/api_keys.json içinde kalır ve Git'e eklenmez. Uygulama kapalıyken START.bat -Smoke ile gerçek pencere açılışı doğrulanabilir.

Hologram çalışma alanını üstteki düğmeden veya Ctrl+H ile açın. Modeli parçalarına ayırabilir, parçaları inceleyebilir, GLB yükleyebilir ve .ultron.json projesi kaydedebilirsiniz. Hologram penceresi kapanınca orijinal masaüstü açık kalır. El kontrolü için hologram içindeki tarayıcı düğmesini kullanın; kamera yalnız tarayıcıdaki düğmeyle başlar.

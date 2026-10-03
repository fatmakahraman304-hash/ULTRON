# ULTRON kontrol merkezi

Güncel ana ekran Mission Control referansının sahnesini ve yerleşimini kullanır. Aşağıdaki eski ekran açıklamaları araç görünümü içindir. SETTINGS ve VISION mevcut ayar/kamera ekranını açar; üstteki dönüş düğmesi kontrol merkezine döner. CPU, RAM, GPU, ağ ve disk değerleri gerçek sistem ölçümleridir.

HOLOGRAMI AÇ veya Ctrl+H gerçek 3D çalışma alanını açar. Ana ekrandaki küre, araç ve şehir görüntüleri sabit görsellerdir. Canlı kamera, harita ve hava durumu bağlanmadığında ekranda belirtilir. BROWSER ve TERMINAL ilgili isteği mesaj kutusuna hazırlar.

Doğrulanmış önizleme `logs/mission/ultron-mission-control-4k.png`: 3840×2160 piksel. Arka plan kaynağı 1672×941 olup ölçeklenir; yazılar ve düğmeler Qt tarafından çıktı çözünürlüğünde çizilir. Yeni görünüm için uygulamayı yeniden başlatın.

START.bat dosyasını açın. Tek ana ekran, MARK'ın orijinal masaüstü arayüzüdür; asistan adı ULTRON'dur. Yeni web kokpitleri, mobil alternatif ve arayüz değiştirme düğmeleri devre dışıdır. Bu ekranların kaynakları henüz fiziksel olarak silinmemiştir.

Orijinal avatar, ses, kamera ve araç kontrolleri korunur. Ctrl+L ile açılan Yerel AI / Görevler bölümünde Ollama, kod, agent ve uzun görev seçenekleri bulunur. Kurulum INSTALL.bat; tanılama DOCTOR.bat. Hologram aracının kurulumu için Node/npm gerekir; INSTALL.bat yalnız hologram sayfasını derler.

Sesle uyandırma için gerçek ultron.onnx modeli gerekir. Model henüz mevcut değildir. Eğitim hazırlığı: ultron/tools/ultron_wakeword/README.md. Normal sesli görüşme ve elle kontrol kullanılabilir.

Kişisel API ayarları config/api_keys.json içinde kalır ve Git'e eklenmez. Uygulama kapalıyken START.bat -Smoke ile gerçek pencere açılışı doğrulanabilir.

Hologram çalışma alanını üstteki düğmeden veya Ctrl+H ile açın. Modeli parçalarına ayırabilir, parçaları inceleyebilir, GLB yükleyebilir ve .ultron.json projesi kaydedebilirsiniz. Hologram penceresi kapanınca orijinal masaüstü açık kalır. El kontrolü için hologram içindeki tarayıcı düğmesini kullanın; kamera yalnız tarayıcıdaki düğmeyle başlar.

## Kırmızı ULTRON görünümü

Ana masaüstü siyah metal paneller, kırmızı vurgu, gümüş başlık ve yüksek DPI destekli kırmızı parçacık halkası kullanır. Ana pencerede MARK LV etiketi yoktur. Merkez görünümü ayarlardan değiştirilebilir; hologram Ctrl+H, yerel AI paneli Ctrl+L ile açılır.

Parçacık halkası 3.000 ışık noktası ve hareketli yörüngelerle çizilir; ölçek ve ekran yoğunluğu değiştiğinde önbellek yeniden üretilir. Yüz maskesi ve sağ alttaki imza kaldırılmıştır.

Paneller kesik köşeli metal katmanlarla çizilir. Konuşma, dosya ve komut alanları ayrı çerçevelerdedir. İşlevsiz yan şemalar kaldırılmıştır. Merkezde metal dokulu bir sahne görseli bulunur; parçacık halkası canlı çizilir. Sistem kartlarının küçük grafikleri gerçek ölçüm geçmişini gösterir.

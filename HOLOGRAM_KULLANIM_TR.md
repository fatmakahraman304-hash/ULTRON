# ULTRON Hologram Laboratuvarı

## Açılış

START.bat → ana çekirdeğin üstündeki **Hologram çalışma alanı** düğmesi.
Sohbete `hologramı aç` da yazılabilir. Gemini Live zaten çalışıyorsa sesle aynı komut söylenebilir.

## Eklenen özellikler

- Gerçek zamanlı Three.js/WebGL 3B sahne, döndürme ve yakınlaştırma.
- Parçalarına ayrılan 14 bileşenli kavramsal enerji çekirdeği ve 11 bileşenli robot kolu.
- Parça seçme, taşıma, yalıtma, odaklanma, tel kafes görünümü ve geometri bilgisi.
- Seçilen parçayı mevcut ULTRON modeline açıklatma.
- Kamera üzerinden yerel el takibi; kamera izin reddi, model yükleme hatası ve kaybolan el için durma davranışı.
- Kendi GLB dosyanı açma (30 MB, 200 statik mesh, 750.000 üçgen sınırı). Dış dosyalar engellenir; dokular tek GLB içinde olmalı. Rig/skin animasyonu desteklenmez. Tek mesh otomatik olarak anlamsal parçalara bölünmez.
- PNG görüntüsü kaydetme, mobil düzen ve klavye erişimi.

## El hareketleri

**Kamerayla el kontrolünü aç** düğmesine bas; tarayıcı kamera izni isterse izin ver. Windows penceresinde **El kontrolünü tarayıcıda aç** düğmesi aynı laboratuvarı varsayılan tarayıcıda açar. Orada kamera düğmesine bas. Backend bağlantısı için Windows uygulamasını açık tut. İçe aktardığın özel modeli tarayıcıda yeniden seçmen gerekir. El kameranın görüş alanında olmalı.

| Hareket | İşlem |
|---|---|
| Tek el; baş ve işaret parmağı ayrı | El hareketiyle sahneyi döndür |
| Baş ve işaret parmağını birleştir | İmlecin üzerindeki parçayı tut; elini hareket ettirerek taşı |
| İki elde baş ve işaret parmaklarını birleştir, elleri aç | Parçaları ayır |
| İki elde tutmayı sürdür, elleri yaklaştır | Parçaları birleştir |
| İki el; parmaklar sıkıştırılmamış | Eller arası mesafeyle yakınlaştır/uzaklaştır |
| Eli görüşten çıkar | Hareket durur |

Kamera görüntüsü aynalı gösterilir. Takip imlecini parçanın üzerine getirip tutma hareketini yap. İyi ışık ve ellerin görünmesi önemlidir. Fare kontrolleri her zaman kullanılabilir.

**Kamera kapat**, paneli kapatma veya sekmeyi gizleme akışı kamera track'lerini kapatır. Fiziksel kamera aynı anda başka uygulama tarafından tutuluyorsa o uygulamada kamerayı kapat. MARK'ın kamera görüntüsü el takibine geçerken durdurulur; mikrofon yeniden açılmaz.

## Fare ve komutlar

- Sol sürükle: döndür. Tekerlek veya iki parmak: yakınlaştır.
- Parçaya veya parça listesine tıkla: seç.
- Shift + sürükle: parçayı taşı.
- **Parçalara ayır / Birleştir** ve ayrım kaydırıcısı: parçaların uzaklığı.
- **Sadece bu parça**, **Parçaya odaklan**, **Sıfırla**: inceleme kontrolleri.
- Alt komut kutusu: `parçala`, `birleştir`, `sıfırla`, `odaklan`, `yalıt`.
- Çalışan Gemini Live'ın Türkçe transkripti aynı kısa komutları bu panele iletir. Panel bir ikinci mikrofon veya yeni konuşma hizmeti başlatmaz.

## Çalışma biçimi ve sınırlar

Bu özellik ekranda hologram görünümünde 3B etkileşim sağlar. Havada görüntü oluşturmaz; bunun için AR gözlüğü veya uygun görüntüleme donanımı gerekir. Filmdeki ULTRON'in tüm kurgusal yetenekleri uygulanmış değildir. Mevcut konuşma, dosya analizi, sistem izleme ve görev araçlarına bu çalışma alanı eklenmiştir.

Örnek modeller çizim amaçlıdır; çalışan reaktör, doğrulanmış mühendislik hesabı veya fizik simülasyonu değildir. İçe aktarılan modellerde işlev ve malzeme bilgisi tahmin edilip gerçekmiş gibi gösterilmez. Fotoğraftaki gerçek nesneyi otomatik 3B tarama veya malzeme tanıma eklenmemiştir.

Kamera kareleri MediaPipe ile Web Worker içinde cihazda işlenir; sunucuya yüklenmez. El modeli ve WASM dosyaları paket içinde bulunur. Backend, el takip worker'ına yalnızca aynı kaynaktan ağ erişimi veren CSP uygular; kütüphanenin harici metrik uçları engellenir. Yerel Windows/localhost uygundur; telefondan kamera erişimi için HTTPS gerekir.

## Doğrulama

- Masaüstü ve mobil üretim derlemeleri.
- Gerçek WebGL etkileşim testi: döndürme, parça seçme/yalıtma, parçalama/birleştirme, tel kafes, metin komutu, GLB yükleme ve bozuk dosyada sahneyi koruma.
- Gerçek MediaPipe modeli, yapay kamera kareleri üzerinde çıkarım yaptı; kameranın durdurulması ve pencerenin kapanması kontrol edildi.
- El işaretleyici algoritması: sıkıştırma, iki el, ölçekten bağımsız algılama, aynalı imleç ve eksik el verisi testleri.
- Windows PyQt WebEngine penceresinde 3B sahne ve tarayıcıya geçiş doğrulandı. Gömülü Qt kamera akışı test ortamında erken sona erdiği için kamera kontrolü tarayıcıda sunulur.
- Gerçek kullanıcının el hareketleri ve sesli komutların mikrofon üzerinden uçtan uca algılanması bu otomatik testlerde doğrulanmadı.

Testler: `scripts/verify_hologram.py`, `scripts/verify_native_hologram.py`, `node scripts/test_gestures.mjs`.
Görüntüler ve sonuçlar: `logs/hologram/`.

Teknik kaynak: [Google MediaPipe el takip kılavuzu](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/web_js).

Son sonuç: 26 entegrasyon testi ve 8 el hareketi algoritması kontrolü geçti. Tarayıcı etkileşim testi ile Windows sahne/tarayıcı geçiş testi başarılı.


## 3 Ekim güncellemesi: çalışma projeleri

- **Projeyi kaydet**: geometriyi, parça konumlarını, kamera açısını, notları, tel kafesi ve kesit durumunu tek `.ultron.json` dosyasında saklar. Windows uygulamasında kaydetme penceresi, tarayıcıda indirme açılır. GLB'den açılan model de dosyaya gömülür; yeniden orijinal GLB'yi seçmek gerekmez.
- **Proje aç**: en fazla 80 MB proje dosyasını doğrulayıp geri yükler. Bozuk dosya mevcut sahneyi değiştirmez. Bu dosyalar otomatik kaydedilmez; çalışmanı kapatmadan önce kaydet.
- **Geri al / İleri al**: aynı modeldeki son 60 düzenleme grubu. Parça taşıma/ayırma, not, yalıtma, tel kafes ve kesit değişiklikleri kapsanır. Model değiştirme veya proje açma düzenleme geçmişini sıfırlar; serbest kamera döndürme ayrı bir geri-al işlemi oluşturmaz.
- **Parça notu**: seçilen parça için en fazla 2.000 karakterlik not; proje içinde saklanır.
- **Parça boyutu**: modelin birleştirilmiş halindeki eksenlere paralel X/Y/Z sınır kutusu. Normalize edilmiş model birimi kullanır; metre veya santimetre değildir.
- **Kesit görünümü**: X yönündeki düzlemle geometrinin bir bölümünü gizler; dolgu yüzeyi üretmez ve fiziksel kesme simülasyonu değildir.

Yeni komutlar: `geri al`, `ileri al`, `kesit aç`, `kesit kapat`, `projeyi kaydet`. Windows'taki mevcut Gemini Live transkripti de açık Windows laboratuvarındaki bu kısa komutlara bağlanır. Tarayıcı laboratuvarında alt komut kutusunu kullan. Yeni bir mikrofon oturumu eklenmedi.

Kısayollar: sahne odaktayken Ctrl+Z, Ctrl+Y / Ctrl+Shift+Z ve Ctrl+S. Not veya komut yazarken metin kutusunun standart kısayolları korunur.

Doğrulama: proje gidiş-dönüşü, not/kesit korunması, geri al/ileri al, bozuk dosyada sahneyi koruma, komut olayları ve 375/820/1440 px ekranlar geçti. Windows'ta proje kaydı da doğrulandı. Gerçek mikrofonla ses tanıma yerine transkript olay bağlantısı test edildi.

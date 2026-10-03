# ULTRON akustik uyandırma modeli

Henüz eğitilmiş ultron.onnx yoktur. Eğitim şablonu düzeltilmiştir: hedef kelime negatif sınıfa eklenmez; batch_n_per_class veri kümelerine göre tanımlanır.

Birleşik proje kökünden hazırlık kontrolü:

```
.venv\Scripts\python.exe ultron\tools\ultron_wakeword\check_training.py
```

Çıkış kodu 2, eğitim girdilerinin eksik olduğunu belirtir. Bu kontrol model üretmez. Piper örnek üreticisi, eğitim bağımlılıkları, arka plan sesleri, oda yankısı kayıtları, negatif özellikler ve bağımsız yanlış tetiklenme doğrulama verileri gereklidir. Yapılandırmadaki göreli veri yolları ultron/backend dizininden çözülür.

Resmi eğitim not defteri:
https://github.com/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb

Hedef ifade ULTRON, model adı ultron olmalıdır. Eğitimden çıkan gerçek ultron.onnx dosyasını backend/data/voice/wake/ultron.onnx konumuna kurun. Başka kelimenin modelini yeniden adlandırmayın. Yükleme testi tek başına doğru algılama kanıtı değildir; gerçek mikrofonla olumlu örnekler, benzer kelimeler ve uzun arka plan kayıtları ayrıca ölçülmelidir.

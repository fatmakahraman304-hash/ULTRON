# ULTRON — Test / Doğrulama Kayıtları

Bu belge yalnızca **gerçekten çalıştırılmış** kontrolleri kaydeder.

## Başlangıç (2026-10-09)
- Referans HEAD: `0638b116c30d221f4167a4df35381a5697237668`.
- `ULTRON Scene Build Check`: **PASS** (GitHub Actions, başlangıç HEAD).
- `Frontend Build Check`: ayrıca workflow mevcut, son HEAD için Scene workflow frontend build'i de kapsıyor.
- Windows `START.bat`, gerçek mikrofon, Ollama, canlı ISS ve RTX 2050 FPS ölçümü: **Bu oturumda henüz çalıştırılmadı**.
- Tüm Python test süiti: **Bu oturumda henüz çalıştırılmadı**.
- Earth Watch davranış regresyon testi: **Başlangıçta mevcut değil**.

## Bu oturumdaki testler
Henüz yeni paket için tamamlanmış test sonucu yok. Kod değiştikçe komut, workflow run ve SHA ile birlikte doldurulacak.

## Çalıştırma sözleşmesi
- `python -m py_compile ultron/backend/server.py actions/ultron_stage.py`
- `cd ultron/frontend && npm ci && npm run build`
- Earth/math regresyon testleri (eklenecek).
- Başarısız sonuç varsa `PASS` olarak kaydedilmez.

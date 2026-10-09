# ULTRON — Kesintisiz Devam / Sıradaki İşler

**Kaynak repo:** `fatmakahraman304-hash/ULTRON`  
**Branch:** `feat/ultron-cloud-shared-memory`

## Hemen yapılacak
1. `CenterStage.tsx` içindeki `EarthWatch` fonksiyonunun ekran etkileşimlerini düzelt:
   - Earth kontrolünde kamera zoom/orbit konumunu koru.
   - Pointer drag ile gerçek nokta seçimini ayır.
   - Konum değiştirmeyi düzgün/smooth hale getir.
2. Tekrarlanabilir Earth coğrafi koordinat dönüşüm testlerini ekle.
3. `scene-check.yml` içinde ilgili testleri çalıştır.
4. GitHub Actions son HEAD build'i PASS olmadıkça teslim edilmiş sayma.
5. `ULTRON_PROGRESS.md` ve `ULTRON_TEST_RESULTS.md` gerçek sonuçlarla güncelle.

## Sonraki büyük geliştirmeler
- Earth Watch P1: offline texture varlığı ve açık lisanslı dünya/şehir katmanları.
- Server P1: Earth operation input doğrulama + kötü niyetli payload regresyonları.
- Agent P1: Cloud/device task at-most-once/idempotence testleri.
- Ses ve Wake Word P2: donanım opsiyonel status/health testleri.
- AI/Memory P2: model fallback, offline graceful degrade, permission/audit kapsamı.

## Devam prosedürü
`git status`, `git rev-parse --short HEAD`, dört ULTRON Markdown belgesi, son commit ve Actions job loglarını oku. Başarısız testleri ilk sıraya al. Kod, docs ve test sonuçlarının SHA'sını senkron tut. Güvenlik/hesap işlemlerinde kullanıcı onayı bekle; güvenli bir sonraki görev için bekleme.

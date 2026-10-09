# ULTRON — Teknik Yol Haritası

Bu belge `MARK-ULTRON-MERGED` gerçek kaynak ağacı üzerinden hazırlanmıştır. Kalıcı yön, kısa döngüler ve doğrulanabilir sonuçlar hedeflenir. **Bir yol haritası maddesi, test edilmeden tamamlanmış sayılmaz.**

## Korunacak çalışan mimari
- Yerel Python 3.12/aiohttp backend, React/TypeScript + Three.js arayüz, Ollama, SQLite ve Gemini Live entegrasyonu.
- Telefon → Cloud komut kuyruğu → masaüstü agent → yerel tool → Cloud sonucu → telefon zinciri.
- Scene Lab, Earth Watch, 3D video, snapshot, mission sequence, trigger ve GLB Asset Library.
- Kullanıcı onayı gerektiren işlemlerde Approval Gate, sandbox ve audit mekanizmaları.

## Gerçek incelemede belirlenen öncelikler

| Seviye | Alan | Somut eksik / risk | Bitti sayılma ölçütü |
| --- | --- | --- | --- |
| P0 | Earth Watch etkileşim | Bir ayar değiştiğinde Three.js renderer yeniden kuruluyor; mevcut kamera zoom/orbit durumu kaybolabilir. Pointer down, sürükleme başlangıcını koordinat tıklaması sanabilir. | Mod kontrolleri arasında kamera korunur; sürükleme yanlış pin seçmez; frontend CI yeşil. |
| P0 | Test güvenilirliği | Scene CI Python derlemesi ve frontend build yapıyor; Earth Watch davranışı için özel test yok. | Deterministik coğrafi geometri testleri ve kodun gerçek modülünü kullanan regresyon testi CI'a girer. |
| P1 | Stage/Earth state sağlamlığı | UI üzerinden gelen bool/koordinat/marker inputlarının bir kısmı doğrudan işleniyor. | Bozuk değerler güvenli biçimde normalize edilir; server testleri yazılır. |
| P1 | Earth Watch görsel kalite | Online Dünya/Cloud texture bağımlılığı; fallback harita şematiktir. | Lisansı açık yerel varlık stratejisi ve offline doğrulama; dış veri başarısızlığı UI'yi çökertmez. |
| P1 | Otonom agent güvenilirliği | Uzun görevlerde lease/timeout/sorunsuz tekrar deneme regresyonları önemlidir. | Kuyruk ve agent result path için tekrar yürütme/idempotence testleri ve ölçüm. |
| P2 | Ses | ULTRON wake-word, barge-in ve mikrofon hata iyileştirmeleri. | Ses sahipliği ve güvenli stop/start sınırı, donanım varsa end-to-end. |
| P2 | AI router + hafıza | Yerel/bulut hata ve model yokluğu durumunda dayanıklı yönlendirme. | Gerçek yok-modeller senaryoları ve permission/audit regresyonları. |
| P2 | Scene Editor | Performans, kalıcılık ve export bütünlüğü. | Import/save/load/render round-trip testleri ve FPS/VRAM sınırları. |
| P3 | Otomasyon uzmanları | Alt görev yaşam döngüsü ve durable checkpoint. | Yetkili tool sınırlaması, tekrar eden işi engelleme ve ölçülen ilerleme. |

## İncelenen yollar
- `ultron/backend/server.py`
- `ultron/frontend/src/dashboard/CenterStage.tsx`
- `ultron/frontend/src/dashboard/runtime.ts`
- `actions/ultron_stage.py`
- `ultron/backend/tests/`
- `.github/workflows/scene-check.yml` ve `frontend-check.yml`

## Geliştirme standartları
1. Mevcut implementasyonu araştır; eksik bilgiyi varsayımla kapatma.
2. Dar, geri alınabilir ve teste bağlanmış değişiklik grupları yap.
3. Build + ilgili test + CI sonucunu ayrı ayrı raporla.
4. Repo dışında dosya değiştirme, secret açığa çıkarma, güvenlik onayını devre dışı bırakma.
5. Güvenilir doğrulama olmadan `PASS` yazma; plan ve ilerleme belgelerini güncelle.
6. Araç/oturum kesilirse `ULTRON_NEXT_TASKS.md` belgesinden devam et.

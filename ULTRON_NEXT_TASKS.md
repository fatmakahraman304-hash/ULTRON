# ULTRON — Sonraki Kesin Görevler / Kesinti Devam Kaydı

**Repo:** `fatmakahraman304-hash/ULTRON`  
**Branch:** `feat/ultron-cloud-shared-memory`  
**Doğrulanmış kod HEAD:** `34b80e43abe023e58a8f65c87688aa104d6d55e7` (ardından doc-only commit gelebilir).  
**CI:** `ULTRON Scene Build Check` run `37894840971` — PASS.

## Hemen yapılacak
1. `git status` ve `python scripts/ultron_dev_resume.py` ile yeni oturumun durumunu oku.
2. Windows 11 cihazında son branch'i pull ederek `START.bat` çalıştır; Earth Watch kamera/zoom kaybı, drag seçimi, Türkiye/Kıbrıs focus ve UTC SUN düğmesini manuel test et. Başarı gözlemi olmadan PASS yazma.
3. İnternetsiz durumdayken Earth Watch fallback, ISS WAIT durumu, network request ve UI cleanup davranışını gözle.
4. **Cloud P1 devam:** `ultron/cloud_service/app.py` için gerçek PostgreSQL üzerinden eşzamanlı claim/ack/retry integration testi yaz ve CI'da opsiyonel servisle koş; `mark_app.py` worker yeniden teslim/retry davranışını incele. Attempt token/fencing (eski worker sonraki claim'i bitiremesin) eklemeden tam idempotence PASS yazma.
5. Yeni kod için `npm run build`, `npm run test:earth`, backend pure unittests ve uygun CI workflow'u çalıştır; 4 geliştirme belgesine gerçek sonuçları yaz.

## Test komutları
```bash
python -m unittest discover -s ultron/backend/tests -p 'test_earth_watch_config.py' -v
python -m unittest discover -s scripts/tests -p 'test_ultron_dev_resume.py' -v
python scripts/ultron_dev_resume.py
python -m unittest discover -s ultron/cloud_service -p 'test_device_queue_contract.py' -v
cd ultron/frontend
npm ci
npm run build
npm run test:earth
```

## Sonraki öncelikler
- Kullanım hakkı açık offline texture + gerçek GPU memory/texture cleanup testi.
- Audio owner, wake-word, Türkçe STT/TTS ve barge-in regresyonları.
- Ollama local/cloud provider düşüşü ve memory persistence testleri.
- Agent görev logları için bounded retry ve state/checkpoint mekanizması.

## Kesinti koşulları
GitHub erişimi, izin veya güvenlik engeli çıkarsa burada gerçek başarısız adımı belirt. Bir oturum kendiliğinden arka planda devam etmez; sonraki Codex oturumunda `AGENTS.md` ve bu dosya üzerinden başlanır.

## 2026-10-09 doğrulanan Cloud queue altyapısı
- SHA: `34b80e43abe023e58a8f65c87688aa104d6d55e7`; Actions `37894840971` PASS.
- Eşzamanlı claim advisory lock, inactive completion reddi, retry limit ve guard için 6 izolasyon testi.
- Sonraki agent kesin adım: live/ephemeral Postgres ile claim/fencing integration tests; Render deploy/telefon testini kullanıcı ortamında ayrı doğrula.

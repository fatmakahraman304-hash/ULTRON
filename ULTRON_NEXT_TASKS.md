# ULTRON — Sonraki Kesin Görevler / Kesinti Devam Kaydı

**Repo:** `fatmakahraman304-hash/ULTRON`  
**Branch:** `feat/ultron-cloud-shared-memory`  
**Doğrulanmış kod HEAD:** `a010726149f7a1352933a2e45af51f9b1a985662` (sonraki değişiklikler yalnızca bu belgelere ait olabilir).  
**CI:** `ULTRON Scene Build Check` run `37893780863` — PASS.

## Hemen yapılacak
1. `git status` ve `python scripts/ultron_dev_resume.py` ile yeni oturumun durumunu oku.
2. Windows 11 cihazında son branch'i pull ederek `START.bat` çalıştır; Earth Watch kamera/zoom kaybı, drag seçimi, Türkiye/Kıbrıs focus ve UTC SUN düğmesini manuel test et. Başarı gözlemi olmadan PASS yazma.
3. İnternetsiz durumdayken Earth Watch fallback, ISS WAIT durumu, network request ve UI cleanup davranışını gözle.
4. `ultron/cloud_service/app.py`, `mark_app.py` ve `ultron/backend/server.py` ile Cloud queue teslim/lease/progress/result sözleşmesini incele; bir komutun iki kez işlenmesini engelleyen ve lease yarışını gösteren izolasyon testleri oluştur.
5. Yeni kod için `npm run build`, `npm run test:earth`, backend pure unittests ve uygun CI workflow'u çalıştır; 4 geliştirme belgesine gerçek sonuçları yaz.

## Test komutları
```bash
python -m unittest discover -s ultron/backend/tests -p 'test_earth_watch_config.py' -v
python -m unittest discover -s scripts/tests -p 'test_ultron_dev_resume.py' -v
python scripts/ultron_dev_resume.py
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

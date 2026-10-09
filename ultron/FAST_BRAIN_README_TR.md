# ULTRON FAST BRAIN • Ücretsiz hızlı yerel beyin (2026-10-09)

## Ne yapar?
ULTRON Windows Ollama beyni bir yanıtta otomatik iki farklı model yarıştırıp üçüncü modelle değerlendirmek yerine artık hızlı tek model kullanır. Çoklu model ve yargılama aracı manuel kullanım için korunur. Konuşma, kod, analiz ve görsel işlerine doğru **kurulu** modeller seçilir; ücretsiz Qwen3.5 4B isteğe bağlıdır.

## Model sırası

| İş | İlk tercih | Kurulu değilse |
| --- | --- | --- |
| Hızlı Türkçe sohbet | qwen3.5:4b | qwen3:4b |
| Analiz | qwen3:8b | qwen3.5:4b veya qwen3:4b |
| Kod | qwen2.5-coder:7b | qwen3.5:4b |
| Görsel | llava:7b | qwen3.5:4b |

Hiçbir model kendiliğinden indirilmez. Sadece Ollama envanterinde olanlar seçilir. Sağlayıcıya ücretli API çağrısı yapılmaz. Qwen3/3.5 için think:false, düşük token limiti ve 10 dakika model sıcak tutma uygulanır; her laptopta kesin hız garantisi yoktur. Selamlaşmada gereksiz büyük tool listesi gönderilmez ama kullanıcı gerçek araç istediğinde izin ve Approval Gate aynen korunur.

## Windows kullanım talimatı

Proje kökünden, doğru Git dalı ve değişiklikleri koruyarak:

    git status
    git branch --show-current
    git pull origin feat/ultron-cloud-shared-memory
    .\.venv\Scripts\python.exe scripts\ultron_fast_brain_doctor.py

Gerçek kısa yanıt sürelerini ölçmek istersen:

    .\.venv\Scripts\python.exe scripts\ultron_fast_brain_doctor.py --benchmark

Sonra START.bat ile yeniden aç. Test için Ollama önceden çalışıyor olmalıdır.

Daha yeni bir model denemek istersen, kullanıcı onayıyla ücretsiz indir:

    ollama pull qwen3.5:4b

Bu birkaç GB internet/disk tüketir; RTX 2050 yaklaşık 4 GB VRAM üzerinde daha fazla RAM/CPU yükü yaratarak yavaşlayabilir. Bazı eski Ollama sürümleri bu yeni mimariyi desteklemez; gerekirse resmî Ollama'yı güncellemek gerekir. Test etmeden daha hızlıdır demeyiz.

## Önemli ayrım

Fast Brain, Windows ULTRON yerel backend model yönlendirmesini iyileştirir. MARK-LV / Gemini Live ses bağlantısı ve iPhone Cloud Live değiştirilmedi. Ücretsiz Ollama beyni, bunların kullanım limitlerini veya ücretini otomatik ortadan kaldırmaz. İki cihazın mevcut Cloud komut köprüsü aynen korunur. Yerel Whisper/Piper/Ollama ses yolunda kullanılabilir, fakat gerçek Windows mikrofon/GPU hız testi yapılmadı. Render, Windows GPU veya Ollama modelini kendiliğinden güncellemez.

CI testleri model seçme, tek çağrı, araç çağrısı, code fallback ve Ollama isteğindeki think:false alanını doğrular. Bunlar sahte/Ollama mock testleridir; gerçek model kalitesi, Windows performansı ve ses gecikmesi cihazda ölçülmelidir.

Resmî Qwen3.5 açık model sayfası: https://ollama.com/library/qwen3.5

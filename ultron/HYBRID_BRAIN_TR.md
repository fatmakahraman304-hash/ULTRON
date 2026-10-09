# ULTRON Hybrid Brain — Ücretsiz Qwen ana beyin, Gemini yedekte

## Tasarım ve sınırlar

**Windows:** Ollama Fast Brain, yalnız kurulu ücretsiz modelleri seçer: sohbet Qwen3 4B (isteğe bağlı Qwen3.5 4B), kod Qwen2.5 Coder 7B, analiz Qwen3 8B, görsel LLaVA 7B. Mevcut MARK Gemini Live sesli konuşma modu korunur; Windows MARK sesli modu otomatik ücretsiz yerel konuşmaya dönüşmemiştir.

**iPhone:** ULTRON Mobile varsayılan sohbet için Windows'taki yerel Qwen'e Cloud üzerinden bağlanır. Windows açık/eşleşmiş ve Ollama çalışıyor olmalıdır. Telefonun içinde Qwen çalışmaz.

**iPhone konuşma:** Mikrofon düğmesine dokun → desteklenen Safari sürümünde tarayıcı SpeechRecognition özelliği Türkçe konuşmayı yazıya çevirir → mevcut Cloud /api/local-chat Windows Qwen'e gönderir → yanıt tarayıcının speechSynthesis sesiyle okunabilir. Bu tek-tıklama/tek-soru akışıdır. Sürekli arka plan mikrofona erişim yoktur.

**Gemini:** Seçicide GEMINI • İSTEĞE BAĞLI seçilip mikrofon ayrıca dokunularak açılır. iPhone açılışı, geri plana girip çıkma, Qwen'in hata vermesi veya ses tanımanın desteklenmemesi Gemini'ye otomatik geçiş yapmaz. Gemini mevcut kota ve kullanım şartları geçerlidir.

**Ses gizliliği:** iOS/Safari SpeechRecognition her tarayıcı/PWA sürümünde mevcut değildir. Tarayıcı konuşmayı tanımak için internet servisi kullanabilir. Bu nedenle bu PWA konuşma tanıması %100 çevrimdışı STT veya garanti edilmiş cihaz-içi işlem olarak pazarlanmamalıdır. Destek yoksa yazılı ücretsiz Qwen sohbetine devam edilir. Windows Whisper ise ayrı bir gerçek yerel STT sistemidir.

## Deneme

1. Windows'ta Ollama ve eşleştirilmiş ULTRON Cloud worker'ı başlat.
2. iPhone ana ekranından ULTRON'u yeniden aç; varsayılan beyin YEREL QWEN • ÜCRETSİZ olmalı.
3. Mikrofona bir kez dokunup Türkçe konuş. Transkript ve Qwen cevabı gelirse telefonu da konuşturabilirsin. Tarayıcı desteklemiyorsa hatayı görürsün.
4. Gemini Live gerekiyorsa modeli manuel GEMINI • İSTEĞE BAĞLI seç ve ayrıca mikrofona dokun.
5. Windows gerçek hızını ölçmek için proje kökünde:
   .\.venv\Scripts\python.exe scripts\ultron_fast_brain_doctor.py --benchmark

İsteğe bağlı yeni ücretsiz model: ollama pull qwen3.5:4b. Birkaç GB indirme, disk ve işlemci/RAM gerektirebilir; RTX2050 cihazda mutlak hız artışı garanti değil.

## Doğrulama

Node testleri ulron/cloud_service değil ultron/cloud_service/test_local_voice.cjs içindedir. Aynı dizindeki test_local_brain_bridge.py Cloud yetkilerini ve varsayılan yerel sohbet yolunu denetler. Bunlar gerçek iPhone PWA mikrofon donanımı veya Windows model yanıt gecikmesi ölçümü değildir. Render Windows video/ses veya GPU modelini çalıştırmaz.

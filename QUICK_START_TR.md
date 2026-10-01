# MARK + ULTRON

Günlük kullanım: **START.bat** dosyasına çift tıklayın. MARK penceresi ve yerel ULTRON servisi birlikte açılır. MARK penceresi kapanınca başlatıcının servisleri de kapanır.

İlk kurulum veya bağımlılıkları onarmak için **INSTALL.bat**, tanılama için **DOCTOR.bat** kullanın. Kurulum internet gerektirebilir; eksik zorunlu bağımlılıkta başarı bildirmez. Node.js/npm frontend derlemeleri için gereklidir. Python 3.11–3.12 kullanılır; mevcut `.venv` önceliklidir. Python bulunamazsa proje içine imzası doğrulanmış resmi Python kurulumu denenir.

MARK'ın Gemini sesli görüşmesi ve mevcut avatar/aksiyon arayüzü korunmuştur. Sağdaki **Yerel AI / Görevler** bölümünden Ollama'ya metin gönderilebilir. Otomatik, kod, hızlı, genel, agent, uzun görev ve çoklu model seçenekleri vardır. **ULTRON görev panelini aç** düğmesi ayrıntılı web panelini yetkili oturumla açar. Tarayıcı paneli yalnız bu bilgisayarda erişilebilen dinamik porta bağlanır.

Mikrofonun sahibi MARK'tır. ULTRON'un ikinci bir ses dinleyicisi başlatması engellenir. Hazır wake phrase **Hey Jarvis**'tir. Özel `ultron.onnx` kaynaklarda bulunmadığından “Ultron” kelimesiyle uyanma doğrulanmış değildir. Model sağlanırsa konumu `ultron/backend/data/voice/wake/ultron.onnx` olur; gerçek akustik doğrulama ayrıca gerekir.

Gemini ayarları `config/api_keys.json` içindedir. Bu dosya kişiseldir, Git'e alınmaz. API anahtarlarını raporlara veya sohbetlere kopyalamayın. Ollama varsayılan olarak `127.0.0.1:11434` adresinde beklenir. Eksik modelde router kurulu modellerden seçim yapar; servis kapalıysa hata görünür, sonsuz bekleme olmaz.

Riskli işlemlerde kullanıcı onayı gereklidir. **Bekleyen onayı incele** düğmesi komutun ayrıntılarını gösterir; uzun görevler ayrıntılı görev panelinden yönetilir. Bir araç isteğinin `approved=true` göndermesi onay sayılmaz.

Tanılama çıktıları `logs/doctor.json`, kurulum sonucu `logs/install-result.json`, başlatma günlükleri `logs/launcher.log`, `logs/backend.log`, `logs/mark.log` konumundadır. DOCTOR'u uygulama kapalıyken çalıştırın; tek örnek kilidi ikinci backend açılmasını önler.

`START.bat -Smoke` gerçek Qt penceresini ve backend'i açıp sekiz saniye sonra kapatan test kipidir. Bu kip Gemini görüşmesini başlatmaz. Normal `START.bat` bu sınırlamayı kullanmaz.

Eski `ultron/ULTRON.bat`, `ultron/scripts/start_ultron.bat` ve `install_windows.bat` birleşik başlatıcıya yönlendirilir. Eski Electron paketleme ve otomatik başlatma yardımcıları kaynak referansı olarak korunmuştur; birleşik sürümün kurulum yolu değildir.

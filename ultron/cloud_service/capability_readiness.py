"""Truthful owner-facing availability of ten aspirational JARVIS capabilities.

A cloud-hosted API cannot infer installed iOS entitlements, real-world devices,
hardware holograms, or audio quality. Report limitations, never fake readiness.
"""
from __future__ import annotations


def readiness(desktop_online: bool = False) -> dict:
    online = bool(desktop_online)
    items = [
        ("expressive_persona", "Konuşma kişiliği ve mizah", "available_in_code",
         "Konuşma tarzı uyarlanır; gerçek insan bilinci ve duyguları yok."),
        ("personal_memory", "Kişisel hafıza ve günlük plan", "available_in_code",
         "Kayıtlı sohbet/hafıza ve istek üzerine günlük plan var; takvim kaynakları otomatik bağlı değil."),
        ("approved_learning", "İzinli öğrenme", "partial",
         "Yeni bilgileri gözden geçirip ONAYLA/REDDET diyebileceğin bir öğrenme kutusu var. "
         "Yalnızca onaylananlar hafızaya eklenir; kendi kendine sınırsız öğrenme veya izleme yok."),
        ("offline_computer", "Bilgisayar kapalıyken kontrol", "blocked_hardware",
         "Windows kapalıyken masaüstü işlemleri yapılamaz; ayrıca açık güvenilir cihaz gerekir."),
        ("native_iphone", "Siri seviyesinde iPhone", "requires_native_setup",
         "PWA/Kestirmeler köprüsü var; tam iOS yetkileri için imzalı uygulama ve Apple izinleri gerekir."),
        ("physical_hologram", "Havada hologram", "blocked_hardware",
         "Ekran üstünde gerçek zamanlı 3D var; havada hologram için fiziksel görüntüleme donanımı gerekir."),
        ("continuous_voice", "Sürekli doğal ses", "requires_device_test",
         "Whisper, Piper ve isteğe bağlı Gemini Live yolları var; cihaz testleri ve mikrofon izni gerekir."),
        ("self_update", "Kendini güncelleme", "requires_approval",
         "GitHub test ve güvenli güncelleme hazırlığı var; yerel kurulum, onay ve yeniden başlatma doğrulanmalı."),
        ("calendar_email", "Takvim ve e-posta", "requires_provider",
         "ULTRON içinde kendi tarihli planlarını oluşturup takip edebilirsin. Apple/Google Takvim veya e-posta bağlantısı, hesap izni ve doğrulanmış senkronizasyon olmadan mevcut değildir."),
        ("smart_devices", "Gerçek akıllı cihazlar", "requires_devices",
         "Desteklenen IoT adaptörleri var; gerçek bağlı cihaz ve kullanıcı izni gerekir."),
    ]
    result = []
    for key, title, status, detail in items:
        if key == "offline_computer" and online:
            detail += " Bilgisayar şu an çevrimiçi; kapandıktan sonra bu durum değişir."
        result.append({"id": key, "name": title, "status": status, "detail": detail})
    return {"desktop_online": online, "capabilities": result,
            "verified_device_test": False,
            "disclaimer": "Kod özellikleri fiziksel cihaz veya yayın doğrulaması değildir."}

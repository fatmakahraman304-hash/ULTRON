"""Truthful owner-facing availability of ten aspirational JARVIS capabilities.

A cloud-hosted API cannot infer installed iOS entitlements, real-world devices,
hardware holograms, or audio quality. Report limitations, never fake readiness.
"""
from __future__ import annotations

import os


def readiness(desktop_online: bool = False) -> dict:
    online = bool(desktop_online)
    items = [
        ("expressive_persona", "Konuşma kişiliği ve mizah", "available_in_code",
         "Konuşma tarzı uyarlanır; gerçek insan bilinci ve duyguları yok."),
        ("personal_memory", "Kişisel hafıza ve günlük plan", "available_in_code",
         "Kayıtlı sohbet/hafıza ve sohbetten komutlar var (“hatırla: …”, “neler hatırlıyorsun”, “unut: …”); plan ekleme, "
         "tekrarlı hatırlatıcı ve sabah brifingi çalışır. Sahibinin onayı olmadan hafızaya yazılmaz."),
        ("approved_learning", "İzinli öğrenme", "partial",
         "Yeni bilgileri gözden geçirip ONAYLA/REDDET diyebileceğin bir öğrenme kutusu var. "
         "Yalnızca onaylananlar hafızaya eklenir; kendi kendine sınırsız öğrenme veya izleme yok."),
        ("offline_computer", "Bilgisayar kapalıyken kontrol", "blocked_hardware",
         "Windows kapalıyken masaüstü işlemleri yapılamaz; ayrıca açık güvenilir cihaz gerekir."),
        ("native_iphone", "Siri seviyesinde iPhone", "requires_native_setup",
         "Ana Ekrana eklenen PWA’da Web Push bildirimi (kilitliyken hatırlatıcı/uyarı) ve Kestirmeler köprüsü var; "
         "Siri seviyesi için imzalı iOS uygulaması ve Apple izinleri gerekir. Kilitliyken bildirim gerçek cihazda henüz doğrulanmadı."),
        ("physical_hologram", "Havada hologram", "blocked_hardware",
         "Ekran üstünde gerçek zamanlı 3D var; havada hologram için fiziksel görüntüleme donanımı gerekir."),
        ("continuous_voice", "Sürekli doğal ses", "requires_device_test",
         "Whisper, Piper ve isteğe bağlı Gemini Live yolları var; cihaz testleri ve mikrofon izni gerekir."),
        ("self_update", "Kendini güncelleme", "requires_approval",
         "GitHub test ve güvenli güncelleme hazırlığı var; yerel kurulum, onay ve yeniden başlatma doğrulanmalı."),
        ("calendar_email", "Takvim ve e-posta", "requires_provider",
         "GÖLGE planların ve Google/iCloud/Outlook takvimine salt-okunur iCal (gizli adres) bağlantısı var; yaklaşan etkinlikler için önceden "
         "bildirim gelir. Takvime yazma ve e-posta okuma/gönderme yoktur (hesap izni gerekir)."),
        ("smart_devices", "Gerçek akıllı cihazlar", "requires_devices",
         "Home Assistant üzerinden ışık, priz, klima, perde, sahne ve kilitleme komutları kodda var (kapı kilidi açılmaz, garaj/kapı açılmaz). "
         "Gerçek çalışması için herkese açık Home Assistant adresi, erişim anahtarı ve bağlı cihazlar gerekir."),
    ]
    result = []
    for key, title, status, detail in items:
        if key == "smart_devices":
            try:
                from smart_home import config as ha_config
                configured = ha_config() is not None
            except Exception:
                configured = bool(os.getenv("HOME_ASSISTANT_URL") and os.getenv("HOME_ASSISTANT_TOKEN"))
            detail += " Bu sunucuda Home Assistant adresi ve anahtarı tanımlı; cihazlarla gerçek deneme yapılmadı." if configured else \
                " Bu sunucuda Home Assistant tanımlı değil."
        if key == "offline_computer" and online:
            detail += " Bilgisayar şu an çevrimiçi; kapandıktan sonra bu durum değişir."
        result.append({"id": key, "name": title, "status": status, "detail": detail})
    return {"desktop_online": online, "capabilities": result,
            "verified_device_test": False,
            "disclaimer": "Kod özellikleri fiziksel cihaz veya yayın doğrulaması değildir."}

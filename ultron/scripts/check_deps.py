"""ULTRON bağımlılık kontrolü — kurulumdan sonra veya ULTRON.bat başlamadan çalışır."""
import importlib.util
import shutil
import sys

def have(mod): return importlib.util.find_spec(mod) is not None
def which(cmd): return shutil.which(cmd) is not None

CHECKS = [
    # (modül/komut, tip, açıklama, zorunlu_mu)
    ("aiohttp",         "py",  "Web sunucu çerçevesi",                True),
    ("psutil",          "py",  "Sistem telemetrisi",                   True),
    ("cryptography",    "py",  "Vault şifreleme (Fernet)",             True),
    ("PIL",             "py",  "Görüntü işleme / screenshot",          True),
    ("pytesseract",     "py",  "OCR Python sarmalayıcı",               False),
    ("sounddevice",     "py",  "Ses I/O (mikrofon / hoparlör)",        False),
    ("faster_whisper",  "py",  "Konuşma tanıma (STT/wake-word)",       False),
    ("pyautogui",       "py",  "GUI otomasyon",                        False),
    ("pygetwindow",     "py",  "Pencere yönetimi",                     False),
    ("playwright",      "py",  "Browser ajan",                         False),
    ("pypdf",           "py",  "PDF işleme",                           False),
    ("piper",           "py",  "TTS Python paketi",                    False),
    ("playsound3",      "py",  "Ses çalma",                            False),
    ("numpy",           "py",  "Sayısal hesaplama (ses/vision)",        False),
    ("ollama",          "cmd", "Ollama CLI (AI motor)",                 True),
    ("tesseract",       "cmd", "Tesseract OCR binary",                  False),
    ("piper",           "cmd", "Piper TTS binary (Türkçe ses)",         False),
    ("espeak-ng",       "cmd", "eSpeak-ng TTS (yedek ses)",            False),
]

ok = []; warn = []; err = []

for item, typ, desc, required in CHECKS:
    if typ == "py":
        found = have(item)
    else:
        found = which(item)
    row = (item, desc, found)
    if found:
        ok.append(row)
    elif required:
        err.append(row)
    else:
        warn.append(row)

print()
print("╔══════════════════════════════════════════════════════╗")
print("║          ULTRON — Bağımlılık Raporu                 ║")
print("╠══════════════════════════════════════════════════════╣")

if ok:
    print("║  ✅ KURULU                                           ║")
    for item, desc, _ in ok:
        line = f"║     • {item:<20} {desc}"
        print(line[:54].ljust(54) + " ║")

if warn:
    print("║  ⚠️  OPSİYONEL / EKSİK                              ║")
    for item, desc, _ in warn:
        line = f"║     • {item:<20} {desc}"
        print(line[:54].ljust(54) + " ║")

if err:
    print("║  ❌ ZORUNLU EKSİK                                    ║")
    for item, desc, _ in err:
        line = f"║     • {item:<20} {desc}"
        print(line[:54].ljust(54) + " ║")

print("╚══════════════════════════════════════════════════════╝")

if err:
    print()
    print("HATA: Zorunlu paketler eksik. Düzeltmek için:")
    print("  scripts\\install_windows.bat")
    sys.exit(1)
elif warn:
    print()
    print(f"Uyarı: {len(warn)} opsiyonel paket eksik (ses, GUI, browser vb.)")
    print("Tüm özellikler için: pip install faster-whisper sounddevice pyautogui playwright")
    sys.exit(0)
else:
    print()
    print("Tüm bağımlılıklar mevcut. ULTRON hazır.")
    sys.exit(0)

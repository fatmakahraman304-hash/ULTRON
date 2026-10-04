# ULTRON son arayüz raporu

## Uygulama

Tek giriş: START.bat → mevcut launcher/backend → PyQt6 QWebEngineView → React dashboard. Orijinal Qt işlev widgetları ses, dosya, onay ve araç callbacklerini korumak için gizli tutulur. Alternatif dashboard seçimi yoktur. Hologram bağımsız bir uzman araç penceresidir.

Referansın üst menü, sol sistem kartları, sağ sohbet/dosya/komut ve alt araç çubuğu düzeni uygulandı. 1920×1080 tasarım alanı ekran boyutuna orantılı ölçeklenir. 1366×768 ve 768×1024 kontrollerinde yatay taşma yoktur. Tasarım referansın kodla yeniden yorumlanmasıdır; görselle piksel düzeyinde aynı olduğu iddia edilmez.

## Değişen dosyalar

- ultron/frontend/src/dashboard/Dashboard.tsx: ana düzen, menüler, sohbet, onay ve araç pencereleri.
- ultron/frontend/src/dashboard/ReferencePanels.tsx: SVG kimlik, gerçek telemetry geçmişi, sistem kartları ve dosya yükleme.
- ultron/frontend/src/dashboard/dashboard.css: metal, kesik köşe, koyu cam, kırmızı enerji çizgileri ve ölçeklenen düzen.
- ultron/frontend/src/dashboard/core/CoreScene.ts: gerçek Three.js sahnesi.
- ultron/frontend/src/dashboard/runtime.ts: mevcut WS olayları, sağlık, native ses/eklenti/dosya bağlantıları.
- ultron/frontend/src/dashboard/Panels.tsx: mevcut backend araç panelleri, tamamlanan görev kontrolü.
- ultron/frontend/src/lib/types.ts; src/main.tsx: telemetry alanları ve ana giriş temizliği.
- integration/panel.py; web_panel.py; hologram_panel.py: tek ana host, native araç pencereleri, normal kapanış ve hologram yönlendirmesi.
- ultron/backend/telemetry.py: gerçek süreç sayısı ve işletim sistemi alanları.
- ultron/backend/server.py: shutdown sırasında açık WS istemcilerini kapatma.
- ui.py; core/ultron_visual.py: mevcut native uyumluluk kodu ve prosedürel çizim değişiklikleri korunmuştur; ana dashboard olarak gösterilmez.
- ultron/backend/tests/test_computer_use.py; test_wave4_fusion.py: ekran-yok ve olay dedup zaman penceresi testlerinin deterministik çalışması.
- scripts/verify_dashboard.py; verify_native_dashboard.py: gerçek tarayıcı ve Qt kabul kontrolleri.
- QUICK_START_TR.md: güncel başlatma ve kullanım.

Eski UI temizliği UI_REMOVED_FILES.json içinde 56 dosya olarak kayıtlıdır: eski cockpit/legacy/mobile, statik mission control ve eski telefon HTML sunumları. Bu turda kalan reactor-environment.png de kaldırıldı. Backend araç kodları korunmuştur. Ana React kaynaklarında JARVIS, MARK LV ve eski imza bulunmamaktadır.

## Core

Boş parçacık enerji çemberi, üç katmanlı metal reaktör, beş farklı yörünge, beyaz vurgular, hareketli parçalar, kalın silindirik platform, ışık kanalları, ışın, oda taşıyıcıları ve zemin. Hiçbir arka plan/reaktör bitmap veya videosu yüklenmez. Dosya önizlemesi kullanıcının kendi yüklediği görseldir.

En çok 2600 parçacık; instanced mekanik parçalar; pixelRatio en çok 1.5; sınırlı bloom boyutu; MSAA; cleanup. FXAA Windows/Qt shader uyumsuzluğu nedeniyle kullanılmaz. IDLE/LISTENING/THINKING/SPEAKING/WORKING/ERROR durumları mevcut backend/native olaylarından gelir. Ses seviyesi mevcut Qt audio-level yolundan geçer. 60 FPS hedefidir; sabit 60 FPS garantisi ölçülmüş değildir.

## İşlev bağlantıları

| Kontrol | Gerçek bağlantı |
|---|---|
| Sohbet / komut | /api/merged/invoke; kurulu Ollama modelleri; native canlı ses seçeneği |
| Mikrofon / ESC | Mevcut Qt mute/interrupt |
| Ayarlar / Kontroller | Mevcut config, ses aygıtları, kamera, wake ve bas-konuş kontrolleri |
| Hologram | /merged/hologram; mevcut GLB, parçalar ve el kontrolü |
| Dosyalar | document/image yükleme, sandbox list_directory/read_text; native medya |
| Terminal / browser | Mevcut agent ve izin politikası; open_url |
| Ekran / OCR | screenshot, vision preview, screen_ocr |
| Planlayıcı | Mevcut görev listesi, başlatma, sonuç, duraklatma ve iptal |
| Hafıza | Mevcut SQLite memory endpointleri |
| Modeller | Backend model listesi; doğrulanmış model seçimi |
| Eklentiler | Native registry ve mevcut backend becerileri |
| Kapat | Normal Qt close; backend WS kapatma ve launcher cleanup |

Onay kapısı kaldırılmadı. İstemcinin approved:true ile kendini onaylatma denemesi reddedildi. Model çıktısı mevcut sözleşmedeki tamamlanmış yanıt biçimindedir; sahte streaming yoktur.

## Doğrulama kayıtları

- Frontend TypeScript/Vite build: PASS (logs/final-build.log).
- Hologram gesture test: 8 assertion PASS; proje doğrulama: 11 kontrol PASS.
- Tarayıcı: DASHBOARD_BROWSER_PASS; gerçek Ollama sohbeti, hafıza, terminal izin yolu, self-approval reddi, hologram, tek UI WS, 30+ frame, state aktarımı; page/console error 0.
- Native: NATIVE_DASHBOARD_PASS; gerçek Qt köprüsüyle SPEAKING ve amplitude aktarımı, tek ana pencere ve normal kapanış; console error 0.
- START.bat -Smoke: gerçek Qt pencere açılışı PASS. Bu smoke modu dış Gemini Live oturumunu başlatmaz; canlı ses konuşmasının uçtan uca kalitesi bu testle doğrulanmış sayılmaz.
- DOCTOR: 0 FAIL; Ollama ve vision gerçek inference PASS. Ayrıntı logs/doctor.json.
- Entegrasyon: 28 passed (logs/final-integration-tests.log). Backend: 954 passed, 4 skipped (logs/final-backend-tests.log). Daha sonraki birleşik tekrar, kullanıcının açık ULTRON oturumu nedeniyle 15 integration fixture hatası verdi (instance lock); uygulama kapatılmadı ve kilit bypass edilmedi.
- Görsel kayıtlar: logs/final-ultron-1920x1080.png, logs/final-ultron-1366x768.png; native-final.png.

Kalan uyarılar: özel ULTRON wake modeli kurulu değil (iki ilgili doctor WARN); pynvml deprecation uyarısı; Three.js paket parçası 500 kB üzerinde. Bunlar gizlenmedi. Görsel çıktılar, cache, kişisel API anahtarları ve backups Git'e dahil edilmez.

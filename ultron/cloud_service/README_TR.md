# ULTRON Cloud Service

Bu servis iPhone ve masaüstü ULTRON'un aynı yazılı sohbet geçmişini ve kalıcı hafızayı kullanması için ayrılmıştır. Yerel mikrofon, wake-word, ekran kontrolü, dosya sistemi ve Ollama laptopta kalır.

## Gerekli ortam değişkenleri

- `DATABASE_URL`: PostgreSQL bağlantı adresi (Supabase/Render/Postgres)
- `GEMINI_API_KEY`: Gemini API anahtarı
- `GEMINI_MODEL`: varsayılan `gemini-3.8-flash`
- `ULTRON_PASSWORD`: iPhone web arayüzü giriş parolası
- `ULTRON_SESSION_SECRET`: uzun rastgele imzalama anahtarı
- `ULTRON_DEVICE_TOKEN`: masaüstü istemcisinin Bearer token'ı
- `ULTRON_USER_ID`: varsayılan `murat`
- `PORT`: varsayılan `10000`

Anahtarları repoya yazmayın. Ana `.gitignore` dosyası `.env` ve `.env.*` dosyalarını dışlıyor.

## Yerelde çalıştırma

```bash
cd ultron/cloud_service
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## API

- `GET /health`
- `POST /api/login`
- `POST /api/logout`
- `GET /api/session`
- `GET /api/messages`
- `POST /api/chat`
- `GET /api/memories`
- `PUT /api/memories`
- `DELETE /api/memories/{key}`

Tarayıcı oturumu HTTPS üzerinde HttpOnly imzalı cookie kullanır. Masaüstü istemcisi `Authorization: Bearer <ULTRON_DEVICE_TOKEN>` ile bağlanabilir.

## Render ayarı

Root Directory: `ultron/cloud_service`

Build Command:

```text
pip install -r requirements.txt
```

Start Command:

```text
python app.py
```

Servis `0.0.0.0:$PORT` üzerinde dinler.

## Ücretsiz iPhone PWA (2026-10-09)

iPhone Safari'de `https://ultron-yubh.onrender.com` → Paylaş → Ana Ekrana Ekle ile kablosuz ve ücretsiz yüklenir. Gerçek native iOS/TestFlight kurulumu değildir; Siri App Intent ve uygulama arka planındaki mikrofon/notification haklarını sınırsız sağlamaz.

Yeni PWA özellikleri:
- Sesli Gemini Live konuşması korunur. `ios_action` ve `ios_shortcut` gelen Kestirmeler isteği yalnız `ULTRON Bridge` adlı kestirme ve desteklenen eylemle hazırlanır, ekranda **IPHONE İŞLEM ONAYI** çıkar; **KESTİRMELERİ AÇ** seçilmeden otomatik başlatılmaz.
- `UZAKTAN` sekmesinde aktif Cloud agent görev sayısı, kuyrukta/çalışıyor/hata özeti görünür. Telefon uygulaması canlı açıkken Cloud durumunu kontrol eder; PWA gizliyken sistem anlık ve kesin bildirim garantisi yoktur.
- `static/mobile-action-guard.js` komut formatı/izinli eylem doğrulaması yapar. `static/sw.js` guard dosyasını offline cache'e dahil eder; önbellek `v37` sürümüne güncellenmiştir.

Test: `node --test ultron/cloud_service/test_mobile_action_guard.cjs` (repo kökünden). Native iPhone kullanımı, Cloud backend deployment veya gerçek telefon/kilit ekranı bundan dolayı kanıtlanmış değildir.

## ULTRON WORLD / Ücretsiz mobil 2D+3D harita (2026-10-09)
- Telefon: Safari ana ekranındaki ULTRON → DÜNYA. 2D OSM/Leaflet sokak haritası zoom 19 ve 3D Three.js küre. Adres arama Photon/OSM, favoriler sadece cihaz localStorage'da; konum için iOS izin gerekir.
- Canlı salt-okunur API: /api/world/weather, /api/world/flights, /api/world/earthquakes, /api/world/air-quality, /api/world/search. Sağlayıcılar Open-Meteo/MET Norway, adsb.lol/adsb.fi v3, USGS, Open-Meteo AQI, Photon. Provider hata verirse örnek/sahte veriyle başarı gösterilmez. MET Norway verisi hava tahminidir, anlık gözlem gibi temsil edilmez.
- Uydu, trafik, Google Street View, RainViewer radar, earth.nullschool rüzgâr ve MarineTraffic gemiler işaretli harici bağlantıdır. Harici veri kalitesi/erişimi servislerine bağlıdır.
- Laptop CORE için güncel feat/ultron-cloud-shared-memory branch'ini yerelde git pull et, START.bat; normal 2D harita / 3D Dünya sesli komutuyla açılabilir. Küçük kuş/orbit/pulse animasyonları CORE içinde boyut kontrollü oynatılır, fakat üretilen her Pygame programı otomatik CORE'a alınmaz.
- Gerçek kaynak CI doğrulama: https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37927499312 ; Node World sözleşme testleri ve masaüstü frontend build CI: 37927499485. Bunlar fiziksel iPhone ve Windows ekran testi değildir.

### ULTRON WORLD sesli ve yazılı telefon komutları — 2026-10-09
- PWA index.html worldVoiceIntent: kullanıcı tarafından konuşulan/yazılan Dünya, 2D/3D, Gazimağusa, Lefkoşa, Kıbrıs, İstanbul, uçaklar/deprem/hava durumu görüntüle komutlarını DÜNYA sekmesine iletir. Harita iframe'i yalnız aynı origin ve kendi parent kaynağının postMessage komutlarını; tip, koordinat, mod ve katman allowlist guard'ını geçirse işler. Lazy-load sırasında en fazla dört komut bekletilir. Sesli sohbet motoru/Gemini reply Cloud oturumuyla devam eder.
- Cache PWA v40. Sesli komut güvenliği ve WORLD sözleşme testleri Scene Build Check 37928165355 SUCCESS; Cloud PostgreSQL 37928165548 SUCCESS. Kod SHA b473a4bfd28835aefae0472fb07a15442e7e383f. Önceki 37928109729 Scene FAIL sebebi test regex'i; düzeltme sonrası PASS. Üretim WORLD real-provider smoke 37928109603 SUCCESS (bu smoke bir önceki sesli komut kodunun commit'inde tetiklendi; sesli komut cihaz testi değildir).
- NOT RUN: fiziksel iPhone Safari PWA sesli komut → iframe görsel etkileşim, WebGL/CDN texture, Windows Qt CORE. Render AutoDeploy canlı HEAD ayrıca doğrulanmalı.

## 2026-10-09 — Original MARK-LV native video engine restored INSIDE ULTRON CORE
- Investigation of actual original MARK files actions/video_player.py and ui.py: the player was a QMediaPlayer with a QGraphicsVideoItem mounted in the avatar/camera/video stack. It supports local files, HTTP direct media, optional yt-dlp YouTube resolution with separate synchronized audio/video, initially muted sound, stop/mute. The merged integration/web_panel.py had MOVED _video_cont to a separate QDialog (user's pop-out regression).
- New integration/video_dock.py MarkVideoDock reparents the SAME original _video_cont into the actual QWebEngineView. It positions the native QWidget according to .reactor-panel .center-stage DOM bounds, scaled by viewport, clamped so as not to cover surrounding telemetry/chat. Rechecks while open and calls Qt _fit_video on size changes. No new QMediaPlayer engine or video_dialog is created.
- integration/web_panel.py NativeBridge.videoRequest forwards explicit typed video commands to actions.video_player, and MARK native voice tools continue using old video_player directly. React Dashboard.tsx adds deterministic typed media routing irrespective of chosen model; CORE adds MARK VIDEO native-only button. Unknown or source-less voice 'video oynat' asks Qt native file picker (instead of generating a fabricated animation). Preset CORE bird/orbit/pulse animations remain separate.
- ui.py now retains native/QGraphicsVideoItem support after reparenting, QMediaPlayer pause/resume signal & button, correct sound output selection for mic protection, auto-closes the dock after EndOfMedia/decoder failure rather than leaving a black box. Opening a different clip cancels stale asynchronous YouTube requests.
- Headless GUI smoke scripts/tests/test_mark_video_dock_qt.py explicitly instantiated real PyQt6 QMediaPlayer, QGraphicsVideoItem, QAudioOutput, and verified QWidget signals/placement/resizing; 5 tests PASS with QT_QPA_PLATFORM=offscreen and Ubuntu EGL/PulseAudio dependencies. Pure geometry/plugin/contract tests scripts/tests/test_mark_video_dock.py 12 PASS.
- Exact tested code SHA 54a2f2408c54385fc53bc69f7cf944a7a22b1637, GitHub Actions Scene Build Check https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931870709 SUCCESS. Prior frontend build https://github.com/fatmakahraman304-hash/ULTRON/actions/runs/37931231558 SUCCESS (no frontend changes since).
- Honest NOT RUN: real Windows GPU/QtWebEngine+QGraphicsVideoItem rendered video frame screenshot, real MP4 decoder and split audio through Windows speakers, live YouTube (yt-dlp/network), complete desktop voice Gemini route. The CI Qt smoke verifies Qt object creation and QWidget behavior, not actual codec playback on a Windows PC.
- This is a Windows-native MARK feature in a GitHub branch; Render is the Cloud Python host and does not execute or install a Windows Qt video widget. Laptop must git pull and START.bat; user might need INSTALL.bat once if dependencies are not present.

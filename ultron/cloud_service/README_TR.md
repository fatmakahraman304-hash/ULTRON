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

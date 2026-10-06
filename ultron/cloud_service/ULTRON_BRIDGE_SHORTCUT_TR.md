# ULTRON Bridge — iPhone Kestirmeler Kurulumu

Bu kestirme, ULTRON Mobile'dan gelen JSON komutlarini iOS Kestirmeler eylemlerine yonlendirir.

## 1. Kestirmeyi olustur

Kestirmeler uygulamasinda yeni bir kestirme olustur ve adini tam olarak:

`ULTRON Bridge`

yap.

## 2. Girdiyi JSON/Sözlük olarak çöz

Kestirme, URL semasi uzerinden metin girdisi alir. Ilk eylemde Kestirme Girdisi'ni Sözlük/JSON olarak çöz.

Beklenen alanlar:

- `action`
- `target`
- `value`

Ornek:

```json
{"version":1,"source":"ultron","action":"set_brightness","target":"","value":"35"}
```

## 3. action alanina gore dallandir

Bir `If` zinciri veya menü/dallandirma yapisi kur.

### set_brightness

`value` alanini sayiya cevir ve “Parlakligi Ayarla” eylemine ver.

### set_volume

`value` alanini sayiya cevir ve “Sesi Ayarla” eylemine ver.

### bluetooth

`target` veya `value` alanini `on/off` olarak kontrol et ve “Bluetooth'u Ayarla” eylemini calistir.

### wifi

`target` veya `value` alanini `on/off` olarak kontrol et ve “Wi-Fi'yi Ayarla” eylemini calistir.

### set_focus

`target` alanina gore istedigin Odak modlarina dal ac. Ornegin “Rahatsiz Etme”, “Kisisel”, “Uyku”.

### open_app

iOS'ta her uygulama dinamik metinle acilmayabilir. En cok kullandigin uygulamalar icin alt dallar ekle ve ilgili “Uygulamayi Ac” eylemini kullan.

Ornekler: Chrome, Spotify, YouTube, WhatsApp, Instagram.

### compose_message

`target` aliciyi, `value` mesaj metnini tasir. Mesaj Gonder eylemi kullanilabilir; iOS izin/onay isteyebilir.

## 4. Test

ULTRON Mobile > UZAKTAN ekraninda **BRIDGE TESTI** dugmesine bas.

Test komutu:

```json
{"version":1,"source":"ultron","action":"set_brightness","target":"","value":"35"}
```

Parlaklik %35'e ayarlaniyorsa kopru calisiyor demektir.

## Notlar

- iOS her sistem ayarini otomasyona acmaz.
- Bazı eylemler ilk calistirmada izin ister.
- ULTRON, iOS guvenlik sinirlarini atlamaz; yalnizca Apple'in Kestirmeler ile izin verdigi eylemleri calistirir.

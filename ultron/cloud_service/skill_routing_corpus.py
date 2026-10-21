"""Labelled utterances for the GÖLGE skill router. None = ordinary chat (must reach the language model).

Labels: laptop, mission, plus the skill names returned by instant_reply.
Add every real-world mis-route you see here, with the correct label.
"""
CASES = [
    # ── clock / date ─────────────────────────────────────────────
    ("saat kaç", "clock"), ("şu an saat kaç", "clock"), ("Tokyo'da saat kaç", "clock"), ("New York'ta saat kaç", "clock"),
    ("bugün günlerden ne", "clock"), ("bugün ayın kaçı", "clock"), ("hangi gündeyiz", "clock"), ("bugünün tarihi nedir", "clock"),
    ("Londra'da saat kaç", "clock"), ("what time is it", "clock"),
    # ── countdown ────────────────────────────────────────────────
    ("yılbaşına kaç gün var", "countdown"), ("23 nisana kaç gün kaldı", "countdown"), ("25 aralık 2026'ya kaç gün var", "countdown"),
    ("cumhuriyet bayramına kaç gün var", "countdown"), ("kaç gün oldu", None),
    # ── math / units ─────────────────────────────────────────────
    ("15 x 4 + 2 kaç eder", "math"), ("karekök 144", "math"), ("200'ün %15'i kaç", "math"), ("2 üzeri 10", "math"),
    ("1.250,5 + 3,5 hesapla", "math"), ("100 bölü 8", "math"), ("(3+4)*5", "math"), ("7 çarpı 8", "math"),
    ("100 km kaç mil", "units"), ("72 f kaç c", "units"), ("5 kg kaç lb", "units"), ("3 gb kaç mb", "units"),
    ("30 derece fahrenheit kaç", None), ("1 mil kaç km", "units"), ("10 inç kaç cm", "units"),
    ("2 ile 3 arasında hangisi büyük", None), ("bana 3 öneri ver", None), ("1 2 3 4", None), ("5 dakika sonra", None),
    # ── weather ──────────────────────────────────────────────────
    ("hava nasıl", "weather"), ("Londra'da hava nasıl", "weather"), ("yarın hava nasıl", "weather"), ("hava durumu", "weather"),
    ("yağmur yağacak mı", "weather"), ("şemsiye almalı mıyım", "weather"), ("İstanbul hava durumu", "weather"),
    ("bugün hava sıcak mı", "weather"), ("hava neden bu kadar sıcak", None), ("iklim değişikliği nedir", None),
    ("hava durumu uygulaması yazar mısın", None), ("havalar ne zaman soğuyacak", None),
    # ── currency / crypto ────────────────────────────────────────
    ("100 dolar kaç tl", "currency"), ("euro kaç tl", "currency"), ("dolar kuru", "currency"), ("50 sterlin kaç lira", "currency"),
    ("dolar neden yükseldi", None), ("euro alayım mı", None), ("dolar ne olur", None),
    ("bitcoin kaç dolar", "crypto"), ("eth fiyatı", "crypto"), ("bitcoin ne kadar", "crypto"), ("bitcoin neden düştü", None),
    ("bitcoin nedir", None), ("bitcoin alayım mı", None),
    # ── news / flights / wiki ────────────────────────────────────
    ("haberler", "news"), ("teknoloji haberleri", "news"), ("spor haberleri", "news"), ("son dakika", "news"), ("bugün neler oldu", "news"),
    ("haberin var mı", None), ("bu haber doğru mu", None), ("sana bir haberim var", None), ("haber yazısı yaz", None),
    ("İstanbul'dan Londra'ya 25 aralık uçuş bak", "flight"), ("yarın Ankara'dan İzmir'e uçak bileti", "flight"),
    ("uçak nasıl uçar", None), ("uçuş", None),
    ("Atatürk kimdir", "wiki"), ("vikipedi Ankara", "wiki"), ("Albert Einstein hakkında vikipedi", "wiki"), ("python nedir", None),
    ("sen kimsin", None), ("bu kimdir", None),
    # ── prayer / quake / sun-moon ────────────────────────────────
    ("namaz vakitleri", "prayer"), ("akşam ezanı ne zaman", "prayer"), ("iftar saat kaçta", "prayer"), ("Ankara'da namaz vakitleri", "prayer"),
    ("namaz nasıl kılınır", None), ("ezan sesi indir", None),
    ("son depremler", "quake"), ("deprem oldu mu", "quake"), ("deprem çantasında neler olmalı", None), ("deprem nedir", None),
    ("gün batımı saat kaçta", "sun_moon"), ("yarın gün doğumu kaçta", "sun_moon"), ("ay evresi nedir", "sun_moon"), ("dolunay ne zaman", "sun_moon"),
    ("ay ışığı şiiri yaz", None),
    # ── status / briefing / agenda / help ────────────────────────
    ("durum raporu", "status"), ("sistem durumu", "status"), ("sistemler nasıl", "status"),
    ("günaydın", "briefing"), ("sabah brifingi", "briefing"), ("günün özeti", "briefing"), ("brifing ver", "briefing"),
    ("günaydın dostum bugün çok yorgunum uzun uzun anlatayım", None),
    ("bugün programım ne", "agenda"), ("yarın ne var", "agenda"), ("bu hafta toplantılarım", "agenda"), ("takvimimde ne var", "agenda"),
    ("neler yapabilirsin", "help"), ("yardım", "help"), ("komutların", "help"),
    # ── reminders / plans ────────────────────────────────────────
    ("20 dakika sonra bana su içmeyi hatırlat", "reminder"), ("yarın 09:00'da toplantıyı hatırlat", "reminder"),
    ("her gün 9'da ilaç içmeyi hatırlat", "reminder"), ("hafta içi her gün 08:30'da spora gitmeyi hatırlat", "reminder"),
    ("cuma akşam 7'de maça gitmeyi hatırlat", "reminder"), ("bana bir şey hatırlat", "reminder"),
    ("hatırlatıcılarım neler", "reminders"), ("hatırlatıcılarımı iptal et", "reminders"),
    ("hatırlıyor musun", None), ("bunu hatırlıyorum", None), ("hatırlatma özelliği nasıl çalışır", None),
    ("yarın 15:00 diş randevusu planıma ekle", "plans"), ("planlarım", "plans"), ("diş randevusu planını tamamla", "plans"),
    ("plan yapmayı sevmiyorum", None), ("bugün planlarım ne", "agenda"),
    # ── memory / prefs / alerts ──────────────────────────────────
    ("hatırla: annemin doğum günü 3 mart", "memory"), ("hafızana kaydet: kahveyi sade içerim", "memory"), ("neler hatırlıyorsun", "memory"),
    ("unut: doğum günü", "memory"), ("not alıyorum bence", None), ("bunu unutma ki yarın sınav var", None),
    ("bildirim ayarlarım", "prefs"), ("sessiz saatler 23 ile 7", "prefs"), ("sabah brifingi bildirimi aç", "prefs"), ("proaktif uyarıları kapat", "prefs"),
    ("akşam özeti bildirimi aç", "prefs"),
    ("bitcoin 70 bin dolara çıkarsa haber ver", "alerts"), ("dolar 45 TL olunca haber ver", "alerts"), ("alarmlarım", "alerts"),
    ("alarm kur 7'ye", "reminder"), ("fiyat alarmlarımı iptal et", "alerts"),
    # ── smart home ───────────────────────────────────────────────
    ("salon ışığını aç", "smart_home"), ("tüm ışıkları kapat", "smart_home"), ("klimayı 24 dereceye ayarla", "smart_home"),
    ("perdeyi aç", "smart_home"), ("kapıyı kilitle", "smart_home"), ("evde ışıklar açık mı", "smart_home"),
    ("ışık hızı nedir", None), ("kapıyı aç", None), ("ışığı neden kapatıyorsun", None), ("klima nasıl çalışır", None),
    ("kapı nasıl kapatılır", None),
    # ── laptop / mission ─────────────────────────────────────────
    ("laptop: chrome aç", "laptop"), ("bilgisayarda spotify'ı aç", "laptop"), ("ekran analizi yap", "laptop"), ("ekranıma bak ve anlat", "laptop"),
    ("bilgisayar nedir", None), ("ekran kartı fiyatları", None), ("telefonumun ekranı kırıldı", None), ("yeni bir laptop öner", None),
    ("görev: yarınki hava ve haberlere göre günümü planla", "mission"), ("misyon - haberleri özetle", "mission"),
    ("görev yaptım", None), ("bugün görev var mı", None),
    # ── ordinary conversation (must stay with the model) ─────────
    ("merhaba", None), ("nasılsın", None), ("bana bir şiir yaz", None), ("python'da liste nasıl sıralanır", None),
    ("türkiye'nin başkenti neresi", None), ("bana bir fıkra anlat", None), ("bugün çok yorgunum", None), ("teşekkürler", None),
    ("dünya yuvarlak mı", None), ("film önerir misin", None), ("bir e-posta taslağı yaz", None), ("bu cümleyi İngilizceye çevir: nasılsın", None),
    ("kahve mi çay mı", None), ("ödevime yardım eder misin", None), ("sence yapay zeka tehlikeli mi", None),
    ("istanbul'un tarihi nedir", None), ("güneş sistemi kaç gezegenden oluşur", None), ("kaç yaşındayım", None),
    ("bir saat sonra ne olacak sence", None), ("dolar mı altın mı", None), ("ayın uzaklığı ne kadar", None),
    ("bu uygulamanın komutlarını kullanarak bana uzun bir şiir yazar mısın lütfen güzel olsun", None),
    ("yarın sınavım var heyecanlıyım", None), ("toplantı nasıl yönetilir", None), ("ışığın hızı saniyede kaç km", None),
]

CASES += [
    # ── no-diacritics / casual spellings ─────────────────────────
    ("saat kac", "clock"), ("hava nasil", "weather"), ("yarin hava nasil olacak", "weather"), ("istanbulda hava nasil", "weather"),
    ("bugun hava durumu ne", "weather"), ("dolar kac tl", "currency"), ("euro ne kadar", "currency"), ("bitcoin kac", "crypto"),
    ("namaz vakitleri ne zaman", "prayer"), ("yilbasina kac gun var", "countdown"), ("kac gun kaldi yaz tatiline", None),
    ("haberler neler", "news"), ("gundem ne", "news"), ("spor haberleri ver", "news"), ("ekonomi haberleri", "news"),
    ("sicaklik kac derece", "weather"), ("hava kac derece", "weather"), ("disarisi soguk mu", None),
    # ── natural phrasing of reminders / plans ────────────────────
    ("yarın sabah 8'de beni uyandır diye hatırlat", "reminder"), ("saat 15'te ilaç içmemi hatırlat", "reminder"),
    ("2 saat sonra çamaşırı çıkarmamı hatırlat", "reminder"), ("her pazartesi 10:00'da raporu hatırlat", "reminder"),
    ("bir dakika sonra hatırlat", "reminder"), ("hatırlatıcı kur yarın 9'da", "reminder"),
    ("unutma ki yarın toplantı var", None), ("bugün ne hatırlatacaksın", "reminders"),
    ("cuma günü takvimime araba bakımı ekle", "plans"), ("takvimime toplantı ekle", "plans"), ("yaklaşan planlarım", "plans"),
    ("araba planını sil", "plans"), ("planı tamamla: spor", "plans"),
    ("plan yapalım mı hafta sonu için", None), ("bir plan öner bana", None), ("ders planı hazırla", None),
    # ── knowledge ────────────────────────────────────────────────
    ("vikipedi İstanbul", "wiki"), ("Mustafa Kemal Atatürk kimdir", "wiki"), ("Nikola Tesla kimdir", "wiki"),
    ("bu şarkıyı kim söylüyor", None), ("bu ne demek", None), ("kimdir bu adam", None),
    ("son depremler neler", "quake"), ("deprem mi oldu", "quake"), ("deprem sigortası nasıl yapılır", None), ("depremde ne yapılmalı", None),
    ("güneş ne zaman batıyor", None), ("gün doğumu kaçta", "sun_moon"), ("ay hangi evrede", "sun_moon"), ("hilal ne zaman", "sun_moon"),
    ("ay dünyadan ne kadar uzakta", None), ("güneş ne kadar büyük", None),
    ("ezan vakti", "prayer"), ("sahur kaçta", "prayer"), ("imsak vakti ne zaman", "prayer"), ("ezanı kim okudu", None),
    ("ethereum fiyatı", "crypto"), ("solana kaç dolar", "crypto"), ("doge ne kadar", "crypto"), ("kripto nedir", None),
    ("bitcoin madenciliği nasıl yapılır", None), ("dolar bozdurmak mantıklı mı", None),
    # ── smart home variants ──────────────────────────────────────
    ("ışığı kapat", "smart_home"), ("yatak odası lambasını %30 yap", "smart_home"), ("klimayı kapat", "smart_home"),
    ("film sahnesini çalıştır", "smart_home"), ("perdeleri kapat", "smart_home"), ("ışıklar açık mı", "smart_home"),
    ("kapının kilidini aç", "smart_home"), ("lambayı yak", "smart_home"),
    ("ışık kaç lümen olmalı", None), ("klima almak istiyorum hangisi iyi", None), ("perde modelleri neler", None), ("lamba tasarımı çiz", None),
    # ── laptop / mission variants ────────────────────────────────
    ("bilgisayarımdaki indirilenler klasörünü listele", "laptop"), ("laptopta not defterini aç", "laptop"), ("pc'de youtube aç", "laptop"),
    ("ekranda ne var", "laptop"), ("ekran görüntüsü al ve özetle", "laptop"), ("bilgisayara ses seviyesini kıs", "laptop"),
    ("bilgisayarı kapat", "laptop"),   # classify() flags it destructive: bridge answers with the confirmation request
    ("bilgisayarım yavaş çalışıyor ne yapmalıyım", None), ("laptop şarjı çabuk bitiyor", None), ("ekran parlaklığı göz yorar mı", None),
    ("ekran koruyucu önerir misin", None), ("görev: bugünkü haberleri özetle ve hatırlat", "mission"),
    ("adım adım: yarın için hazırlık yap", "mission"),
    # ── mixed / long ordinary chat containing trigger words ──────
    ("bugün hava çok güzel ama içimden dışarı çıkmak gelmiyor", None), ("haberleri izlemek beni geriyor", None),
    ("saatlerce çalıştım yoruldum", None), ("dolar bozdurdum bugün", None), ("bitcoin hakkında ne düşünüyorsun", None),
    ("deprem korkum var ne yapmalıyım", None), ("yarın sabah erken kalkmam lazım", None), ("o gün çok güzel bir gündü", None),
    ("hatırladım şimdi", None), ("alarm sesi çok yüksek", None), ("sana bir plan anlatayım", None), ("namaz kılmak istiyorum bana dua öğret", None),
    ("kaç kişi geldi", None), ("kaç lira etti bilmiyorum", None), ("yarın ne yapsam", None), ("bugün ne yesem", None),
    ("hava atıyorsun", None), ("saat başı kalkıp yürüyorum", None), ("aylık ne kadar biriktirmeliyim", None),
]

CASES += [
    ("alışveriş listesine süt ekle", "lists"), ("alışveriş listesine süt, ekmek ve yumurta ekle", "lists"), ("süt alışveriş listesine ekle", "lists"),
    ("listelerim", "lists"), ("alışveriş listesini temizle", "lists"), ("film listesine Inception ekle", "lists"),
    ("10 dakika zamanlayıcı kur", "reminder"), ("zamanlayıcı kur 5 dakika makarna", "reminder"),
    ("bu listeyi beğendim", None), ("bir liste yapalım mı", None), ("listenin en başı kim", None), ("zamanlayıcı nasıl çalışır", None),
    ("en iyi 10 film listesi öner", None), ("liste yap bana", None), ("zamanlayıcı uygulaması yaz", None),
]

CASES += [
    ("150 lira market harcaması ekle", "expenses"), ("bugün kahveye 80 tl harcadım", "expenses"), ("harcama ekle 150 market", "expenses"),
    ("bu ay ne kadar harcadım", "expenses"), ("harcamalarım", "expenses"), ("son harcamayı sil", "expenses"), ("dün 1.250,50 lira benzin harcadım", "expenses"),
    ("çok harcadım bugün", None), ("bugün ne kadar harcayabilirim", None), ("maaşım 25.000 tl", None), ("harcama yapmayı sevmiyorum", None),
    ("para biriktirmenin yolları neler", None), ("tasarruf için ne yapmalıyım", None),
]

CASES += [
    ("Ahmet'in doğum günü 3 Mart", "birthdays"), ("Ayşe'nin doğum günü 15.06", "birthdays"), ("doğum günü ekle: Ali 20 Aralık", "birthdays"),
    ("doğum günüm 5 mayıs", "birthdays"), ("doğum günlerim", "birthdays"), ("yaklaşan doğum günleri", "birthdays"),
    ("her yıl 14 şubat sevgililer gününü hatırlat", "reminder"),
    ("doğum günü hediyesi öner", None), ("doğum günü partisi nasıl planlanır", None), ("bugün benim doğum günüm", None),
    ("doğum günün kutlu olsun", None), ("doğum günü pastası tarifi", None),
]

CASES += [
    ("2 bardak su içtim", "habits"), ("su içtim", "habits"), ("1 litre su içtim", "habits"), ("7 saat uyudum", "habits"), ("uyudum 7,5 saat", "habits"),
    ("30 dakika yürüdüm", "habits"), ("1 saat koştum", "habits"), ("8000 adım attım", "habits"), ("kilom 72,5", "habits"), ("modum 4", "habits"),
    ("sağlık özetim", "habits"), ("bugün kaç bardak su içtim", "habits"), ("bu hafta ne kadar spor yaptım", "habits"),
    ("çok su içtim", None), ("dün gece kötü uyudum", None), ("su içmek sağlıklı mı", None), ("kaç bardak su içmeliyim", None),
    ("kilo vermek için ne yapmalıyım", None), ("uyku düzenim bozuk", None), ("spor yapmak istiyorum program öner", None), ("modum çok kötü", None),
]

CASES += [
    ("Ankara'dan İstanbul'a yol tarifi", "navigation"), ("İzmir'e nasıl giderim", "navigation"), ("İzmir'e yürüyerek yol tarifi", "navigation"),
    ("yol tarifi: Girne", "navigation"), ("yakınımda eczane", "navigation"), ("en yakın benzin istasyonu", "navigation"),
    ("yakınımda market var mı", "navigation"), ("trafik durumu", "navigation"),
    ("yol tarifi nasıl alınır", None), ("yakın arkadaşım geldi", None), ("yakınımda biri var mı", None), ("en yakın zamanda görüşelim", None),
    ("trafik cezası nasıl ödenir", None), ("rota planlama uygulaması yaz", None), ("trafikte sıkıştım çok sinirliyim", None),
    ("pomodoro başlat", "focus"), ("pomodoro 25 5", "focus"), ("50 dakika odaklan", "focus"), ("pomodoro durdur", "focus"),
    ("odaklanamıyorum", None), ("pomodoro tekniği nedir", None), ("odaklanmak için ne yapmalıyım", None),
]

CASES += [
    ("yarın ne zaman boşum", "plans"), ("cuma müsait saatlerim", "plans"), ("bugün boş zamanım var mı", "plans"), ("bu hafta boş saatlerim", "plans"),
    ("boş zamanlarımda ne yapabilirim", None), ("boş kalmak istemiyorum", None), ("müsait misin", None), ("yarın boş vaktim olursa sinemaya gidelim", None),
]

CASES += [
    ("kısa cevap ver", "style"), ("samimi ol", "style"), ("daha resmi ol", "style"), ("bana sen de", "style"), ("bana Murat diye hitap et", "style"),
    ("emoji kullanma", "style"), ("detaylı anlat", "style"), ("konuşma tarzım ne", "style"), ("tarzı sıfırla", "style"),
    ("bana kısa bir hikaye anlat", None), ("emoji nedir", None), ("kısa vadeli yatırım nedir", None), ("resmi tatil ne zaman", None), ("samimi bir mektup yaz", None),
    # "X hakkında ne biliyorsun" answers only when memory/history has X (covered in test_style_recall_feedback), so it is not a corpus case.
    ("dün ne konuştuk", "recall"), ("geçen hafta ne konuştuk", "recall"), ("kahve hakkında ne konuşmuştuk", "recall"),
    ("hafıza özeti", "recall"), ("Ankara hakkında ne düşünüyorsun", None), ("dün ne yaptın", None),
    ("yanlış anladın", "feedback"), ("tam istediğim buydu", "feedback"), ("en çok kullandığım komutlar", "feedback"), ("bana öneri ver", "feedback"),
    ("geri bildirimlerim", "feedback"), ("bu filmi öner", None), ("doğru mu bu", None),
]

CASES += [
    ("yazı tura at", "utility"), ("2 zar at", "utility"), ("20 yüzlü zar at", "utility"), ("1 ile 50 arasında rastgele sayı", "utility"),
    ("seç: pizza, hamburger, lahmacun", "utility"), ("45 gün sonra hangi gün", "utility"), ("3 hafta sonra ne zaman", "utility"),
    ("5 mayıs 2027 hangi gün", "utility"), ("1 mart 2026 ile 15 nisan 2026 arasında kaç gün", "utility"),
    ("15.03.1990 doğumluyum kaç yaşındayım", "utility"), ("boyum 180 kilom 75", "utility"), ("850 lira 4 kişi böl", "utility"),
    ("850 tl %10 bahşiş hesapla", "utility"),
    ("zar atmak istiyorum", None), ("yazı yazmak zor", None), ("bana bir hikaye seç", None), ("tura çıkmak istiyorum", None), ("kilom çok arttı", None),
]

CASES += [
    ("günlüğe yaz: bugün çok verimliydim", "journal"), ("günlüğüm", "journal"), ("dünkü günlüğüm", "journal"), ("bu haftaki günlüğüm", "journal"),
    ("günlüğümde kahve geçenler", "journal"), ("son günlük kaydını sil", "journal"),
    ("günlük plan yap", None), ("günlük burç yorumu", None), ("günlük kaç adım atmalıyım", None), ("günlüğüm kayboldu mu", None),
]

CASES += [
    ("düzelt: kahve => sade kahve", "memory"), ("hafızada kahve notumun geçmişi", "memory"),
    ("son notlarım", "recall"), ("bugün ne kaydettim", "recall"), ("son 3 kayıt", "recall"),
    ("Roma'nın geçmişi", None), ("düzelt bunu", None), ("son haberler", "news"),
]

CASES += [
    ("haftalık özet", "weekly"), ("geçen hafta nasıldı", "weekly"), ("bu haftanın özeti", "weekly"), ("haftalık rapor", "weekly"),
    ("haftalık burç yorumu", None), ("hafta sonu planım ne", None), ("bu hafta hava nasıl olacak", "weather"),
]

CASES += [("haftalık özet bildirimi aç", "prefs"), ("haftalık özet bildirimini kapat", "prefs")]

CASES += [("aylık bütçem 15000 tl", "expenses"), ("bütçe belirle 15000", "expenses"), ("bütçem", "expenses"), ("bütçe durumu", "expenses"), ("bütçe nedir", None), ("devlet bütçesi ne kadar", None)]

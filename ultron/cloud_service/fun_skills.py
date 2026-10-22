"""Offline "companion" content: motivation, proverbs, idioms, jokes, facts, word of the day, riddles, games,
wellbeing exercises and small tips. No model, no network. Facts are limited to well-established ones; quotes are
unattributed on purpose (no misattribution); wellbeing text is general information, not medical advice.
"""
from __future__ import annotations

import random
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

HOME_TZ = ZoneInfo("Europe/Istanbul")

MOTIVATION = (
    "Küçük adımlar da seni hedefe götürür; önemli olan bugün bir adım atmak.",
    "Mükemmel olmayı bekleme; başla, yolda düzelt.",
    "Zor bir gün, kötü bir hayat demek değildir.",
    "Dün yapamadığını bugün denemek bile ilerlemedir.",
    "Yorulmak pes etmek demek değil; biraz dinlen, sonra devam et.",
    "Büyük işler, her gün yapılan küçük işlerin toplamıdır.",
    "Kendine, bir arkadaşına davrandığın kadar nazik davran.",
    "Hata yapmak öğrenmenin ücretidir; ödediysen değerlendir.",
    "Bugün tek bir şeyi iyi yapmak, on şeyi yarım yapmaktan iyidir.",
    "Başlamak için hazır hissetmeni bekleme; hazırlık yaparken hazır olursun.",
    "Sabır, zamana güvenmenin sessiz halidir.",
    "Odağın neredeyse enerjin oradadır; neye odaklandığını seç.",
    "İlerleme düz bir çizgi değildir; geri adım atsan da yön doğruysa sorun yok.",
    "Bugünün işini yarına bırakmak yerine, yarının işini bugüne küçült.",
    "Kendini başkalarıyla değil, dünkü kendinle karşılaştır.",
)

PROVERBS = (
    ("Damlaya damlaya göl olur.", "Küçük birikimler zamanla büyük sonuç verir."),
    ("Sakla samanı, gelir zamanı.", "Bugün gereksiz görünen şey ileride işe yarayabilir; tutumlu ol."),
    ("Ağaç yaşken eğilir.", "Eğitim ve alışkanlıklar küçük yaşta daha kolay kazanılır."),
    ("Bir elin nesi var, iki elin sesi var.", "Birlikte çalışmak daha güçlüdür."),
    ("Acele işe şeytan karışır.", "Aceleyle yapılan işte hata olur."),
    ("Sabreden derviş muradına ermiş.", "Sabırla bekleyen isteğine ulaşır."),
    ("Her yokuşun bir inişi vardır.", "Zor zamanlar geçer."),
    ("Komşu komşunun külüne muhtaç.", "İnsanlar birbirine ihtiyaç duyar."),
    ("Ne ekersen onu biçersin.", "Yaptıklarının karşılığını görürsün."),
    ("Görünen köy kılavuz istemez.", "Açık olan şeyin kanıtlanmasına gerek yoktur."),
    ("Güneş balçıkla sıvanmaz.", "Bariz bir gerçek gizlenemez."),
    ("Taş yerinde ağırdır.", "Herkes ve her şey kendi yerinde değerlidir."),
    ("Bin düşün bir söyle.", "Konuşmadan önce iyice düşün."),
    ("Çok yaşayan bilmez, çok gezen bilir.", "Bilgi deneyimle kazanılır."),
    ("Dost acı söyler.", "Gerçek dost doğruyu söylemekten çekinmez."),
    ("Yuvarlanan taş yosun tutmaz.", "Sürekli yer değiştiren kalıcı bir şey biriktiremez."),
    ("Borç yiyen, bin yıl yaşar.", "Borç insanı uzun süre bağlayabilir; dikkatli ol."),
    ("İşleyen demir ışıldar.", "Çalışan ve kendini geliştiren değerini korur."),
)

IDIOMS = (
    ("Ağzı kulaklarına varmak", "Çok sevinmek."),
    ("Burnundan kıl aldırmamak", "Çok titiz ve huysuz olmak."),
    ("Gözü yükseklerde olmak", "Büyük hedefler peşinde olmak."),
    ("İçi içine sığmamak", "Heyecandan yerinde duramamak."),
    ("Kulak asmamak", "Önemsememek, dinlememek."),
    ("Ayak uydurmak", "Çevreye ve duruma uyum sağlamak."),
    ("Eli açık olmak", "Cömert olmak."),
    ("Kafa yormak", "Uzun uzun düşünmek."),
    ("Dilinin ucuna gelmek", "Tam hatırlayacakken söyleyememek."),
    ("Taşı gediğine koymak", "Tam yerinde ve etkili bir söz söylemek."),
    ("Havaya girmek", "Keyiflenip coşmak."),
    ("Yüreği ağzına gelmek", "Çok korkmak ya da heyecanlanmak."),
)

JOKES = (
    "Doktor hastaya demiş ki: “Sigarayı bırakmalısınız.” Hasta: “Tamam doktor, siz de not almayı bırakın, ben hallederim.”",
    "Temel’e sormuşlar: “Neden hep geç kalıyorsun?” Demiş ki: “Erken çıkıyorum ama yol uzuyor.”",
    "Telefonum bana dedi ki: “Şarjım %1.” Ben de: “Ben de.”",
    "Alarmım çaldı; ben de “beş dakika daha” dedim. Alarm üç kere daha aynı şeyi duydu.",
    "Matematik kitabı neden üzgün? Çünkü çok problemi var.",
    "Diyete başlamak kolay; asıl zor olan, buzdolabının ışığını kapatabilmek.",
    "Kahve içmeden konuşmayın bana; içtikten sonra da pek konuşmam ama en azından uyanık olurum.",
    "Bilgisayarım yavaşlayınca ona “sabır” dedim; o da bana “güncelleniyor” dedi.",
    "Haftanın en uzun günü pazartesi değil, perşembe: Herkes cumayı bekliyor ama cuma gelmiyor.",
    "Zaman yönetimi dersine geç kaldım; hoca “konu zaten buydu” dedi.",
)

FACTS = (
    "Bal, uygun saklandığında bozulmaz; antik mezarlarda binlerce yıllık yenilebilir bal bulunmuştur.",
    "Ahtapotun üç kalbi vardır: ikisi solungaçlara, biri vücuda kan pompalar.",
    "Venüs'te bir gün (kendi ekseni etrafında dönüş), bir yıldan (Güneş çevresindeki tur) daha uzundur.",
    "Işık Güneş'ten Dünya'ya yaklaşık 8 dakika 20 saniyede ulaşır.",
    "Botanik açıdan muz bir “berry” (tek yumurtalıktan gelişen etli meyve) sayılır; çilek ise bu sınıfa girmez.",
    "İnsan vücudundaki kemik sayısı yetişkinlerde 206'dır; bebeklerde yaklaşık 270 kadardır ve zamanla kaynaşır.",
    "Everest'in tepesi her yıl milimetre düzeyinde yükselir; Hint levhasının Avrasya altına itilmesi sürmektedir.",
    "Dünya yüzeyinin yaklaşık %71'i sularla kaplıdır.",
    "Kediler günün büyük bölümünü, çoğunlukla 12–16 saat kadarını uyuyarak geçirir.",
    "Ay, Dünya'dan her yıl yaklaşık 3,8 santimetre uzaklaşmaktadır.",
    "Eyfel Kulesi, sıcakta metalin genleşmesi nedeniyle yazın birkaç santimetre uzayabilir.",
    "Yetişkin bir insanın vücudundaki suyun oranı yaklaşık %60'tır.",
    "Satürn'ün yoğunluğu sudan düşüktür; yeterince büyük bir havuz olsaydı yüzerdi.",
    "Mısır piramitleri Kleopatra'nın yaşadığı çağdan daha eski; Giza piramitleri onun zamanında bile 2.000 yıldan fazla yaşındaydı.",
    "Karınca kolonileri, bireyler arasında kimyasal izlerle (feromon) iletişim kurar.",
    "Türkiye'de Göbeklitepe, bilinen en eski tapınak yapılarından biridir ve yaklaşık 11.000–12.000 yıl öncesine tarihlenir.",
    "Dünya'nın atmosferinin yaklaşık %78'i azottur, oksijen yaklaşık %21'dir.",
    "Bir insan gözü yaklaşık 10 milyon farklı rengi ayırt edebilir (tahmini ve kişiye göre değişen bir değerdir).",
)

WORDS = (
    ("Efsunlu", "Büyülü, etkileyici."), ("Serencam", "Başa gelen olay, serüven."), ("Hüzün", "İçe işleyen hafif keder."),
    ("Mahcup", "Utanmış, çekingen."), ("Nostalji", "Geçmişe duyulan özlem."), ("Tevekkül", "Olacağa razı olma, sakin kabullenme."),
    ("Zarafet", "İncelik, nazik ve ölçülü davranış."), ("Gönenç", "Refah, bolluk ve huzur."), ("Sükûnet", "Sakinlik, dinginlik."),
    ("Mütevazı", "Alçakgönüllü."), ("Muhabbet", "Sıcak sohbet, dostça yakınlık."), ("Vefa", "Sözünde ve dostluğunda durma."),
    ("Kıvam", "Uygun yoğunluk, olması gereken düzey."), ("Aydınlık", "Işığın bol olduğu hal; umut verici durum."), ("Gurbet", "Yurdundan uzak yer."),
)

TIPS = (
    "Bugün tek bir şeyi ertelemeden yap; en küçüğünden başla.",
    "Telefonu yatmadan yarım saat önce bırakmak uykuyu rahatlatabilir.",
    "Önemli bir işe başlamadan önce masandaki gereksiz her şeyi kaldır.",
    "Yemekten önce bir bardak su içmek tokluk hissini dengelemeye yardım edebilir.",
    "Konuşmadan önce üçe kadar saymak sinirli anlarda faydalı olur.",
    "Her akşam yarının üç önemli işini yaz; sabah karar yorgunluğu azalır.",
    "Haftada bir kez gelir ve giderlerine kısaca bak; küçük sızıntılar görünür olur.",
    "Dışarı çıkıp 10 dakika yürümek zihni tazeleyebilir.",
)

SAVING = (
    "Maaş yattığında önce birikimini ayır, kalanla harca (önce kendine öde).",
    "Büyük alışverişlerde 24 saat bekle; heves geçerse ihtiyaç değildi.",
    "Abonelik listesi çıkar; ayda bir kullanmadıklarını iptal et.",
    "Market listesiyle git, aç karnına alışveriş yapma.",
    "Acil durum fonunu önce 1 aylık gidere, sonra 3 aylığa tamamla.",
    "Faturaları otomatik ödemeye bağla ama ayda bir kontrol et.",
    "Küçük günlük harcamaları bir ay yaz; toplamı çoğu zaman şaşırtır.",
    "Büyük alımlarda en az üç yerden fiyat karşılaştır.",
)

PRODUCTIVITY = (
    "En zor işi sabah ilk iş yap (“kurbağayı ye”).",
    "25 dakika odak + 5 dakika mola (Pomodoro) tekniğini dene: “pomodoro başlat”.",
    "Bildirimleri bir çalışma bloğu boyunca kapat.",
    "İki dakikadan kısa süren işi hemen yap, ertelemek daha uzun sürer.",
    "Bir işi bitirmeden diğerine geçme; yarım işler zihinde yer tutar.",
    "Gün sonunda 5 dakika harca: neler oldu, yarın ne yapacağım.",
    "Toplantı ve mesaj yanıtlarını gün içinde iki-üç bloğa topla.",
    "Hedefi büyük yazma; bugün yapılacak en küçük somut adımı yaz.",
)

SLEEP_HYGIENE = (
    "Her gün aynı saatte yatıp kalkmaya çalış (hafta sonu dahil).",
    "Öğleden sonra kafeini azalt; birçok kişide etkisi saatlerce sürer.",
    "Yatak odasını serin, karanlık ve sessiz tut.",
    "Yatmadan önce ağır yemekten ve yoğun egzersizden kaçın.",
    "Yatakta telefon/ekran kullanımını azalt; yatağı uyku için ayır.",
    "Uyuyamazsan 20 dakikadan fazla yatakta dönme; sakin bir şey yapıp tekrar dene.",
)

COMPLIMENTS = (
    "Bugün enerjin harika görünüyor; sormadan söylemiş olayım. 🙂",
    "Çok şeyi aynı anda toparlıyorsun; bu hiç kolay değil.",
    "Kararlılığın gerçekten ilham verici.",
    "Düşünceli biri olduğun, soruların ve ilgi alanlarından belli.",
    "Kendine zaman ayırman, iyi bir karar.",
)

FOODS = {
    "kahvalti": ("menemen", "sahanda yumurta ve peynir tabağı", "simit-peynir-çay", "omlet ve salata", "yulaf ve meyve", "börek ve ayran"),
    "ogle": ("mercimek çorbası ve pilav", "tavuklu salata", "kuru fasulye", "ızgara köfte ve piyaz", "sebzeli makarna", "tost ve ayran"),
    "aksam": ("fırında tavuk ve sebze", "karnıyarık", "etli nohut", "menemenli pide", "izgara balık ve salata", "mantı", "kıymalı ıspanak"),
    "tatli": ("sütlaç", "revani", "kazandibi", "meyve tabağı", "irmik helvası", "ayva tatlısı"),
}

RIDDLES = (
    ("Konuşmaz ama cevap verir; bakınca seni gösterir. Nedir?", "ayna"),
    ("Ne kadar çok alırsan o kadar büyür. Nedir?", "çukur"),
    ("Yedikçe büyür, su içince ölür. Nedir?", "ateş"),
    ("Dışı yeşil, içi kırmızı, içinde siyah çekirdekler var. Nedir?", "karpuz"),
    ("Kanadı var ama uçmaz; dönünce rüzgâr yapar. Nedir?", "vantilatör"),
    ("İki kolu var ama sarılmaz; sürekli döner, zamanı gösterir. Nedir?", "saat"),
)

_MOTIV = re.compile(r"^(?:motivasyon(?:\s+ver)?|beni\s+motive\s+et|bana\s+moral\s+ver|moral\s+ver|guzel\s+bir\s+soz\s+soyle)\s*\??$")
_PROVERB = re.compile(r"^(?:ata\s*sozu|atasozu)(?:\s+(?:soyle|ver|goster))?\s*\??$|^bir\s+atasozu\s+soyle\s*\??$")
_IDIOM = re.compile(r"^(?:deyim|bir\s+deyim\s+soyle)(?:\s+(?:soyle|ver))?\s*\??$")
_JOKE = re.compile(r"^(?:espri|saka)(?:\s+yap)?\s*\??$|^beni\s+guldur\s*\??$")      # "bana bir fıkra anlat" stays a creative request for the model
_FACT = re.compile(r"^(?:ilginc\s+bilgi|ilginc\s+bir\s+bilgi\s+ver|ilginc\s+bir\s+sey\s+soyle|bana\s+ilginc\s+bir\s+bilgi\s+ver)\s*\??$")
_WORD = re.compile(r"^(?:gunun\s+kelimesi|bugunun\s+kelimesi)\s*\??$")
_TIP = re.compile(r"^(?:gunun\s+tavsiyesi|rastgele\s+tavsiye|kucuk\s+bir\s+ipucu\s+ver)\s*\??$")
_SAVE = re.compile(r"^(?:tasarruf|biriktirme)\s+(?:ipucu|ipuclari|tavsiyesi|onerisi)\s*\??$|^para\s+biriktirme\s+ipucu\s*\??$")
_PROD = re.compile(r"^(?:verimlilik|odaklanma|calisma)\s+(?:ipucu|ipuclari|tavsiyesi|onerisi)\s*\??$")
_SLEEP = re.compile(r"^(?:uyku\s+hijyeni|uyku\s+ipucu|uyku\s+tavsiyesi|iyi\s+uyumak\s+icin\s+ipucu)\s*\??$")
_COMPLIMENT = re.compile(r"^(?:iltifat\s+et|bana\s+iltifat\s+et|bir\s+iltifat\s+et)\s*\??$")
_FOOD = re.compile(r"^(?:ne\s+yesem|yemek\s+onerisi|(kahvalti|ogle|aksam)\s+(?:yemegi\s+)?(?:onerisi|icin\s+oneri)|tatli\s+onerisi)\s*\??$")
_BREATH = re.compile(r"^(?:nefes\s+egzersizi|nefes\s+al|sakinlesmek\s+istiyorum|sakinlesme\s+egzersizi)\s*\??$")
_EYES = re.compile(r"^(?:goz\s+dinlendirme|goz\s+egzersizi|20\s*-?\s*20\s*-?\s*20)\s*\??$")
_STRETCH = re.compile(r"^(?:esneme\s+hareketleri|masa\s+basi\s+egzersiz\w*|boyun\s+agrisi\s+egzersiz\w*)\s*\??$")
_RPS = re.compile(r"^tas\s+kagit\s+makas(?:\s+oyna)?\s*[:\-]?\s*(tas|kagit|makas)\s*$|^tas\s+kagit\s+makas\s+oyna\s*\??$")
_EIGHT = re.compile(r"^(?:8|sekiz)\s*top\s*[:\-]\s*(.{3,120})$|^sihirli\s+(?:8|sekiz)\s*top\s*[:\-]\s*(.{3,120})$")
_RIDDLE = re.compile(r"^(?:bilmece(?:\s+(?:sor|ver|soyle))?|bana\s+bilmece\s+sor)\s*\??$")
_RIDDLE_ANS = re.compile(r"^(?:bilmece\s+cevabi|bilmecenin\s+cevabi\s+ne|cevap\s+ver|pes\s+ettim)\s*\??$|^bilmece\s+cevap\s*[:\-]\s*(.{1,40})$")
EIGHT = ("Kesinlikle evet.", "Büyük ihtimalle evet.", "İşaretler olumlu.", "Şimdilik evet gibi görünüyor.", "Belirsiz, tekrar sor.", "Şimdi söylemesem daha iyi.",
         "Pek sanmıyorum.", "Cevabım hayır.", "Çok şüpheli.", "Buna güvenme.")

_BREATH_TEXT = ("🌬 4-7-8 nefesi (3–4 tur yeter):\n1) Burnundan 4 saniye nefes al.\n2) 7 saniye tut.\n3) Ağzından 8 saniye yavaşça ver.\n"
                "Rahatsızlık ya da baş dönmesi hissedersen bırak ve normal nefes al. Bu genel bir rahatlama egzersizidir, tıbbi tavsiye değildir.")
_EYES_TEXT = ("👀 20-20-20 kuralı: Her 20 dakikada bir, 20 saniye boyunca yaklaşık 6 metre (20 feet) uzağa bak; gözlerini bilinçli kırp. "
              "Hatırlatıcı için “20 dakikada bir gözlerimi dinlendirmemi hatırlat” diyebilirsin.")
_STRETCH_TEXT = ("🧘 Masa başı esneme (her biri 20–30 sn):\n• Boynu yavaşça sağa-sola yatır\n• Omuzları 10 kez geriye çevir\n• Kollarını başının üstünde birleştirip yukarı uzan\n"
                 "• Bileklerini döndür, parmaklarını aç-kapat\n• Ayağa kalk, 10 adım yürü\nAğrı hissedersen bırak; süregelen ağrı için bir uzmana danış.")


def wants_fun(text: str) -> bool:
    return answer(text, rng=random.Random(0)) is not None or bool(_RIDDLE_ANS.match(fold_turkish(text)))


def _pick(seq, rng):
    return rng.choice(seq)


def answer(text: str, now: datetime | None = None, rng: random.Random | None = None) -> str | None:
    f = fold_turkish(str(text or "")).strip()
    if not f or len(f) > 160:
        return None
    rng = rng or random.SystemRandom()
    today = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).date()
    if _MOTIV.match(f):
        return "💪 " + _pick(MOTIVATION, rng)
    if _PROVERB.match(f):
        p, meaning = _pick(PROVERBS, rng)
        return f"📜 {p}\nAnlamı: {meaning}"
    if _IDIOM.match(f):
        d, meaning = _pick(IDIOMS, rng)
        return f"🗣 {d}\nAnlamı: {meaning}"
    if _JOKE.match(f):
        return "😄 " + _pick(JOKES, rng)
    if _FACT.match(f):
        return "💡 " + _pick(FACTS, rng)
    if _WORD.match(f):
        w, meaning = WORDS[today.toordinal() % len(WORDS)]
        return f"📖 Günün kelimesi: {w}\nAnlamı: {meaning}"
    if _TIP.match(f):
        return "✅ " + _pick(TIPS, rng)
    if _SAVE.match(f):
        return "💰 " + _pick(SAVING, rng)
    if _PROD.match(f):
        return "🎯 " + _pick(PRODUCTIVITY, rng)
    if _SLEEP.match(f):
        return "😴 " + _pick(SLEEP_HYGIENE, rng)
    if _COMPLIMENT.match(f):
        return _pick(COMPLIMENTS, rng)
    m = _FOOD.match(f)
    if m:
        meal = m.group(1) or ("tatli" if "tatli" in f else None)
        if not meal:
            hour = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).hour
            meal = "kahvalti" if hour < 11 else "ogle" if hour < 16 else "aksam"
        label = {"kahvalti": "Kahvaltı", "ogle": "Öğle", "aksam": "Akşam", "tatli": "Tatlı"}[meal]
        options = rng.sample(FOODS[meal], 3)
        return f"🍽 {label} için fikirler: " + ", ".join(options) + "."
    if _BREATH.match(f):
        return _BREATH_TEXT
    if _EYES.match(f):
        return _EYES_TEXT
    if _STRETCH.match(f):
        return _STRETCH_TEXT
    m = _RPS.match(f)
    if m:
        mine = rng.choice(("tas", "kagit", "makas"))
        names = {"tas": "taş ✊", "kagit": "kağıt ✋", "makas": "makas ✌"}
        if not m.group(1):
            return "Taş, kağıt, makas! Seçimini yaz: “taş kağıt makas: taş”."
        you = m.group(1)
        beats = {"tas": "makas", "kagit": "tas", "makas": "kagit"}
        result = "Berabere!" if you == mine else "Sen kazandın! 🎉" if beats[you] == mine else "Ben kazandım! 😎"
        return f"Sen {names[you]}, ben {names[mine]} — {result}"
    m = _EIGHT.match(f)
    if m:
        return "🎱 " + _pick(EIGHT, rng)
    return None


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    """Riddles keep the last question per owner so “bilmece cevabı” can reveal it."""
    f = fold_turkish(str(text or "")).strip()
    if pool is None or len(f) > 160:
        return None
    if _RIDDLE.match(f):
        question, answer_text = random.SystemRandom().choice(RIDDLES)
        await pool.execute(
            "INSERT INTO owner_prefs(user_id,prefs) VALUES($1,jsonb_build_object('riddle',$2::jsonb)) "
            "ON CONFLICT(user_id) DO UPDATE SET prefs=COALESCE(owner_prefs.prefs,'{}'::jsonb)||jsonb_build_object('riddle',$2::jsonb),updated_at=NOW()",
            user_id, '{"a": "%s"}' % answer_text)
        return f"🧩 {question}\nCevabını yaz ya da “bilmece cevabı” de."
    m = _RIDDLE_ANS.match(f)
    if m:
        row = await pool.fetchval("SELECT prefs->'riddle'->>'a' FROM owner_prefs WHERE user_id=$1", user_id)
        if not row:
            return "Henüz bir bilmece sormadım. “bilmece sor” de."
        if m.group(1):
            guess = m.group(1).strip()
            return "🎉 Doğru bildin!" if fold_turkish(guess) == fold_turkish(row) else "Olmadı, tekrar dene ya da “bilmece cevabı” de."
        return f"Cevap: {row}."
    return answer(text, now)

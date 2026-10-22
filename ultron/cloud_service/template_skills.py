"""Ready-made checklists: "seyahat için liste hazırla", "deprem çantası listesi hazırla", "hazır listeler".

Items are added to the owner's normal lists (same table as "alışveriş listesine süt ekle"), so every list command
works on them afterwards; items already on the list are not duplicated.
"""
from __future__ import annotations

import re
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

TEMPLATES = {
    "seyahat": ("Seyahat", ("pasaport/kimlik", "bilet ve rezervasyon çıktıları", "telefon ve şarj aleti", "powerbank", "kulaklık", "kişisel ilaçlar", "diş fırçası ve macun",
                            "şampuan ve duş malzemeleri", "kıyafetler (gün sayısı + 1)", "iç çamaşırı ve çorap", "yedek ayakkabı", "güneş kremi", "para ve kredi kartı",
                            "seyahat sigortası belgesi", "evi kapatma kontrolü (gaz, ütü, pencere)")),
    "kamp": ("Kamp", ("çadır", "uyku tulumu", "mat", "el feneri ve yedek pil", "kibrit/çakmak", "ocak ve tüp", "su matarası", "yemek malzemeleri", "çatal-bıçak-tabak",
                      "çöp poşeti", "ilk yardım çantası", "böcek kovucu", "güneş kremi", "yedek kıyafet", "katlanır bıçak/çok amaçlı alet")),
    "tasinma": ("Taşınma", ("koli ve bant", "kalın kalem (koliyi etiketle)", "köpük/gazete (kırılacaklar için)", "adres değişikliği bildirimi", "elektrik/su/doğalgaz abonelik taşıma",
                            "internet hat taşıma", "eski evin sayaç fotoğrafları", "önemli belgeleri ayrı çantaya koy", "temizlik malzemesi", "ilk gece çantası")),
    "sinav": ("Sınav günü", ("kimlik ve sınav giriş belgesi", "kurşun kalem ve silgi", "kalemtıraş", "saat (akıllı olmayan)", "su", "hafif atıştırmalık", "yedek kalem", "sınav yerinin adresi ve ulaşım planı")),
    "is gorusmesi": ("İş görüşmesi", ("özgeçmiş çıktısı", "kimlik", "referans listesi", "şirket hakkında kısa araştırma", "sorulacak sorular", "kıyafet hazırlığı", "yol ve süre planı", "not defteri ve kalem")),
    "piknik": ("Piknik", ("örtü", "su ve içecekler", "yiyecekler", "tabak ve çatal-bıçak", "peçete", "çöp poşeti", "güneş kremi", "şapka", "top/oyunlar", "böcek kovucu")),
    "dogum gunu partisi": ("Doğum günü partisi", ("pasta", "mum ve çakmak", "balon ve süsler", "davetiye/mesajlar", "içecekler", "atıştırmalıklar", "tabak-bardak-peçete", "müzik listesi", "hediye", "fotoğraf makinesi/telefon şarjı")),
    "deprem cantasi": ("Deprem çantası", ("su (kişi başı en az 3 günlük)", "uzun ömürlü yiyecek/konserve", "el feneri ve yedek pil", "pilli radyo", "düdük", "ilk yardım malzemeleri", "kişisel ilaçlar",
                                           "powerbank", "battaniye", "yedek kıyafet", "hijyen malzemeleri", "önemli belge kopyaları", "nakit para", "toz maskesi", "eldiven")),
    "plaj": ("Plaj", ("havlu", "güneş kremi", "şapka ve güneş gözlüğü", "mayo ve yedek kıyafet", "su", "terlik", "plaj çantası", "şemsiye/gölgelik", "atıştırmalık")),
    "hastane cantasi": ("Hastane çantası", ("kimlik ve sağlık belgeleri", "kullanılan ilaçların listesi", "telefon ve şarj aleti", "terlik", "rahat pijama/sabahlık", "kişisel bakım malzemeleri", "çorap", "yedek kıyafet", "kulaklık ve kitap")),
    "bebek cantasi": ("Bebek çantası", ("bez", "ıslak mendil", "yedek kıyafet", "mama/biberon", "su", "battaniye", "pişik kremi", "oyuncak/emzik", "bez değiştirme örtüsü", "poşet")),
    "bayram": ("Bayram hazırlığı", ("ev temizliği", "tatlı ve ikramlıklar", "bayramlık kıyafetler", "harçlık ve bozuk para", "akraba ziyaret listesi", "alışveriş listesi", "ulaşım/bilet kontrolü", "mesaj ve arama listesi")),
    "market": ("Haftalık market", ("ekmek", "süt", "yumurta", "peynir", "zeytin", "domates", "salatalık", "meyve", "makarna/pirinç", "yağ", "çay/kahve", "deterjan", "tuvalet kağıdı")),
}
_ALIASES = {"seyahat": "seyahat", "tatil": "seyahat", "valiz": "seyahat", "yolculuk": "seyahat", "kamp": "kamp", "tasinma": "tasinma", "ev tasima": "tasinma", "sinav": "sinav",
            "sinav gunu": "sinav", "is gorusmesi": "is gorusmesi", "mulakat": "is gorusmesi", "piknik": "piknik", "dogum gunu": "dogum gunu partisi",
            "dogum gunu partisi": "dogum gunu partisi", "parti": "dogum gunu partisi", "deprem cantasi": "deprem cantasi", "afet cantasi": "deprem cantasi",
            "acil durum cantasi": "deprem cantasi", "plaj": "plaj", "hastane cantasi": "hastane cantasi", "dogum cantasi": "hastane cantasi", "bebek cantasi": "bebek cantasi",
            "bebek": "bebek cantasi", "bayram": "bayram", "bayram hazirligi": "bayram", "market": "market", "haftalik market": "market"}
_ALIAS_RX = "|".join(sorted(_ALIASES, key=len, reverse=True))
_MAKE = re.compile(rf"^({_ALIAS_RX})\s+(?:icin\s+)?(?:listesi|liste)\s+(?:hazirla|olustur|yap|ekle|getir)\s*$|^({_ALIAS_RX})\s+(?:icin\s+)?(?:hazir\s+)?(?:listesi|liste)\s*$")
_CATALOG = re.compile(r"^(?:hazir\s+listeler|liste\s+sablonlari|hangi\s+hazir\s+listeler\s+var)\s*\??$")


def wants_templates(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 80 and bool(_MAKE.match(f) or _CATALOG.match(f))


async def handle(text: str, pool: Any, user_id: str) -> str | None:
    if pool is None or not wants_templates(text):
        return None
    f = fold_turkish(text).strip()
    if _CATALOG.match(f):
        return "Hazır listeler: " + ", ".join(label.lower() for label, _ in TEMPLATES.values()) + ". Örn. “seyahat için liste hazırla”."
    m = _MAKE.match(f)
    key = _ALIASES[m.group(1) or m.group(2)]
    label, items = TEMPLATES[key]
    list_label = label
    name = fold_turkish(label)[:40]                        # same key the normal list commands derive from "<name> listesine …"
    added = 0
    for it in items:
        got = await pool.fetchval(
            "INSERT INTO owner_list_items(user_id,list_name,item,item_key,list_label) VALUES($1,$2,$3,$4,$5) ON CONFLICT(user_id,list_name,item_key) DO NOTHING RETURNING id",
            user_id, name, it[:120], fold_turkish(it), list_label)
        added += 1 if got else 0
    if not added:
        return f"“{label}” listen zaten hazır; “{label.lower()} listem” ile görebilirsin."
    return f"“{label}” listesi hazır: {added} madde eklendi. “{label.lower()} listem” diyerek görebilir, “{label.lower()} listesine … ekle” ile genişletebilirsin."

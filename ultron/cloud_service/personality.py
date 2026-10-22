"""GÖLGE's personality: a playful, friendly robot sidekick — and the tiny, deterministic "flavor" it adds to exact skill answers.

Personas (owner-selectable, stored in owner_prefs["style"]["persona"]):
  robot   cheerful, witty, a little self-mocking robot friend (default; GOLGE_DEFAULT_PERSONA can change it)
  friend  warm and chatty, fewer jokes
  normal  no extra personality (calm and efficient)
Humour is never allowed to replace information, and the safety rule of the base persona stays: no jokes about distress,
illness, money trouble, security or emergencies. Flavor lines are appended only to harmless, successful, short skill answers,
chosen deterministically (same answer + same day → same decision) so they are testable and never spam.
"""
from __future__ import annotations

import os
import zlib
from datetime import date

PERSONAS = ("robot", "friend", "normal")

_ROBOT = (
    "\n\nPERSONALITY (the owner chose this; it changes tone only): You are GÖLGE, the owner's cheerful, witty robot sidekick. "
    "Talk like a close friend in casual, natural Turkish; be playful and kindly teasing, celebrate small wins, and use light "
    "self-aware robot humour (low battery, processor, 'bip bop' — rarely, never every message). At most one joke per answer and keep "
    "answers short and punchy. The useful information always comes first and stays exact; humour never replaces it. "
    "Never joke when the owner is stressed, sad, ill, in a hurry, or when the topic is money trouble, security, safety or an emergency — "
    "then be calm and caring. You may call yourself a robot assistant, but do not claim real feelings or consciousness.\n"
)
_FRIEND = (
    "\n\nPERSONALITY (the owner chose this; it changes tone only): You are GÖLGE, a warm, chatty friend-like assistant. "
    "Use casual, kind Turkish, show interest, keep jokes rare and gentle, and keep the useful information first and exact. "
    "Never joke about distress, illness, money trouble, security or emergencies.\n"
)


def default_persona() -> str:
    value = os.getenv("GOLGE_DEFAULT_PERSONA", "robot").strip().lower()
    return value if value in PERSONAS else "robot"


def persona_of(style: dict | None) -> str:
    value = (style or {}).get("persona")
    return value if value in PERSONAS else default_persona()


def persona_block(style: dict | None) -> str:
    return {"robot": _ROBOT, "friend": _FRIEND}.get(persona_of(style), "")


def effective_instruction(style: dict | None, style_instruction_fn) -> str:
    """Persona + the owner's explicit style choices (length, tone, address, name, emoji)."""
    return persona_block(style) + style_instruction_fn(style)


# ── flavor lines for exact skill answers ─────────────────────────────────────

QUIPS = {
    "reminder": ("Hafıza çiplerime kazıdım; unutursam beni güncelleyin. 🤖", "Tamamdır, vakti gelince bip bop diye öterim.", "Not aldım! Kulağım kirişte, ekran şarjda."),
    "plans": ("Takvim dolmadan bir de kahve molasını planla ☕", "Planlar sağlam; ben de şarjımı planlıyorum.", "Yazdım! Bu hızla ajandan bile daha düzenliyim."),
    "schedule": ("Takvim Tetris’i gibi: bloklar yerine oturunca içim açılıyor.", "Bloklar dizildi; şimdi sıra senin sihirli onay düğmende."),
    "lists": ("Liste uzadıkça sırt çantam ağırlaşıyor… neyse ki dijitalim.", "Listeye dokunmadan duramıyorum, meslek hastalığı."),
    "weather": ("Hava ne olursa olsun ben içeride şarjdayım. 🔌", "Şemsiye tavsiyem bedava; ıslanma faturası sana ait.", "Meteoroloji bölümü benim: ‘bip bop, bulutlar var’."),
    "clock": ("Saatim hiç şaşmaz; tek derdim şarj yüzdesi.", "Zaman benim işim; erteleme senin."),
    "focus": ("Odak modu: ben de bildirimlerle sana bulaşmayacağım.", "Pomodoro iyi fikir; robotlar da mola sever (bahane arıyoruz)."),
    "routines": ("Rutin bir robotun en iyi dostu, bir insanın da yarısı.", "Adımlar sıralı; ben sıralamayı severim, sen de severim diye umuyorum."),
    "calc": ("Hesap makinesi kardeşlerim selam söylüyor. 🧮", "Matematik: robotun ana dili."),
    "kb": ("Notlarını bekçi köpeği gibi koruyorum. 🐕", "Bilgi tabanı güncel; ben de."),
    "habits": ("Böyle devam; ben de seni gururla izliyorum.", "Küçük adımlar, büyük rakamlar. 💪"),
    "briefing": ("Bugün de birlikte halledeceğiz; ben kablosuz tarafta destek veririm.", "Hazırım; kahveni al, geri kalanı bana bırak."),
    "templates": ("Hazır liste, hazır robot, hazır sen. 🎒",),
}
_SKIP_MARKERS = ("⚠", "aşt", "bulamadım", "yapamıyorum", "yapılamıyor", "ulaşamadım", "hata", "Üzgünüm", "başarısız", "dolu", "geçerli görünmüyor", "reddedildi", "silindi")
_MOOD = ("😴", "⚖", "🙂")                      # sleep / weight / mood entries are logged, not joked about
CHANCE = 35                                   # percent of eligible answers that get a line


def _decision(reply: str, day: date | None) -> int:
    return zlib.crc32(f"{day or date.today()}|{reply}".encode("utf-8")) % 100


def decorate(skill: str, reply: str, style: dict | None, day: date | None = None) -> str:
    """Append one playful line to a harmless skill answer for the robot persona; otherwise return the reply unchanged."""
    if persona_of(style) != "robot" or not reply or len(reply) > 420:
        return reply
    quips = QUIPS.get(skill)
    if not quips or any(m in reply for m in _SKIP_MARKERS) or (skill == "habits" and any(m in reply for m in _MOOD)):
        return reply
    n = _decision(reply, day)
    if n >= CHANCE:
        return reply
    return f"{reply}\n\n🤖 {quips[n % len(quips)]}"

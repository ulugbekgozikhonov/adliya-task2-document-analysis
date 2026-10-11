"""Topshiriq muddatini tushunish: matndagi muddat iborasi -> tur + (iloji bo'lsa) aniq sana.

Turlar:
  sana        - aniq sana: "18.09.2026", "2026-yil 20-sentabrga qadar"
  nisbiy      - hujjat sanasidan hisoblanadi: "o'n kun muddatda", "uch ish kuni ichida"
  shartli     - boshqa voqeaga bog'liq: "prototip tayyor bo'lgandan so'ng 15 kun ichida"
  davriy      - takrorlanadi: "har oyda", "har chorakda", "har oyning 5-sanasiga qadar"
  boshlanish  - shu sanadan boshlab: "2026-yil 15-martdan boshlab"
  doimiy      - "doimiy"
  yo'q        - muddat ko'rsatilmagan
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta

from app.dates import find_date

NUMBERS = {
    "bir": 1, "ikki": 2, "uch": 3, "to'rt": 4, "besh": 5, "olti": 6,
    "yetti": 7, "sakkiz": 8, "to'qqiz": 9, "o'n": 10, "o'n besh": 15, "yigirma": 20,
}  # fmt: skip
NUM = r"(\d+|o'n besh|" + "|".join(sorted(NUMBERS, key=len, reverse=True)) + r")"

CONDITIONAL = re.compile(
    r"([\w' -]{3,60}?(?:dan|gandan|ngandan)\s+so'ng\s+"
    + NUM
    + r"\s+(?:ish\s+)?(?:kun|hafta|oy)\w*\s+ichida)",
    re.IGNORECASE,
)
PERIODIC = re.compile(
    r"(har\s+(?:oy|chorak|hafta|yil|kun)\w*(?:\s+(?:yakunidan\s+keyingi\s+oyning|juma|dushanba)\b)?"
    r"(?:\s+\d{1,2}-sanasiga\s+qadar|\s+kuni)?)",
    re.IGNORECASE,
)
START = re.compile(r"(\d{4}-yil\s+\d{1,2}-[a-z]+?)dan\s+boshlab", re.IGNORECASE)
RELATIVE = re.compile(NUM + r"\s+(ish\s+)?(kun|hafta|oy)\w*\s+(?:muddatda|ichida)", re.IGNORECASE)
ABSOLUTE = re.compile(
    r"\d{2}\.\d{2}\.\d{4}(?:\s*yilgacha)?|\d{4}-yil\s+\d{1,2}-[a-z]+", re.IGNORECASE
)
DEADLINE_SUFFIX = re.compile(r"\w*\s*(?:qadar|gacha)", re.IGNORECASE)


@dataclass
class Deadline:
    type: str = "yo'q"
    raw: str = ""
    date: str = ""  # ISO, hisoblab bo'lsa


def _number(word: str) -> int:
    return int(word) if word.isdigit() else NUMBERS.get(word.lower(), 0)


def _add(start: date, n: int, unit: str, business: bool) -> date:
    if unit.startswith("oy"):
        month = start.month - 1 + n
        year, month = start.year + month // 12, month % 12 + 1
        return date(year, month, min(start.day, 28))
    if unit.startswith("hafta"):
        return start + timedelta(weeks=n)
    if not business:
        return start + timedelta(days=n)
    d = start
    while n:
        d += timedelta(days=1)
        if d.weekday() < 5:  # dushanba-juma
            n -= 1
    return d


def parse_deadline(text: str, doc_date: str = "", in_sentence: bool = False) -> Deadline:
    """in_sentence=True: matn - butun gap. Unda aniq sana faqat "...gacha/qadar" bilan kelsa muddat
    hisoblanadi ("2026-yil 2-sentabrda imzolangan memorandum" dagi sana muddat emas)."""
    text = " ".join(text.split())
    if m := CONDITIONAL.search(text):
        return Deadline("shartli", m.group(1).strip())
    if m := PERIODIC.search(text):
        return Deadline("davriy", m.group(1).strip())
    if m := START.search(text):
        d = find_date(m.group(1))
        return Deadline("boshlanish", m.group(0), d.isoformat() if d else "")
    for m in ABSOLUTE.finditer(text):
        is_deadline = "yilgacha" in m.group(0) or DEADLINE_SUFFIX.match(text, m.end())
        if in_sentence and not is_deadline:
            continue
        d = find_date(m.group(0))
        if d:
            return Deadline("sana", m.group(0), d.isoformat())
    if m := RELATIVE.search(text):
        n, business, unit = _number(m.group(1)), bool(m.group(2)), m.group(3).lower()
        result = ""
        if doc_date and n:
            result = _add(date.fromisoformat(doc_date), n, unit, business).isoformat()
        return Deadline("nisbiy", m.group(0), result)
    if re.search(r"\bdoimiy\b", text, re.IGNORECASE):
        return Deadline("doimiy", "doimiy")
    return Deadline()

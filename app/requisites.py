"""Rekvizitlar: jo'natuvchi tashkilot, hujjat raqami, sana, imzolagan shaxs.

Rasmiy hujjatlarning qat'iy shabloniga tayanadi:
  - jo'natuvchi - eng tepadagi KATTA harfli qatorlar (manzil yoki "QARORI" dan oldin);
  - raqam       - "№" belgisidan keyin (OCR uni "No", "Ne", "Ҳе" deb o'qishi mumkin);
  - sana        - raqam yonida: "08.09.2026" yoki "2026-yil 10-fevral";
  - imzolagan   - pastda: lavozim + "A. Familiya" ("Ijrochi:" qatori emas).
"""

import re
from dataclasses import dataclass

from app.dates import parse_date

NUMBER = re.compile(r"(?:№|N[oeа°º»]|Ҳе|Ме|Мо|Ма)\s*([0-9][\w/-]*)")
DATE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b|\b\d{4}-yil\s+\d{1,2}-[a-z]+", re.IGNORECASE)
NAME = re.compile(r"\b([A-ZА-Я][a-zа-я]?\.\s?[A-ZА-Я][a-zа-я']+)\s*$")
POSITION = re.compile(
    r"rais|direktor|rahbar|boshlig'i|vazir|o'rinbosar|kotib|hokim|prokuror", re.IGNORECASE
)
STOP_HEADER = re.compile(r"^\d{6}|^Q\s?A\s?R\s?O\s?R|^QARORI|^BUYRUG|^FARMOYISH", re.IGNORECASE)


@dataclass
class Requisites:
    sender: str = ""
    number: str = ""
    date: str = ""  # ISO: 2026-09-08
    date_raw: str = ""
    signer: str = ""
    signer_position: str = ""


def _latin(text: str) -> str:
    """OCR ba'zan lotin harfi o'rniga ko'rinishi bir xil kirill harfini qo'yadi (М, О, А...)."""
    return text.translate(str.maketrans("АВЕКМНОРСТХаеорсх", "ABEKMHOPCTXaeopcx"))


def sender(lines: list[str]) -> str:
    """Eng tepadagi katta harfli qatorlar: tashkilot nomi."""
    parts = []
    for line in lines[:6]:
        if STOP_HEADER.search(line):
            break
        letters = [c for c in line if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) > 0.8:
            parts.append(line.strip('" '))
        elif parts:
            break
    name = " ".join(parts)
    # Qarorda tashkilot nomi qaratqich kelishigida: "... KENGASHINING" -> "... Kengashi"
    name = re.sub(r"(\w+?)(?:I?NING)$", lambda m: m.group(1) + "I", name, flags=re.IGNORECASE)
    return _sentence_case(name) if name.isupper() else name


def _sentence_case(text: str) -> str:
    """ "NOTARIAT VA FHDYO KENGASHI" -> "Notariat va FHDYO kengashi" (qisqartmalar saqlanadi)."""
    words = []
    for word in text.split():
        vowels = sum(c in "AEIOU" for c in word)
        is_acronym = len(word) >= 3 and vowels <= 1
        words.append(word if is_acronym else word.lower())
    result = " ".join(words)
    return result[:1].upper() + result[1:]


def number_and_date(lines: list[str]) -> tuple[str, str]:
    """Raqam va sanani hujjatning yuqori qismidan qidiradi ("-son xatga" bo'sh maydoni emas)."""
    for line in lines[:10]:
        if "xatga" in line or "qaroriga" in line:
            continue
        num = NUMBER.search(line)
        if num:
            date = DATE.search(line)
            return num.group(1).rstrip(".,"), date.group(0) if date else ""
    return "", ""


def signer(lines: list[str]) -> tuple[str, str]:
    """Pastdan yuqoriga: lavozim so'zi bor va "A. Familiya" bilan tugaydigan qator."""
    for line in reversed(lines):
        if line.lower().startswith(("ijrochi", "tel")):
            continue
        fixed = _latin(line)
        name = NAME.search(fixed)
        if name and POSITION.search(fixed):
            position = fixed[: name.start()].strip(" .,")
            return name.group(1).replace(". ", ".").replace(".", ". "), position
    return "", ""


def extract_requisites(lines: list[str]) -> Requisites:
    num, date_raw = number_and_date(lines)
    name, position = signer(lines)
    return Requisites(
        sender=sender(lines),
        number=num,
        date=parse_date(date_raw) or "",
        date_raw=date_raw,
        signer=name,
        signer_position=position,
    )

"""O'zbekcha sana yozuvlarini ISO formatga o'tkazish: "08.09.2026", "2026-yil 20-sentabrga qadar"."""

import re
from datetime import date

MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avgust": 8, "sentabr": 9, "oktabr": 10, "noyabr": 11, "dekabr": 12,
}  # fmt: skip

NUMERIC = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")
WORDS = re.compile(r"\b(\d{4})-yil\s+(\d{1,2})-([a-z]+)", re.IGNORECASE)


def find_date(text: str) -> date | None:
    """Matndagi birinchi sanani topadi. Oy nomi qo'shimcha bilan ham bo'lishi mumkin: "sentabrga"."""
    m = NUMERIC.search(text)
    if m:
        day, month, year = map(int, m.groups())
        return _safe(year, month, day)
    m = WORDS.search(text)
    if m:
        year, day, word = int(m.group(1)), int(m.group(2)), m.group(3).lower()
        month = next((n for name, n in MONTHS.items() if word.startswith(name)), None)
        if month:
            return _safe(year, month, day)
    return None


def _safe(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date(text: str) -> str | None:
    d = find_date(text)
    return d.isoformat() if d else None

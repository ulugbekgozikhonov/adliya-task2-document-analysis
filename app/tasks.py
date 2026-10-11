"""Topshiriqlarni ajratish: jadvaldan (ilova ham) va abzatslardan.

Jadval: ustunlar sarlavha bo'yicha aniqlanadi (mazmun / ijrochi / muddat / natija).
Abzats: gap buyruq fe'li bilan tugasa ("-sin", "-ilsin", "so'raymiz") - topshiriq.
  Ijrochi - gap boshidagi tashkiliy birlik ("... bo'limi", "... boshqarmasi" ...).
  Muddat  - gap ichidagi muddat iborasi (app.deadlines).
"""

import re
from dataclasses import dataclass, field

from app.deadlines import Deadline, parse_deadline
from app.pdf_reader import Page

ORG = (
    r"bo'limi|boshqarmasi|departamenti|laboratoriyasi|bo'linmalari|bo'linmalar|bo'linmasi|"
    r"kotibiyati|xizmati|guruhi|koordinatori|markazi|markaz|agentligi|komissiyasi|kengashi"
)
EXECUTOR = re.compile(r"^((?:\S+\s+){0,4}?\S*(?:" + ORG + r"))\b", re.IGNORECASE)
CO_EXECUTOR = re.compile(
    r"((?:\S+\s+){0,4}?\S*(?:" + ORG + r"))\s+bilan\s+birgalikda", re.IGNORECASE
)
VIA = re.compile(r"((?:\S+\s+){0,1}?\S*(?:" + ORG + r"))\s+orqali", re.IGNORECASE)
DIRECTIVE = re.compile(r"\b\w+(?:sin|silar)\b|so'raymiz|so'raladi", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<!\b\d\.)(?<!\b\d\d\.)(?<=[.!?])\s+(?=(?:\d{1,2}\.\s+)?[A-Z\"«])")
NUMBERED = re.compile(r"^(\d{1,2})\.\s+")
REFERS_TO_TABLE = re.compile(r"quyidagi|jadvalda|ilovada|ilovaga", re.IGNORECASE)
CONTROL = re.compile(r"nazorat\s+qilish\s+(.+?)\s+zimmasiga\s+yuklansin", re.IGNORECASE)
DEFAULT_RULE = re.compile(r"muddati\s+alohida\s+ko'rsatilmagan\s+topshiriqlar", re.IGNORECASE)
RECIPIENT = "Qabul qiluvchi tashkilot"


@dataclass
class Task:
    source: str  # "jadval" | "abzats"
    number: str
    content: str
    executor: str
    deadline: Deadline = field(default_factory=Deadline)
    result: str = ""  # "Natija shakli" ustuni (bo'lsa)


@dataclass
class TaskResult:
    tasks: list[Task]
    control: str = ""  # "nazorat ... zimmasiga yuklansin" - nazorat qiluvchi


# ---------------------------------------------------------------- jadval
def _column(header: list[str], *keywords: str) -> int | None:
    for i, cell in enumerate(header):
        if any(k in cell.lower() for k in keywords):
            return i
    return None


def tasks_from_table(table: list[list[str]], doc_date: str) -> list[Task]:
    header, rows = table[0], table[1:]
    content = _column(header, "mazmun", "tadbir", "topshiriq")
    executor = _column(header, "ijrochi")
    deadline = _column(header, "muddat")
    result = _column(header, "natija")
    # Sarlavha OCR'da buzilsa - odatiy tartib: №, mazmun, ijrochi, ..., muddat
    content = 1 if content is None else content
    executor = 2 if executor is None else executor
    deadline = len(header) - 1 if deadline is None else deadline
    tasks = []
    for row in rows:
        if len(row) <= max(content, executor, deadline) or not row[content]:
            continue
        tasks.append(
            Task(
                source="jadval",
                number=row[0] if content != 0 else str(len(tasks) + 1),
                content=row[content],
                executor=row[executor],
                deadline=parse_deadline(row[deadline], doc_date),
                result=row[result] if result is not None else "",
            )
        )
    return tasks


# ---------------------------------------------------------------- abzats
def body_sentences(lines: list[str]) -> list[str]:
    """Hujjat tanasini gaplarga bo'ladi.

    Avval qator boshidagi raqam ("3. ...") bo'yicha bandlarga ajratiladi - bu nuqtadan
    ishonchliroq (OCR "tayyorlasin." ni "tayyorlasin," deb o'qishi mumkin). Keyin har bir
    band ichida gaplarga bo'linadi: band raqami faqat birinchi gapda qoladi.
    """
    blocks: list[str] = []
    for line in lines:
        if NUMBERED.match(line) or not blocks:
            blocks.append(line)
        else:
            blocks[-1] += " " + line
    sentences = []
    for block in blocks:
        block = re.sub(r"-\s+(?=[a-z])", "", block)  # qator oxiridagi so'z bo'linishi
        sentences += [s.strip() for s in SENTENCE_END.split(block) if s.strip()]
    return sentences


def _executor(sentence: str, is_letter: bool) -> str:
    main = EXECUTOR.search(sentence)
    via = VIA.search(sentence)
    name = main.group(1) if main else (via.group(1) if via else "")
    # "Markazning Tizim tahlili bo'limi" -> "Tizim tahlili bo'limi"
    name = re.sub(r"^\w+ning\s+", "", name)
    rest = sentence[main.end() :] if main else sentence
    co = CO_EXECUTOR.search(rest)
    if co and name:
        name = f"{name}, {co.group(1)}"
    if not name and is_letter:
        name = RECIPIENT  # "... taqdim etishingizni so'raymiz" - xat yo'llangan tashkilot
    return name[:1].upper() + name[1:]


def tasks_from_text(lines: list[str], doc_date: str, is_letter: bool) -> TaskResult:
    tasks, control, default = [], "", None
    for sentence in body_sentences(lines):
        if not DIRECTIVE.search(sentence):
            continue
        if m := CONTROL.search(sentence):
            control = m.group(1)
            continue
        number_match = NUMBERED.match(sentence)
        text = sentence[number_match.end() :] if number_match else sentence
        deadline = parse_deadline(text, doc_date, in_sentence=True)
        if DEFAULT_RULE.search(text):
            default = deadline
            continue
        if REFERS_TO_TABLE.search(text) and deadline.type == "yo'q":
            continue  # "quyidagi topshiriqlar belgilansin" - jadvalga kirish gapi
        tasks.append(
            Task(
                source="abzats",
                number=number_match.group(1) if number_match else "",
                content=text,
                executor=_executor(text, is_letter),
                deadline=deadline,
            )
        )
    # "Muddati alohida ko'rsatilmagan topshiriqlar bir oy muddatda ijro etilsin"
    if default:
        for t in tasks:
            if t.deadline.type == "yo'q":
                t.deadline = Deadline(default.type, default.raw + " (umumiy qoida)", default.date)
    return TaskResult(tasks, control[:1].upper() + control[1:])


def extract_tasks(pages: list[Page], doc_date: str, is_letter: bool) -> TaskResult:
    body = [line for page in pages for line in _body_lines(page.lines)]
    result = tasks_from_text(body, doc_date, is_letter)
    for page in pages:
        for table in page.tables:
            result.tasks.extend(tasks_from_table(table, doc_date))
    return result


def _body_lines(lines: list[str]) -> list[str]:
    """Rekvizit qatorlaridan keyin, imzodan oldin turgan qatorlar."""
    start = next((i + 1 for i, line in enumerate(lines) if "qaror qiladi" in line.lower()), None)
    if start is None:
        start = next(
            (i + 1 for i, line in enumerate(lines) if "markaziga" in line or "xatga" in line), 0
        )
    end = len(lines)
    for i in range(len(lines) - 1, start - 1, -1):
        if re.search(r"\b[A-ZА-Я][a-z]?\.\s?[A-ZА-Я][a-z']+\s*$", lines[i]):
            end = i
            break
    return lines[start:end]

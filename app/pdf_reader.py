"""PDF -> sahifalar: matn qatorlari va jadvallar (matnli va skaner PDF uchun bir xil shaklda).

Matnli PDF: pdfplumber (matn qatlami bor).
Skaner PDF: sahifa rasmga aylantiriladi -> OpenCV bilan jadval kataklari topiladi ->
Tesseract OCR (o'zbek tili) har bir katakni va qolgan matnni o'qiydi.
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import cv2
import numpy as np
import pdfplumber
import pymupdf
import pytesseract

from app.config import settings

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

APOSTROPHES = str.maketrans({c: "'" for c in "ʻʼ‘’`´"})
# Test hujjatlaridagi "Test uchun example" belgisi va pastki izoh (OCR'da buzilib ham chiqadi)
NOISE_LINE = re.compile(
    r"^\W*[TF]\w{2,3}\s+uch\w*\s+\S+\W*$|tizimini\s+sin|uchun\s+tuzil|shaxslar\s+s\w*rtli",
    re.IGNORECASE,
)


@dataclass
class Page:
    kind: str  # "text" | "scan"
    lines: list[str] = field(default_factory=list)  # jadvaldan tashqaridagi matn
    tables: list[list[list[str]]] = field(default_factory=list)  # jadval -> qator -> katak


def clean(text: str) -> str:
    text = text.translate(APOSTROPHES).replace("“", '"').replace("”", '"')
    return re.sub(r"[ \t]+", " ", text).strip()


def clean_cell(text: str) -> str:
    text = clean(text.replace("\n", " "))
    # OCR shovqini: yolg'iz turgan tinish belgilari ("." "—" "{" "|" ...)
    text = re.sub(r"(?<!\w)[.,;:{}()\[\]|—–_~^`\"]+(?!\w)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def keep_line(line: str) -> bool:
    if not line or NOISE_LINE.search(line):
        return False
    # Qisqa qator "Test uchun example" ga o'xshasa (OCR uni buzib o'qiydi) - tashlab yuboriladi
    short = len(line) <= 30
    return not (short and SequenceMatcher(None, line.lower(), "test uchun example").ratio() > 0.6)


# ---------------------------------------------------------------- matnli PDF
def read_text_page(page: pdfplumber.page.Page) -> Page:
    found = page.find_tables()
    tables = [[[clean_cell(c or "") for c in row] for row in t.extract()] for t in found]
    rest = page
    for t in found:
        rest = rest.outside_bbox(t.bbox)
    lines = [clean(x) for x in (rest.extract_text() or "").splitlines()]
    return Page("text", [x for x in lines if keep_line(x)], tables)


# ---------------------------------------------------------------- skaner PDF
def render(doc: pymupdf.Document, index: int, dpi: int = 300) -> np.ndarray:
    pix = doc[index].get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)


def line_masks(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Gorizontal va vertikal chiziqlar (jadval to'ri) maskalari."""
    height, width = gray.shape
    bw = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -10)
    horiz = cv2.morphologyEx(
        bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (width // 25, 1))
    )
    vert = cv2.morphologyEx(
        bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, height // 60))
    )
    return horiz, vert


def deskew(gray: np.ndarray) -> np.ndarray:
    """Uzun gorizontal chiziqlarning burchagi bo'yicha qiyshiq skanerni to'g'rilaydi."""
    horiz, _ = line_masks(gray)
    segments = cv2.HoughLinesP(
        horiz, 1, np.pi / 1800, 200, minLineLength=gray.shape[1] // 4, maxLineGap=20
    )
    if segments is None:
        return gray
    angles = [
        np.degrees(np.arctan2(y2 - y1, x2 - x1)) for x1, y1, x2, y2 in segments.reshape(-1, 4)
    ]
    angle = float(np.median([a for a in angles if abs(a) < 5] or [0.0]))
    if abs(angle) < 0.1:
        return gray
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)


def find_cells(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Jadval chiziqlarini topib, kataklarning (x, y, w, h) ro'yxatini qaytaradi."""
    height, width = gray.shape
    horiz, vert = line_masks(gray)
    # Uzilib qolgan chiziqlarni ulash (skanerda chiziq ba'zan xira chiqadi)
    horiz = cv2.dilate(horiz, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)))
    vert = cv2.dilate(vert, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)))
    grid = cv2.dilate(horiz | vert, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(~grid, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = [b for b in boxes if 40 < b[2] < width * 0.9 and 30 < b[3] < height * 0.5]

    # Ichida boshqa kataklar bor "katta" to'rtburchak - bu butun jadval ramkasi, katak emas
    def contains(a, b):
        return (
            a != b
            and a[0] <= b[0]
            and a[1] <= b[1]
            and a[0] + a[2] >= b[0] + b[2]
            and a[1] + a[3] >= b[1] + b[3]
        )

    return [a for a in boxes if not any(contains(a, b) for b in boxes)]


def group_rows(boxes: list[tuple[int, int, int, int]]) -> list[list[tuple]]:
    """Kataklarni qatorlarga ajratadi: katak markazi oldingi qator ichida bo'lsa - shu qator."""
    rows: list[list[tuple]] = []
    for box in sorted(boxes, key=lambda b: b[1] + b[3] / 2):
        center = box[1] + box[3] / 2
        if rows:
            first = rows[-1][0]
            if first[1] <= center <= first[1] + first[3]:
                rows[-1].append(box)
                continue
        rows.append([box])
    return [sorted(r) for r in rows]


def ocr(image: np.ndarray, psm: int = 6) -> str:
    return pytesseract.image_to_string(image, lang=settings.ocr_lang, config=f"--psm {psm}")


def read_scan_page(gray: np.ndarray) -> Page:
    gray = deskew(gray)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    rows = [r for r in group_rows(find_cells(gray)) if len(r) >= 2]
    if len(rows) < 2:  # bitta qatorli "jadval" - blankadagi chiziqlar, jadval emas
        rows = []
    cells = [b for r in rows for b in r]
    table = [
        [clean_cell(ocr(bw[y + 4 : y + h - 4, x + 4 : x + w - 4])) for x, y, w, h in row]
        for row in rows
    ]
    rest = bw.copy()
    if table:  # jadval hududini oq bilan bo'yab, qolgan matnni o'qiymiz
        x0 = min(b[0] for b in cells)
        y0 = min(b[1] for b in cells)
        x1 = max(b[0] + b[2] for b in cells)
        y1 = max(b[1] + b[3] for b in cells)
        cv2.rectangle(rest, (x0 - 10, y0 - 10), (x1 + 10, y1 + 10), 255, -1)
    lines = [clean(x) for x in ocr(rest, psm=4).splitlines()]
    return Page("scan", [x for x in lines if keep_line(x)], [table] if table else [])


# ---------------------------------------------------------------- umumiy
def read_pdf(path: str) -> list[Page]:
    pages: list[Page] = []
    doc = pymupdf.open(path)
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            if len((page.extract_text() or "").strip()) >= 30:
                pages.append(read_text_page(page))
            else:
                pages.append(read_scan_page(render(doc, i)))
    return pages

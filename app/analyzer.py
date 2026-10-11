"""Hujjatni to'liq tahlil qilish: PDF -> rekvizitlar + topshiriqlar (JSON uchun lug'at)."""

import re
from dataclasses import asdict
from pathlib import Path

from app.pdf_reader import read_pdf
from app.requisites import extract_requisites
from app.tasks import extract_tasks


def analyze(path: str | Path) -> dict:
    pages = read_pdf(str(path))
    first = pages[0].lines
    req = extract_requisites(first)
    # Qaror sarlavhasida "Q A R O R I" bo'ladi; bo'lmasa - xat
    is_decision = any(re.search(r"Q\s?A\s?R\s?O\s?R\s?I", line) for line in first[:8])
    result = extract_tasks(pages, req.date, is_letter=not is_decision)
    return {
        "file": Path(path).name,
        "kind": pages[0].kind,
        "doc_type": "qaror" if is_decision else "xat",
        "pages": len(pages),
        "requisites": asdict(req),
        "control": result.control,
        "tasks": [asdict(t) for t in result.tasks],
    }

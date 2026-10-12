"""Veb-interfeys: PDF yuklash -> "Tahlil qilish" -> rekvizitlar va topshiriqlar.

Ishlatish:  uvicorn app.web:app --port 8000   ->  http://localhost:8000
Hujjat hech qayerga yuborilmaydi: vaqtinchalik faylga yoziladi, tahlil qilinadi va o'chiriladi.
"""

import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.analyzer import analyze

MAX_SIZE = 20 * 1024 * 1024  # 20 MB
INDEX = Path(__file__).parent / "static" / "index.html"

app = FastAPI(title="Hujjat tahlili")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX.read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze_pdf(file: UploadFile) -> dict:
    data = file.file.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "Fayl hajmi 20 MB dan oshmasligi kerak")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "Faqat PDF fayl qabul qilinadi")

    start = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "document.pdf"
        path.write_bytes(data)
        result = analyze(path)
    result["file"] = file.filename
    result["seconds"] = round(time.time() - start, 1)
    return result

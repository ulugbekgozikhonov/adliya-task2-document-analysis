# Hujjatlarni tahlil qilish: rekvizitlar va topshiriqlar

PDF hujjatdan (matnli yoki skaner qilingan) avtomatik ajratiladi:

- **rekvizitlar:** jo'natuvchi tashkilot, hujjat raqami, sana, imzolagan shaxs;
- **topshiriqlar:** har biri mazmuni, ijrochisi va muddati bilan (abzatsda, jadvalda yoki ilovada).

Hammasi lokal ishlaydi: hujjat hech qanday tashqi xizmatga yuborilmaydi, veb-sahifa ham
tashqi kutubxona va CDN'siz.

| Qism              | Texnologiya                                                    |
| ----------------- | -------------------------------------------------------------- |
| Matnli PDF        | pdfplumber (matn va jadvallar)                                 |
| Skaner PDF        | PyMuPDF (rasmga aylantirish) + OpenCV + Tesseract OCR (o'zbek) |
| Ma'lumot ajratish | Qoidalar (regex + hujjat shabloni)                             |
| Veb               | FastAPI + bitta HTML sahifa                                    |
| Ishga tushirish   | Docker Compose                                                 |

**Natija** (berilgan 6 ta hujjat, har biri matnli va skaner nusxada):

| PDF turi   | Rekvizitlar | Topshiriqlar topildi | Ijrochi | Muddat |
| ---------- | ----------: | -------------------: | ------: | -----: |
| Matnli PDF |      100.0% |               100.0% |  100.0% | 100.0% |
| Skaner PDF |      100.0% |                97.4% |  100.0% | 100.0% |

Bu raqamlarni qanday tushunish kerakligi: [Aniqlik](#aniqlik) bo'limida.

---

## Mundarija

1. [Ishga tushirish](#ishga-tushirish)
2. [Qanday ishlaydi](#qanday-ishlaydi)
3. [Nega aynan shu usul](#nega-aynan-shu-usul)
4. [Aniqlik](#aniqlik)
5. [Qayerda xato qiladi](#qayerda-xato-qiladi)
6. [Keyingi qadamlar](#keyingi-qadamlar)
7. [API](#api)
8. [Loyiha tuzilmasi](#loyiha-tuzilmasi)

---

## Ishga tushirish

### Docker bilan (tavsiya)

```bash
docker compose up -d --build
```

Brauzerda: **http://localhost:8001** → PDF tanlang → **Tahlil qilish**.

Tesseract va o'zbek tili modeli image ichiga o'rnatiladi, alohida o'rnatish shart emas.

### Docker'siz

1. Tesseract OCR'ni o'rnating, o'zbek tili (`uzb`) bilan. Windows: https://github.com/UB-Mannheim/tesseract/wiki
2. Python muhit:

```bash
python -m venv .venv
.venv\Scripts\activate             # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.web:app --port 8001
```

Tesseract boshqa joyga o'rnatilgan bo'lsa: `.env` faylida `TESSERACT_CMD=...`.

### Berilgan hujjatlar bo'yicha natija va aniqlik

```bash
python -m scripts.extract     # data/ dagi 12 ta PDF -> results/*.json
python -m scripts.evaluate    # results/ ni to'g'ri javoblar bilan solishtiradi -> reports/eval_report.md
```

---

## Qanday ishlaydi

```
PDF
 │
 ├── matn qatlami bor (>= 30 belgi)  →  pdfplumber: matn qatorlari + jadvallar
 │
 └── matn yo'q (skaner)              →  sahifa → rasm (300 DPI)
                                        → qiyshiqlikni to'g'rilash (Hough chiziqlari)
                                        → jadval chiziqlarini topish (OpenCV morfologiya)
                                        → har bir katakni alohida OCR (Tesseract, uzb)
                                        → qolgan matnni OCR
 │
 ▼
Bir xil tuzilma:  sahifa → { matn qatorlari, jadvallar }
 │
 ├── Rekvizitlar (app/requisites.py)
 │     jo'natuvchi - eng tepadagi katta harfli qatorlar ("...KENGASHINING" → "...kengashi")
 │     raqam       - "№" dan keyin (OCR uni "No", "Ne", "Ҳе" deb o'qishi hisobga olingan)
 │     sana        - raqam yonida: "08.09.2026" yoki "2026-yil 10-fevral"
 │     imzolagan   - pastda: lavozim + "A. Familiya" ("Ijrochi:" qatori emas)
 │
 ├── Topshiriqlar (app/tasks.py)
 │     jadval  - ustunlar sarlavha bo'yicha: mazmun / ijrochi / muddat / natija shakli
 │     abzats  - band ("3. ...") yoki gap buyruq fe'li bilan tugasa (-sin, -ilsin, so'raymiz)
 │               ijrochi: gap boshidagi tashkiliy birlik (... bo'limi, ... boshqarmasi)
 │
 └── Muddat (app/deadlines.py)  →  tur + sana (hisoblab bo'lsa)
```

Matnli va skaner PDF bir xil tuzilmaga keltiriladi, shuning uchun keyingi bosqichlar PDF
turini bilmaydi va ikkalasi uchun bir xil ishlaydi.

### Muddat turlari

| Tur          | Misol                                            | Natija                                |
| ------------ | ------------------------------------------------ | ------------------------------------- |
| `sana`       | "2026-yil 20-sentabrga qadar", "18.09.2026"      | 2026-09-20                            |
| `nisbiy`     | "o'n kun muddatda", "uch ish kuni ichida"        | hujjat sanasidan hisoblanadi          |
| `shartli`    | "prototip tayyor bo'lgandan so'ng 15 kun ichida" | matn holicha (sanani bilib bo'lmaydi) |
| `davriy`     | "har oyda", "har oyning 5-sanasiga qadar"        | matn holicha                          |
| `boshlanish` | "2026-yil 15-martdan boshlab"                    | 2026-03-15                            |
| `doimiy`     | "doimiy"                                         | -                                     |
| `yo'q`       | muddat ko'rsatilmagan                            | -                                     |

"Uch **ish** kuni" faqat dushanba-jumani sanaydi. Qarordagi umumiy qoida ("muddati alohida
ko'rsatilmagan topshiriqlar bir oy muddatda ijro etilsin") muddati yo'q topshiriqlarga
avtomatik qo'llanadi.

### Kelishuvlar (nima topshiriq hisoblanadi)

- "Nazorat qilish ... zimmasiga yuklansin" - topshiriq emas, alohida **nazorat** maydoni.
- "Quyidagi topshiriqlar belgilansin" kabi jadvalga kirish gapi - topshiriq emas
  (o'z muddati bo'lsa - topshiriq).
- Xatda ijrochi ko'rsatilmagan bo'lsa ("... taqdim etishingizni so'raymiz") -
  "Qabul qiluvchi tashkilot".
- Gap ichidagi sana faqat "...gacha / qadar" bilan kelsa muddat hisoblanadi
  ("2026-yil 2-sentabrda imzolangan memorandum" dagi sana muddat emas).

---

## Nega aynan shu usul

**Bulut xizmatlari mumkin emas** (topshiriq sharti), shuning uchun OCR ham, tahlil ham lokal.

**Tesseract OCR.** Bepul, oflayn ishlaydi, o'zbek (lotin) modeli bor. Sinovda skanerdagi
matnni deyarli xatosiz o'qidi. Jadvallarda butun sahifani o'qish ustunlarni aralashtirib
yuboradi, shuning uchun avval OpenCV bilan jadval kataklari topiladi va har bir katak
alohida o'qiladi.

**Qiyshiqlikni to'g'rilash.** Bitta skaner ~1° qiyshiq tushgan edi: bir qatordagi kataklar
turli balandlikda qolib, jadvaldan 2 ta ustun yo'qolgan. To'g'rilangandan keyin jadval to'liq
o'qildi va OCR xatolari ham kamaydi ("so'ng" → "50719" xatosi yo'qoldi).

**Ma'lumot ajratish - qoidalar, LLM emas.** Rasmiy hujjatlarning shabloni qat'iy: raqam "№"
dan keyin, imzo pastda, topshiriq buyruq fe'li bilan tugaydi. Qoidalar:

- tez ishlaydi (matnli PDF ~0.1 s) va GPU talab qilmaydi;
- natija har safar bir xil va har bir qarorni tushuntirib berish mumkin;
- "to'qib chiqarish" (gallyutsinatsiya) xavfi yo'q.

Kamchiligi - qoidaga tushmaydigan yangi turdagi hujjatda xato qiladi (pastda). Shuning uchun
abzatsdagi murakkab topshiriqlar uchun lokal LLM keyingi qadam sifatida ko'rilgan.

---

## Aniqlik

To'g'ri javoblar hujjatlarni o'qib, qo'lda yozilgan: `data/ground_truth.json` (6 ta hujjat,
39 ta topshiriq). Skaner nusxasining mazmuni matnli nusxa bilan bir xil, shuning uchun bitta
to'g'ri javob ikkala nusxa uchun ishlatiladi. To'liq hisobot: [reports/eval_report.md](reports/eval_report.md).

| PDF turi   | Rekvizitlar | Recall | Precision | Ijrochi | Muddat | Nazorat |
| ---------- | ----------: | -----: | --------: | ------: | -----: | ------: |
| Matnli PDF |      100.0% | 100.0% |    100.0% |  100.0% | 100.0% |  100.0% |
| Skaner PDF |      100.0% |  97.4% |     97.4% |  100.0% | 100.0% |  100.0% |

- **Recall** - hujjatdagi topshiriqlardan nechtasi topildi; **precision** - topilganlardan
  nechtasi haqiqiy topshiriq.
- Ijrochi va muddat to'g'ri topilgan topshiriqlar ichida hisoblangan. Muddat uchun turi
  ham, sanasi ham mos kelishi kerak.

**Muhim:** qoidalar shu 6 ta hujjatni ko'rib yozilgan va shu hujjatlarda tekshirilgan.
100% - umumlashtirish kafolati emas. Boshqa tashkilotlarning, boshqacha tuzilgan
hujjatlarida natija pastroq bo'lishi kutiladi. Ishonchli baho uchun mustaqil hujjatlar
to'plami kerak.

**Tezlik** (CPU, GPU'siz): matnli PDF ~0.1 s; skaner 2-12 s (OCR har bir katakni alohida o'qiydi).

---

## Qayerda xato qiladi

**Sinovda kuzatilgan:**

| Holat                                       | Misol                                        | Ta'siri                                                         |
| ------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------- |
| OCR so'zni tanib bo'lmas darajada buzadi    | "Ro'yxatga" → `Ко"уха ва` (NAMUNA_1, skaner) | Topshiriq topiladi, lekin ijrochi buzuq                         |
| OCR tinish belgisini adashtiradi            | "tayyorlasin." → "tayyorlasin,"              | Hal qilingan: bandlar qator boshidagi raqam bo'yicha ajratiladi |
| OCR "№" ni buzadi                           | `No`, `Ne`, `Ҳе`, `Ме`                       | Hal qilingan: barcha variantlar hisobga olingan                 |
| OCR lotin harfini kirill bilan almashtiradi | `М. Tursunov` (kirill М)                     | Hal qilingan: o'xshash kirill harflari lotinga o'giriladi       |
| Skaner qiyshiq                              | ~1° burilish                                 | Hal qilingan: avtomatik to'g'rilash                             |

**Kutiladigan cheklovlar:**

- Ijrochi gap **boshida** bo'lishi va tashkiliy birlik so'zi bilan tugashi kerak
  ("... bo'limi", "... boshqarmasi"). "Topshiriq ... tomonidan bajarilsin" kabi boshqa
  tuzilishlarda topilmaydi.
- Jadval chiziqlari bo'lmasa (ustunlar faqat bo'sh joy bilan ajratilgan) skanerdagi jadval
  topilmaydi.
- Bir necha sahifaga cho'zilgan jadval va qo'lda yozilgan matn sinab ko'rilmagan.
- Shartli va davriy muddatlar sanaga aylantirilmaydi - matn holicha ko'rsatiladi.
- "Test uchun example" belgisini olib tashlash filtri faqat shu test hujjatlariga xos.
- Qaror va xat formatlari uchun yozilgan; buyruq, bayonnoma kabi boshqa hujjat turlari
  sinalmagan.

---

## Keyingi qadamlar

1. **Lokal LLM** (masalan Qwen2.5, Ollama orqali) - qoidaga tushmagan abzatslar uchun:
   modeldan topshiriqni JSON ko'rinishida ajratish so'raladi, natijasi esa asl matn bilan
   tekshiriladi (ijrochi va muddat matnda haqiqatan bormi).
2. **Mustaqil test to'plami** - boshqa tashkilotlarning 30-50 ta hujjati, aniqlikni
   umumlashtirish nuqtai nazaridan o'lchash uchun.
3. **Ishonch darajasi** - OCR ishonchi past yoki qoida aniq ishlamagan maydonlarni
   foydalanuvchiga belgilab ko'rsatish (qo'lda tekshirish uchun).
4. **Murakkab jadvallar** - sahifadan sahifaga o'tuvchi jadvallar va chiziqsiz jadvallar.

---

## API

| Metod  | Manzil         | Tavsif                          |
| ------ | -------------- | ------------------------------- |
| `GET`  | `/`            | Veb-sahifa                      |
| `POST` | `/api/analyze` | PDF fayl (`file`) → JSON natija |
| `GET`  | `/health`      | Holat tekshiruvi                |

Fayl hajmi 20 MB gacha; faqat PDF qabul qilinadi (`%PDF` belgisi tekshiriladi). Yuklangan
fayl vaqtinchalik papkaga yoziladi va tahlildan keyin o'chiriladi.

Javob namunasi (qisqartirilgan):

```json
{
  "file": "xat_1_abzatsdagi_topshiriqlar_skaner.pdf",
  "kind": "scan",
  "doc_type": "xat",
  "requisites": {
    "sender": "Raqamli huquqiy xizmatlar agentligi",
    "number": "03-12/1456",
    "date": "2026-09-08",
    "signer": "Sh. Qodirov",
    "signer_position": "Direktor o'rinbosari"
  },
  "tasks": [
    {
      "source": "abzats",
      "number": "3",
      "executor": "Axborot xavfsizligi bo'limi, Sun'iy intellekt laboratoriyasi",
      "deadline": {"type": "nisbiy", "raw": "o'n kun muddatda", "date": "2026-09-18"}
    }
  ]
}
```

---

## Loyiha tuzilmasi

```
app/
├── config.py        sozlamalar (Tesseract yo'li, OCR tili)
├── pdf_reader.py    PDF → sahifalar (matnli: pdfplumber; skaner: OpenCV + Tesseract)
├── dates.py         o'zbekcha sanalar → ISO
├── requisites.py    rekvizitlar
├── deadlines.py     muddat turi va sanasi
├── tasks.py         topshiriqlar (jadval va abzats)
├── analyzer.py      hammasini birlashtiradi
├── web.py           FastAPI
└── static/index.html  veb-sahifa
scripts/
├── extract.py       data/ → results/*.json
├── evaluate.py      results/ vs ground_truth → reports/eval_report.md
└── dump.py          bitta PDF'ning o'qilgan matni va jadvallarini ko'rish
data/
├── matnli/, skaner/ berilgan hujjatlar
└── ground_truth.json  to'g'ri javoblar
results/             berilgan 12 ta hujjat bo'yicha natijalar (JSON)
reports/             aniqlik hisoboti
```

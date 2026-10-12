"""Tahlil natijalarini qo'lda yozilgan to'g'ri javoblar bilan solishtirish.

To'g'ri javoblar: data/ground_truth.json (6 ta hujjat). Skaner nusxasining mazmuni matnli
nusxa bilan bir xil, shuning uchun bitta to'g'ri javob ikkala nusxa uchun ishlatiladi.
Natija: reports/eval_report.md - matnli va skaner PDF uchun alohida.
Ishlatish:  python -m scripts.evaluate   (avval: python -m scripts.extract)
"""

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

TRUTH = Path("data/ground_truth.json")
RESULTS = Path("results")
REPORT = Path("reports/eval_report.md")
FIELDS = ["sender", "number", "date", "signer"]


def norm(text: str) -> str:
    """Taqqoslash uchun: kichik harf, tinish belgilarisiz, bo'sh joylar bitta."""
    return " ".join(re.sub(r"[^\w' ]+", " ", text.lower()).split())


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def same_executor(expected: str, got: str) -> bool:
    """Bir nechta ijrochi tartibidan qat'i nazar; OCR'ning mayda xatolariga chidamli (>= 0.85)."""
    a = sorted(norm(x) for x in expected.split(","))
    b = sorted(norm(x) for x in got.split(","))
    return len(a) == len(b) and all(similar(x, y) >= 0.85 for x, y in zip(a, b, strict=True))


def match_tasks(expected: list[dict], got: list[dict]) -> list[tuple[dict, dict | None]]:
    """Har bir kutilgan topshiriqqa mazmun boshlanishi eng o'xshash topshiriqni juftlaydi."""
    free = list(got)
    pairs = []
    for exp in expected:
        key = norm(exp["content"])
        best, best_score = None, 0.0
        for task in free:
            score = SequenceMatcher(None, key, norm(task["content"])[: len(key)]).ratio()
            if score > best_score:
                best, best_score = task, score
        if best is not None and best_score >= 0.8:
            free.remove(best)
            pairs.append((exp, best))
        else:
            pairs.append((exp, None))
    return pairs


def pct(part: int, total: int) -> str:
    return f"{part / total:.1%}" if total else "-"


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]

    def line(cells: list[str]) -> str:
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths, strict=True)) + " |"

    return [line(headers), "| " + " | ".join("-" * w for w in widths) + " |", *map(line, rows)]


def main() -> None:
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    stats: dict[str, dict[str, int]] = {"text": defaultdict(int), "scan": defaultdict(int)}
    errors: list[list[str]] = []

    for path in sorted(RESULTS.glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        gt = truth.get(path.stem.removesuffix("_skaner"))
        if gt is None:
            continue
        s = stats[result["kind"]]
        s["docs"] += 1

        for field in FIELDS:  # rekvizitlar
            ok = similar(gt["requisites"][field], result["requisites"][field]) >= 0.9
            s["req_ok"] += ok
            s["req_total"] += 1
            if not ok:
                expected, got = gt["requisites"][field], result["requisites"][field]
                errors.append([path.stem, f"rekvizit: {field}", expected, got])

        s["control_ok"] += similar(gt["control"], result["control"]) >= 0.9 or (
            not gt["control"] and not result["control"]
        )

        pairs = match_tasks(gt["tasks"], result["tasks"])
        s["expected"] += len(gt["tasks"])
        s["predicted"] += len(result["tasks"])
        for exp, got in pairs:
            if got is None:
                errors.append([path.stem, "topshiriq topilmadi", exp["content"], "-"])
                continue
            s["matched"] += 1
            if same_executor(exp["executor"], got["executor"]):
                s["executor_ok"] += 1
            else:
                errors.append([path.stem, "ijrochi", exp["executor"], got["executor"]])
            d = got["deadline"]
            if d["type"] == exp["deadline_type"] and d["date"] == exp["deadline_date"]:
                s["deadline_ok"] += 1
            else:
                expected = f"{exp['deadline_type']} {exp['deadline_date']}"
                errors.append([path.stem, "muddat", expected, f"{d['type']} {d['date']}"])

    rows = []
    for kind, label in (("text", "Matnli PDF"), ("scan", "Skaner PDF")):
        s = stats[kind]
        rows.append(
            [
                label,
                str(s["docs"]),
                pct(s["req_ok"], s["req_total"]),
                pct(s["matched"], s["expected"]),
                pct(s["matched"], s["predicted"]),
                pct(s["executor_ok"], s["matched"]),
                pct(s["deadline_ok"], s["matched"]),
                pct(s["control_ok"], s["docs"]),
            ]
        )

    headers = ["PDF turi", "Hujjat", "Rekvizitlar", "Topshiriq (recall)",
               "Topshiriq (precision)", "Ijrochi", "Muddat", "Nazorat"]  # fmt: skip
    md = [
        "# Hujjat tahlili: aniqlik hisoboti",
        "",
        "`python -m scripts.evaluate` tomonidan yaratilgan. To'g'ri javoblar: `data/ground_truth.json`.",
        "",
        "## Umumiy natija",
        "",
        *md_table(headers, rows),
        "",
        "- **Rekvizitlar**: jo'natuvchi, raqam, sana, imzolagan - to'g'ri topilganlar ulushi.",
        "- **Recall**: hujjatdagi topshiriqlardan nechtasi topildi.",
        "- **Precision**: topilganlardan nechtasi haqiqiy topshiriq.",
        "- **Ijrochi / Muddat**: to'g'ri topilgan topshiriqlar ichida ijrochi / muddat to'g'ri.",
        "",
        "## Xatolar",
        "",
        *(
            md_table(["Hujjat", "Nima", "Kutilgan", "Topildi"], errors)
            if errors
            else ["Xato yo'q."]
        ),
    ]
    text = "\n".join(md) + "\n"
    print(text)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

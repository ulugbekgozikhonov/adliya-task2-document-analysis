"""Hujjat(lar)ni tahlil qilib, natijani results/ papkasiga JSON qilib yozadi.

Ishlatish:
  python -m scripts.extract                      # data/ dagi barcha PDF
  python -m scripts.extract data/matnli/xat_1_abzatsdagi_topshiriqlar.pdf
"""

import json
import sys
import time
from pathlib import Path

from app.analyzer import analyze

OUT = Path("results")


def main() -> None:
    files = [Path(p) for p in sys.argv[1:]] or sorted(Path("data").rglob("*.pdf"))
    OUT.mkdir(exist_ok=True)
    for path in files:
        start = time.time()
        result = analyze(path)
        (OUT / f"{path.stem}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        req = result["requisites"]
        print(
            f"{path.name:45} {time.time() - start:5.1f}s  {result['doc_type']:5} "
            f"№{req['number']:<11} {req['date']}  topshiriqlar: {len(result['tasks'])}"
        )


if __name__ == "__main__":
    main()

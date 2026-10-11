"""PDF o'quvchi natijasini ko'rish.

Ishlatish:  python -m scripts.dump data/skaner/xat_2_jadvaldagi_topshiriqlar_skaner.pdf
"""

import sys
import time

from app.requisites import extract_requisites
from app.pdf_reader import read_pdf

def main() -> None:
    start = time.time()
    pages = read_pdf(sys.argv[1])
    print(f"{len(pages)} sahifa, {time.time() - start:.1f} s")
    req = extract_requisites(pages[0].lines)
    print(f"\nREKVIZITLAR: {req}")
    for i, page in enumerate(pages, 1):
        print(f"\n===== {i}-sahifa [{page.kind}]: {len(page.lines)} qator, {len(page.tables)} jadval")
        for line in page.lines:
            print("  ", line)
        for table in page.tables:
            print("   --- jadval:")
            for row in table:
                print("     ", row)


if __name__ == "__main__":
    main()

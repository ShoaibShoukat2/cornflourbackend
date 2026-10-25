from pathlib import Path
import re

text = Path(r"C:\Users\Shoaib\AppData\Local\Temp\instova.js").read_text(encoding="utf-8", errors="ignore")
needles = [
    "No Active",
    "Active Plan",
    "Direct",
    "Indirect",
    "referral",
    "has_package",
    "total_team",
    "Level",
    "baseURL",
    "pythonanywhere",
    "/api",
]
for needle in needles:
    indexes = [m.start() for m in re.finditer(re.escape(needle), text)]
    print(f"\n=== {needle} count={len(indexes)} ===")
    for start in indexes[:8]:
        snippet = text[max(0, start - 80): start + 140].replace("\n", " ")
        print(snippet)
        print("---")

from pathlib import Path
import re

text = Path(r"C:\Users\Shoaib\AppData\Local\Temp\instova.js").read_text(encoding="utf-8", errors="ignore")
for needle in ["No plan", "no plan", "Active", "package_label", "Buy plan", "Your plan", "Plan ", "profile"]:
    print("\n====", needle, text.lower().count(needle.lower()))
    for m in re.finditer(re.escape(needle), text, re.I):
        snippet = text[max(0, m.start() - 100): m.start() + 180].replace("\n", " ")
        if "unstable" in snippet or "priorityLevel" in snippet:
            continue
        print(snippet)
        print("---")

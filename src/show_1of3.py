import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
s = json.load((REPO / "results/audit_sample.json").open(encoding="utf-8"))
for it in s:
    if it["n_models"] != 1:
        continue
    print(f"[1/3] {it['party']}")
    print("  >", it["text"][:240])
    print("  VIDEO:", it["transcript"][:170])
    print()

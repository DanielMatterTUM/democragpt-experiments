import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
L = json.load((REPO / "results/audit_linked.json").open(encoding="utf-8"))
for r in L:
    print(f"[{r['n_models']}/3] {r['verdict']:4s} {r['label']:26s}")
    print(f"   TEXT: {r['text'][:120]}")
    print(f"   WHY : {r['why'][:110]}")

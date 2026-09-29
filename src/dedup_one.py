"""Dedup a request log: keep the last successful record per
(model, codebook, condition, uid). Repair runs append duplicates."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
name = sys.argv[1] if len(sys.argv) > 1 else "requests_full"
p = REPO / "results" / f"{name}.jsonl"
recs = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
print("records in:", len(recs))

best = {}
for r in recs:
    k = (r.get("model"), r.get("codebook"), r.get("condition"), r.get("uid"))
    if k not in best or (r.get("label") is not None and best[k].get("label") is None):
        best[k] = r

out = [best[k] for k in sorted(best, key=lambda k: tuple(str(x) for x in k))]
with p.open("w", encoding="utf-8") as fh:
    for r in out:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"records out: {len(out)} | null labels: "
      f"{sum(1 for r in out if r.get('label') is None)}")

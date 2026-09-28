import json
from collections import Counter
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "results/requests_full.jsonl"
rows = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
bad = [r for r in rows if r.get("label") is None]
print("total", len(rows), "| null labels", len(bad))
for r in bad:
    print(" ", r["model"], "cb" + r["codebook"], "cond" + r["condition"],
          r["uid"], "| finish:", r.get("native_finish_reason"),
          "| err:", (r.get("error") or "")[:160])
    print("    raw:", repr(r.get("raw_content"))[:200])

"""Deduplicate results/requests_full.jsonl: the repair run appended a second
record for cells that had previously failed. Keep the LAST successful record
per (model, codebook, condition, uid) and drop superseded failures.
"""
import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "results/requests_full.jsonl"
recs = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
print("records in:", len(recs))

best: dict[tuple, dict] = {}
for r in recs:
    k = (r.get("model"), r.get("codebook"), r.get("condition"), r.get("uid"))
    ok = r.get("label") is not None
    if k not in best or (ok and best[k].get("label") is None):
        best[k] = r

out = [best[k] for k in sorted(best, key=lambda k: tuple(str(x) for x in k))]
q = p.with_suffix(".dedup.jsonl")
with q.open("w", encoding="utf-8") as fh:
    for r in out:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("records out:", len(out), "->", q.name)
print("null labels remaining:", sum(1 for r in out if r.get("label") is None))

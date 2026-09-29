"""Cost model for the large comment-only Jev run, from measured per-call costs."""
import json
from collections import defaultdict
from pathlib import Path

RES = Path(__file__).resolve().parents[1] / "results"
r = [json.loads(l) for l in (RES / "requests_full.jsonl").open(encoding="utf-8")]

per = defaultdict(list)
for x in r:
    if x["model"] != "jev-1.13" or x.get("was_cached"):
        continue
    if x.get("cost_usd"):
        per[(x["codebook"], x["condition"])].append(x["cost_usd"])

print("measured Jev cost per call (live calls only):")
unit = {}
for k, v in sorted(per.items()):
    m = sum(v) / len(v)
    unit[k] = m
    print(f"  codebook {k[0]}, condition {k[1]}: n={len(v):4d}  "
          f"${m*1000:.4f}/1k  (${m:.6f}/call)")

budget = 0.2978
print(f"\nremaining budget: ${budget:.4f}")
for cb in ("A", "B"):
    u = unit.get((cb, "B"), 0)
    n = int(budget * 0.98 / u) if u else 0
    print(f"  codebook {cb} on condition B alone: {n:,} comments "
          f"(${n*u:.4f})")

both = unit.get(("A", "B"), 0) + unit.get(("B", "B"), 0)
n = int(budget * 0.95 / both) if both else 0
print(f"  both codebooks on condition B:     {n:,} comments (${n*both:.4f})")
print(f"\n  -> target sample: {min(n, 10000):,} comments, both codebooks, condition B")

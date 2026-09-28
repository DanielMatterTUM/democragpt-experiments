"""Critical audit of the positive cases.

Two questions the raw example list does not answer:
  1. Do the flags survive a human reading of the comment in context?
  2. Where does the instrument over- or under-call?

Prints positives stratified by how many models agreed (3/2/1), plus the full
list of single-model-only flags -- those are where false positives hide.
"""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

rows = {json.loads(l)["uid"]: json.loads(l)
        for l in (REPO / "data/sample_comments.jsonl").open(encoding="utf-8")}
preds = [json.loads(l) for l in (RES / "predictions_full.jsonl").open(encoding="utf-8")]

tab = defaultdict(dict)
for p in preds:
    if p["label"] is None:
        continue
    tab[(p["model"], p["codebook"], p["condition"], p["uid"])] = p["label"]
models = sorted({p["model"] for p in preds})

pool = defaultdict(set)
for (m, cb, cond, uid), lab in tab.items():
    if cb == "A" and cond == "A" and lab == "ja":
        pool[uid].add(m)

# manual verdicts, filled in after reading; kept out of the code so the tool
# stays a neutral reader.
VERDICT_FILE = REPO / "results/example_verdicts.json"

print(f"distinct positives (cond A): {len(pool)}")
for k in (3, 2, 1):
    print(f"  agreed by {k} model(s): {sum(1 for v in pool.values() if len(v)==k)}")
print()

rng = random.Random(11)
groups = {
    "3/3 (Konsens)": sorted([u for u, v in pool.items() if len(v) == 3]),
    "2/3": sorted([u for u, v in pool.items() if len(v) == 2]),
    "1/3 (nur ein Modell)": sorted([u for u, v in pool.items() if len(v) == 1]),
}

for name, uids in groups.items():
    print("=" * 78)
    print(f"### {name}  —  {len(uids)} Kommentare")
    print("=" * 78)
    for uid in uids:
        r = rows[uid]
        b = Counter(tab[(m, "B", "A", uid)] for m in models
                    if tab.get((m, "B", "A", uid)) not in (None, "keine_reaktanz"))
        print(f"\n  ({r['party']}, {r['comment_chars']} Z.)  B: {dict(b) or '-'}")
        print(f"  > {r['comment_text']}")
        print(f"  VIDEO: {r['transcript'][:230]}")
    print()

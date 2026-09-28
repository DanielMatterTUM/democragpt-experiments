"""Inspect the comments coded as reactance — a critical read, not a validation.

Purpose: look at what the models actually flagged, decide per example whether it
really is reactance in the Brehm/PRPM sense, and report the error profile.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

LAB_B = {"konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik", "keine_reaktanz"}

rows = {json.loads(l)["uid"]: json.loads(l)
        for l in (REPO / "data/sample_comments.jsonl").open(encoding="utf-8")}
preds = [json.loads(l) for l in (RES / "predictions_full.jsonl").open(encoding="utf-8")]

# (model, uid) -> {cb: label} for condition A
tab = defaultdict(dict)
for p in preds:
    if p["condition"] != "A" or p["label"] is None:
        continue
    tab[(p["model"], p["uid"])][p["codebook"]] = p["label"]

models = sorted({p["model"] for p in preds})

# --- positive cases, pooled over models, de-duplicated by uid -------------
pool = defaultdict(set)          # uid -> set of models that flagged it as ja
for (m, uid), d in tab.items():
    if d.get("A") == "ja":
        pool[uid].add(m)

freq = Counter(len(v) for v in pool.values())
print(f"=== Codebook A positives (condition A) ===")
print(f"total flagged (model-comments): {sum(len(v) for v in pool.values())}")
print(f"distinct comments flagged by >=1 model: {len(pool)}")
print(f"flagged by all 3 models: {sum(1 for v in pool.values() if len(v) == 3)}")
print(f"flagged by 2 models: {sum(1 for v in pool.values() if len(v) == 2)}")
print(f"flagged by exactly 1 model: {sum(1 for v in pool.values() if len(v) == 1)}")
print()

ranked = sorted(pool, key=lambda u: (-len(pool[u]), u))
pick = "all" if (len(sys.argv) < 2 or sys.argv[1] == "all") else int(sys.argv[1])
show = ranked if pick == "all" else ranked[:pick]

for uid in show:
    r = rows[uid]
    who = ",".join(sorted(pool[uid]))
    bl = {m: tab[(m, uid)].get("B") for m in models}
    bt = [v for v in bl.values() if v and v != "keine_reaktanz"]
    bset = ",".join(sorted(set(bt))) if bt else "-"
    print(f"[{who}] party={r['party']} chars={r['comment_chars']}")
    print(f"   {r['comment_text']}")
    print(f"   B-labels: {bset}")
    print(f"   TRANSCRIPT: {r['transcript'][:300]}")
    print()

print("=== B-label distribution over comments flagged 'ja' by A (cond A) ===")
c = Counter()
for uid in pool:
    for m in models:
        lb = tab[(m, uid)].get("B")
        if lb and lb != "keine_reaktanz":
            c[lb] += 1
print(" ", c.most_common())

print("\n=== discordance: B names a type but A says nein (cond A) ===")
discord = []
for (m, uid), d in tab.items():
    if d.get("A") == "nein" and d.get("B") not in (None, "keine_reaktanz"):
        discord.append((m, uid, d["B"]))
print(f"count: {len(discord)}")
bylabel = Counter(b for _, _, b in discord)
print(" ", bylabel.most_common())
seen = set()
n = 0
for m, uid, b in discord:
    if uid in seen or n >= 10:
        continue
    seen.add(uid)
    n += 1
    print(f"  [{m} -> {b}] {rows[uid]['comment_text'][:190]}")

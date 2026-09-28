"""Link manual verdicts to real uids and compute precision by consensus stratum.

The verdict list in audit_verdicts.json is positional: entry i of stratum k
corresponds to entry i of audit_sample.json for that stratum (both files were
produced by the same deterministic sampling).
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

sample = json.load((RES / "audit_sample.json").open(encoding="utf-8"))
verd = json.load((RES / "audit_verdicts.json").open(encoding="utf-8"))

by_stratum = {}
for it in sample:
    by_stratum.setdefault(str(it["n_models"]), []).append(it)

linked, mism = [], 0
for k, entries in verd["strata"].items():
    pool = by_stratum[k]
    for i, v in enumerate(entries):
        if i >= len(pool):
            break
        item = pool[i]
        rec = {"uid": item["uid"], "n_models": int(k), "party": item["party"],
               "text": item["text"], "verdict": v["verdict"],
               "label": v.get("label", "-"), "why": v["why"]}
        linked.append(rec)
        # sanity: does the recorded 'why' describe this comment?
        head = item["text"][:40].lower()
        if v["why"].split(".")[0][:20].lower() not in head and \
           not any(w in head for w in v["why"].lower().split()[:3]):
            mism += 1

(RES / "audit_linked.json").write_text(json.dumps(linked, indent=1, ensure_ascii=False),
                                       encoding="utf-8")
print(f"linked {len(linked)} verdicts ({mism} with a loose rationale match)")
print()
for k in ("3", "2", "1"):
    sub = [r for r in linked if r["n_models"] == int(k)]
    ja = sum(1 for r in sub if r["verdict"] == "ja")
    print(f"  {k}/3 models: {ja}/{len(sub)} = {100*ja/len(sub):.0f} % precision")
ja_all = sum(1 for r in linked if r["verdict"] == "ja")
print(f"  pooled     : {ja_all}/{len(linked)} = {100*ja_all/len(linked):.0f} % precision")

# ---- weight by the true stratum sizes -------------------------------------
preds = [json.loads(l) for l in (RES / "predictions_full.jsonl").open(encoding="utf-8")]
from collections import defaultdict
pool_flag = defaultdict(set)
for p in preds:
    if p["codebook"] == "A" and p["condition"] == "A" and p["label"] == "ja":
        pool_flag[p["uid"]].add(p["model"])
sizes = {k: sum(1 for v in pool_flag.values() if len(v) == k) for k in (1, 2, 3)}
prec = {k: sum(1 for r in linked if r["n_models"] == k and r["verdict"] == "ja")
        / max(1, sum(1 for r in linked if r["n_models"] == k)) for k in (1, 2, 3)}
tot = sum(sizes.values())
weighted = sum(sizes[k] * prec.get(k, 0) for k in (1, 2, 3)) / tot
print()
print(f"  distinct positives: {tot}  {sizes}")
print(f"  estimated precision (stratum-weighted): {100*weighted:.0f} %")
print(f"  => ~{round(weighted*tot)} true reactance cases among {tot} flagged")
# lenient variant: count stratum-1 borderline cases as ja
b1 = sum(1 for r in linked if r["n_models"] == 1
         and r["verdict"] == "nein" and "orderline" in r["why"])
lenient = (sum(sizes[k] * prec.get(k, 0) for k in (1, 2, 3)) + sizes[1] * (b1 / 12)) / tot
print(f"  lenient variant (3 borderline counted as ja): {100*lenient:.0f} %")

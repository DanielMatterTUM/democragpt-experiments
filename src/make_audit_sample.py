"""Stratified dump for manual precision coding of the original three-model pool.

Audit v1 predates GLM-5.3-Flash. Re-running this script against the current
``predictions_full.jsonl`` must therefore reproduce the historical 3/3, 2/3
and 1/3 strata from Jev, GPT-6-Luna and DeepSeek only. GLM is deliberately
excluded here; ``make_audit_sample_v2.py`` is the four-model audit sampler.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIT_MODELS_3 = {"jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash"}

rows = {json.loads(l)["uid"]: json.loads(l)
        for l in (REPO / "data/sample_comments.jsonl").open(encoding="utf-8")}
preds = [json.loads(l) for l in (REPO / "results/predictions_full.jsonl").open(encoding="utf-8")]
tab = defaultdict(dict)
for p in preds:
    if p["label"] is None:
        continue
    tab[(p["model"], p["codebook"], p["condition"], p["uid"])] = p["label"]
pool = defaultdict(set)
for (m, cb, cond, uid), lab in tab.items():
    if (m in AUDIT_MODELS_3 and cb == "A" and cond == "A" and lab == "ja"):
        pool[uid].add(m)

rng = random.Random(2026)
groups = {3: [], 2: [], 1: []}
for u, v in pool.items():
    groups[len(v)].append(u)
for k in groups:
    groups[k].sort()
    rng.shuffle(groups[k])

# 12 per stratum -> 36 hand-coded positives, enough for a coarse precision estimate
sample = [(u, k) for k in (3, 2, 1) for u in groups[k][:12]]
out = []
for uid, k in sample:
    r = rows[uid]
    out.append({"uid": uid, "n_models": k, "party": r["party"],
                "chars": r["comment_chars"], "text": r["comment_text"],
                "transcript": r["transcript"][:400]})
(RES := REPO / "results").joinpath("audit_sample.json").write_text(
    json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"wrote results/audit_sample.json with {len(out)} items")
for uid, k in sample:
    print(f"\n[{k}/3] {rows[uid]['party']}")
    print(f"  {rows[uid]['comment_text']}")
    print(f"  VIDEO: {rows[uid]['transcript'][:200]}")

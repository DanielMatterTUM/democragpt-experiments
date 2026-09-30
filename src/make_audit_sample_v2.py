#!/usr/bin/env python3
"""Draw the FOUR-model audit sample (audit v2) for a future annotation round.

Why this file exists (see report section "manual audit after adding GLM"):
the v1 audit (36 cases) was drawn from the original three-model positive pool
before GLM-5.3-Flash was added, so it says nothing about the GLM-only flags
(a 1-of-4 stratum that did not exist in v1). This script draws the v2 sample
from the full four-model pool, stratified by how many of the four models flag
each positive:

    4 of 4   (unanimous)
    3 of 4
    2 of 4
    1 of 4   (solitary flags -- including the 61 GLM-only ones)

The 1-of-4 stratum is reported split by which model is the lone flagger, because
that is exactly the GLM-only question the report must not extrapolate from v1.

The sample is written to results/audit_sample_v2.json with explicit metadata
(audit_version 2, the four models, condition A, codebook A, n_candidates, and
verdicts = PENDING). It is NOT scored here: scoring a v2 round is a manual
coding task, and no verdict in this file is invented. score_audit_v2.py (to be
run after the coding round) produces results/audit_scoping.json for v2.
"""
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

# The four models, in the order the report lists them.
MODELS_4 = ["jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash", "glm-5.3-flash"]
N_PER_STRATUM = 8          # 8 per 4/3/2/4 stratum
N_PER_SOLO = 6             # 6 per lone-flagging model within the 1-of-4 stratum
SEED = 20260929


def load_jsonl(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


rows = {r["uid"]: r for r in load_jsonl(REPO / "data/sample_matrix.jsonl")}
preds = load_jsonl(RES / "predictions_full.jsonl")

# four-model positive pool (Codebook A, Condition A)
pool = defaultdict(set)
for p in preds:
    if p["codebook"] == "A" and p["condition"] == "A" and p["label"] == "ja":
        pool[p["uid"]].add(p["model"])

# strata: 4/4, 3/4, 2/4, and 1/4 (1/4 split by which model)
g4 = sorted(u for u, v in pool.items() if len(v) == 4)
g3 = sorted(u for u, v in pool.items() if len(v) == 3)
g2 = sorted(u for u, v in pool.items() if len(v) == 2)
g1 = sorted(u for u, v in pool.items() if len(v) == 1)
solo = {m: sorted(u for u in g1 if pool[u] == {m}) for m in MODELS_4}

rng = random.Random(SEED)

sample, verdicts = [], {"4": [], "3": [], "2": [], "1": []}


def add(uid, k, stratum_tag):
    r = rows[uid]
    sample.append({"uid": uid, "n_models": k, "stratum": stratum_tag,
                   "flagging_models": sorted(pool[uid]),
                   "party": r["party"], "chars": r["comment_chars"],
                   "text": r["comment_text"], "transcript": r["transcript"][:400]})
    verdicts[stratum_tag].append({"uid": uid, "verdict": "PENDING", "label": None,
                                  "why": "(not yet coded in v2)"})


for u in rng.sample(g4, min(N_PER_STRATUM, len(g4))):
    add(u, 4, "4")
for u in rng.sample(g3, min(N_PER_STRATUM, len(g3))):
    add(u, 3, "3")
for u in rng.sample(g2, min(N_PER_STRATUM, len(g2))):
    add(u, 2, "2")
# 1-of-4 stratum: stratify the lone flags BY model so the GLM-only cases are
# explicitly present (and countable) in the v2 round
for m in MODELS_4:
    for u in rng.sample(solo[m], min(N_PER_SOLO, len(solo[m]))):
        add(u, 1, "1")

out = {
    "meta": {
        "audit_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "condition": "A", "codebook": "A", "sample": "matrix",
        "models": MODELS_4,
        "status": "PENDING_ANNOTATION",
        "n_candidates": len(pool),
        "n_audited": 0,
        "strata_target": {
            "4": {"n_available": len(g4), "n_drawn": len(verdicts["4"])},
            "3": {"n_available": len(g3), "n_drawn": len(verdicts["3"])},
            "2": {"n_available": len(g2), "n_drawn": len(verdicts["2"])},
            "1": {"n_available": len(g1), "n_drawn": len(verdicts["1"]),
                  "split_by_lone_model": {m: len(x) for m, x in
                                           [(m, [v for v in verdicts["1"]
                                                   if v["uid"] in set(solo[m])])
                                            for m in MODELS_4]},
                  "available_by_lone_model": {m: len(solo[m]) for m in MODELS_4}},
        },
        "scope_note": ("v2 covers the full four-model pool. Every verdict in "
                       "this file is PENDING; none is annotated yet. Score it "
                       "with score_audit_v2.py after the coding round."),
        "source_files": ["predictions_full.jsonl", "sample_matrix.jsonl"],
        "seed": SEED,
    },
    "sample": sample,
    "verdicts": verdicts,
}
(RES / "audit_sample_v2.json").write_text(
    json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

sizes4 = {k: sum(1 for v in pool.values() if len(v) == k) for k in (4, 3, 2, 1)}
print(f"wrote results/audit_sample_v2.json ({len(sample)} candidates, "
      f"all PENDING)")
print(f"  4-model pool: {sizes4}  (distinct positives {sum(sizes4.values())})")
print(f"  1-of-4 split by lone model: "
      f"{ {m: len(solo[m]) for m in MODELS_4} }")
print(f"  drawn: 4-of-4={len(verdicts['4'])}  3-of-4={len(verdicts['3'])}  "
      f"2-of-4={len(verdicts['2'])}  1-of-4={len(verdicts['1'])}")
print("  NOTE: verdicts are PENDING -- do not score until the v2 coding round.")

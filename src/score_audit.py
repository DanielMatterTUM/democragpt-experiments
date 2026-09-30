#!/usr/bin/env python3
"""Link manual verdicts to real uids, compute precision by consensus stratum.

SCOPE (the point of this rewrite): the manual audit (36 cases) was drawn from
the ORIGINAL THREE-MODEL positive pool -- GLM was not part of it. So the
strata are "k of the 3 original models flagged this case" (3/3, 2/3, 1/3), and
every number this script emits is labelled with the model set it applies to.
GLM-only flags (a 4-model "1-of-4" stratum) are NOT covered by this audit and
must not be extrapolated from it; `make_audit_sample_v2.py` records the 4-model
sample that a v2 annotation round should score.

The verdict list in audit_verdicts.json is positional: entry i of stratum k
corresponds to entry i of audit_sample.json for that stratum (both files were
produced by the same deterministic sampling).

Output: results/audit_scoping.json -- the single generated source for every
precision number in the report (no hard-coded percentages in the LaTeX):
  { "meta": {...3 models, condition A, codebook A, audit_version 1...},
    "strata": { "3": {n, n_pos, precision_pct, wilson95, cases:[...]}, ... },
    "pooled": {...},
    "pool_sizes_3model": {...}, "pool_sizes_4model": {...},
    "glm_only_flags": 61, "glm_in_audit": false }
"""
import json
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

from statsmodels.stats.proportion import proportion_confint

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

AUDIT_MODELS_3 = ["jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash"]  # audit pool
GLM = "glm-5.3-flash"

sample = json.load((RES / "audit_sample.json").open(encoding="utf-8"))
verd = json.load((RES / "audit_verdicts.json").open(encoding="utf-8"))

by_stratum = {}
for it in sample:
    by_stratum.setdefault(str(it["n_models"]), []).append(it)

linked, mism = [], 0
for k, entries in verd["strata"].items():
    pool = by_stratum.get(k, [])
    for i, v in enumerate(entries):
        if i >= len(pool):
            break
        item = pool[i]
        rec = {"uid": item["uid"], "n_models": int(k), "party": item["party"],
               "text": item["text"], "verdict": v["verdict"],
               "label": v.get("label", "-"), "why": v["why"]}
        linked.append(rec)
        head = item["text"][:40].lower()
        if v["why"].split(".")[0][:20].lower() not in head and \
           not any(w in head for w in v["why"].lower().split()[:3]):
            mism += 1

(RES / "audit_linked.json").write_text(json.dumps(linked, indent=1, ensure_ascii=False),
                                       encoding="utf-8")


def wilson(count, total):
    """Wilson score 95% interval for a binomial proportion (small n)."""
    if total == 0:
        return None
    lo, hi = proportion_confint(count=count, nobs=total, alpha=0.05, method="wilson")
    return [round(100 * lo, 1), round(100 * hi, 1)]


def stratum_stats(rows, k):
    n = len(rows)
    n_pos = sum(1 for r in rows if r["verdict"] == "ja")
    return {"n": n, "n_positive": n_pos,
            "precision_pct": round(100 * n_pos / n, 1) if n else None,
            "wilson95_pct": wilson(n_pos, n),
            "cases": [{"uid": r["uid"], "verdict": r["verdict"],
                       "why": r["why"]} for r in rows]}


# ---- 4-model pool context (matrix, Codebook A, Condition A) ---------------
preds = [json.loads(l) for l in (RES / "predictions_full.jsonl").open(encoding="utf-8")]
pool4 = defaultdict(set)
for p in preds:
    if p["codebook"] == "A" and p["condition"] == "A" and p["label"] == "ja":
        pool4[p["uid"]].add(p["model"])
sizes4 = {k: sum(1 for v in pool4.values() if len(v) == k) for k in (4, 3, 2, 1)}
sizes3 = {k: sum(1 for v in pool4.values()
                 if len(v & set(AUDIT_MODELS_3)) == k) for k in (3, 2, 1)}
glm_only = sum(1 for v in pool4.values() if v == {GLM})

out = {
    "meta": {
        "audit_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "condition": "A", "codebook": "A", "sample": "matrix",
        "models": AUDIT_MODELS_3,
        "glm_in_audit": False,
        "n_candidates": sum(sizes3.values()),
        "n_audited": len(linked),
        "coded_by": verd.get("coded_by"),
        "scope_note": ("Audit v1 was drawn from the original three-model "
                       "positive pool; GLM-5.3-Flash was added later and took "
                       "part in neither the sampling nor the coding. The "
                       "strata are therefore 'k of the 3 original models'."),
        "source_files": ["audit_sample.json", "audit_verdicts.json",
                         "predictions_full.jsonl"],
    },
    "strata": {str(k): stratum_stats([r for r in linked if r["n_models"] == k], k)
               for k in (3, 2, 1)},
    "pool_sizes_3model": sizes3,
    "pool_sizes_4model": sizes4,
    "glm_only_flags": glm_only,
    "n_positive_distinct_4model": sum(sizes4.values()),
}
ja_all = sum(1 for r in linked if r["verdict"] == "ja")
out["pooled"] = {"n": len(linked), "n_positive": ja_all,
                 "precision_pct": round(100 * ja_all / len(linked), 1) if linked else None,
                 "wilson95_pct": wilson(ja_all, len(linked))}

# stratum-weighted estimate over the 3-model pool (the population the audit
# actually sampled from)
tot3 = sum(sizes3.values())
w3 = sum(sizes3[k] * (out["strata"][str(k)]["n_positive"]
                      / max(1, out["strata"][str(k)]["n"])) for k in (3, 2, 1)) / tot3
out["weighted_3model_pool"] = {"n": tot3, "pct": round(100 * w3, 1)}
# and the same weights applied to the 4-model pool (only for the 1, 2, 3 strata
# that exist in both; 4-of-4 and the GLM-only 1-of-4 cases have no audited rate)
out["weighted_4model_pool_unaudited_tail"] = {
    "n": sum(sizes4.values()),
    "caveat": "the 4-of-4 and GLM-only strata carry no audited rate",
    "pct": None}

(RES / "audit_scoping.json").write_text(
    json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

print(f"linked {len(linked)} verdicts ({mism} with a loose rationale match)")
print("  scope: 3 original models (GLM NOT in the audit); condition A, codebook A")
for k in (3, 2, 1):
    s = out["strata"][str(k)]
    print(f"  {k} of 3 models: {s['n_positive']}/{s['n']} = {s['precision_pct']:.0f} % "
          f"wilson95 {s['wilson95_pct']}")
print(f"  pooled       : {out['pooled']['n_positive']}/{out['pooled']['n']} = "
      f"{out['pooled']['precision_pct']:.0f} %")
print(f"  3-model pool sizes {sizes3}  (weighted {out['weighted_3model_pool']['pct']} %)")
print(f"  4-model pool sizes {sizes4}  (GLM-only flags NOT audited: {glm_only})")
print("wrote results/audit_scoping.json + audit_linked.json")

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
d = json.load((REPO / "results/exp_paraphrase.json").open(encoding="utf-8"))
print(f"n={d['n_comments']} calls={d['calls']} cost=${d['cost_usd']}")
print(f"{'stratum':>9} {'n':>4} " + " ".join(f"{k:>16}" for k in
      ["T1_deemphasis", "T2_politeness", "T3_defiller", "all_variants_agree"]))
for k in sorted(d["per_stratum"], key=lambda x: (x == "0", -int(x))):
    r = d["per_stratum"][k]
    print(f"{k:>9} {r['n']:>4} " + " ".join(
        f"{(r.get(c) if r.get(c) is not None else 0):>15.1f}%"
        for c in ["T1_deemphasis", "T2_politeness", "T3_defiller",
                  "all_variants_agree"]))
print("\norig label counts per stratum:")
for k in sorted(d["per_stratum"], key=lambda x: (x == "0", -int(x))):
    print(f"  {k}: {d['per_stratum'][k]['label_counts_orig']}")

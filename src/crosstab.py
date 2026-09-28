"""Cross-tabulate Codebook A against Codebook B per comment and model.

Purpose: quantify the false-positive class behind the ~10x prevalence gap
(Codebook A says 2-8 %, Codebook B says 29-56 %). Cells where B names a
reactance type but A says "nein" are exactly the disagreement / plain-criticism
comments that the proposed Codebook B boundary fix targets.
"""
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LAB_B = {"konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik", "keine_reaktanz"}

preds = [json.loads(l) for l in (REPO / "results/predictions_full.jsonl").open()]
models = sorted({p["model"] for p in preds})

# (model, condition) -> uid -> {A: label, B: label}
tab = {}
for p in preds:
    if p["label"] is None:
        continue
    key = (p["model"], p["condition"])
    tab.setdefault(key, {}).setdefault(p["uid"], {})[p["codebook"]] = p["label"]

print("=== Codebook A (rows) x Codebook B (cols), per model & condition ===\n")
rows_out = []
for (m, cond) in sorted(tab):
    cells = tab[(m, cond)]
    complete = {u: d for u, d in cells.items()
                if "A" in d and "B" in d and d["B"] in LAB_B}
    if not complete:
        continue
    # careful: a plain equality of the two booleans is ALSO satisfied by the
    # both-negative cell, so count the four cells explicitly instead.
    both_react = sum(1 for d in complete.values()
                     if d["A"] == "ja" and d["B"] != "keine_reaktanz")
    b_type_a_no = sum(1 for d in complete.values()
                      if d["A"] == "nein" and d["B"] != "keine_reaktanz")
    a_yes_b_no = sum(1 for d in complete.values()
                     if d["A"] == "ja" and d["B"] == "keine_reaktanz")
    both_no = sum(1 for d in complete.values()
                  if d["A"] == "nein" and d["B"] == "keine_reaktanz")
    n = len(complete)
    assert both_react + b_type_a_no + a_yes_b_no + both_no == n, "cells must partition"
    print(f"{m}  (condition {cond}, n={n})")
    print(f"  both reactance      : {both_react:4d}  ({100*both_react/n:5.1f} %)")
    print(f"  B=type, A=nein      : {b_type_a_no:4d}  ({100*b_type_a_no/n:5.1f} %)  <-- FP class")
    print(f"  A=ja,    B=keine    : {a_yes_b_no:4d}  ({100*a_yes_b_no/n:5.1f} %)  <-- FN class")
    print(f"  both no reactance   : {both_no:4d}  ({100*both_no/n:5.1f} %)")
    print()
    rows_out.append([m, cond, n, both_react, b_type_a_no, a_yes_b_no, both_no])

out = REPO / "results/analysis_crosstab_ab.csv"
with out.open("w", encoding="utf-8") as fh:
    fh.write("model,condition,n_paired,both_reactance,b_type_a_no,a_yes_b_none,both_none\n")
    for r in rows_out:
        fh.write(",".join(str(x) for x in r) + "\n")
print("wrote", out)

# Which B labels are responsible for the FP class, pooled over models (cond A)
print("\n=== FP-class composition (B=type & A=nein), condition A, pooled over models ===")
comp = Counter()
for (m, cond) in sorted(tab):
    if cond != "A":
        continue
    for d in tab[(m, cond)].values():
        if d.get("A") == "nein" and d.get("B") in LAB_B - {"keine_reaktanz"}:
            comp[d["B"]] += 1
for lab, n in comp.most_common():
    print(f"  {lab:28s} {n}")

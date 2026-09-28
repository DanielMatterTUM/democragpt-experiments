"""Validate the revised Codebook B gate with Jev before spending on the full matrix.

Runs Codebook A and Codebook B (gate version) on a small Jev-only subset and
reports:
  * Codebook B prevalence before/after the gate fix
  * A-vs-B crosstab (does B now agree with A?)
  * examples of comments that changed label
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LAB_B = {"konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik", "keine_reaktanz"}

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60

subprocess.run([sys.executable, "src/run_benchmark.py", "--models", "jev-1.13",
                "--codebooks", "A", "B", "--conditions", "A",
                "--limit", str(N), "--workers", "8",
                "--run-name", "jev_gate_check"], cwd=REPO, check=True)

preds = [json.loads(l) for l in (REPO / "results/predictions_jev_gate_check.jsonl").open()]
rows = {json.loads(l)["uid"]: json.loads(l)
        for l in (REPO / "data/sample_comments.jsonl").open()}

tab = {}
for p in preds:
    tab.setdefault(p["uid"], {})[p["codebook"]] = p["label"]

print(f"\nJev, condition A, n={len(tab)}\n")
for cb in ("A", "B"):
    labs = [d[cb] for d in tab.values() if d.get(cb)]
    pos = [x for x in labs if x != ("nein" if cb == "A" else "keine_reaktanz")]
    print(f"  codebook {cb}: n={len(labs):3d}  reactant={len(pos):3d}  "
          f"prevalence={100*len(pos)/max(1,len(labs)):5.1f} %")
    if cb == "B":
        print("   ", Counter(labs).most_common())

both_react = sum(1 for d in tab.values()
                 if d.get("A") == "ja" and d.get("B") not in (None, "keine_reaktanz"))
fp = sum(1 for d in tab.values()
         if d.get("A") == "nein" and d.get("B") not in (None, "keine_reaktanz"))
fn = sum(1 for d in tab.values()
         if d.get("A") == "ja" and d.get("B") == "keine_reaktanz")
both_no = sum(1 for d in tab.values()
              if d.get("A") == "nein" and d.get("B") == "keine_reaktanz")
print(f"\n  A x B crosstab:  both_react={both_react}  FP(B=type,A=nein)={fp}  "
      f"FN={fn}  both_no={both_no}")
print(f"  FP:TP ratio = {fp/max(1,both_react):.1f}   (was 13-20x before the fix)\n")

print("=== comments the gate still codes as reactance (sample) ===")
shown = 0
for uid, d in tab.items():
    if d.get("A") == "ja" and d.get("B") not in (None, "keine_reaktanz"):
        print(f"  [{d['B']}] {rows[uid]['comment_text'][:150]}")
        shown += 1
        if shown >= 12:
            break

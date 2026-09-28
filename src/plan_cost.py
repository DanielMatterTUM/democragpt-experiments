"""Cost planner: estimate the full-matrix price before spending the budget."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_benchmark import CHAT_MODELS, JEV_MODELS  # noqa: E402

# measured $/1000 rows from the 201-comment run (results/analysis_cost.csv)
# codebook B prompts are ~1.8x the codebook A criteria text.
MEASURED = {
    #          cbA/condA  cbA/condB  cbB/condA  cbB/condB
    "jev-1.13":          (0.055, 0.045, 0.087, 0.078),
    "gpt-6-luna":        (0.126, 0.097, 0.205, 0.160),
    "deepseek-v4.1-flash": (0.161, 0.123, 0.170, 0.108),
    "glm-5.3-flash":     (0.168, 0.109, 0.136, 0.085),
}

n_rows = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
print(f"estimated cost for {n_rows} rows (full 2x2 matrix), $/1000 rows scaled:\n")
grand = 0.0
for m, (a, b, c, d) in MEASURED.items():
    per1k = a + b + c + d
    total = per1k * n_rows / 1000
    grand += total
    print(f"  {m:22s} ${per1k:.3f}/1k  ->  ${total:6.3f}  ({n_rows} rows x 4 cells)")
print(f"\n  ALL FOUR models: ${grand:.3f}")

cheapest_two = MEASURED["jev-1.13"], MEASURED["gpt-6-luna"]
t2 = sum(sum(v) * n_rows / 1000 for v in cheapest_two)
print(f"  jev + gpt-6-luna : ${t2:.3f}")
three = MEASURED["jev-1.13"], MEASURED["gpt-6-luna"], MEASURED["deepseek-v4.1-flash"]
t3 = sum(sum(v) * n_rows / 1000 for v in three)
print(f"  + deepseek        : ${t3:.3f}")
print(f"\n  Codebook A only (2 conditions, all 4): "
      f"${sum((v[0]+v[1])*n_rows/1000 for v in MEASURED.values()):.3f}")

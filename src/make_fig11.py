"""Abb. 11 — the large-scale run: 2,001 comments, comment-only, sharpened codebook.

(a) prevalence with bootstrap CI, codebook A vs B
(b) the confidence bands: p(ja) < 0.1 -> 0 positives, p(ja) > 0.6 -> 100 %
    i.e. the decision API is effectively a two-state detector
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
FIG = RES / "figures"

sns.set_theme(style="ticks", context="paper", font="DejaVu Sans")
sns.set_context("paper", rc={
    "axes.labelsize": 8.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5, "figure.dpi": 200, "savefig.dpi": 300,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "axes.linewidth": 0.6, "grid.linewidth": 0.4, "grid.alpha": 0.25,
})
plt.rcParams["pdf.fonttype"] = 42

D = json.load((RES / "analysis_f1.json").open(encoding="utf-8"))
B = D.get("big_run") or {}
if not B:
    raise SystemExit("no big_run in analysis_f1.json -- run analyze_f1.py first")

fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 2.7))

# ---- (a) prevalence, two codebooks ---------------------------------------
a, b = B["codebook_A"], B["codebook_B"]
vals = [a["prevalence_pct"], b["prevalence_pct"]]
err = [[a["prevalence_pct"] - a["ci95"][0], a["ci95"][1] - a["prevalence_pct"]],
       [b["prevalence_pct"] * 0.55, b["prevalence_pct"] * 0.9]]
bars = a1.bar([0, 1], vals, 0.5, color=["#2f6f8f", "#c4622d"],
              edgecolor="#333", linewidth=0.5)
a1.errorbar([0, 1], vals, yerr=err, fmt="none", ecolor="#222",
            elinewidth=0.9, capsize=3, zorder=4)
for i, (v, r) in enumerate(zip(vals, [a, b])):
    a1.annotate(f"{v:.2f} %", (i, v), textcoords="offset points", xytext=(0, 8),
                ha="center", fontsize=7.4, fontweight="bold")
    a1.annotate(f"n = {r['n_positive']}", (i, v), textcoords="offset points",
                xytext=(0, -12), ha="center", fontsize=6.4, color="white")
a1.set_xticks([0, 1])
a1.set_xticklabels(["Codebook A\n(binär)", "Codebook B\n(7 Typen)"], fontsize=7.6)
a1.set_ylabel("Prävalenz (%)")
a1.set_ylim(0, 4.6)
a1.set_title(f"a  Prävalenz, n = {B['n_comments']} Kommentare", loc="left", pad=6)
a1.annotate(f"95-%-KI Codebook A: [{a['ci95'][0]}, {a['ci95'][1]}]",
            xy=(0.5, 4.15), ha="center", fontsize=6.2, color="#444")

# ---- (b) confidence bands ------------------------------------------------
cb = B["confidence_bands"]
order = ["<0.1", "0.1-0.3", "0.3-0.6", "0.6-0.9", ">=0.9"]
xs = np.arange(len(order))
rates = [cb.get(k, {}).get("rate_pct") or 0 for k in order]
ns = [cb.get(k, {}).get("n", 0) for k in order]
cols = ["#9c9c9c" if r == 0 else ("#c4622d" if r < 50 else "#2f6f8f")
        for r in rates]
bars2 = a2.bar(xs, rates, 0.55, color=cols, edgecolor="#333", linewidth=0.5)
for i, (r, n) in enumerate(zip(rates, ns)):
    a2.annotate(f"{r:.0f} %", (i, r), textcoords="offset points", xytext=(0, 4),
                ha="center", fontsize=7.0, fontweight="bold")
    a2.annotate(f"n={n}", (i, 2.5), ha="center", fontsize=6.0, color="white")
a2.set_xticks(xs)
a2.set_xticklabels([f"$p$={o}" if o.startswith("<") or o.startswith(">")
                    else f"$p$∈{o}" for o in order], fontsize=7.0)
a2.set_ylabel("Anteil positiver\nKodierungen (%)", labelpad=1)
a2.set_ylim(0, 112)
a2.set_title("b  Jev-Konfidenzbänder (Codebook A)", loc="left", pad=6)

# no suptitle -- the report caption carries "Abb. 11 ..."
fig.tight_layout(rect=(0, 0, 1, 1.0))
fig.savefig(FIG / "fig11_bigscale.pdf")
import subprocess
subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                str(FIG / "fig11_bigscale.pdf"), str(FIG / "fig11_bigscale")],
               check=True)
plt.close(fig)
print("wrote fig11_bigscale")

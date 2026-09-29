"""Abb. 3 with a SECOND y-axis: raw agreement (%, 0-100) on the left, the
chance-corrected coefficients (kappa, AC1; both 0-1) on the right.

The original figure put a 0-100 percentage and two 0-1 coefficients on one axis,
which silently misrepresented the coefficients -- they looked tiny. Two axes fix
that, and the point of the figure (the coefficients are NOT small; they disagree
with the raw percentage) becomes visible.
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

ABBR = {"jev-1.13": "jev", "gpt-6-luna": "gpt6",
        "deepseek-v4.1-flash": "deep", "glm-5.3-flash": "glm"}
BLUE, ORANGE, GREY = "#2f6f8f", "#c4622d", "#4d4d4d"


def draw(ax, ax2, data, ttl, sub):
    x = np.arange(len(data))
    w = 0.3
    raw = [d["raw_pct"] for d in data]
    kap = [d["kappa"] for d in data]
    ac1 = [d["ac1"] for d in data]

    # LEFT axis: raw agreement in percent
    b = ax.bar(x - w / 2, raw, w, color="#c9d6e0", edgecolor="#333",
               linewidth=0.4, label="Rohübereinstimmung (%)", zorder=2)
    for i, v in enumerate(raw):
        ax.annotate(f"{v:.1f} %", (x[i] - w / 2, v), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=6.2, color="#333")
    ax.set_ylim(0, 108)
    ax.set_ylabel("Rohübereinstimmung (%)", color="#33475b", fontsize=7.6, labelpad=6)
    ax.set_xlabel("")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{ABBR.get(d['a'], d['a'])}\nvs. {ABBR.get(d['b'], d['b'])}"
                        for d in data], fontsize=6.8)
    ax.set_title(f"{ttl}\n{sub}", fontsize=8.6, loc="left", pad=7)
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)

    # RIGHT axis: chance-corrected coefficients, 0-1
    ax2.plot(x - w / 2, kap, "o", color=BLUE, ms=5, zorder=3, label="Cohen's κ")
    ax2.plot(x + w / 2, ac1, "s", color=ORANGE, ms=5, zorder=3, label="Gwet's AC1")
    for i in range(len(data)):
        ax2.annotate(f"{kap[i]:.2f}", (x[i] - w / 2, kap[i]),
                     textcoords="offset points", xytext=(0, -11), ha="center",
                     fontsize=6.2, color=BLUE)
        ax2.annotate(f"{ac1[i]:.2f}", (x[i] + w / 2, ac1[i]),
                     textcoords="offset points", xytext=(0, 6), ha="center",
                     fontsize=6.2, color=ORANGE)
    ax2.set_ylim(0, 1.08)
    ax2.set_ylabel("Chance-bereinigte Koeffizienten (0–1)", color="#33475b",
                   fontsize=7.6, labelpad=6)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color("#33475b")
    return ax, ax2


def add_legend(fig, axes, twin):
    """One shared legend below the panels. Placed INSIDE the figure box (y=0.005)
    with space reserved by tight_layout -- at a negative y it was clipped away
    entirely by savefig(bbox_inches='tight')."""
    h1, l1 = axes[0].get_legend_handles_labels()
    h2, l2 = twin[0].get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, ncol=3, frameon=False,
               loc="lower center", bbox_to_anchor=(0.5, 0.005),
               handlelength=1.5, fontsize=7.4)


def main():
    X = json.load((RES / "analysis_ext.json").open(encoding="utf-8"))
    mp = X.get("model_pairwise", [])
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 3.0))
    twin = []
    for ax, cb in zip(axes, ("A", "B")):
        data = [r for r in mp if r["cb"] == cb and r["cond"] == "A"]
        if not data:
            continue
        _, t = draw(ax, ax.twinx(), data, f"Codebook {cb}, Condition A",
                    f"n = {data[0]['n']} Kommentare")
        twin.append(t)
    add_legend(fig, axes, twin)
    # no suptitle -- the report caption carries "Abb. 3 ..."
    fig.tight_layout(rect=(0, 0.10, 1, 1.0))
    fig.subplots_adjust(wspace=0.55)
    fig.savefig(FIG / "fig3_agreement.pdf")
    import subprocess
    subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                    str(FIG / "fig3_agreement.pdf"), str(FIG / "fig3_agreement")],
                   check=True)
    plt.close(fig)
    print("wrote fig3_agreement (dual axis)")


if __name__ == "__main__":
    main()

"""Figure: full model x model heatmap matrix (square cells, colour only, no labels).

Requested layout: one column per model on the x axis, one row per model on the y
axis, each cell the confusion matrix of (row model) vs (column model) rendered as
a square heatmap. For Codebook A the 2x2 confusion matrix is what goes in each
cell; for Codebook B the 7x7 version is shown in the diagonal cells as a small
inset-style block, which keeps the cells square.
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
FIG = RES / "figures"

sns.set_theme(style="white", context="paper", font="DejaVu Sans")
sns.set_context("paper", rc={
    "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})
plt.rcParams["pdf.fonttype"] = 42

SEQ = LinearSegmentedColormap.from_list(
    "seq", ["#f7f9fb", "#cfe0ea", "#7fadc4", "#2f6f8f", "#143b50"])
CLS = {"keine_reaktanz": "keine", "konfrontation_angriff": "konfr.",
       "ablenkung_whataboutism": "Ablen.", "delegierung_hilflosigkeit": "Deleg.",
       "vermeidung_rueckzug": "Verm.", "reflektierte_rechtfertigung": "Refl.",
       "konstruktive_kritik": "konstr."}
LAB_A = ["nein", "ja"]


def short(m):
    return {"jev-1.13": "jev", "gpt-6-luna": "gpt6",
            "deepseek-v4.1-flash": "deep", "glm-5.3-flash": "glm"}.get(m, m)


def build(cb: str, cond: str):
    X = json.load((RES / "analysis_ext.json").open(encoding="utf-8"))
    mp = X.get("model_pairwise", [])
    models = sorted({r["a"] for r in mp} | {r["b"] for r in mp})
    idx = {}
    for r in mp:
        if r["cb"] == cb and r["cond"] == cond:
            idx[(r["a"], r["b"])] = r
            idx[(r["b"], r["a"])] = r          # symmetric access
    return models, idx


def panel(ax, rec, labels, title, cb, cell_k):
    """Draw one confusion matrix inside a square axes."""
    if rec is None:
        ax.set_facecolor("#f4f4f4")
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.5, 0.5, "—", ha="center", va="center", fontsize=9, color="#999")
        ax.set_title(title, fontsize=6.2, pad=3)
        return
    m = np.array(rec["raw"], dtype=float)
    if cb == "A":
        # 2x2 -> draw directly, row-normalised off, raw counts
        ax.imshow(m, cmap=SEQ, vmin=0, vmax=m.max() if m.max() else 1,
                  interpolation="nearest")
        # mark the off-diagonal cells (disagreements) with a hairline box
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                if i != j and m[i, j] > 0:
                    ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                           edgecolor="#c0392b", lw=0.7, zorder=4))
        k = len(labels)
    else:
        # 7x7 inside a square cell: render small, no ticks
        ax.imshow(m, cmap=SEQ, vmin=0, vmax=m.max() if m.max() else 1,
                  interpolation="nearest")
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                if i != j and m[i, j] > 0:
                    ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                           edgecolor="#c0392b", lw=0.35, zorder=4))
        k = len(labels)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    frac = m.max() / m.sum() if m.sum() else 0
    cap = f"{rec['raw_pct']:.0f} %" if cb == "A" else f"{frac*100:.0f} %"
    sub = (f"κ={rec['kappa']:.2f}" if cb == "A"
           else f"κ={rec['kappa']:.2f}  AC1={rec['ac1']:.2f}")
    ax.set_title(f"{title}\n{cap} · {sub}", fontsize=5.6, pad=2.5, linespacing=1.25)
    # orientation marker: rows = model A, cols = model B
    ax.text(0.5, -0.06, "↓ A (Zeile) · B (Spalte) →", transform=ax.transAxes,
            ha="center", va="top", fontsize=4.6, color="#777")


def matrix_figure(cb: str, cond: str, fname: str, title: str):
    models, idx = build(cb, cond)
    if len(models) < 2:
        print("  skip", fname)
        return
    labels = (LAB_A if cb == "A"
              else next(iter(idx.values()))["labels"])
    labels = [CLS.get(l, l) for l in labels]
    n = len(models)
    cell = 1.42
    fig, axes = plt.subplots(n, n, figsize=(cell * n + 1.0, cell * n + 0.9))
    axes = np.atleast_2d(axes)
    for i, ma in enumerate(models):
        for j, mb in enumerate(models):
            rec = idx.get((ma, mb))
            t = ("identisch" if ma == mb else f"{short(ma)} → {short(mb)}")
            if ma == mb:
                ax = axes[i, j]
                ax.set_facecolor("#eef1f3")
                for s in ax.spines.values():
                    s.set_visible(False)
                ax.set_xticks([]); ax.set_yticks([])
                ax.text(0.5, 0.5, "—\nidentisch", ha="center", va="center",
                        fontsize=6, color="#8a8a8a", linespacing=1.4)
                ax.set_title(short(ma), fontsize=6, pad=3, color="#8a8a8a")
            else:
                panel(axes[i, j], rec, labels, t, cb, cell)
    for j, m in enumerate(models):
        axes[0, j].text(0.5, 1.30, f"{short(m)}  (Spalte B)", transform=axes[0, j].transAxes,
                        ha="center", va="bottom", fontsize=7, fontweight="bold")
    for i, m in enumerate(models):
        axes[i, 0].text(-0.28, 0.5, f"{short(m)}\n(Zeile A)", transform=axes[i, 0].transAxes,
                        ha="right", va="center", fontsize=7, fontweight="bold",
                        rotation=90)
    # no suptitle: the report caption carries "Abb. 9 ..." -- a title inside the
    # image duplicates it on the page
    fig.tight_layout(rect=(0.01, 0.01, 0.99, 0.99))
    fig.savefig(FIG / f"{fname}.pdf")
    import subprocess
    subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                    str(FIG / f"{fname}.pdf"), str(FIG / fname)], check=True)
    plt.close(fig)
    print("  wrote", fname)


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    matrix_figure("A", "A", "fig9_heatmap_matrix_A",
                  "Abb. 9  Verwirrungsmatrizen Modell × Modell, Codebook A, Condition A\n"
                  "Zeilen: Modell A · Spalten: Modell B · rot umrandet: Diskrepanzen")
    matrix_figure("B", "A", "fig10_heatmap_matrix_B",
                  "Abb. 10  Verwirrungsmatrizen Modell × Modell, Codebook B, Condition A\n"
                  "Zeilen: Modell A · Spalten: Modell B · rot umrandet: Diskrepanzen")

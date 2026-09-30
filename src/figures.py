"""Unified figure suite for the reactance benchmark.

ONE style, ONE entry point. Every figure is written as a vector PDF (for LaTeX
\\includegraphics) and, optionally, a 300 dpi PNG for quick inspection.

Design rules (applied to all figures)
-------------------------------------
* single rcParams block in `_style()`; no per-figure styling
* sequential blue colormap for counts, diverging grey for normalised diagonals
* every confusion matrix labelled with its actual row/column labels
* greyscale-safe: magnitude is also encoded in the annotation text
* no titles inside the image -- LaTeX \\caption provides them
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
FIG = RES / "figures"

# ----------------------------------------------------------------- style
BLUE, RUST, GREY, OLIVE = "#2f6f8f", "#b4552d", "#5a5a5a", "#5c7a4a"
SEQ_CMAP = LinearSegmentedColormap.from_list(
    "seq", ["#ffffff", "#dce8ef", "#a8c6d6", "#6c9cb5", "#3d7291", "#1d455c"])
MODEL_COLOR = {"jev-1.13": BLUE, "gpt-6-luna": RUST,
               "deepseek-v4.1-flash": OLIVE, "glm-5.3-flash": "#7a5c9e"}
# short, unambiguous model names for axes
MSHORT = {"jev-1.13": "jev-1.13", "gpt-6-luna": "gpt-6-luna",
          "deepseek-v4.1-flash": "deepseek-flash",
          "glm-5.3-flash": "glm-5.3-flash"}
# probability-band colours reused across figures
BAND = {"neg": "#9fb3bf", "mid": RUST, "pos": BLUE}

LAB_B = ["keine_reaktanz", "konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik"]
LAB_A = ["nein", "ja"]
# compact class labels that still fit a 7-wide grid
# ONE-line short English class names: two-line names collide in a 7-wide grid
CLS = {"keine_reaktanz": "none", "konfrontation_angriff": "attack",
       "ablenkung_whataboutism": "deflect",
       "delegierung_hilflosigkeit": "delegate",
       "vermeidung_rueckzug": "avoid",
       "reflektierte_rechtfertigung": "justify",
       "konstruktive_kritik": "critique"}


def _style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 8.6,
        "axes.labelsize": 8,
        "xtick.labelsize": 7.4,
        "ytick.labelsize": 7.4,
        "legend.fontsize": 7.4,
        "axes.linewidth": 0.6,
        "axes.edgecolor": "#333333",
        "axes.grid": True,
        "grid.color": "#b9b9b9",
        "grid.linewidth": 0.4,
        "grid.alpha": 0.45,
        "axes.axisbelow": True,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "figure.dpi": 200,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.015,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "legend.frameon": False,
    })
    for ax in ("axes.spines.top", "axes.spines.right"):
        plt.rcParams[ax] = False


def _save(fig, name: str, png: bool = True) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    if png:
        subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                        str(FIG / f"{name}.pdf"), str(FIG / name)], check=True)
    plt.close(fig)
    print("   ", name)


def _load(n, d=None):
    p = RES / n
    return json.load(p.open(encoding="utf-8")) if p.exists() else d


D = _load("report_data.json", {}) or {}
X = _load("analysis_ext.json", {}) or {}
GATE = _load("analysis_gate.json", {}) or {}
BIG = (_load("analysis_big.json", {}) or {})
AUD = _load("audit_linked.json", []) or []
RELI = _load("exp_reliability.json", {}) or {}
PARA = _load("exp_paraphrase.json", {}) or {}
MODELS = D.get("models", [])
S = D.get("summary", [])


def _order(models):
    pref = ["jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash", "glm-5.3-flash"]
    return [m for m in pref if m in models] + [m for m in models if m not in pref]


def _cmap_grid(ax, m, row_labels, col_labels, norm=False, annot_size=6.4,
               show_axis_labels=True, annotate=True):
    """Draw one confusion matrix with explicit row/column labels. When
    annotate=False (dense 7x7 sub-cells) the cells carry NO numbers -- only
    colour, per the 'full matrix of heatmaps, no labels' design."""
    m = np.asarray(m, dtype=float)
    vmax = 1.0 if norm else max(m.max(), 1)
    im = ax.imshow(m, cmap=SEQ_CMAP, vmin=0, vmax=vmax, interpolation="nearest",
                   aspect="equal")
    ax.set_xticks(range(len(col_labels)))
    ax.set_yticks(range(len(row_labels)))
    ax.set_xticklabels(col_labels if show_axis_labels else [], fontsize=6.0)
    ax.set_yticklabels(row_labels if show_axis_labels else [], fontsize=6.0)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(0.5)
        s.set_color("#666666")
    if not annotate:
        return im
    thr = vmax * 0.6
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m[i, j]
            txt = f"{v:.2f}" if (norm and v > 0) else (f"{int(v)}" if v > 0 else "")
            if txt:
                ax.text(j, i, txt, ha="center", va="center", fontsize=annot_size,
                        color="white" if v > thr else "#22404f",
                        fontweight="bold" if (not norm and i == j and len(m) > 1)
                        else "normal")
    return im


# ===================================================== 1 prevalence
def fig_prevalence():
    b = [r for r in X.get("bootstrap_prev", []) if r["cb"] == "A"]
    if not b:
        return
    models = _order({r["model"] for r in b})
    hi_all = max((r["pct"] + (r["ci_hi"] - r["pct"]) for r in b), default=9)
    ylim = min(16, max(9.6, hi_all + 1.6))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8), sharey=True)
    for ax, cond, ttl in ((axes[0], "A", "(a)  with video transcript"),
                          (axes[1], "B", "(b)  comment text only")):
        sub = {r["model"]: r for r in b if r["cond"] == cond}
        xs = np.arange(len(models))
        for i, m in enumerate(models):
            r = sub.get(m)
            if not r:
                continue
            lo = r["pct"] - r["ci_lo"]
            hi = r["ci_hi"] - r["pct"]
            ax.errorbar(i, r["pct"], yerr=[[lo], [hi]], fmt="o",
                        color=MODEL_COLOR.get(m, GREY), ms=5.5, capsize=3.5,
                        elinewidth=1.2, capthick=1.2, zorder=3)
            ax.annotate(f"{r['pct']:.2f}", (i, r["ci_hi"]), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=6.6,
                        color=MODEL_COLOR.get(m, GREY))
        ax.set_xticks(xs)
        ax.set_xticklabels([MSHORT.get(m, m) for m in models], fontsize=7)
        ax.set_title(ttl, loc="left")
        ax.set_ylim(0, ylim)
        ax.axhline(0, color="#333", lw=0.6)
    axes[0].set_ylabel("Reactance share (%)")
    fig.tight_layout()
    _save(fig, "fig01_prevalence")


# ===================================================== 2 audit
def fig_audit():
    """Manual-audit precision, version 1.

    v1 scope (stated on the figure, not in the caption): the 36 audited cases
    were drawn from the ORIGINAL THREE-MODEL positive pool; GLM-5.3-Flash was
    added to the experiment after the audit was sampled, so the strata are
    "k of the 3 original models". All precision values and Wilson 95%
    intervals are read from results/audit_scoping.json -- a single generated
    source, no hand-typed percentages (see report section on the 92/95 %
    inconsistency)."""
    AUD_SC = _load("audit_scoping.json", {}) or {}
    strata = AUD_SC.get("strata") or {}
    k_keys = [k for k in ("3", "2", "1") if strata.get(k)]
    if not k_keys:
        return
    precs, ns, wis = [], [], []
    for k in k_keys:
        s = strata[k]
        lo, hi = s["wilson95_pct"]
        precs.append(s["precision_pct"])
        ns.append(s["n"])
        # Wilson half-widths in the SAME (percentage-point) units as the bars
        wis.append([s["precision_pct"] - lo, hi - s["precision_pct"]])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.7),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    cols = [BLUE, "#7ea7bd", "#bccfd9"]
    a1.bar(range(3), precs, 0.55, color=cols, edgecolor="#333", linewidth=0.5)
    for i, (p, n, (wlo, whi)) in enumerate(zip(precs, ns, wis)):
        a1.errorbar([i], [p], yerr=[[wlo], [whi]], fmt="none", ecolor="#222",
                     elinewidth=0.9, capsize=3, zorder=4)
        a1.annotate(f"{p:.0f} %", (i, p + whi), textcoords="offset points",
                    xytext=(0, 5), ha="center", fontsize=7.4, fontweight="bold")
        a1.annotate(f"n={n}", (i, 4), ha="center", fontsize=6.4, color="white")
    a1.set_xticks(range(3))
    a1.set_xticklabels(["3 of 3\nmodels", "2 of 3", "1 of 3"], fontsize=7.2)
    a1.set_ylabel("Precision (%), Wilson 95% CI")
    a1.set_ylim(0, 116)
    a1.set_title("(a)  Precision by consensus (3-model audit)", loc="left")
    sizes = [sum(1 for v in (strata.get(k) or {"cases": []}).get("cases", []) and [])
             for k in k_keys] or [27, 26, 66]
    sz3 = (AUD_SC.get("pool_sizes_3model") or {})
    sizes = [sz3.get(k, 0) for k in k_keys]
    tot = sum(sizes)
    sh = [100 * s / tot for s in sizes]
    a2.bar(range(3), sh, 0.55, color=cols, edgecolor="#333", linewidth=0.5)
    for i, (v, s) in enumerate(zip(sh, sizes)):
        a2.annotate(f"{v:.0f} %", (i, v), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=7.2, fontweight="bold")
        a2.annotate(f"n={s}", (i, 3), ha="center", fontsize=6.4, color="white")
    a2.set_xticks(range(3))
    a2.set_xticklabels(["3/3", "2/3", "1/3"], fontsize=7.2)
    a2.set_ylabel(f"Share of {tot} positives flagged by the 3 original models (%)")
    a2.set_ylim(0, 68)
    a2.set_title("(b)  Distribution of the 3-model positives", loc="left")
    fig.tight_layout()
    _save(fig, "fig02_audit")


# ===================================================== 3 agreement (single 0-1 axis)
def fig_agreement():
    """Raw agreement / kappa / AC1 per model pair (left two panels) and the
    per-model F1 against the consensus majority (right panel). One 0-1 axis
    for all numbers: raw agreement used to be a percentage on a second axis,
    which is what made the dual scale; percentages are just 10x this scale.
    F1 is a first-class citizen here, next to the other coefficients, instead
    of a separate chapter."""
    mp = [r for r in X.get("model_pairwise", []) if r["cond"] == "A"]
    cons = [r for r in X.get("consensus_reference", [])]
    if not mp and not cons:
        return
    ABBR = {"jev-1.13": "jev", "gpt-6-luna": "gpt6",
            "deepseek-v4.1-flash": "deep", "glm-5.3-flash": "glm"}
    models = _order({r["model"] for r in cons})
    n_cons = 1 if not models else 0
    fig, axes = plt.subplots(1, 2 + (1 if models else 0), figsize=(8.2, 3.0))
    if models:
        axes = np.atleast_1d(axes)
        p_axes = axes[:2]; f1_ax = axes[2]
    else:
        p_axes = axes
    for ax, cb in zip(p_axes, ("A", "B")):
        data = [r for r in mp if r["cb"] == cb]
        x = np.arange(len(data))
        w = 0.2
        raw = [d["raw_pct"] / 100 for d in data]
        kap = [d["kappa"] for d in data]
        ac1 = [d["ac1"] for d in data]
        ax.bar(x - w, raw, w, color="#cfdae1", edgecolor="#333",
               linewidth=0.45, label="Raw agreement", zorder=2)
        ax.bar(x, kap, w, color=BLUE, edgecolor="#333",
               linewidth=0.45, label="Cohen's $\\kappa$", zorder=2)
        ax.bar(x + w, ac1, w, color=RUST, edgecolor="#333",
               linewidth=0.45, label="Gwet's AC1", zorder=2)
        for i in range(len(data)):
            for j, v in enumerate((raw[i], kap[i], ac1[i])):
                ax.annotate(f"{v:.2f}", (x[i] - w + j * w, v),
                            textcoords="offset points", xytext=(0, 2),
                            ha="center", fontsize=5.6)
        ax.set_ylim(0, 1.12)
        ax.set_ylabel("Agreement / coefficient (0-1)")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{ABBR.get(d['a'], d['a'])}–{ABBR.get(d['b'], d['b'])}"
                            for d in data], fontsize=6.4, rotation=25, ha="right")
        ax.set_title(f"(a)  Codebook {cb}, pairs, Condition A", loc="left")
        ax.spines[["top", "right"]].set_visible(False)
    if models:
        w2 = 0.2
        xs = np.arange(len(models))
        for j, (cb, off) in enumerate((("A", -w2), ("B", w2))):
            vals, miss = [], []
            for i, m in enumerate(models):
                r = next((c for c in cons
                          if c["model"] == m and c["cond"] == cb), None)
                (vals.append(r["f1"]) if r else None)
            ax_ = f1_ax
            col = BLUE if cb == "A" else RUST
            ax_.bar(xs + off, [v if v is not None else 0 for v in vals], w2,
                    color=col, edgecolor="#333", linewidth=0.45,
                    label=f"Codebook {cb}", zorder=2)
            for i, m in enumerate(models):
                r = next((c for c in cons if c["model"] == m and c["cond"] == cb), None)
                if r and r["f1"] is not None:
                    ax_.annotate(f"{r['f1']:.2f}", (xs[i] + off, r["f1"]),
                                  textcoords="offset points", xytext=(0, 2),
                                  ha="center", fontsize=5.6)
        f1_ax.set_ylim(0, 1.12)
        f1_ax.set_ylabel("F1 (0-1)")
        f1_ax.set_xticks(xs)
        f1_ax.set_xticklabels([MSHORT.get(m, m) for m in models], fontsize=6.6,
                               rotation=15, ha="right")
        f1_ax.set_title("(c)  F1 vs consensus majority", loc="left")
        f1_ax.legend(loc="upper right", fontsize=6.4)
        f1_ax.spines[["top", "right"]].set_visible(False)
    h, l = p_axes[0].get_legend_handles_labels()
    fig.legend(h, l, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.subplots_adjust(wspace=0.6)
    _save(fig, "fig03_agreement")


# ===================================================== 4 cost / latency
def fig_cost():
    if not S:
        return
    models = _order({s["model"] for s in S})

    def g(cb, cond, m, k):
        for s in S:
            if s["cb"] == cb and s["cond"] == cond and s["model"] == m:
                return s.get(k)
        return None
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.7))
    for cb, mk in (("A", "o"), ("B", "s")):
        xs = [i + (-0.08 if cb == "A" else 0.08) for i in range(len(models))]
        lat = [g(cb, "A", m, "lat") for m in models]
        cost = [g(cb, "A", m, "usd_1k") for m in models]
        col = BLUE if cb == "A" else RUST
        a1.plot(xs, lat, mk, color=col, ms=4.6, label=f"Codebook {cb}", zorder=3)
        a2.plot(xs, cost, mk, color=col, ms=4.6, label=f"Codebook {cb}", zorder=3)
        for xx, yy in zip(xs, lat):
            if yy:
                a1.annotate(f"{yy:.2f}", (xx, yy), textcoords="offset points",
                            xytext=(0, 6), ha="center", fontsize=6.0)
        for xx, yy in zip(xs, cost):
            if yy:
                a2.annotate(f"{yy:.3f}", (xx, yy), textcoords="offset points",
                            xytext=(0, 6), ha="center", fontsize=6.0)
    for ax, yl, ttl, lim in ((a1, "Mean response time (s)", "(a)  Speed", (0, 5.4)),
                             (a2, "US$ per 1,000 comments", "(b)  Cost", (0, 0.46))):
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([MSHORT.get(m, m) for m in models], fontsize=6.6,
                           rotation=15, ha="right")
        ax.set_ylabel(yl)
        ax.set_title(ttl, loc="left")
        ax.set_ylim(*lim)
        ax.legend(loc="upper left")
    fig.tight_layout()
    _save(fig, "fig04_cost")


# ===================================================== 5 model x model heatmaps
def fig_confusion_models(cb: str):
    """3x3 grid: rows = model A, columns = model B. Each cell is one confusion
    matrix. Two review findings are encoded here:
      * tick labels appear ONLY on the outer edge of the grid -- labelling every
        inner cell made the 7 class names collide into unreadable mush;
      * the 7x7 cells carry colour only, the 2x2 cells carry counts as well.
    """
    mp = [r for r in X.get("model_pairwise", []) if r["cb"] == cb and r["cond"] == "A"]
    if not mp:
        return
    models = _order({r["a"] for r in mp} | {r["b"] for r in mp})
    idx = {}
    for r in mp:
        idx[(r["a"], r["b"])] = r
        idx[(r["b"], r["a"])] = r
    labels = LAB_A if cb == "A" else LAB_B
    # one-line short names in both cases (multi-line names collide)
    short_lbl = labels if cb == "A" else [CLS.get(l, l) for l in labels]
    annotate_cells = (cb == "A")          # 2x2 keeps numbers; 7x7 is colour-only
    n = len(models)
    cell = 1.66
    fig, axes = plt.subplots(n, n, figsize=(cell * n + 0.85, cell * n + 0.75))
    axes = np.atleast_2d(axes)
    for i, ma in enumerate(models):
        for j, mb in enumerate(models):
            ax = axes[i, j]
            if ma == mb:
                ax.set_facecolor("#f2f2f2")
                for s in ax.spines.values():
                    s.set_visible(False)
                ax.set_xticks([]); ax.set_yticks([])
                ax.grid(False)
                continue
            r = idx.get((ma, mb))
            if not r:
                ax.axis("off")
                continue
            m = np.asarray(r["raw"], dtype=float)
            # LOG colour scale. On a linear scale with a ~1150-count diagonal the
            # off-diagonal cells (1-3 comments) are indistinguishable from 0 --
            # the whole point of this figure is to make those visible.
            vmax = max(m.max(), 2)
            ax.imshow(m, cmap=SEQ_CMAP, norm=LogNorm(vmin=0.7, vmax=vmax),
                      interpolation="nearest", aspect="equal")
            k = len(short_lbl)
            ax.set_xticks(range(k))
            ax.set_yticks(range(k))
            # OUTER EDGE ONLY: x labels on the bottom row, y labels on the left column
            ax.set_xticklabels(short_lbl if i == n - 1 else [], fontsize=6.6,
                               rotation=45, ha="right")
            ax.set_yticklabels(short_lbl if j == 0 else [], fontsize=6.6)
            ax.grid(False)
            for s in ax.spines.values():
                s.set_visible(True)
                s.set_linewidth(0.5)
                s.set_color("#666666")
            if annotate_cells:
                for a in range(k):
                    for b in range(k):
                        v = m[a, b]
                        if v:
                            ax.text(b, a, f"{int(v)}", ha="center", va="center",
                                    fontsize=6.4,
                                    color="white" if v > vmax * 0.6 else "#22404f")
            for a in range(k):
                for b in range(k):
                    if a != b and m[a, b] > 0:
                        ax.add_patch(Rectangle((b - 0.5, a - 0.5), 1, 1,
                                               fill=False, edgecolor=RUST,
                                               lw=0.8, zorder=5))
            ax.set_title(f"{r['raw_pct']:.1f} %   $\\kappa$={r['kappa']:.2f}",
                         fontsize=6.4, pad=3)
    for j, m in enumerate(models):
        axes[0, j].annotate(MSHORT.get(m, m), xy=(0.5, 1.30),
                            xycoords="axes fraction", ha="center", va="bottom",
                            fontsize=7.2, fontweight="bold")
    for i, m in enumerate(models):
        axes[i, 0].annotate(MSHORT.get(m, m), xy=(-0.52, 0.5),
                            xycoords="axes fraction", ha="center", va="center",
                            fontsize=7.2, fontweight="bold", rotation=90)
    # One shared colour legend. Do NOT pass ax=axes to fig.colorbar: it steals
    # space from the bottom-row axes and lands on top of their tick labels.
    # Reserve an explicit band instead.
    sm = plt.cm.ScalarMappable(
        cmap=SEQ_CMAP, norm=LogNorm(vmin=0.7, vmax=max(
            2, max((np.asarray(idx[(a, b)]["raw"]).max()
                    for (a, b) in idx), default=2))))
    fig.subplots_adjust(left=0.10, right=0.98, top=0.92, bottom=0.15,
                        wspace=0.30, hspace=0.34)
    cax = fig.add_axes([0.32, 0.062, 0.42, 0.020])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.set_label("comments per cell (log scale)", fontsize=7, labelpad=2)
    cbar.ax.tick_params(labelsize=6.4)
    fig.legend(handles=[Line2D([], [], marker="s", markersize=6, linestyle="none",
                               markerfacecolor="none", markeredgecolor=RUST,
                               markeredgewidth=1.0, label="disagreement")],
               loc="lower left", bbox_to_anchor=(0.02, 0.028), fontsize=6.8)
    _save(fig, f"fig05_confusion_models_{cb}")


# ===================================================== 6 condition A vs B
def fig_confusion_condition(cb: str):
    """Condition A (transcript) vs Condition B (comment-only), per model.

    Generalised over the codebook (the old version hard-coded Codebook A):
      * Codebook A: the binary 2x2 (nein/ja), absolute + row-normalised --
        unchanged in substance.
      * Codebook B: TWO stability questions, both reported:
          row 0  type-level: the full 7-class A x B confusion (colour, log scale)
                   -- does the transcript change the INFERRED KIND of reactance?
          row 1  binary-level: reactant/none collapse with counts (the 4 cells
                   A=no/B=no, A=no/B=yes, A=yes/B=no, A=yes/B=yes)
                   -- are the SAME comments classified as reactant?
    The aggregate prevalence difference is NOT sufficient for either question:
    two conditions can have identical prevalence while labelling different
    comments. This figure is the case-level answer and sits next to the
    transcript claim in the report."""
    cp = [r for r in X.get("condition_pairwise", [])
          if r["cb"] == cb and r.get("raw")]
    if not cp:
        return
    models = _order({r["model"] for r in cp})
    if cb == "A":
        fig, axes = plt.subplots(2, len(models), figsize=(2.05 * len(models), 4.0))
        axes = np.atleast_2d(axes)
        for j, m in enumerate(models):
            r = next((x for x in cp if x["model"] == m), None)
            if not r:
                continue
            for i, (mat, norm, tag) in enumerate(
                    ((r["raw"], False, "absolute"), (r["norm"], True, "row-normalised"))):
                ax = axes[i, j]
                _cmap_grid(ax, mat, ["nein", "ja"], ["nein", "ja"], norm=norm,
                           annot_size=7.0)
                ax.set_xlabel("Condition B", fontsize=6.6)
                if i == 0:
                    ax.set_title(MSHORT.get(m, m), fontsize=7.4, pad=5)
                if j == 0:
                    ax.set_ylabel(f"Condition A\n({tag})", fontsize=6.8)
        fig.tight_layout()
        _save(fig, "fig06_confusion_condition_A")
        return

    # Codebook B: type-level 7x7 (row 0) + binary reactant/none 2x2 (row 1)
    type_lbl = [CLS.get(l, l) for l in LAB_B]
    bin_lbl = ["none", "reactant"]
    fig, axes = plt.subplots(2, len(models), figsize=(2.2 * len(models), 4.7))
    axes = np.atleast_2d(axes)
    for j, m in enumerate(models):
        r = next((x for x in cp if x["model"] == m), None)
        if not r:
            continue
        # row 0: 7x7 type confusion, colour only (log scale -- see fig05)
        ax = axes[0, j]
        mtr = np.asarray(r["raw"], dtype=float)
        vmax = max(int(mtr.max()), 2)
        ax.imshow(mtr, cmap=SEQ_CMAP, norm=LogNorm(vmin=0.7, vmax=vmax),
                  interpolation="nearest", aspect="equal")
        k = len(LAB_B)
        ax.set_xticks(range(k))
        ax.set_yticks(range(k))
        ax.set_xticklabels(type_lbl if j == len(models) - 1 else [],
                           fontsize=5.2, rotation=45, ha="right")
        ax.set_yticklabels(type_lbl if j == 0 else [], fontsize=5.4)
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_linewidth(0.5)
            s.set_color("#666666")
        if j == 0:
            ax.set_ylabel("Condition A\n(type)", fontsize=6.8)
        ax.set_xlabel("Condition B (type)" if j == len(models) - 1 else "",
                      fontsize=6.6)
        ax.set_title(f"{MSHORT.get(m, m)}\n{r['raw_pct']:.1f}% raw agree",
                     fontsize=7.2, pad=4)
        # row 1: binary reactant/none collapse, with counts
        b = r.get("binary")
        ax2 = axes[1, j]
        if b:
            mat = np.asarray([[b["A_no_B_no"], b["A_no_B_yes"]],
                               [b["A_yes_B_no"], b["A_yes_B_yes"]]], dtype=float)
            _cmap_grid(ax2, mat, bin_lbl, bin_lbl, norm=False, annot_size=6.6)
            nflip = b["A_no_B_yes"] + b["A_yes_B_no"]
            ax2.set_title(f"reactant: {b['case_agreement_pct']:.1f}% same\n"
                           f"({nflip} flip)", fontsize=6.8, pad=4)
        else:
            ax2.axis("off")
        ax2.set_xlabel("Condition B (binary)", fontsize=6.6)
        if j == 0:
            ax2.set_ylabel("Condition A\n(binary)", fontsize=6.8)
    fig.tight_layout()
    _save(fig, "fig06_confusion_condition_B")


# ===================================================== 7 codebook A vs B
def fig_confusion_codebook():
    cc = [r for r in X.get("codebook_confusion", []) if r["cond"] == "A"]
    if not cc:
        return
    models = _order({r["model"] for r in cc})
    fig, axes = plt.subplots(2, len(models), figsize=(2.15 * len(models), 4.1))
    axes = np.atleast_2d(axes)
    for j, m in enumerate(models):
        r = next((x for x in cc if x["model"] == m), None)
        if not r:
            continue
        for i, (mat, norm, tag) in enumerate(
                ((r["raw_2x2"], False, "absolute"), (r["norm_2x2"], True, "row-normalised"))):
            ax = axes[i, j]
            _cmap_grid(ax, mat, ["nein", "ja"],
                       ["none", "reactant"], norm=norm, annot_size=7.0)
            ax.set_xlabel("Codebook B", fontsize=6.6)
            if i == 0:
                ax.set_title(f"{MSHORT.get(m, m)}", fontsize=7.4, pad=5)
            if j == 0:
                ax.set_ylabel(f"Codebook A\n({tag})", fontsize=6.8)
    fig.tight_layout()
    _save(fig, "fig07_confusion_codebook")


# ===================================================== 8 calibration
def fig_calibration():
    cal = X.get("calibration", [])
    sweep = X.get("threshold_sweep", [])
    ts = next((s for s in sweep if s["cond"] == "A"), sweep[0] if sweep else None)
    if not cal or not ts:
        return
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.8))
    c = next((x for x in cal if x["cond"] == "A"), cal[0])
    if c["bins"]:
        xs = [0.5 * (b["lo"] + b["hi"]) for b in c["bins"]]
        ys = [b["mean_p"] for b in c["bins"]]
        ns = [b["n"] for b in c["bins"]]
        a1.plot([0, 1], [0, 1], color=GREY, lw=0.7, ls=(0, (4, 3)),
                label="perfectly calibrated", zorder=1)
        a1.plot(xs, ys, "o-", color=BLUE, ms=4.4, lw=1.1, zorder=3, label="Jev")
        for x, y, n in zip(xs, ys, ns):
            a1.annotate(f"{n}", (x, y), textcoords="offset points", xytext=(3, -9),
                        fontsize=5.4, color=GREY)
        a1.set_xlabel("predicted $P(\\mathrm{ja})$")
        a1.set_ylabel("observed rate")
        a1.set_xlim(-0.03, 1.03)
        a1.set_ylim(-0.03, 1.03)
        a1.set_title("(a)  Calibration", loc="left")
        a1.legend(loc="upper left")
    s = ts["sweep"]
    a2.plot([r["coverage_pct"] for r in s], [r["precision"] for r in s],
            "o-", color=RUST, ms=4.2, lw=1.1, zorder=3)
    for r in s:
        a2.annotate(f"{r['t']:.1f}", (r["coverage_pct"], r["precision"]),
                    textcoords="offset points", xytext=(4, -3), fontsize=5.4,
                    color=GREY)
    a2.axhline(46, color=GREY, lw=0.7, ls=(0, (4, 3)))
    a2.annotate("46 % without threshold", (20, 50), fontsize=5.8, color=GREY)
    a2.set_xlabel("flagged share of comments (%)")
    a2.set_ylabel("precision vs majority vote")
    a2.set_ylim(0, 100)
    a2.set_title("(b)  Threshold trade-off", loc="left")
    fig.tight_layout()
    _save(fig, "fig08_calibration")


# ===================================================== 9 reliability
def fig_reliability():
    if not PARA and not RELI:
        return
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    if PARA:
        per = PARA["per_stratum"]
        ks = [k for k in ("3", "2", "1", "0") if k in per]
        labs = [f"{k} of 3" if k != "0" else "control" for k in ks]
        variants = ["T1_deemphasis", "T2_politeness", "T3_defiller"]
        names = ["emphasis", "politeness", "filler"]
        cols = ["#8fb0c0", RUST, "#b9c9a8"]
        w = 0.26
        x = np.arange(len(ks))
        for i, (v, nm) in enumerate(zip(variants, names)):
            ys = [per[k].get(v) or 0 for k in ks]
            axes[0].bar(x + (i - 1) * w, ys, w, label=nm, color=cols[i],
                        edgecolor="#333", linewidth=0.45)
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(labs, fontsize=7.0)
        axes[0].set_ylabel("label unchanged (%)")
        axes[0].set_ylim(0, 118)
        axes[0].legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.34))
        axes[0].set_title("(a)  Surface robustness", loc="left")
    if RELI:
        e2 = RELI["E2_repeat_stability"]
        vals = [e2.get("negatives_only_pct") or 0, e2.get("positives_only_pct") or 0,
                e2.get("overall_pct") or 0]
        labs = ["control", "positives", "overall"]
        axes[1].bar(range(3), vals, 0.55, color=["#bccfd9", RUST, BLUE],
                    edgecolor="#333", linewidth=0.45)
        for i, v in enumerate(vals):
            axes[1].annotate(f"{v:.1f}", (i, v), textcoords="offset points",
                             xytext=(0, 4), ha="center", fontsize=6.8,
                             fontweight="bold")
        axes[1].set_xticks(range(3))
        axes[1].set_xticklabels(labs, fontsize=7.0)
        axes[1].set_ylabel("label stable (%)")
        axes[1].set_ylim(0, 110)
        axes[1].set_title("(b)  Repeat stability", loc="left")
    fig.tight_layout()
    _save(fig, "fig09_reliability")


# ===================================================== 10 big scale
def fig_bigscale():
    """Large-scale sample (n=2,001, condition B, Jev + GLM).

    (a) Prevalence per model and codebook (Jev + GLM) with Jev's 95% CI;
    (b) Jev's confidence-band structure.
    """
    if not BIG:
        return
    PA, PB = BIG["prevalence_A"], BIG["prevalence_B"]
    models = [m for m in ("jev-1.13", "glm-5.3-flash") if m in PA]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.8))
    for i, P in enumerate((PA, PB)):
        for j, m in enumerate(models):
            r = P[m]
            a1.bar([i + j * 0.42 - 0.21], [r["prevalence_pct"]], 0.38,
                   color=MODEL_COLOR[m], edgecolor="#333", linewidth=0.5,
                   label=f"Codebook {['A','B'][i]}: {MSHORT[m]}")
            if m == "jev-1.13" and r.get("ci95"):
                a1.errorbar([i - 0.21], [r["prevalence_pct"]],
                             yerr=[[r["prevalence_pct"] - r["ci95"][0]],
                                   [r["ci95"][1] - r["prevalence_pct"]]],
                             fmt="none", ecolor="#222", elinewidth=1.0,
                             capsize=3, zorder=4)
            a1.annotate(f"{r['prevalence_pct']:.1f}%", (i + j * 0.42 - 0.21,
                        r["prevalence_pct"]), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=6.6,
                        fontweight="bold")
            a1.annotate(f"n+={r['n_positive']}", (i + j * 0.42 - 0.21, 0.28),
                        ha="center", fontsize=5.8, color="white")
    a1.set_xticks([0.21, 1.21])
    a1.set_xticklabels(["Codebook A (binary)", "Codebook B (type)"], fontsize=7.4)
    a1.set_ylabel("Prevalence (%)")
    a1.set_ylim(0, 11.5)
    a1.legend(fontsize=6.2, frameon=False, loc="upper left", ncols=2)
    a1.set_title("(a)  Large-scale sample, n = 2,001 (Jev + GLM, cond. B)",
                 loc="left", fontsize=8)
    _ja = PA.get("jev-1.13", {})
    if _ja.get("ci95"):
        a1.annotate(f"95% CI (Jev, A): [{_ja['ci95'][0]}; {_ja['ci95'][1]}]",
                    xy=(0, 10.8), ha="center", fontsize=6.2, color="#444")
    cb = BIG["confidence_bands"]
    order = ["<0.1", "0.1-0.3", "0.3-0.6", "0.6-0.9", ">=0.9"]
    rates = [cb.get(k, {}).get("rate_pct") or 0 for k in order]
    ns = [cb.get(k, {}).get("n", 0) for k in order]
    cols = [BAND["neg"] if r == 0 else (BAND["mid"] if r < 50 else BAND["pos"])
            for r in rates]
    a2.bar(range(5), rates, 0.55, color=cols, edgecolor="#333", linewidth=0.5)
    for i, (r, n) in enumerate(zip(rates, ns)):
        a2.annotate(f"{r:.0f} %", (i, r), textcoords="offset points", xytext=(0, 4),
                    ha="center", fontsize=6.8, fontweight="bold")
        a2.annotate(f"{n}", (i, 3), ha="center", fontsize=6.0, color="white")
    a2.set_xticks(range(5))
    a2.set_xticklabels(["$<0{,}1$", "0,1–0,3", "0,3–0,6", "0,6–0,9", "$\\geq0{,}9$"],
                       fontsize=6.6)
    a2.set_xlabel("confidence band $P(\\mathrm{ja})$")
    a2.set_ylabel("coded positive (%)")
    a2.set_ylim(0, 112)
    a2.set_title("(b)  Confidence bands", loc="left")
    fig.tight_layout()
    _save(fig, "fig10_bigscale")


# ===================================================== 11 gate confusion grid
def fig_gate_matrix():
    """Gated condition, CONDITIONAL SIX-CLASS type confusion grid (main figure).

    Each cell is the six-class (type) confusion matrix of ONE model pair, drawn
    only over the comments on which BOTH models retained Jev's positive gate
    (i.e. neither re-labelled it `keine_reaktanz`). The question the figure
    answers: "given that two models both agree the gate is right, which reactance
    types do they confuse?" The gate question (do they agree the gate is right
    at all?) is a DIFFERENT question and lives in fig_gate_rejection, not here.
    Class support per column (which types are effectively empty on this set) is
    annotated, because a six-class kappa on near-empty classes is not a robust
    global statistic (report section: sparse type classes)."""
    runs = GATE.get("runs", {})
    r = (runs.get("matrix", {}).get("conditions") or {}).get("B")
    if not r or not r.get("pairwise_type"):
        return
    models = _order(r["models"])
    idx = {}
    for pw in r["pairwise_type"]:
        idx[(pw["a"], pw["b"])] = pw
        idx[(pw["b"], pw["a"])] = pw
    n = len(models)
    TYPE_LBL = [l for l in LAB_B if l != "keine_reaktanz"]
    short_lbl = [CLS.get(l, l) for l in TYPE_LBL]
    cell = 1.66
    fig, axes = plt.subplots(n, n, figsize=(cell * n + 0.85, cell * n + 0.75))
    axes = np.atleast_2d(axes)
    vmax_all = 1
    for i, ma in enumerate(models):
        for j, mb in enumerate(models):
            ax = axes[i, j]
            if ma == mb:
                ax.set_facecolor("#f2f2f2")
                for s in ax.spines.values():
                    s.set_visible(False)
                ax.set_xticks([]); ax.set_yticks([])
                ax.grid(False)
                continue
            pw = idx.get((ma, mb))
            if not pw:
                ax.axis("off")
                continue
            m = np.asarray(pw["raw"], dtype=float)
            vmax_all = max(vmax_all, int(m.max()))
            ax.imshow(m, cmap=SEQ_CMAP, norm=LogNorm(vmin=0.7, vmax=max(2, m.max())),
                      interpolation="nearest", aspect="equal")
            k = len(short_lbl)
            ax.set_xticks(range(k))
            ax.set_yticks(range(k))
            ax.set_xticklabels(short_lbl if i == n - 1 else [], fontsize=6.4,
                               rotation=45, ha="right")
            ax.set_yticklabels(short_lbl if j == 0 else [], fontsize=6.4)
            ax.grid(False)
            for s in ax.spines.values():
                s.set_visible(True)
                s.set_linewidth(0.5)
                s.set_color("#666666")
            for a in range(k):
                for b in range(k):
                    v = m[a, b]
                    if v:
                        ax.text(b, a, f"{int(v)}", ha="center", va="center",
                                fontsize=6.0,
                                color="white" if v > vmax_all * 0.6 else "#22404f")
                    if a != b and v > 0:
                        ax.add_patch(Rectangle((b - 0.5, a - 0.5), 1, 1,
                                               fill=False, edgecolor=RUST,
                                               lw=0.8, zorder=5))
            ax.set_title(f"n={pw['n']}  {pw['raw_pct']:.0f}%  $\\kappa$={pw['kappa']:.2f}",
                         fontsize=6.2, pad=3)
    for j, m in enumerate(models):
        axes[0, j].annotate(MSHORT.get(m, m), xy=(0.5, 1.30),
                            xycoords="axes fraction", ha="center", va="bottom",
                            fontsize=7.0, fontweight="bold")
    for i, m in enumerate(models):
        axes[i, 0].annotate(MSHORT.get(m, m), xy=(-0.52, 0.5),
                            xycoords="axes fraction", ha="center", va="center",
                            fontsize=7.0, fontweight="bold", rotation=90)
    sm = plt.cm.ScalarMappable(
        cmap=SEQ_CMAP, norm=LogNorm(vmin=0.7, vmax=max(2, vmax_all)))
    fig.subplots_adjust(left=0.10, right=0.98, top=0.92, bottom=0.15,
                        wspace=0.30, hspace=0.34)
    cax = fig.add_axes([0.32, 0.062, 0.42, 0.020])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.set_label("comments per cell (log scale)", fontsize=7, labelpad=2)
    cbar.ax.tick_params(labelsize=6.4)
    fig.legend(handles=[Line2D([], [], marker="s", markersize=6, linestyle="none",
                               markerfacecolor="none", markeredgecolor=RUST,
                               markeredgewidth=1.0, label="disagreement")],
               loc="lower left", bbox_to_anchor=(0.02, 0.028), fontsize=6.8)
    # sparse-class support annotation: which of the six types have (almost) no
    # support on the gated set. A global six-class kappa is only as meaningful as
    # the emptiest class, so the report shows the per-type counts explicitly.
    total_support = {tl: 0 for tl in TYPE_LBL}
    for td in r.get("type_distribution", []):
        for tl in TYPE_LBL:
            total_support[tl] += td["dist"].get(tl, 0)
    fig.text(0.98, 0.005,
             "type support on the gated set: " +
             ", ".join(f"{short_lbl[i]}={total_support[tl]}"
                       for i, tl in enumerate(TYPE_LBL)),
             ha="right", fontsize=6.2, color="#444")
    _save(fig, "fig11_gate_confusion")


# ===================================================== 11b gate rejection (separate, simple)
def fig_gate_rejection():
    """Gate-consistency panel (the OTHER half of the gated question).

    For every downstream model: of the comments Jev's gate let through, the share
    RETAINING the gate (model assigns one of the six types) vs REJECTING it
    (model re-labels `keine_reaktanz`). One horizontal stacked bar per model.
    This is a gate-rejection diagnostic, NOT type disagreement -- which is why
    it is its own figure next to, and not mixed into, fig11."""
    r = ((GATE.get("runs", {}) or {}).get("matrix", {})
         .get("conditions") or {}).get("B") or {}
    gc = r.get("gate_consistency")
    if not gc:
        return
    models = _order([g["model"] for g in gc])
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    y = np.arange(len(models))[::-1]
    for i, m in enumerate(models):
        g = next(x for x in gc if x["model"] == m)
        tot = max(1, g["n"])
        ret = 100 * g["n_accept"] / tot
        rej = 100 * g["n_reject"] / tot
        ax.barh(y[i], ret, left=0, color=BLUE, edgecolor="#333", linewidth=0.4,
                label="retain gate (a type)" if i == len(models) - 1 else None)
        ax.barh(y[i], rej, left=ret, color=RUST, edgecolor="#333", linewidth=0.4,
                label="reject gate (`keine_reaktanz`)" if i == len(models) - 1 else None)
        ax.text(ret / 2, y[i], f"retain {ret:.0f}%\n({g['n_accept']}/{g['n']})",
                ha="center", va="center", fontsize=6.4, color="white", fontweight="bold")
        ax.text(ret + rej / 2, y[i], f"reject {rej:.0f}%\n({g['n_reject']})",
                ha="center", va="center", fontsize=6.4,
                color="white" if rej > 25 else "#22404f", fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels([MSHORT.get(m, m) for m in models], fontsize=7.0)
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of Jev-gated comments (%)", fontsize=7.2)
    ax.set_title("(Jev gate, matrix sample, Condition B)", loc="left", fontsize=7.2)
    ax.legend(loc="lower right", fontsize=6.4)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    _save(fig, "fig13_gate_rejection")


# ===================================================== 12 gate majority vote
def fig_gate_majority():
    """Conditional type consensus on the gated set, reported as TWO quantities
    that the old single 'majority' figure conflated (matrix sample, condition B):

      (a) gate acceptance  : 1/4 .. 4/4 -- how many models retained the gate
      (b) type consensus    : among the models that retained it, how strongly do
                              their type labels agree (k-of-n plurality, where a
                              2-2 split is a TIE, not a 2-of-4 majority)
    Ties are never resolved by label order, and no model is scored against an
    arbitrarily tie-broken reference (the per-model agreement panel omits tied
    comments)."""
    r = ((GATE.get("runs", {}) or {}).get("matrix", {})
         .get("conditions") or {}).get("B") or {}
    tc = r.get("type_consensus")
    if not tc or not tc.get("gate_accept"):
        return
    n_v = tc["n_voters"]
    n_gate = tc["n_gated"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.7))

    # (a) gate acceptance distribution (all n_gated comments)
    ga = tc["gate_accept"]
    ks = [n_v - i for i in range(n_v + 1)]          # 4,3,2,1,0
    ga_vals = [ga.get(f"{k}-of-{n_v}", 0) for k in ks]
    xs = np.arange(len(ks))
    a1.bar(xs, ga_vals, 0.5, color=[BAND["neg"], "#9fb3bf", BAND["mid"], BLUE, BLUE][:len(xs)],
           edgecolor="#333", linewidth=0.5)
    for i, (k, v) in enumerate(zip(ks, ga_vals)):
        a1.annotate(f"{v}", (i, v), textcoords="offset points", xytext=(0, 2),
                    ha="center", fontsize=6.8, fontweight="bold")
        a1.annotate(f"{v / n_gate:.0%}", (i, v), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=5.8, color="#444")
    a1.set_xticks(xs)
    a1.set_xticklabels([f"{k}/{n_v}" for k in ks], fontsize=7.0)
    a1.set_ylabel("gated comments (n=" + f"{n_gate})")
    a1.set_title("(a)  Gate acceptance: models retaining reactance", loc="left")

    # (b) type consensus among the RETAINERS (ties shown, not resolved)
    tcs = tc["type_consensus"]
    ks2 = [n_v - i for i in range(n_v + 1)]          # 4,3,2,1,0
    tcs_vals = [tcs.get(f"{k}-of-{n_v}", 0) for k in ks2]
    n_tie = tcs.get("tie", 0)
    xs2 = np.arange(len(ks2) + 1)
    b2_vals = tcs_vals + [n_tie]
    cols2 = ([BAND["neg"], "#9fb3bf", BAND["mid"], BLUE, BLUE][:len(ks2)]
              + [GREY])
    a2.bar(xs2, b2_vals, 0.5, color=cols2, edgecolor="#333", linewidth=0.5)
    for i, (k, v) in enumerate(zip(ks2, tcs_vals)):
        a2.annotate(f"{v}", (i, v), textcoords="offset points", xytext=(0, 2),
                    ha="center", fontsize=6.8, fontweight="bold")
    a2.annotate(f"{n_tie}", (len(ks2), n_tie), textcoords="offset points",
                xytext=(0, 2), ha="center", fontsize=6.8, fontweight="bold", color=GREY)
    a2.set_xticks(xs2)
    a2.set_xticklabels([f"{k}/{n_v}" for k in ks2] + ["2-2\ntie"], fontsize=7.0)
    a2.set_ylabel("gated comments")
    a2.set_title("(b)  Type consensus among the models that retained it", loc="left")
    fig.tight_layout()
    _save(fig, "fig12_gate_majority")


ALL = (
    ("prevalence", fig_prevalence),
    ("audit", fig_audit),
    ("agreement", fig_agreement),
    ("cost", fig_cost),
    ("confusion-models-A", lambda: fig_confusion_models("A")),
    ("confusion-models-B", lambda: fig_confusion_models("B")),
    ("confusion-condition-A", lambda: fig_confusion_condition("A")),
    ("confusion-condition-B", lambda: fig_confusion_condition("B")),
    ("confusion-codebook", fig_confusion_codebook),
    ("calibration", fig_calibration),
    ("reliability", fig_reliability),
    ("bigscale", fig_bigscale),
    ("gate-confusion", fig_gate_matrix),
    ("gate-rejection", fig_gate_rejection),
    ("gate-majority", fig_gate_majority),
)


def main(only: str | None = None) -> None:
    _style()
    for name, fn in ALL:
        if only and only != name:
            continue
        try:
            print(f"  {name} ...")
            fn()
        except Exception as e:                                     # noqa: BLE001
            print(f"    SKIP {name}: {type(e).__name__}: {e}")
    print("figures ->", FIG)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
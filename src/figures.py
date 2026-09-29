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
        ax.set_ylim(0, 9.6)
        ax.axhline(0, color="#333", lw=0.6)
    axes[0].set_ylabel("Reactance share (%)")
    fig.tight_layout()
    _save(fig, "fig01_prevalence")


# ===================================================== 2 audit
def fig_audit():
    if not AUD:
        return
    pool = {}
    for row in (X.get("_pool") or []):
        pool[row["uid"]] = row
    preds = [json.loads(l) for l in
             (RES / "predictions_full.jsonl").open(encoding="utf-8")]
    flags = {}
    for p in preds:
        if p["codebook"] == "A" and p["condition"] == "A" and p["label"] == "ja":
            flags.setdefault(p["uid"], set()).add(p["model"])
    sizes = [sum(1 for v in flags.values() if len(v) == k) for k in (3, 2, 1)]
    precs, ns = [], []
    for k in (3, 2, 1):
        sub = [r for r in AUD if r["n_models"] == k]
        precs.append(100 * sum(1 for r in sub if r["verdict"] == "ja") / max(1, len(sub)))
        ns.append(len(sub))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.7),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    cols = [BLUE, "#7ea7bd", "#bccfd9"]
    bars = a1.bar(range(3), precs, 0.55, color=cols, edgecolor="#333", linewidth=0.5)
    import math
    err = [1.96 * math.sqrt(max(p, 0.01) * (100 - p) / 12) for p in precs]
    a1.errorbar(range(3), precs, yerr=err, fmt="none", ecolor="#222",
                elinewidth=0.9, capsize=3, zorder=4)
    for i, (p, n) in enumerate(zip(precs, ns)):
        a1.annotate(f"{p:.0f} %", (i, p + err[i]), textcoords="offset points",
                    xytext=(0, 5), ha="center", fontsize=7.4, fontweight="bold")
        a1.annotate(f"n={n}", (i, 4), ha="center", fontsize=6.4, color="white")
    a1.set_xticks(range(3))
    a1.set_xticklabels(["3 of 3\nmodels", "2 von 3", "1 von 3"], fontsize=7.2)
    a1.set_ylabel("Precision (%)")
    a1.set_ylim(0, 116)
    a1.set_title("(a)  Precision by consensus", loc="left")
    tot = sum(sizes)
    sh = [100 * s / tot for s in sizes]
    a2.bar(range(3), sh, 0.55, color=cols, edgecolor="#333", linewidth=0.5)
    for i, (v, s) in enumerate(zip(sh, sizes)):
        a2.annotate(f"{v:.0f} %", (i, v), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=7.2, fontweight="bold")
        a2.annotate(f"n={s}", (i, 3), ha="center", fontsize=6.4, color="white")
    a2.set_xticks(range(3))
    a2.set_xticklabels(["3/3", "2/3", "1/3"], fontsize=7.2)
    a2.set_ylabel("Share of all 119 positives (%)")
    a2.set_ylim(0, 68)
    a2.set_title("(b)  Distribution of positives", loc="left")
    fig.tight_layout()
    _save(fig, "fig02_audit")


# ===================================================== 3 agreement (dual axis)
def fig_agreement():
    mp = X.get("model_pairwise", [])
    if not mp:
        return
    ABBR = {"jev-1.13": "jev", "gpt-6-luna": "gpt6",
            "deepseek-v4.1-flash": "deep", "glm-5.3-flash": "glm"}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    twins = []
    for ax, cb in zip(axes, ("A", "B")):
        data = [r for r in mp if r["cb"] == cb and r["cond"] == "A"]
        if not data:
            continue
        ax2 = ax.twinx()
        twins.append(ax2)
        x = np.arange(len(data))
        w = 0.3
        raw = [d["raw_pct"] for d in data]
        kap = [d["kappa"] for d in data]
        ac1 = [d["ac1"] for d in data]
        ax.bar(x - w / 2, raw, w, color="#cfdae1", edgecolor="#333",
               linewidth=0.45, label="Raw agreement (%)", zorder=2)
        for i, v in enumerate(raw):
            ax.annotate(f"{v:.1f}", (x[i] - w / 2, v), textcoords="offset points",
                        xytext=(0, 3), ha="center", fontsize=6.2)
        ax.set_ylim(0, 112)
        ax.set_ylabel("Raw agreement (%)", fontsize=7.6)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{ABBR.get(d['a'], d['a'])}–{ABBR.get(d['b'], d['b'])}"
                            for d in data], fontsize=6.6, rotation=20, ha="right")
        ax.set_title(f"Codebook {cb}", loc="left")
        ax2.plot(x - w / 2, kap, "o", color=BLUE, ms=4.6, label="Cohen's $\\kappa$",
                 zorder=3)
        ax2.plot(x + w / 2, ac1, "s", color=RUST, ms=4.6, label="Gwet's AC1", zorder=3)
        for i in range(len(data)):
            ax2.annotate(f"{kap[i]:.2f}", (x[i] - w / 2, kap[i]),
                         textcoords="offset points", xytext=(0, -10), ha="center",
                         fontsize=6.0, color=BLUE)
            ax2.annotate(f"{ac1[i]:.2f}", (x[i] + w / 2, ac1[i]),
                         textcoords="offset points", xytext=(0, 5), ha="center",
                         fontsize=6.0, color=RUST)
        ax2.set_ylim(0, 1.12)
        ax2.set_ylabel("Chance-corrected (0–1)", fontsize=7.6)
        ax2.grid(False)
        ax2.spines["right"].set_visible(True)
    h1, l1 = axes[0].get_legend_handles_labels()
    h2, l2 = twins[0].get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, ncol=3, loc="lower center",
               bbox_to_anchor=(0.5, -0.04), handlelength=1.4)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.subplots_adjust(wspace=0.55)
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
def fig_confusion_condition():
    cp = [r for r in X.get("condition_pairwise", [])
          if r["cb"] == "A" and r.get("raw")]
    if not cp:
        return
    models = _order({r["model"] for r in cp})
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
    _save(fig, "fig06_confusion_condition")


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
    if not BIG:
        return
    a, b = BIG["codebook_A"], BIG["codebook_B"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.8))
    vals = [a["prevalence_pct"], b["prevalence_pct"]]
    a1.bar([0, 1], vals, 0.5, color=[BLUE, RUST], edgecolor="#333", linewidth=0.5)
    a1.errorbar([0], [a["prevalence_pct"]],
                yerr=[[a["prevalence_pct"] - a["ci95"][0]],
                      [a["ci95"][1] - a["prevalence_pct"]]],
                fmt="none", ecolor="#222", elinewidth=1.0, capsize=4, zorder=4)
    for i, r in enumerate((a, b)):
        a1.annotate(f"{vals[i]:.2f} %", (i, vals[i]), textcoords="offset points",
                    xytext=(0, 8 if i == 0 else 10), ha="center", fontsize=7.4,
                    fontweight="bold")
        a1.annotate(f"n={r['n_positive']}", (i, 0.12), ha="center", fontsize=6.4,
                    color="white")
    a1.set_xticks([0, 1])
    a1.set_xticklabels(["Codebook A\n(binary)", "Codebook B\n(7 Typen)"], fontsize=7.4)
    a1.set_ylabel("Prevalence (%)")
    a1.set_ylim(0, 4.8)
    a1.set_title("(a)  Prevalence", loc="left")
    a1.annotate(f"95% CI, A: [{a['ci95'][0]}; {a['ci95'][1]}]", xy=(0.5, 4.3),
                ha="center", fontsize=6.2, color="#444")
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


ALL = (
    ("prevalence", fig_prevalence),
    ("audit", fig_audit),
    ("agreement", fig_agreement),
    ("cost", fig_cost),
    ("confusion-models-A", lambda: fig_confusion_models("A")),
    ("confusion-models-B", lambda: fig_confusion_models("B")),
    ("confusion-condition", fig_confusion_condition),
    ("confusion-codebook", fig_confusion_codebook),
    ("calibration", fig_calibration),
    ("reliability", fig_reliability),
    ("bigscale", fig_bigscale),
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
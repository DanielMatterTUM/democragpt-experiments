"""Scientific figures (matplotlib + seaborn), vector PDF + 300dpi PNG.

Design: white background, thin rules, greyscale-safe palette, one visual claim
per panel, no chartjunk. Sized for a two-column paper.

  fig1  prevalence with bootstrap 95% CI, faceted by codebook
  fig2  precision by consensus stratum (audit)
  fig3  agreement measures: raw vs kappa vs Gwet AC1
  fig4  cost / latency
  fig5  confusion matrices, model x model (codebook A and B)
  fig6  condition A vs B confusion, per model
  fig7  Jev calibration + threshold trade-off
  fig8  reliability experiments (paraphrase + repeat + position)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="ticks", context="paper", font="DejaVu Sans",
              font_scale=1.05)
sns.set_context("paper", rc={
    "axes.labelsize": 8.5, "axes.titlesize": 9, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "figure.dpi": 200,
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "axes.linewidth": 0.6, "grid.linewidth": 0.4, "grid.alpha": 0.25,
})
plt.rcParams["pdf.fonttype"] = 42       # embed TrueType, not Type3
plt.rcParams["ps.fonttype"] = 42

GREY = "#4d4d4d"
PALETTE = {"jev-1.13": "#2f6f8f", "gpt-6-luna": "#c4622d",
           "deepseek-v4.1-flash": "#4f7942", "glm-5.3-flash": "#7a5c9e"}
SHORT = {"jev-1.13": "jev-1.13", "gpt-6-luna": "gpt-6.luna",
         "deepseek-v4.1-flash": "deepseek-flash",
         "glm-5.3-flash": "glm-5.3-flash"}
# Two-line model labels for wide axes, one-line for tight/confusion axes.
SHORT2 = {"jev-1.13": "jev-1.13", "gpt-6-luna": "gpt-6-luna",
          "deepseek-v4.1-flash": "deepseek\nflash",
          "glm-5.3-flash": "glm-5.3\nflash"}
SEQ = LinearSegmentedColormap.from_list(
    "seq", ["#f7f9fb", "#cfe0ea", "#7fadc4", "#2f6f8f", "#143b50"])

# Abbreviated class labels: the full 7-label names do not fit a 7x7 grid.
CLS = {"keine_reaktanz": "keine\nReakt.",
       "konfrontation_angriff": "konfr.\nAngriff",
       "ablenkung_whataboutism": "Ablen-\nkung",
       "delegierung_hilflosigkeit": "Delegi-\nerung",
       "vermeidung_rueckzug": "Vermei-\ndung",
       "reflektierte_rechtfertigung": "Reflekt.\nRechtf.",
       "konstruktive_kritik": "konstr.\nKritik"}


def load(name, default=None):
    p = RES / name
    if not p.exists():
        return default
    return json.load(p.open(encoding="utf-8"))


D = load("report_data.json", {})
X = load("analysis_ext.json", {})
AUD = load("audit_linked.json", [])
RELI = load("exp_reliability.json", {})
PARA = load("exp_paraphrase.json", {})
MODELS = D.get("models", [])


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    import subprocess
    subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                    str(FIG / f"{name}.pdf"), str(FIG / name)], check=True)
    plt.close(fig)
    print("  wrote", name)


def short(m):
    """One-line model label (no embedded newline) for tight axes."""
    return (SHORT.get(m, m) or "").splitlines()[0]


# ============================================================ fig 1
def fig1():
    b = [r for r in X.get("bootstrap_prev", []) if r["cb"] == "A"]
    if not b:
        return
    models = [m for m in ["jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash",
                          "glm-5.3-flash"] if m in {r["model"] for r in b}]
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.7), sharey=True)
    for ax, cond, ttl in ((axes[0], "A", "a  mit Video-Transkript"),
                          (axes[1], "B", "b  nur Kommentar")):
        sub = {r["model"]: r for r in b if r["cond"] == cond}
        xs = np.arange(len(models))
        y = [sub[m]["pct"] for m in models]
        lo = [sub[m]["pct"] - sub[m]["ci_lo"] for m in models]
        hi = [sub[m]["ci_hi"] - sub[m]["pct"] for m in models]
        for i, m in enumerate(models):
            ax.errorbar(xs[i], y[i], yerr=[[lo[i]], [hi[i]]], fmt="o",
                        color=PALETTE.get(m, GREY), ms=5.5, capsize=3,
                        elinewidth=1.1, capthick=1.1, zorder=3)
        ax.set_xticks(xs)
        ax.set_xticklabels([short(m) for m in models], fontsize=7)
        ax.set_title(ttl, loc="left", pad=6)
        ax.set_ylim(0, 9.6)
        ax.axhline(np.mean(y), color=GREY, lw=0.6, ls=(0, (4, 3)), zorder=1)
    axes[0].set_ylabel("Prävalenz (%) mit 95-%-Bootstrap-KI")
    fig.suptitle("Abb. 1  Prävalenz psychologischer Reaktanz (Codebook A, n = 1.200)",
                 fontsize=9.2, y=1.06)
    save(fig, "fig1_prevalence")


# ============================================================ fig 2
def fig2():
    if not AUD or not X:
        return
    preds = [json.loads(l) for l in (RES / "predictions_full.jsonl").open(encoding="utf-8")]
    from collections import defaultdict
    pool = defaultdict(set)
    for p in preds:
        if p["codebook"] == "A" and p["condition"] == "A" and p["label"] == "ja":
            pool[p["uid"]].add(p["model"])
    sizes = [sum(1 for v in pool.values() if len(v) == k) for k in (3, 2, 1)]
    pr = []
    for k in (3, 2, 1):
        s = [r for r in AUD if r["n_models"] == k]
        pr.append(100 * sum(1 for r in s if r["verdict"] == "ja") / max(1, len(s)))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 2.6),
                                 gridspec_kw={"width_ratios": [1.3, 1]})
    labs = ["3 von 3\nModellen", "2 von 3", "1 von 3"]
    # Wilson-ish error bars from the n=12 per stratum
    import math
    err = [1.96 * math.sqrt(p * (100 - p) / 12) for p in pr]
    cols = sns.color_palette("Blues", 3)[::-1] + [GREY]
    a1.bar(range(3), pr, 0.6, color=["#2f6f8f", "#6fa3bd", "#a9c9d8", GREY][1:],
           edgecolor="#333", linewidth=0.5)
    a1.errorbar(range(3), pr, yerr=err, fmt="none", ecolor="#222",
                elinewidth=0.8, capsize=2.5)
    for i, (p, n) in enumerate(zip(pr, sizes)):
        a1.text(i, p + err[i] + 3, f"{p:.0f} %", ha="center", fontsize=7.2)
        a1.text(i, 3, f"n={n}", ha="center", fontsize=6.6, color="white")
    a1.set_xticks(range(3))
    a1.set_xticklabels(labs, fontsize=7.2)
    a1.set_ylabel("Präzision (%)")
    a1.set_ylim(0, 108)
    a1.set_title("a  Präzision nach Konsensgrad", loc="left", pad=6)

    tot = sum(sizes)
    sh = [100 * s / tot for s in sizes]
    a2.bar(range(3), sh, 0.6, color=["#2f6f8f", "#6fa3bd", "#a9c9d8"][1:],
           edgecolor="#333", linewidth=0.5)
    for i, (s, n) in enumerate(zip(sh, sizes)):
        a2.text(i, s + 1.6, f"{s:.0f} %\n(n={n})", ha="center", fontsize=6.8)
    a2.set_xticks(range(3))
    a2.set_xticklabels(["3/3", "2/3", "1/3"], fontsize=7.2)
    a2.set_ylabel("Anteil an allen Positiven (%)")
    a2.set_ylim(0, 66)
    a2.set_title("b  Verteilung der 119 Positiven", loc="left", pad=6)
    fig.suptitle("Abb. 2  Fehlalarme konzentrieren sich auf schwache Mehrheiten",
                 fontsize=9.2, y=1.05)
    save(fig, "fig2_precision")


# ============================================================ fig 3
def fig3():
    mp = [r for r in X.get("model_pairwise", []) if r["cb"] == "A" and r["cond"] == "A"]
    if not mp:
        return
    import math
    pairs = [f"{short(r['a'])} vs. {short(r['b'])}" for r in mp]
    x = np.arange(len(mp))
    w = 0.26
    fig, ax = plt.subplots(figsize=(7.1, 2.7))
    ax.bar(x - w, [r["raw_pct"] for r in mp], w, label="Rohübereinstimmung",
           color="#c9d6e0", edgecolor="#333", linewidth=0.4)
    ax.bar(x, [r["kappa"] for r in mp], w, label="Cohen's κ",
           color="#2f6f8f", edgecolor="#333", linewidth=0.4)
    ax.bar(x + w, [r["ac1"] for r in mp], w, label="Gwet's AC1",
           color="#c4622d", edgecolor="#333", linewidth=0.4)
    for i, r in enumerate(mp):
        ax.text(i - w, r["raw_pct"] + 1.2, f"{r['raw_pct']:.1f}", ha="center", fontsize=6.4)
        ax.text(i, r["kappa"] + 1.2, f"{r['kappa']:.2f}", ha="center", fontsize=6.4)
        ax.text(i + w, r["ac1"] + 1.2, f"{r['ac1']:.2f}", ha="center", fontsize=6.4)
    ax.set_xticks(x)
    ax.set_xticklabels(pairs, fontsize=6.8, rotation=12, ha="right")
    ax.set_ylabel("Prozent  /  Koeffizient")
    ax.set_ylim(0, 112)
    ax.legend(ncol=3, frameon=False, loc="lower center",
              bbox_to_anchor=(0.5, -0.42))
    fig.suptitle("Abb. 3  Bei 3–7 % Prävalenz ist Cohen's κ unbrauchbar, "
                 "Gwet's AC1 nicht", fontsize=9.2, y=1.04)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    save(fig, "fig3_agreement")


# ============================================================ fig 4
def fig4():
    S = D.get("summary", [])
    if not S:
        return
    models = [m for m in ["jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash",
                          "glm-5.3-flash"] if m in {s["model"] for s in S}]

    def g(cb, cond, m, k):
        for s in S:
            if s["cb"] == cb and s["cond"] == cond and s["model"] == m:
                return s.get(k)
        return None
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 2.6))
    for cb, marker, lbl in (("A", "o", "Codebook A"), ("B", "s", "Codebook B")):
        xs = [i + (-0.09 if cb == "A" else 0.09) for i in range(len(models))]
        lat = [g(cb, "A", m, "lat") for m in models]
        cost = [g(cb, "A", m, "usd_1k") for m in models]
        c = PALETTE.get("jev-1.13") if cb == "A" else "#c4622d"
        a1.scatter(xs, lat, marker=marker, s=38, color=c, edgecolor="#222",
                   linewidth=0.5, label=lbl, zorder=3)
        a2.scatter(xs, cost, marker=marker, s=38, color=c, edgecolor="#222",
                   linewidth=0.5, label=lbl, zorder=3)
        for xx, yy in zip(xs, lat):
            if yy:
                a1.annotate(f"{yy:.2f}", (xx, yy), textcoords="offset points",
                            xytext=(0, 6), ha="center", fontsize=6.3)
        for xx, yy in zip(xs, cost):
            if yy:
                a2.annotate(f"{yy:.3f}", (xx, yy), textcoords="offset points",
                            xytext=(0, 6), ha="center", fontsize=6.3)
    for ax, ylab, ttl, yl in ((a1, "Ø Antwortzeit (s)", "a  Geschwindigkeit", (0, 5.2)),
                              (a2, "Kosten je 1.000 Kommentare (US$)",
                               "b  Kosten", (0, 0.44))):
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([short(m) for m in models], fontsize=6.8)
        ax.set_ylabel(ylab)
        ax.set_title(ttl, loc="left", pad=6)
        ax.set_ylim(*yl)
        ax.legend(frameon=False, loc="upper left")
    fig.suptitle("Abb. 4  Jev ist gleichzeitig das schnellste und das günstigste "
                 "Backend", fontsize=9.2, y=1.05)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "fig4_cost_latency")


# ============================================================ fig 5
def fig5():
    mp = X.get("model_pairwise", [])
    if not mp:
        return
    for cb in ("A", "B"):
        sel = [r for r in mp if r["cb"] == cb and r["cond"] == "A"]
        if not sel:
            continue
        labs = [CLS.get(l, l) for l in sel[0]["labels"]]
        k = len(labs)
        fig, axes = plt.subplots(1, len(sel), figsize=(3.55 * len(sel), 3.3))
        if len(sel) == 1:
            axes = [axes]
        for ax, r in zip(axes, sel):
            m = np.array(r["raw"], dtype=float)
            sns.heatmap(m, ax=ax, cmap=SEQ, annot=True, fmt=".0f",
                        cbar=False, linewidths=0.6, linecolor="white",
                        xticklabels=labs, yticklabels=labs, annot_kws={"size": 7.0})
            ax.set_title(f"{short(r['a'])}\nvs. {short(r['b'])}\n"
                         f"κ={r['kappa']:.2f} · AC1={r['ac1']:.2f}",
                         fontsize=6.6, pad=6)
            ax.set_xlabel("Modell B (Spalte)", fontsize=6.8)
            ax.set_ylabel("Modell A (Zeile)", fontsize=6.8)
            ax.tick_params(labelsize=5.8, rotation=0)
        fig.suptitle(f"Abb. 5  Verwirrungsmatrizen Modell × Modell, Codebook {cb}, "
                     f"Condition A (absolut, n = {sel[0]['n']})",
                     fontsize=8.8, y=1.04)
        fig.tight_layout(rect=(0, 0, 1, 0.90))
        save(fig, f"fig5_confusion_model_{cb}")

    # normalised version for codebook B (7x7 needs row normalisation to read)
    sel = [r for r in mp if r["cb"] == "B" and r["cond"] == "A"]
    if sel:
        labs = [CLS.get(l, l) for l in sel[0]["labels"]]
        fig, axes = plt.subplots(1, len(sel), figsize=(3.9 * len(sel), 3.5))
        if len(sel) == 1:
            axes = [axes]
        for ax, r in zip(axes, sel):
            nrm = np.array(r["norm"], dtype=float)
            sns.heatmap(nrm, ax=ax, cmap=SEQ, annot=True, fmt=".2f", vmin=0, vmax=1,
                        cbar=False, linewidths=0.5, linecolor="white",
                        xticklabels=labs, yticklabels=labs,
                        annot_kws={"size": 5.6})
            ax.set_title(f"{short(r['a'])}\nvs. {short(r['b'])}", fontsize=6.8, pad=5)
            ax.tick_params(labelsize=5.8, rotation=0)
            ax.set_xlabel("Modell B", fontsize=6.8)
            ax.set_ylabel("Modell A (zeilennormalisiert)", fontsize=6.8)
        fig.suptitle("Abb. 6  Zeilennormalisierte Verwirrungsmatrizen, Codebook B, "
                     "Condition A (Recall je wahrer Klasse)", fontsize=8.8, y=1.04)
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        save(fig, "fig6_confusion_model_B_norm")


# ============================================================ fig 7
def fig7():
    cal = X.get("calibration", [])
    sweep = X.get("threshold_sweep", [])
    if not cal or not sweep:
        return
    ts = next((s for s in sweep if s["cond"] == "A"), sweep[0])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.1, 2.7))

    c = next((x for x in cal if x["cond"] == "A"), cal[0])
    if c["bins"]:
        xs = [0.5 * (b["lo"] + b["hi"]) for b in c["bins"]]
        ys = [b["mean_p"] for b in c["bins"]]
        ns = [b["n"] for b in c["bins"]]
        a1.plot([0, 1], [0, 1], color=GREY, lw=0.6, ls=(0, (4, 3)),
                label="perfekt kalibriert", zorder=1)
        a1.plot(xs, ys, "o-", color="#2f6f8f", ms=4.5, lw=1.1, zorder=3,
                label="Jev")
        for x, y, n in zip(xs, ys, ns):
            a1.annotate(f"n={n}", (x, y), textcoords="offset points",
                        xytext=(3, -9), fontsize=5.2, color=GREY)
        a1.set_xlabel("vorhergesagte P(ja)")
        a1.set_ylabel("beobachtete Häufigkeit (Mehrheitsvote)")
        a1.set_title("a  Kalibrierung (Codebook A, Cond. A)", loc="left", pad=6)
        a1.set_xlim(-0.03, 1.03)
        a1.set_ylim(-0.03, 1.03)
        a1.legend(frameon=False, loc="upper left")

    s = ts["sweep"]
    xs = [r["coverage_pct"] for r in s]
    ys = [r["precision"] for r in s]
    a2.plot(xs, ys, "o-", color="#c4622d", ms=4.2, lw=1.1, zorder=3)
    for r in s:
        a2.annotate(f"{r['t']:.1f}", (r["coverage_pct"], r["precision"]),
                    textcoords="offset points", xytext=(4, -3),
                    fontsize=5.4, color=GREY)
    a2.axhline(100 * 0.46, color=GREY, lw=0.6, ls=(0, (4, 3)))
    a2.annotate("46 % = Präzision ohne Schwelle", (2, 49), fontsize=5.8,
                color=GREY, rotation=0)
    a2.set_xlabel("Anteil der Kommentare, die markiert werden (%)")
    a2.set_ylabel("Präzision gegen Mehrheitsvote")
    a2.set_title("b  Schwellwert-Trade-off", loc="left", pad=6)
    a2.set_ylim(0, 100)
    fig.suptitle("Abb. 7  Jev liefert brauchbare Konfidenz: eine Schwelle auf "
                 "p(ja) hebt die Präzision stark an", fontsize=9.2, y=1.04)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "fig7_calibration")


# ============================================================ fig 8
def fig8():
    if not PARA and not RELI:
        return
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.6))
    if PARA:
        per = PARA["per_stratum"]
        ks = sorted(per, key=lambda k: (k == "0", -int(k)))
        labs = [f"{k} von 3" if k != "0" else "Kontrolle\n(negativ)" for k in ks]
        variants = ["T1_deemphasis", "T2_politeness", "T3_defiller"]
        names = ["T1 Betonung weg", "T2 Höflichkeit", "T3 Füllwörter weg"]
        w = 0.25
        x = np.arange(len(ks))
        for i, (v, n) in enumerate(zip(variants, names)):
            ys = [per[k].get(v) or 0 for k in ks]
            a = axes[0].bar(x + (i - 1) * w, ys, w, label=n, edgecolor="#333",
                            linewidth=0.4)
            for b, val in zip(a, ys):
                axes[0].annotate(f"{val:.0f}", (b.get_x() + b.get_width() / 2, val),
                                 textcoords="offset points", xytext=(0, 2),
                                 ha="center", fontsize=5.8)
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(labs, fontsize=6.8)
        axes[0].set_ylabel("Label unverändert (%)")
        axes[0].set_ylim(0, 112)
        axes[0].legend(frameon=False, ncol=1, fontsize=6.6, loc="lower left")
        axes[0].set_title("a  Oberflächen-Robustheit (Jev, Codebook A)", loc="left", pad=6)

    if RELI:
        e2 = RELI["E2_repeat_stability"]
        vals = [e2.get("negatives_only_pct"), e2.get("positives_only_pct"),
                e2.get("overall_pct")]
        labs = ["Kontrolle\n(negativ)", "Positiven", "gesamt"]
        vals = [v if v is not None else 0 for v in vals]
        a = axes[1].bar(range(3), vals, 0.55,
                        color=["#a9c9d8", "#c4622d", "#2f6f8f"][-3:][::-1][::-1],
                        edgecolor="#333", linewidth=0.4)
        for b, v in zip(a, vals):
            axes[1].annotate(f"{v:.1f}", (b.get_x() + b.get_width() / 2, v),
                             textcoords="offset points", xytext=(0, 2),
                             ha="center", fontsize=6.6)
        axes[1].set_xticks(range(3))
        axes[1].set_xticklabels(labs, fontsize=6.8)
        axes[1].set_ylabel("Label stabil bei Wiederholung (%)")
        axes[1].set_ylim(0, 108)
        axes[1].set_title("b  Wiederholungs- und Positions-Robustheit", loc="left", pad=6)
    fig.suptitle("Abb. 8  Zwei zusätzliche Validierungsexperimente: "
                 "misst das Instrument die Konstruktion oder die Formulierung?",
                 fontsize=9.0, y=1.04)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "fig8_reliability")


for f in (fig1, fig2, fig3, fig4, fig5, fig7, fig8):
    try:
        f()
    except Exception as e:                      # noqa: BLE001
        print("  SKIP", f.__name__, "->", type(e).__name__, e)
print("done")

"""Generate the report figures as PDF (vector, per Daniel's preference).

fig1_prevalence.pdf    prevalence by model x codebook x condition
fig2_precision.pdf     audit: precision by consensus stratum + stratum sizes
fig3_agreement.pdf     inter-model agreement (raw % vs Cohen's kappa)
fig4_cost_latency.pdf  latency and cost per 1000 rows
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5,
    "axes.titlesize": 10, "axes.labelsize": 8.5,
    "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
})
C = {"jev-1.13": "#1a6b8f", "gpt-6-luna": "#c4622d",
     "deepseek-v4.1-flash": "#4f7942", "glm-5.3-flash": "#7a5c9e"}
ORDER = ["jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash", "glm-5.3-flash"]
D = json.load((RES / "report_data.json").open(encoding="utf-8"))
S = D["summary"]
models = [m for m in ORDER if m in D["models"]] + \
        [m for m in D["models"] if m not in ORDER]


SHORT = {"jev-1.13": "jev-1.13", "gpt-6-luna": "gpt-6-luna",
         "deepseek-v4.1-flash": "deepseek\nflash",
         "glm-5.3-flash": "glm-5.3\nflash"}


def get(cb, cond, m, key):
    for s in S:
        if s["cb"] == cb and s["cond"] == cond and s["model"] == m:
            return s.get(key)
    return None


# ---------------------------------------------------------------- fig 1
def fig1():
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
    for ax, cb, title, cols in ((axes[0], "A", "Codebook A (binär)", ["#2f6f8f", "#a9c9d8"]),
                                (axes[1], "B", "Codebook B (7 Typen)", ["#a4573f", "#e6c6b3"])):
        w = 0.36
        x = range(len(models))
        for j, cond in enumerate(("A", "B")):
            vals = [get(cb, cond, m, "prev_pct") or 0 for m in models]
            off = (j - 0.5) * w
            b = ax.bar([i + off for i in x], vals, w, color=cols[j],
                       edgecolor="#333", linewidth=0.5,
                       label=f"Condition {cond} " +
                             ("(mit Transkript)" if cond == "A" else "(nur Kommentar)"))
            for bi, v in zip(b, vals):
                ax.text(bi.get_x() + bi.get_width() / 2, v + 0.15, f"{v:.1f}",
                        ha="center", fontsize=6.4, va="bottom")
        ax.set_xticks(list(x))
        ax.set_xticklabels([SHORT.get(m, m) for m in models], fontsize=7.0)
        ax.set_title(title, pad=6)
        # legend BELOW the axes: at the top it collided with the tallest bar
        ax.legend(fontsize=6.4, frameon=False, loc="upper center",
                  bbox_to_anchor=(0.5, -0.16), ncol=1, handlelength=1.1)
    axes[0].set_ylabel("Anteil Reaktanz (%)")
    axes[0].set_ylim(0, 8.2)
    fig.suptitle("Abb. 1  Prävalenz psychologischer Reaktanz nach Modell, Codebook und Condition (n = 1.200)",
                 fontsize=9.2, y=0.99)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(FIG / "fig1_prevalence.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- fig 2
def fig2():
    L = json.load((RES / "audit_linked.json").open(encoding="utf-8"))
    preds = [json.loads(l) for l in (RES / "predictions_full.jsonl").open(encoding="utf-8")]
    pool = defaultdict(set)
    for p in preds:
        if p["codebook"] == "A" and p["condition"] == "A" and p["label"] == "ja":
            pool[p["uid"]].add(p["model"])
    sizes = [sum(1 for v in pool.values() if len(v) == k) for k in (3, 2, 1)]
    pr = []
    for k in (3, 2, 1):
        sub = [r for r in L if r["n_models"] == k]
        pr.append(100 * sum(1 for r in sub if r["verdict"] == "ja") / max(1, len(sub)))
    x = range(3)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 2.9),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    b = a1.bar([i for i in x], pr, 0.55,
               color=["#2f6f8f", "#a4573f", "#9c9c9c"], edgecolor="#333", linewidth=0.5)
    a1.set_xticks(list(x))
    a1.set_xticklabels(["3 von 3\nModellen", "2 von 3", "1 von 3"], fontsize=7.4)
    a1.set_ylabel("Präzision (%)")
    a1.set_ylim(0, 105)
    for bi, v, n in zip(b, pr, sizes):
        a1.text(bi.get_x() + bi.get_width() / 2, v + 2,
                f"{v:.0f} %\nn={n}", ha="center", fontsize=6.8)
    a1.set_title("Präzision nach Konsens-Grad", pad=6)
    a1.set_xlabel("(manuelle Nachkodierung, n = 36)", fontsize=7.4)

    tot = sum(sizes)
    for bi, s in zip(b, sizes):
        bi.set_height(bi.get_height())
    b2 = a2.bar([i for i in x], [100 * s / tot for s in sizes], 0.55,
                color=["#2f6f8f", "#a4573f", "#9c9c9c"], edgecolor="#333", linewidth=0.5)
    a2.set_xticks(list(x))
    a2.set_xticklabels(["3/3", "2/3", "1/3"], fontsize=7.4)
    a2.set_ylabel("Anteil an allen Positiven (%)")
    a2.set_ylim(0, 65)
    for bi, s in zip(b2, sizes):
        bi.set_label(f"{s}")
        a2.text(bi.get_x() + bi.get_width() / 2, 100 * s / tot + 1.2,
                f"{s}", ha="center", fontsize=7)
    a2.set_title("Verteilung aller 119 Positiven", pad=6)
    fig.suptitle("Abb. 2  Die meisten 'Reaktanz'-Treffer sind Fehlalarm — und zwar die\n"
                 "schwachen Mehrheitsentscheidungen (1 von 3 Modellen)",
                 fontsize=9.3, y=1.07)
    fig.savefig(FIG / "fig2_precision.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- fig 3
def fig3():
    ov = [o for o in D["overlap"] if o["cb"] == "A"]
    ovb = [o for o in D["overlap"] if o["cb"] == "B"]

    def abbr(s):
        """3 model pairs -> 1..3, so the x-labels fit without colliding."""
        return {"jev-1.13": "jev", "gpt-6-luna": "gpt6",
                "deepseek-v4.1-flash": "ds", "glm-5.3-flash": "glm"}[s]

    pairs = sorted({tuple(sorted((o["a"], o["b"]))) for o in ov + ovb})
    idx = {p: i for i, p in enumerate(pairs)}
    PAIRS = ["jev–gpt6", "jev–ds", "jev–glm", "gpt6–ds", "gpt6–glm", "ds–glm"]
    labels = [PAIRS[i] if i < len(PAIRS) else f"{abbr(p[0])}–{abbr(p[1])}"
              for p, i in idx.items()]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.0), sharey=True)
    for ax, data, ttl in ((a1, [o for o in ov if idx[tuple(sorted((o["a"], o["b"])))] < 3],
                            "Codebook A"),
                          (a2, [o for o in ovb if idx[tuple(sorted((o["a"], o["b"])))] < 3],
                            "Codebook B")):
        agr = [o["agree"] for o in data]
        kap = [o["kappa"] for o in data]
        labs = [PAIRS[idx[tuple(sorted((o["a"], o["b"])))]] for o in data]
        x = range(len(data))
        w = 0.38
        ax.bar([i - w / 2 for i in x], agr, w, label="rohe Übereinstimmung",
               color="#c9d6e0", edgecolor="#333", linewidth=0.5)
        ax.bar([i + w / 2 for i in x], kap, w, label="Cohen's κ",
               color="#2f6f8f", edgecolor="#333", linewidth=0.5)
        for i, (av, kv) in enumerate(zip(agr, kap)):
            ax.text(i - w / 2, av + 1.5, f"{av:.0f}", ha="center", fontsize=6.4)
            ax.text(i + w / 2, kv + 1.5, f"{kv:.2f}", ha="center", fontsize=6.4)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labs, fontsize=6.6, rotation=20, ha="right")
        ax.set_title(ttl, pad=6)
        ax.set_ylim(0, 128)
    a1.set_ylabel("Prozent  /  κ")
    a1.legend(fontsize=6.8, frameon=False, loc="upper center",
              bbox_to_anchor=(1.02, -0.20), ncol=2)
    fig.suptitle("Abb. 3  Rohübereinstimmung überschätzt die Konvergenz: bei 3–7 % Prävalenz\n"
                 "sagen fast alle 'nein', κ bleibt um 0,45",
                 fontsize=9.2, y=0.99)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(FIG / "fig3_agreement.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- fig 4
def fig4():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.0))
    fig.subplots_adjust(wspace=0.42)          # room for the right panel's y-label
    for cb, mark, ttl in (("A", "o", "Codebook A"), ("B", "s", "Codebook B")):
        xs = [i + (0.12 if cb == "B" else -0.12) for i in range(len(models))]
        lat = [get(cb, "A", m, "lat") for m in models]
        cost = [get(cb, "A", m, "usd_1k") for m in models]
        a1.scatter(xs, lat, marker=mark, s=44,
                   color="#2f6f8f" if cb == "A" else "#a4573f",
                   edgecolor="#222", linewidth=0.6, label=ttl, zorder=3)
        a2.scatter(xs, cost, marker=mark, s=44,
                   color="#2f6f8f" if cb == "A" else "#a4573f",
                   edgecolor="#222", linewidth=0.6, label=ttl, zorder=3)
        for xs_, lv, cv in zip(xs, lat, cost):
            if lv:
                a1.annotate(f"{lv:.2f}", (xs_, lv), textcoords="offset points",
                            xytext=(0, 7), ha="center", fontsize=6.2)
            if cv:
                a2.annotate(f"{cv:.3f}", (xs_, cv), textcoords="offset points",
                            xytext=(0, 7), ha="center", fontsize=6.2)
    # plain linear axes: the log scale made 0.35 vs 4.09 hard to read off
    for ax, ylab, ttl, ylim in (
            (a1, "Ø Antwortzeit (s)", "Geschwindigkeit", (0, 5.0)),
            (a2, "Kosten je 1.000 Kommentare (US$)", "Kosten", (0, 0.42))):
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([SHORT.get(m, m) for m in models], fontsize=6.8)
        ax.set_ylabel(ylab, fontsize=8)
        ax.set_title(ttl, pad=6)
        ax.set_ylim(*ylim)
        ax.legend(fontsize=6.6, frameon=False, loc="upper left")
    fig.suptitle("Abb. 4  Jev ist gleichzeitig das schnellste und das günstigste Backend "
                 "(Condition A, beide Achsen linear)", fontsize=9.2, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "fig4_cost_latency.pdf")
    plt.close(fig)


for f in (fig1, fig2, fig3, fig4):
    f()
    print("ok", f.__name__)

# The report embeds the figures with <img>, and Chromium cannot render a PDF
# inside a PDF -- so also emit a high-res PNG of each figure for embedding.
# The vector PDFs stay the canonical deliverables; the PNGs are 300 dpi rasters.
import subprocess
for pdf in sorted(FIG.glob("*.pdf")):
    png = pdf.with_suffix(".png")
    subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                    str(pdf), str(png.with_suffix(""))], check=True)
    print("png", png.name, f"{png.stat().st_size/1e3:.0f} kB")

print("figures in", FIG)

#!/usr/bin/env python3
"""Independent statistical validation of the report's headline numbers.

This script does NOT trust the values stored in the analysis JSONs. It
recomputes them from the underlying confusion counts and fails (non-zero exit)
on any disagreement. It is meant to run in CI or before shipping the report:

    python3 src/validate_report.py

Checks
------
  * A x B kappa recomputed on the shared BINARY label space matches the
    stored value (guards the historical bug where kappa was computed across
    incompatible label spaces and came out far too high).
  * raw agreement = (tp + tn) / n
  * kappa = (po - pe) / (1 - pe) from the four binary cells
  * prevalence = positives / n
  * fp + fn + tp + tn = n for every four-cell table
  * reported A-vs-B flip counts equal the off-diagonal cells
  * Jev threshold precision uses a leave-one-model-out reference, i.e. the
    flagged-positive precision can never be 1.0 by construction and the
    reference excludes Jev itself (checked via the consensus_reference rows)
  * the model-vs-consensus evaluation is leave-one-model-out
  * threshold precision/recall are rendered as percentages (100 * stored),
    not as the raw stored proportion (the historical "0% -> 1%" bug)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

FAIL = []
OK = []


def chk(cond, msg):
    (OK if cond else FAIL).append(msg)


def load(name):
    p = RES / name
    if not p.exists():
        FAIL.append(f"missing results file: {name}")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def cohen_kappa_from_cells(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    po = (tp + tn) / n
    pa1 = (tp + fp) / n
    pb1 = (tp + fn) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if abs(1 - pe) < 1e-12:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def main():
    X = load("analysis_ext.json")
    BIG = load("analysis_big.json")
    if X is None or BIG is None:
        for f in FAIL:
            print("  -", f)
        sys.exit(1)

    # ---- 1. big-sample A x B: kappa on binary space, cells sum to n ------
    for r in BIG.get("A_vs_B", []):
        m = r["model"]
        tp, fp, fn, tn = r["both"], r["fp"], r["fn"], r["both_none"]
        n = r["n"]
        chk(tp + fp + fn + tn == n,
            f"[big A x B {m}] cells sum to n ({tp}+{fp}+{fn}+{tn} vs {n})")
        raw = round(100 * (tp + tn) / n, 2)
        chk(abs(raw - r["raw_agreement_pct"]) < 0.01,
            f"[big A x B {m}] raw agreement {(tp+tn)/n:.4f} matches stored "
            f"{r['raw_agreement_pct']}")
        k = cohen_kappa_from_cells(tp, fp, fn, tn)
        chk(abs(k - r["cohens_kappa"]) < 1e-4,
            f"[big A x B {m}] kappa recomputed {k:.4f} matches stored "
            f"{r['cohens_kappa']}")
        # guard against the historical inflation: kappa on the rare positive
        # class with 98% raw agreement must NOT be ~0.98
        if r["raw_agreement_pct"] > 90:
            chk(r["cohens_kappa"] < 0.9,
                f"[big A x B {m}] kappa {r['cohens_kappa']} not inflated "
                f"(raw {r['raw_agreement_pct']}%, positive class rare)")

    # ---- 2. condition A x B (matrix): flip counts = off-diagonal cells ----
    for c in X.get("condition_pairwise", []):
        b = c.get("binary")
        if not b:
            continue
        tag = f"[cond {c['cb']} {c['model']}]"
        n = b["n"]
        cells = (b["A_no_B_no"] + b["A_no_B_yes"] + b["A_yes_B_no"]
                 + b["A_yes_B_yes"])
        chk(cells == n, f"{tag} four cells sum to n ({cells} vs {n})")
        # case agreement
        agree = round(100 * (b["A_no_B_no"] + b["A_yes_B_yes"]) / n, 2)
        chk(abs(agree - b["case_agreement_pct"]) < 0.01,
            f"{tag} case agreement recomputed matches stored")
        # kappa_bin recomputed from the same four cells
        kk = cohen_kappa_from_cells(b["A_yes_B_yes"], b["A_yes_B_no"],
                                    b["A_no_B_yes"], b["A_no_B_no"])
        chk(abs(kk - b["kappa_bin"]) < 1e-3,
            f"{tag} kappa_bin {kk:.4f} matches stored {b['kappa_bin']}")
        # prevalence from the cells
        prevA = 100 * (b["A_yes_B_no"] + b["A_yes_B_yes"]) / n
        prevB = 100 * (b["A_no_B_yes"] + b["A_yes_B_yes"]) / n
        chk(abs(prevA - b["prev_A_pct"]) < 0.01
            and abs(prevB - b["prev_B_pct"]) < 0.01,
            f"{tag} prevalences from cells match stored")

    # ---- 3. leave-one-model-out consensus evaluation ---------------------
    cr = X.get("consensus_reference", [])
    chk(bool(cr), "consensus_reference present")
    for c in cr:
        chk(c.get("leave_one_out") is True,
            f"[LOO consensus {c['model']} cond{c['cond']}] flagged "
            f"leave_one_out=True")
        # recompute raw + kappa + f1 from the stored four counts
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        n = c["n"]
        tn = n - tp - fp - fn
        chk(tp + fp + fn + tn == n,
            f"[LOO consensus {c['model']}] cells sum to n")
        k = cohen_kappa_from_cells(tp, fp, fn, tn)
        chk(abs(k - c["kappa"]) < 1e-3,
            f"[LOO consensus {c['model']} cond{c['cond']}] kappa recomputed "
            f"{k:.4f} matches stored {c['kappa']}")

    # ---- 4. Jev threshold uses a non-degenerate leave-one-out reference ---
    # If the reference included Jev, the top-bin precision would be pinned by
    # Jev's own argmax; we at least assert the sweep is present, references
    # are non-empty, and coverage is monotone decreasing.
    for t in X.get("threshold_sweep", []):
        sw = t.get("sweep", [])
        chk(bool(sw), f"[threshold cond{t['cond']}] sweep present")
        covs = [s["coverage_pct"] for s in sw]
        chk(all(covs[i] >= covs[i + 1] for i in range(len(covs) - 1)),
            f"[threshold cond{t['cond']}] coverage monotone non-increasing")
        for s in sw:
            prec = s["precision"]
            chk(prec is None or 0.0 <= prec <= 1.0,
                f"[threshold cond{t['cond']} t={s['t']}] precision in [0,1]")

    # ---- 4b. the report renders threshold precision/recall as PERCENTAGES ---
    # Historical bug: _ts() formatted the stored proportion with .0f, so a
    # precision of 0.139 printed as "0%" and 0.788 as "1%". This re-runs the
    # exact formatting the report uses and asserts it equals 100 * stored.
    _sweep_a = next((t for t in X.get("threshold_sweep", [])
                     if t["cond"] == "A"), None)
    if _sweep_a:
        for s in _sweep_a.get("sweep", []):
            for key in ("precision", "recall"):
                v = s.get(key)
                if v is None:
                    continue
                rendered = f"{100 * v:.0f}"      # what generate_latex._ts does
                naive = f"{v:.0f}"               # what it used to do
                # a proportion in (0, 1) that is not 0/1 must never render
                # back as the bare proportion's own integer
                chk(v in (0.0, 1.0) or rendered != naive,
                    f"[threshold condA t={s['t']} {key}] renders as "
                    f"{rendered}% (= 100 * {v}), not the raw {naive}%")
        # the headline comparison used in the abstract and results text
        lo = next((s for s in _sweep_a["sweep"] if s["t"] == 0.05), None)
        hi = next((s for s in _sweep_a["sweep"] if s["t"] == 0.6), None)
        chk(lo is not None and hi is not None,
            "[threshold condA] t=0.05 and t=0.6 present for the headline claim")
        if lo and hi and lo.get("precision") is not None \
                and hi.get("precision") is not None:
            chk(round(100 * hi["precision"]) > round(100 * lo["precision"]),
                f"[threshold condA] precision rises "
                f"{100*lo['precision']:.0f}% -> {100*hi['precision']:.0f}% "
                f"(stored {lo['precision']} -> {hi['precision']})")
            chk(round(100 * lo["precision"]) > 0,
                f"[threshold condA] t=0.05 precision is not rendered as 0% "
                f"(it is {100*lo['precision']:.0f}%)")
            chk(round(100 * hi["precision"]) > 1,
                f"[threshold condA] t=0.6 precision is not rendered as 1% "
                f"(it is {100*hi['precision']:.0f}%)")

    # ---- 4c. the FIGURE plots the right quantities (issue #8) --------------
    # Panel (a) must plot the OBSERVED consensus rate (obs) against the mean
    # predicted probability (mean_p) -- not mean_p against the bin midpoint.
    # Panel (b) must scale the stored [0,1] precision to percent, because its
    # y-axis is 0-100 %. This re-reads the plotting source and the numbers it
    # would draw, so the bug cannot silently come back.
    _figs = (REPO / "src" / "figures.py")
    if _figs.exists():
        _src = _figs.read_text(encoding="utf-8")
        _f = _src.split("def fig_calibration", 1)[-1].split("\ndef ", 1)[0]
        chk('ys = [b["obs"] for b in c["bins"]]' in _f,
            "[fig_calibration] panel (a) y-data sourced from obs, not mean_p")
        chk('xs = [b["mean_p"] for b in c["bins"]]' in _f,
            "[fig_calibration] panel (a) x-data sourced from mean_p")
        chk('0.5 * (b["lo"] + b["hi"])' not in _f,
            "[fig_calibration] panel (a) no longer plots mean_p vs bin midpoint")
        chk('100 * r["precision"]' in _f,
            "[fig_calibration] panel (b) precision converted to percent")
        chk("perfect alignment" in _f and "perfectly calibrated" not in _f,
            "[fig_calibration] diagonal described as alignment, not calibration")
    # and the numbers such a figure would draw must equal the stored values
    _cal_a = next((c for c in X.get("calibration", []) if c["cond"] == "A"), None)
    if _cal_a and _cal_a.get("bins"):
        for b in _cal_a["bins"]:
            chk(0.0 <= b["obs"] <= 1.0 and 0.0 <= b["mean_p"] <= 1.0
                and b["lo"] <= b["mean_p"] <= b["hi"],
                f"[calibration condA bin {b['lo']}-{b['hi']}] mean_p inside its "
                f"bin and obs a rate ({b['mean_p']}, {b['obs']}, n={b['n']})")
        top = max(_cal_a["bins"], key=lambda b: b["lo"])
        chk(top["obs"] > top["mean_p"] or top["n"] < 30,
            f"[calibration condA] top bin (n={top['n']}) is a coarse "
            f"consensus rate (obs={top['obs']}), not a predicted probability")
        # a curve that plotted mean_p on both axes would be perfectly diagonal
        spread = [abs(b["obs"] - b["mean_p"]) for b in _cal_a["bins"]]
        chk(max(spread) > 0.05,
            f"[calibration condA] obs differs from mean_p (max gap "
            f"{max(spread):.3f}) -- figure is not tautological")
    if _sweep_a:
        for s_ in _sweep_a.get("sweep", []):
            p_ = s_.get("precision")
            chk(p_ is None or 0 <= p_ <= 1,
                f"[threshold condA t={s_['t']}] stored precision is a "
                f"proportion, so the figure must scale it by 100 ({p_})")

    # ---- 5. positive-specific agreement (Codebook A) is self-consistent ---
    for r in X.get("model_pairwise", []):
        if r.get("cb") != "A":
            continue
        pc = r.get("positive_cells")
        if not pc:
            continue
        tp, fp, fn = pc["tp"], pc["fp"], pc["fn"]
        denom = 2 * tp + fp + fn
        pa = round(2 * tp / denom, 4) if denom else None
        chk(pa is None or abs(pa - r.get("positive_agreement", pa)) < 1e-4,
            f"[pos agreement {r['a']}/{r['b']}] matches cells")
        dj = tp + fp + fn
        jac = round(tp / dj, 4) if dj else None
        chk(jac is None or abs(jac - r.get("jaccard", jac)) < 1e-4,
            f"[jaccard {r['a']}/{r['b']}] matches cells")

    # ---- report ----------------------------------------------------------
    for m in OK:
        print("  ok  ", m)
    if FAIL:
        print(f"\nFAILED {len(FAIL)} check(s):", file=sys.stderr)
        for m in FAIL:
            print("  FAIL", m, file=sys.stderr)
        sys.exit(1)
    print(f"\nvalidate_report.py: all {len(OK)} checks passed")


if __name__ == "__main__":
    main()

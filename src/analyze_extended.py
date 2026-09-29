"""Extended analysis: confusion matrices, agreement, calibration, inference tests.

All from existing data (no new API calls) except `paraphrase` which is a separate
script. Produces results/analysis_ext.json for the report builder.

Agreement measures
------------------
  raw/percent  : plain agreement (overstates under class imbalance)
  Cohen's kappa : chance-corrected, unstable at low prevalence
  Gwet's AC1     : prevalence-robust alternative to kappa (McHugh 2012)
  Krippendorff   : not applicable (no repeated coders)
Normalised matrices are row-normalised (recall per true class).

Paired tests
------------
  McNemar exact (binomial) for paired binary decisions, e.g. A vs B condition.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

LAB_A = ["nein", "ja"]
LAB_B = ["keine_reaktanz", "konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik"]


def load(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


# ---------------------------------------------------------------- agreement
def cohen_kappa(a, b, labels):
    n = len(a)
    if not n:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in set(labels) | set(a) | set(b))
    if abs(1 - pe) < 1e-12:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def gwets_ac1(a, b, labels):
    """Gwet's AC1: prevalence-robust agreement, better than kappa when classes
    are heavily skewed (which is exactly our 3-7% case)."""
    n = len(a)
    if not n:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    # Pe for AC1 uses the average of observed proportions across both raters
    props = [(ca[l] / n + cb[l] / n) / 2 for l in set(labels) | set(a) | set(b)]
    pe = sum(p * (1 - p) for p in props)
    if abs(1 - pe) < 1e-12:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def confusion(a, b, labels):
    """rows = a (reference/true), cols = b. Returns raw + row-normalised."""
    k = len(labels)
    m = np.zeros((k, k), dtype=int)
    ia = {l: i for i, l in enumerate(labels)}
    for x, y in zip(a, b):
        if x in ia and y in ia:
            m[ia[x], ia[y]] += 1
    norm = np.zeros_like(m, dtype=float)
    for i in range(k):
        s = m[i].sum()
        if s:
            norm[i] = m[i] / s
    return m, norm


def mcnemar_exact(a, b):
    """Exact (binomial) McNemar for paired binary decisions on {0,1}."""
    b01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    b10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n = b01 + b10
    if n == 0:
        return {"b01": 0, "b10": 0, "p": 1.0, "n": 0}
    k = min(b01, b10)
    p = min(1.0, 2 * stats.binom.cdf(k, n, 0.5))
    return {"b01": b01, "b10": b10, "p": round(float(p), 6), "n": n}


def bootstrap_ci(vals, scale=100, n=2000, seed=11, alpha=0.05):
    """Percentile bootstrap CI of a proportion, returned in PERCENT.

    (scale=100 -> 0/1 coded input becomes a percentage with a percentage CI.)
    """
    if not len(vals):
        return None
    rng = np.random.default_rng(seed)
    arr = np.asarray(vals, dtype=float)
    idx = rng.integers(0, len(arr), size=(n, len(arr)))
    draws = scale * arr[idx].mean(axis=1)
    return [round(float(np.quantile(draws, alpha / 2)), 3),
            round(float(np.quantile(draws, 1 - alpha / 2)), 3)]


# ---------------------------------------------------------------- main
def main():
    preds = load(RES / "predictions_full.jsonl")
    rows = {json.loads(l)["uid"]: json.loads(l)
            for l in (REPO / "data/sample_matrix.jsonl").open(encoding="utf-8")}

    models = sorted({p["model"] for p in preds})
    lab = {}
    for p in preds:
        if p["label"] is not None:
            lab[(p["model"], p["codebook"], p["condition"], p["uid"])] = p["label"]

    def vec(m, cb, cond, uids):
        return [lab.get((m, cb, cond, u)) for u in uids]

    out = {"models": models,
           "model_pairwise": [],     # confusion matrices model x model
           "condition_pairwise": [],  # confusion matrices condition A x B
           "codebook_pairwise": [],   # codebook A x B
           "bootstrap_prev": [],
           "mcnemar": [],
           "calibration": [],
           "threshold_sweep": [],
           "consensus_reference": [],
           "transcript_effect": []}

    # ---------- 1. model x model, per codebook & condition -----------------
    for cb in ("A", "B"):
        labels = LAB_A if cb == "A" else LAB_B
        for cond in ("A", "B"):
            present = [m for m in models
                       if any((m, cb, cond, u) in lab for u in rows)]
            uids = sorted([u for u in rows if (present[0], cb, cond, u) in lab])
            for m1, m2 in combinations(present, 2):
                pairs = [(x, y) for x, y in
                         zip(vec(m1, cb, cond, uids), vec(m2, cb, cond, uids))
                         if x in labels and y in labels]
                if not pairs:
                    continue
                a = [x for x, _ in pairs]
                b = [y for _, y in pairs]
                m, nrm = confusion(a, b, labels)
                # F1 of model A's labels with model B's as (reference-free)
                # ground truth: exact label agreement is the only "true
                # positive", every mismatch is one false positive AND one false
                # negative (symmetric by construction), so precision = recall
                # = raw agreement and F1 = raw agreement. Kept as its own
                # number because it is what a pipeline would actually compute.
                m_np = np.asarray(m)
                n_ = len(pairs)
                if n_ and m_np.sum():
                    off = m_np.sum() - sum(m_np[i, i] for i in range(len(labels)))
                    tp = float(sum(m_np[i, i] for i in range(len(labels))))
                    prec = tp / (tp + off) if (tp + off) else None
                    rec = prec
                    f1v = (2 * prec * rec / (prec + rec) if prec and prec + rec
                            else None)
                else:
                    f1v = None
                out["model_pairwise"].append({
                    "cb": cb, "cond": cond, "a": m1, "b": m2,
                    "labels": labels, "n": len(pairs),
                    "raw": m.tolist(), "norm": nrm.tolist(),
                    "raw_pct": round(100 * sum(1 for x, y in pairs if x == y) / len(pairs), 2),
                    "kappa": round(cohen_kappa(a, b, labels), 4),
                    "ac1": round(gwets_ac1(a, b, labels), 4),
                    "f1": round(f1v, 4) if f1v is not None else None,
                })

    # ---------- 2. condition A x B, per model & codebook --------------------
    for cb in ("A", "B"):
        labels = LAB_A if cb == "A" else LAB_B
        for m in models:
            uids = sorted([u for u in rows
                           if (m, cb, "A", u) in lab and (m, cb, "B", u) in lab])
            pairs = [(x, y) for x, y in
                     zip(vec(m, cb, "A", uids), vec(m, cb, "B", uids))
                     if x in labels and y in labels]
            if not pairs:
                continue
            a = [x for x, _ in pairs]
            b = [y for _, y in pairs]
            mtx, nrm = confusion(a, b, labels)
            rec = {"cb": cb, "model": m, "labels": labels, "n": len(pairs),
                   "raw": mtx.tolist(), "norm": nrm.tolist(),
                   "raw_pct": round(100 * sum(1 for x, y in pairs if x == y) / len(pairs), 2),
                   "kappa": round(cohen_kappa(a, b, labels), 4),
                   "ac1": round(gwets_ac1(a, b, labels), 4)}
            if cb == "A":
                ba = [1 if x == "ja" else 0 for x in a]
                bb = [1 if y == "ja" else 0 for y in b]
                rec["mcnemar"] = mcnemar_exact(ba, bb)
                rec["prev_A_pct"] = round(100 * np.mean(ba), 2)
                rec["prev_B_pct"] = round(100 * np.mean(bb), 2)
            out["condition_pairwise"].append(rec)

    # ---------- 3. codebook A x B ------------------------------------------
    for cond in ("A", "B"):
        for m in models:
            uids = sorted([u for u in rows
                           if (m, "A", cond, u) in lab and (m, "B", cond, u) in lab])
            pairs = [(x, y) for x, y in
                     zip(vec(m, "A", cond, uids), vec(m, "B", cond, uids))
                     if x in LAB_A and y in LAB_B]
            if not pairs:
                continue
            both = sum(1 for x, y in pairs
                       if x == "ja" and y != "keine_reaktanz")
            fp = sum(1 for x, y in pairs
                     if x == "nein" and y != "keine_reaktanz")
            fn = sum(1 for x, y in pairs
                     if x == "ja" and y == "keine_reaktanz")
            bn = sum(1 for x, y in pairs
                     if x == "nein" and y == "keine_reaktanz")
            out["codebook_pairwise"].append({
                "model": m, "cond": cond, "n": len(pairs),
                "both": both, "fp": fp, "fn": fn, "both_no": bn,
                "fp_tp": round(fp / both, 2) if both else None,
                "b_uses_A_labels": sum(1 for _, y in pairs if y in ("ja", "nein")),
            })

    # ---------- 3b. codebook A x B full confusion (2 x 7 and collapsed 2 x 2) --
    CB2 = ["konfrontation_angriff", "ablenkung_whataboutism",
           "delegierung_hilflosigkeit", "vermeidung_rueckzug",
           "reflektierte_rechtfertigung", "konstruktive_kritik"]
    collapsed_lbl = ["keine_reaktanz", "reaktant"]
    for cond in ("A", "B"):
        for m in models:
            uids = sorted([u for u in rows
                           if (m, "A", cond, u) in lab and (m, "B", cond, u) in lab])
            pairs = [(x, y) for x, y in
                     zip(vec(m, "A", cond, uids), vec(m, "B", cond, uids))
                     if x in LAB_A and y in LAB_B]
            if not pairs:
                continue
            # full 2 x 7
            ia = {"nein": 0, "ja": 1}
            mtx = np.zeros((2, len(LAB_B)), dtype=int)
            for x, y in pairs:
                mtx[ia[x], LAB_B.index(y)] += 1
            nrm = np.zeros_like(mtx, dtype=float)
            for i in range(2):
                s = mtx[i].sum()
                if s:
                    nrm[i] = mtx[i] / s
            # collapsed 2 x 2 (A yes/no vs B reactant/none)
            m2 = np.zeros((2, 2), dtype=int)
            for x, y in pairs:
                m2[ia[x], 0 if y == "keine_reaktanz" else 1] += 1
            n2 = np.zeros_like(m2, dtype=float)
            for i in range(2):
                s = m2[i].sum()
                if s:
                    n2[i] = m2[i] / s
            extra = next((c for c in out["codebook_pairwise"]
                          if c["model"] == m and c["cond"] == cond), None)
            out.setdefault("codebook_confusion", []).append({
                "model": m, "cond": cond, "n": len(pairs),
                "labels_A": LAB_A, "labels_B": LAB_B,
                "labels_B_collapsed": collapsed_lbl,
                "raw_2x7": mtx.tolist(), "norm_2x7": nrm.tolist(),
                "raw_2x2": m2.tolist(), "norm_2x2": n2.tolist(),
                "fp_tp": (extra or {}).get("fp_tp"),
                "both": (extra or {}).get("both"), "fp": (extra or {}).get("fp"),
                "fn": (extra or {}).get("fn"),
                "precision": (round(m2[1, 1] / (m2[1, 1] + m2[0, 1]), 4)
                              if (m2[1, 1] + m2[0, 1]) else None),
                "recall": (round(m2[1, 1] / (m2[1, 1] + m2[1, 0]), 4)
                           if (m2[1, 1] + m2[1, 0]) else None)})

    # ---------- 3c. binary F1 against the consensus majority ----------------
    for cond in ("A", "B"):
        uids = [u for u in rows
                if all((m, "A", cond, u) in lab for m in models)]
        if not uids:
            continue
        ref = []
        for u in uids:
            v = [lab[(m, "A", cond, u)] for m in models]
            ref.append("ja" if v.count("ja") > len(v) / 2 else "nein")
        for m in models:
            pred = [lab[(m, "A", cond, u)] for u in uids]
            tp = sum(1 for a, b in zip(pred, ref) if a == "ja" and b == "ja")
            fp_ = sum(1 for a, b in zip(pred, ref) if a == "ja" and b == "nein")
            fn_ = sum(1 for a, b in zip(pred, ref) if a == "nein" and b == "ja")
            pr = tp / (tp + fp_) if tp + fp_ else None
            rc = tp / (tp + fn_) if tp + fn_ else None
            out.setdefault("binary_f1", []).append({
                "model": m, "cond": cond, "n": len(uids),
                "ref_positives": ref.count("ja"), "tp": tp, "fp": fp_, "fn": fn_,
                "precision": round(pr, 4) if pr is not None else None,
                "recall": round(rc, 4) if rc is not None else None,
                "f1": (round(2 * pr * rc / (pr + rc), 4)
                       if pr and rc else None)})

    # ---------- 4. bootstrap CI on prevalence ------------------------------
    for cb, neg in (("A", "nein"), ("B", "keine_reaktanz")):
        for cond in ("A", "B"):
            for m in models:
                vs = [1 if lab.get((m, cb, cond, u)) not in (None, neg) else 0
                      for u in rows if (m, cb, cond, u) in lab]
                if not vs:
                    continue
                obs = 100 * float(np.mean(vs))
                ci = bootstrap_ci(vs)
                out["bootstrap_prev"].append({
                    "cb": cb, "cond": cond, "model": m, "n": len(vs),
                    "pct": round(obs, 2), "ci_lo": ci[0], "ci_hi": ci[1]})

    # ---------- 5. consensus as reference (codebook A) ---------------------
    for cond in ("A", "B"):
        uids = [u for u in rows
                if all((m, "A", cond, u) in lab for m in models)]
        if not uids:
            continue
        # reference = majority vote of the three models
        ref = {}
        for u in uids:
            votes = [lab[(m, "A", cond, u)] for m in models]
            ref[u] = "ja" if votes.count("ja") > len(votes) / 2 else "nein"
        npos = sum(1 for u in uids if ref[u] == "ja")
        for m in models:
            pred = [lab[(m, "A", cond, u)] for u in uids]
            refs = [ref[u] for u in uids]
            tp = sum(1 for a, b in zip(pred, refs) if a == "ja" and b == "ja")
            fp = sum(1 for a, b in zip(pred, refs) if a == "ja" and b == "nein")
            fn = sum(1 for a, b in zip(pred, refs) if a == "nein" and b == "ja")
            prec = tp / (tp + fp) if tp + fp else None
            rec = tp / (tp + fn) if tp + fn else None
            f1 = (2 * prec * rec / (prec + rec)) if prec and rec else None
            # reference-free agreement measures of this model vs the majority
            # (same definitions as the pairwise section), so a single table can
            # carry raw / F1 / kappa / AC1 side by side
            kk = cohen_kappa(pred, refs, LAB_A)
            aa = gwets_ac1(pred, refs, LAB_A)
            out["consensus_reference"].append({
                "model": m, "cond": cond, "n": len(uids), "n_ref_pos": npos,
                "tp": tp, "fp": fp, "fn": fn,
                "precision": round(prec, 4) if prec is not None else None,
                "recall": round(rec, 4) if rec is not None else None,
                "f1": round(f1, 4) if f1 is not None else None,
                "raw": round(float(np.mean([a == b for a, b in zip(pred, refs)])), 4),
                "kappa": round(kk, 4) if kk is not None else None,
                "ac1": round(aa, 4) if aa is not None else None})

    # ---------- 6. Jev calibration + threshold sweep -----------------------
    reqs = load(RES / "requests_full.jsonl")
    jev = [r for r in reqs if r["model"] == "jev-1.13" and r.get("probabilities")
           and r.get("label") in LAB_A]
    seen = set()
    for cb in ("A",):
        for cond in ("A", "B"):
            recs = {}
            for r in jev:
                if r["codebook"] != cb or r["condition"] != cond:
                    continue
                if r["uid"] in recs:
                    continue
                recs[r["uid"]] = r
            if not recs:
                continue
            # consensus reference from the other two chat models
            chat = [m for m in models if m != "jev-1.13"]
            rowsx = []
            for u, r in recs.items():
                votes = [lab.get((m, "A", cond, u)) for m in chat]
                votes = [v for v in votes if v in LAB_A]
                if len(votes) < 2:
                    continue
                ref = "ja" if votes.count("ja") > len(votes) / 2 else "nein"
                p = r["probabilities"]
                pos = "ja" if p.get("ja", 0) >= p.get("nein", 0) else "nein"
                rowsx.append({
                    "p_pos": p.get("ja", 0.0), "conf": r.get("confidence"),
                    "pred": pos, "ref": ref})
            if not rowsx:
                continue
            # calibration bins
            bins = np.linspace(0, 1, 11)
            cal = []
            for lo, hi in zip(bins[:-1], bins[1:]):
                sel = [x for x in rowsx
                       if (lo <= x["p_pos"] < hi) or (hi == 1.0 and x["p_pos"] == 1.0)]
                if len(sel) < 5:
                    continue
                cal.append({
                    "lo": round(float(lo), 2), "hi": round(float(hi), 2),
                    "n": len(sel),
                    "mean_p": round(float(np.mean([x["p_pos"] for x in sel])), 3),
                    "obs": round(float(np.mean([1.0 if x["ref"] == "ja" else 0.0
                                                for x in sel])), 3)})
            out["calibration"].append({"cond": cond, "bins": cal,
                                       "n": len(rowsx)})
            # threshold sweep: flag as positive when p_pos >= t
            sweep = []
            for t in [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                sel = [x for x in rowsx if x["p_pos"] >= t]
                tp = sum(1 for x in sel if x["ref"] == "ja")
                fp = sum(1 for x in sel if x["ref"] == "nein")
                fn = sum(1 for x in rowsx if x["p_pos"] < t and x["ref"] == "ja")
                prec = tp / (tp + fp) if tp + fp else None
                rec = tp / (tp + fn) if tp + fn else None
                sweep.append({
                    "t": t, "n_flagged": len(sel),
                    "coverage_pct": round(100 * len(sel) / len(rowsx), 2),
                    "tp": tp, "fp": fp, "fn": fn,
                    "precision": round(prec, 3) if prec is not None else None,
                    "recall": round(rec, 3) if rec is not None else None})
            out["threshold_sweep"].append({"cond": cond, "sweep": sweep,
                                           "n": len(rowsx)})

    # ---------- 7. transcript length effect --------------------------------
    for cb, neg in (("A", "nein"), ("B", "keine_reaktanz")):
        for cond in ("A", "B"):
            buckets = defaultdict(lambda: [0, 0])
            for m in models:
                for u in rows:
                    l = lab.get((m, cb, cond, u))
                    if l is None:
                        continue
                    # only meaningful where the transcript is actually used
                    tlen = rows[u]["transcript_chars"]
                    b = ("<700" if tlen < 700 else
                         "700-1000" if tlen < 1000 else ">=1000")
                    buckets[b][1] += 1
                    if l != neg:
                        buckets[b][0] += 1
            tot = sum(v[1] for v in buckets.values())
            if not tot:
                continue
            for b, (p, n) in sorted(buckets.items()):
                out["transcript_effect"].append({
                    "cb": cb, "cond": cond, "bucket": b, "n": n,
                    "pct": round(100 * p / n, 2)})

    (RES / "analysis_ext.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote results/analysis_ext.json")
    print("\n== bootstrap 95% CI (codebook A) ==")
    for b in out["bootstrap_prev"]:
        if b["cb"] == "A":
            print(f"  {b['model']:20s} cond{b['cond']} {b['pct']:5.2f}% "
                  f"[{b['ci_lo']}, {b['ci_hi']}]  n={b['n']}")
    print("\n== McNemar A vs B condition (codebook A) ==")
    for c in out["condition_pairwise"]:
        if c.get("mcnemar"):
            mm = c["mcnemar"]
            print(f"  {c['model']:20s} prevA={c['prev_A_pct']}% prevB={c['prev_B_pct']}% "
                  f"discordant {mm['b10']}/{mm['b01']} p={mm['p']}")
    print("\n== Gwet AC1 vs Cohen kappa (codebook A, cond A) ==")
    for mp in out["model_pairwise"]:
        if mp["cb"] == "A" and mp["cond"] == "A":
            print(f"  {mp['a'][:12]:12s} vs {mp['b'][:12]:12s} "
                  f"raw={mp['raw_pct']}% k={mp['kappa']} AC1={mp['ac1']}")
    print("\n== consensus reference (codebook A, cond A) ==")
    for cr in out["consensus_reference"]:
        if cr["cond"] == "A":
            print(f"  {cr['model']:20s} P={cr['precision']} R={cr['recall']} "
                  f"F1={cr['f1']}  (ref positives {cr['n_ref_pos']})")
    print("\n== Jev threshold sweep (cond A) ==")
    for ts in out["threshold_sweep"]:
        if ts["cond"] == "A":
            for s in ts["sweep"]:
                print(f"  t>={s['t']:.2f}  flagged={s['n_flagged']:5d} "
                      f"({s['coverage_pct']:5.1f}%)  P={s['precision']} R={s['recall']}")


if __name__ == "__main__":
    main()

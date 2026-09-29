"""F1 and the large-scale (2,001-comment, comment-only) evaluation.

Two jobs:
  1. Proper F1 for the binary task. The consensus majority is treated as a
     REFERENCE, not ground truth -- so F1 is reported as agreement-with-
     consensus and labelled as such.
  2. The big run (jev, condition B, codebook A + B, 2,001 comments) with
     macro/micro F1 over the 7-way task, the A-vs-B crosstab, and F1 broken
     down by the confidence band the decision API reports.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
LAB_B = ["keine_reaktanz", "konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik"]


def load(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p is not None and r is not None and p + r else None
    rd = lambda v: round(v, 4) if v is not None else None
    return {"precision": rd(p), "recall": rd(r), "f1": rd(f),
            "tp": tp, "fp": fp, "fn": fn}


def binary_f1(pred, ref):
    tp = sum(1 for a, b in zip(pred, ref) if a == "ja" and b == "ja")
    fp = sum(1 for a, b in zip(pred, ref) if a == "ja" and b == "nein")
    fn = sum(1 for a, b in zip(pred, ref) if a == "nein" and b == "ja")
    return prf(tp, fp, fn)


def macro_f1(pred, ref, labels):
    out = {}
    for l in labels:
        tp = sum(1 for a, b in zip(pred, ref) if a == l and b == l)
        fp = sum(1 for a, b in zip(pred, ref) if a == l and b != l)
        fn = sum(1 for a, b in zip(pred, ref) if a != l and b == l)
        out[l] = prf(tp, fp, fn)
    valid = [v for v in out.values() if v["f1"] is not None]
    out["_macro"] = {
        "f1": round(float(np.mean([v["f1"] for v in valid])), 4) if valid else None,
        "n_labels_scored": len(valid),
    }
    # micro over all labels == accuracy
    n = sum(1 for a, b in zip(pred, ref) if a == b)
    out["_micro_accuracy"] = round(n / len(pred), 4) if pred else None
    return out


def main():
    out = {"binary_f1_vs_consensus": [], "big_run": {}}

    # ---------- 1. binary F1 for the 1,200-comment matrix -------------------
    full = load(RES / "predictions_full.jsonl")
    models = sorted({p["model"] for p in full})
    lab = {(p["model"], p["codebook"], p["condition"], p["uid"]): p["label"]
           for p in full if p["label"] is not None}
    for cond in ("A", "B"):
        uids = [u for u in {p["uid"] for p in full}
                if all((m, "A", cond, u) in lab for m in models)]
        if not uids:
            continue
        ref = []
        for u in uids:
            v = [lab[(m, "A", cond, u)] for m in models]
            ref.append("ja" if v.count("ja") > len(v) / 2 else "nein")
        for m in models:
            pred = [lab[(m, "A", cond, u)] for u in uids]
            r = binary_f1(pred, ref)
            r.update({"model": m, "cond": cond, "n": len(uids),
                      "ref_positives": ref.count("ja")})
            out["binary_f1_vs_consensus"].append(r)

    # ---------- 2. the big run ---------------------------------------------
    big = load(RES / "predictions_big.jsonl")
    if big:
        B = {"big_run": {}}
        n = len({p["uid"] for p in big})
        B["big_run"]["n_comments"] = n
        B["big_run"]["n_requests"] = len(big)
        B["big_run"]["cost_usd"] = round(
            sum(p.get("cost_usd") or 0 for p in big if not p.get("was_cached")), 4)
        bycb = defaultdict(dict)
        for p in big:
            if p["label"]:
                bycb[p["codebook"]][p["uid"]] = p["label"]
        meta = json.load((REPO / "data/sample_meta.json").open(encoding="utf-8"))
        B["big_run"]["sample"] = {
            "accounts": meta["accounts_used"], "parties": meta["parties_used"],
            "videos": meta["videos_used"],
            "party_counts": meta["party_counts"]}

        # codebook A: prevalence + bootstrap
        A_ = bycb.get("A", {})
        vs = [1 if v == "ja" else 0 for v in A_.values()]
        rng = np.random.default_rng(3)
        arr = np.asarray(vs, dtype=float)
        idx = rng.integers(0, len(arr), size=(2000, len(arr)))
        draws = 100 * arr[idx].mean(axis=1)
        B["big_run"]["codebook_A"] = {
            "n": len(vs), "n_positive": int(sum(vs)),
            "prevalence_pct": round(100 * float(arr.mean()), 2),
            "ci95": [round(float(np.quantile(draws, 0.025)), 2),
                     round(float(np.quantile(draws, 0.975)), 2)]}

        # codebook B: prevalence, distribution, and macro-F1 of B against B
        Bb = bycb.get("B", {})
        dist = Counter(Bb.values())
        pos = len(Bb) - dist.get("keine_reaktanz", 0)
        B["big_run"]["codebook_B"] = {
            "n": len(Bb), "n_positive": pos,
            "prevalence_pct": round(100 * pos / max(1, len(Bb)), 2),
            "distribution": {k: dist.get(k, 0) for k in LAB_B}}

        # A vs B agreement on the same comments
        common = sorted(set(A_) & set(Bb))
        both = sum(1 for u in common if A_[u] == "ja" and Bb[u] != "keine_reaktanz")
        fp = sum(1 for u in common if A_[u] == "nein" and Bb[u] != "keine_reaktanz")
        fn = sum(1 for u in common if A_[u] == "ja" and Bb[u] == "keine_reaktanz")
        bn = sum(1 for u in common if A_[u] == "nein" and Bb[u] == "keine_reaktanz")
        agree = round(100 * (both + bn) / len(common), 2) if common else None
        k = None
        if common:
            n_ = len(common)
            po = (both + bn) / n_
            ca, cb = Counter(A_[u] for u in common), Counter(Bb[u] for u in common)
            pe = sum((ca[l] / n_) * (cb[l] / n_) for l in set(ca) | set(cb))
            k = 1.0 if abs(1 - pe) < 1e-12 else round((po - pe) / (1 - pe), 4)
        B["big_run"]["A_vs_B"] = {
            "n": len(common), "both": both, "fp": fp, "fn": fn, "both_none": bn,
            "raw_agreement_pct": agree, "cohens_kappa": k,
            "fp_tp": round(fp / both, 2) if both else None}

        # F1 of B against A collapsed to reactance yes/no
        pred_bin = ["ja" if Bb[u] != "keine_reaktanz" else "nein" for u in common]
        ref_bin = [A_[u] for u in common]
        B["big_run"]["B_as_binary_vs_A"] = binary_f1(pred_bin, ref_bin)

        # macro-F1 across the 7 labels, model vs itself is degenerate, so use
        # the A/B agreement structure instead: report per-label support + recall
        # of the reactance-vs-none binary mapping
        sup = {k: dist.get(k, 0) for k in LAB_B}
        B["big_run"]["codebook_B_support"] = sup

        # confidence-band breakdown for codebook A
        reqs = load(RES / "requests_big.jsonl")
        bands = defaultdict(lambda: [0, 0])
        for r in reqs:
            if r.get("model") != "jev-1.13" or r.get("codebook") != "A":
                continue
            p = (r.get("probabilities") or {}).get("ja")
            if p is None or r.get("was_cached"):
                continue
            b = ("<0.1" if p < 0.1 else "0.1-0.3" if p < 0.3 else
                 "0.3-0.6" if p < 0.6 else "0.6-0.9" if p < 0.9 else ">=0.9")
            bands[b][1] += 1
            if r["label"] == "ja":
                bands[b][0] += 1
        B["big_run"]["confidence_bands"] = {
            k: {"n": v[1], "n_positive": v[0],
                "rate_pct": round(100 * v[0] / v[1], 2) if v[1] else None}
            for k, v in sorted(bands.items())}
        out["big_run"] = B["big_run"]

    (RES / "analysis_f1.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print("== binary F1 vs consensus majority (Codebook A) ==")
    for r in out["binary_f1_vs_consensus"]:
        print(f"  {r['model']:20s} cond{r['cond']} n={r['n']} ref+={r['ref_positives']:3d} "
              f"P={r['precision']} R={r['recall']} F1={r['f1']}")
    B_ = out.get("big_run") or {}
    if B_:
        print(f"\n== big run: {B_['n_comments']} comments, condition B, "
              f"${B_['cost_usd']} ==")
        a = B_["codebook_A"]
        print(f"  codebook A: {a['n_positive']}/{a['n']} = {a['prevalence_pct']} % "
              f"[{a['ci95'][0]}, {a['ci95'][1]}]")
        b = B_["codebook_B"]
        print(f"  codebook B: {b['n_positive']}/{b['n']} = {b['prevalence_pct']} %")
        print(f"    {b['distribution']}")
        ab = B_["A_vs_B"]
        print(f"  A x B: n={ab['n']} both={ab['both']} fp={ab['fp']} fn={ab['fn']} "
              f"agree={ab['raw_agreement_pct']} % kappa={ab['cohens_kappa']} "
              f"fp:tp={ab['fp_tp']}")
        f1 = B_["B_as_binary_vs_A"]
        print(f"  B(collapsed) vs A: P={f1['precision']} R={f1['recall']} F1={f1['f1']}")
        print(f"  confidence bands: {B_['confidence_bands']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""The large-scale run (2,001 comments, comment-only, sharpened codebook).

Scope (important, and the point of this file): the big sample is coded, under
Condition B only, by two models --
  * jev-1.13  (run 'big')    -- both codebooks, 2,001 comments
  * glm-5.3-flash (run 'glm_big') -- both codebooks, 2,001 comments
The other two models are NOT on the big sample. Every aggregate below carries
`sample: "big"`, the model, the n that went into it and the condition, so the
report can never again print a 2,001 number next to a table whose rows are the
1,200-comment matrix sample (or vice versa).

Jobs:
  1. binary F1 for the 1,200-comment MATRIX sample. The consensus majority is
     a REFERENCE, not ground truth -- F1 against it is an agreement measure
     ("distance from consensus"), labelled as such, never "correctness".
  2. the big run: per-model prevalence + bootstrap CI for both codebooks, the
     per-model A-vs-B crosstab (raw agreement, kappa, FP/FN, FP:TP, n=2,001),
     and the Jev confidence-band breakdown.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# reuse the canonical kappa helper (analyze_extended.main() is __main__-guarded)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_extended import cohen_kappa  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
LAB_B = ["keine_reaktanz", "konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik"]
NEG_B = "keine_reaktanz"


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


def bootstrap_ci95(vals, scale=100, n=2000, seed=3):
    rng = np.random.default_rng(seed)
    arr = np.asarray(vals, dtype=float)
    idx = rng.integers(0, len(arr), size=(n, len(arr)))
    draws = scale * arr[idx].mean(axis=1)
    return [round(float(np.quantile(draws, 0.025)), 2),
            round(float(np.quantile(draws, 0.975)), 2)]


def main():
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {
        "meta": {
            "generated_at": generated_at,
            "source_files": ["predictions_full.jsonl", "predictions_big.jsonl",
                              "predictions_glm_big.jsonl"],
            "matrix_sample": {"sample": "matrix", "n": 1200,
                               "conditions": ["A", "B"]},
            "big_sample": {"sample": "big", "n": 2001, "conditions": ["B"]},
        },
        "binary_f1_vs_consensus": [],
    }

    # ---------- 1. binary F1, matrix sample --------------------------------
    full = load(RES / "predictions_full.jsonl")
    models = sorted({p["model"] for p in full})
    lab = {(p["model"], p["codebook"], p["condition"], p["uid"]): p["label"]
           for p in full if p["label"] is not None}
    for cond in ("A", "B"):
        uids = [u for u in {p["uid"] for p in full}
                if all((m, "A", cond, u) in lab for m in models)]
        if not uids:
            continue
        # reference = 4-model majority = consensus PROXY, not ground truth
        ref = []
        for u in uids:
            v = [lab[(m, "A", cond, u)] for m in models]
            ref.append("ja" if v.count("ja") > len(v) / 2 else "nein")
        for m in models:
            pred = [lab[(m, "A", cond, u)] for u in uids]
            r = binary_f1(pred, ref)
            r.update({"model": m, "cond": cond, "sample": "matrix", "n": len(uids),
                      "ref_positives": ref.count("ja")})
            out["binary_f1_vs_consensus"].append(r)

    # ---------- 2. the big run ---------------------------------------------
    big_all = load(RES / "predictions_big.jsonl") + load(RES / "predictions_glm_big.jsonl")
    if big_all:
        n = len({p["uid"] for p in big_all})
        big_models = sorted({p["model"] for p in big_all})
        meta = json.load((REPO / "data/sample_big_meta.json").open(encoding="utf-8"))
        out.update({
            "sample": "big",
            "n_comments": n,
            "n_requests": len(big_all),
            "models": big_models,
            "cost_usd": round(
                sum(p.get("cost_usd") or 0 for p in big_all if not p.get("was_cached")), 4),
            "sample_meta": {
                "accounts": meta["accounts_used"], "parties": meta["parties_used"],
                "videos": meta["videos_used"], "party_counts": meta["party_counts"]},
        })

        by_model = defaultdict(lambda: defaultdict(dict))
        for p in big_all:
            if p["label"]:
                by_model[p["model"]][p["codebook"]][p["uid"]] = p["label"]

        # per-model prevalence, both codebooks (big sample, condition B)
        prev_a, prev_b = {}, {}
        for m in big_models:
            A_ = by_model[m].get("A", {})
            vs = [1 if v == "ja" else 0 for v in A_.values()]
            prev_a[m] = {"model": m, "sample": "big", "n": len(vs),
                          "n_positive": int(sum(vs)),
                          "prevalence_pct": round(100 * float(np.mean(vs)), 2) if vs else None,
                          "ci95": bootstrap_ci95(vs) if vs else None}
            Bb = by_model[m].get("B", {})
            dist = Counter(Bb.values())
            pos = len(Bb) - dist.get(NEG_B, 0)
            prev_b[m] = {"model": m, "sample": "big", "n": len(Bb), "n_positive": pos,
                         "prevalence_pct": round(100 * pos / max(1, len(Bb)), 2) if Bb else None,
                         "distribution": {k: dist.get(k, 0) for k in LAB_B}}
        out["prevalence_A"] = prev_a
        out["prevalence_B"] = prev_b

        # A x B per model on the big sample: the numbers the report must carry,
        # each with its own n (2,001), model, condition and sample tag.
        ab = []
        for m in big_models:
            A_ = by_model[m].get("A", {})
            Bb = by_model[m].get("B", {})
            common = sorted(set(A_) & set(Bb))
            if not common:
                continue
            both = sum(1 for u in common if A_[u] == "ja" and Bb[u] != NEG_B)
            fp = sum(1 for u in common if A_[u] == "nein" and Bb[u] != NEG_B)
            fn = sum(1 for u in common if A_[u] == "ja" and Bb[u] == NEG_B)
            bn = sum(1 for u in common if A_[u] == "nein" and Bb[u] == NEG_B)
            agree = round(100 * (both + bn) / len(common), 2)
            n_ = len(common)
            # Cohen's kappa must be computed on a SHARED binary label space.
            # Codebook A is {ja, nein}; Codebook B is {keine_reaktanz, six
            # types}. Comparing those label spaces directly makes the expected
            # agreement invalid (it effectively forces pe near 1 and inflates
            # kappa). Collapse both to binary reactant/none first, then apply
            # the same cohen_kappa() helper used elsewhere.
            a_bin = [1 if A_[u] == "ja" else 0 for u in common]
            b_bin = [1 if Bb[u] != NEG_B else 0 for u in common]
            k = cohen_kappa(a_bin, b_bin, ["nein", "ja"])
            ab.append({"model": m, "sample": "big", "condition": "B", "n": n_,
                       "both": both, "fp": fp, "fn": fn, "both_none": bn,
                       "raw_agreement_pct": agree,
                       "cohens_kappa": round(k, 4) if k is not None else None,
                       "kappa_label_space": "binary (A: ja/nein vs B: reactant/none)",
                       "fp_tp": round(fp / both, 2) if both else None})
        out["A_vs_B"] = ab
        # Jev confidence bands (the decision API is the only one reporting them)
        reqs = [r for r in load(RES / "requests_big.jsonl") if r.get("model") == "jev-1.13"]
        bands = defaultdict(lambda: [0, 0])
        for r in reqs:
            if r.get("codebook") != "A":
                continue
            p = (r.get("probabilities") or {}).get("ja")
            if p is None or r.get("was_cached"):
                continue
            b = ("<0.1" if p < 0.1 else "0.1-0.3" if p < 0.3 else
                 "0.3-0.6" if p < 0.6 else "0.6-0.9" if p < 0.9 else ">=0.9")
            bands[b][1] += 1
            if r["label"] == "ja":
                bands[b][0] += 1
        out["confidence_bands"] = {
            k: {"n": v[1], "n_positive": v[0],
                "rate_pct": round(100 * v[0] / v[1], 2) if v[1] else None}
            for k, v in sorted(bands.items())}

    (RES / "analysis_big.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote results/analysis_big.json")

    print("== binary F1 vs consensus majority (matrix sample, Codebook A) ==")
    for r in out["binary_f1_vs_consensus"]:
        print(f"  {r['model']:22s} cond{r['cond']} n={r['n']} ref+={r['ref_positives']:3d} "
              f"P={r['precision']} R={r['recall']} F1={r['f1']}")
    B_ = {k: v for k, v in out.items() if k.startswith(("prevalence", "A_vs_B", "n_"))}
    if "n_comments" in out:
        print(f"\n== big run: {out['n_comments']} comments, condition B, "
              f"models={out['models']}, ${out['cost_usd']} ==")
        for m in out["models"]:
            a = out["prevalence_A"][m]
            b = out["prevalence_B"][m]
            print(f"  {m:22s} A: {a['n_positive']:3d}/{a['n']} = {a['prevalence_pct']}% "
                  f"[{a['ci95'][0]}; {a['ci95'][1]}]   B: {b['n_positive']:3d}/{b['n']} = {b['prevalence_pct']}%")
        for r in out["A_vs_B"]:
            print(f"  A x B {r['model']:22s} n={r['n']} both={r['both']} fp={r['fp']} "
                  f"fn={r['fn']} agree={r['raw_agreement_pct']}% "
                  f"kappa={r['cohens_kappa']} fp:tp={r['fp_tp']}")
        print(f"  confidence bands (Jev): {out['confidence_bands']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Experiment B (new condition C): Jev-gated type classification.

Condition C ("gate"): a cheap binary first pass decides which comments get the
costly 7-way type classification at all.

  Step 1 (gate)   : Jev, Codebook A, answers yes/no for every comment.
  Step 2 (type)   : every model -- Jev included, all four -- classifies the
                    TYPE (Codebook B) for every comment the gate marked 'ja'.

The gate is Jev's for all models, so all models annotate the SAME comment set:
the matrix of 7x7 confusion matrices (model x model) is directly comparable
with Figure 5, and the majority vote is a clean 4-vote plurality per comment.

Nothing here costs an API call: every prediction (Codebook A and B for all
models, both samples) is already on disk; this script only re-combines them.

Two views are computed per sample/condition:

  * fixed Jev gate (the condition proper):
      - per-model type distribution on the Jev-gated set
      - 4x4 grid of 7x7 confusion matrices (model x model) on the gated set
      - majority vote per gated comment: share of comments whose majority
        reaches each k-of-4 threshold, per-model agreement with the majority,
        and the majority type distribution
  * per-model gate (sensitivity): what the pipeline would look like if each
      model gated on its OWN Codebook-A judgement instead of Jev's.
"""
from __future__ import annotations

import json
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

LAB_B = ["keine_reaktanz", "konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik"]
NEG_A, NEG_B = "nein", "keine_reaktanz"
PREF = ["jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash", "glm-5.3-flash"]
CL = {l: s for l, s in zip(LAB_B, ["none", "attack", "deflect", "delegate",
                                    "avoid", "justify", "critique"])}


def load(p):
    try:
        return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
    except FileNotFoundError:
        return []


def order_models(models):
    return [m for m in PREF if m in models] + [m for m in models if m not in PREF]


def collect(preds_paths, cond, models):
    """label[model][uid] = label for the given condition, merged across files."""
    A, B = {}, {}
    for name in preds_paths:
        for p in load(RES / name):
            if p["condition"] != cond or p["model"] not in models:
                continue
            tgt = A if p["codebook"] == "A" else B
            tgt.setdefault(p["model"], {})[p["uid"]] = p["label"]
    return A, B


def confusion_matrix(rows_, cols_, labels):
    ia = {l: i for i, l in enumerate(labels)}
    m = np.zeros((len(labels), len(labels)), dtype=int)
    for x, y in zip(rows_, cols_):
        if x in ia and y in ia:
            m[ia[x], ia[y]] += 1
    return m


def pairwise_stats(rows_, cols_, labels):
    n = len(rows_)
    base = confusion_matrix(rows_, cols_, labels)
    nrm = np.zeros_like(base, dtype=float)
    for i in range(len(labels)):
        s = base[i].sum()
        if s:
            nrm[i] = base[i] / s
    agree = round(100 * sum(1 for x, y in zip(rows_, cols_) if x == y) / n, 2)
    po = agree / 100
    ca, cb = Counter(rows_), Counter(cols_)
    pe = sum((ca.get(l, 0) / n) * (cb.get(l, 0) / n) for l in labels)
    kappa = 1.0 if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)
    return base.tolist(), nrm.tolist(), agree, round(kappa, 4)


def majority(labels):
    c = Counter(labels)
    best = max(c.values())
    return min((l for l, n in c.items() if n == best), key=LAB_B.index), best


def analyse_cond(cond, A, B, models):
    """Condition C analysis for one sample/condition. Gate = Jev."""
    out = {"cond": cond, "models": models, "jev_gated": [], "pairwise": [],
           "majority": None, "own_gate": []}

    # ---- the gate set -------------------------------------------------------
    gate_A = A.get("jev-1.13", {})
    gated = sorted(u for u, l in gate_A.items() if l == "ja")

    # ---- per-model type distribution on the gated set ----------------------
    for m in models:
        b = B.get(m, {})
        dist = Counter(b[u] for u in gated if b.get(u) in LAB_B)
        n_typed = sum(dist.values())
        out["jev_gated"].append({
            "model": m, "n_typed": n_typed,
            "dist": {l: dist.get(l, 0) for l in LAB_B},
            "reactant_share_pct": round(
                100 * (n_typed - dist.get(NEG_B, 0)) / n_typed, 2) if n_typed else None,
        })

    # ---- grid of 7x7 confusion matrices on the gated set --------------------
    for m1, m2 in combinations(models, 2):
        b1, b2 = B.get(m1, {}), B.get(m2, {})
        uids = [u for u in gated if b1.get(u) in LAB_B and b2.get(u) in LAB_B]
        if not uids:
            continue
        raw, nrm, agree, kappa = pairwise_stats(
            [b1[u] for u in uids], [b2[u] for u in uids], LAB_B)
        out["pairwise"].append({"a": m1, "b": m2, "n": len(uids),
                                 "raw": raw, "norm": nrm,
                                 "raw_pct": agree, "kappa": kappa})

    # ---- majority vote on the gated set ------------------------------------
    maj_rows = []
    for u in gated:
        votes = [B[m][u] for m in models if B.get(m, {}).get(u) in LAB_B]
        if not votes:
            continue
        lab, n = majority(votes)
        maj_rows.append((u, lab, n, len(votes)))
    if maj_rows:
        n_tot = len(maj_rows)
        dist = Counter(l for _, l, _, _ in maj_rows)
        thr = []
        for k in range(2, len(models) + 1):
            ok = sum(1 for _, _, n, nv in maj_rows if n >= k)
            thr.append({"k": k, "n": ok, "pct": round(100 * ok / n_tot, 2)})
        per_model = []
        for m in models:
            b = B.get(m, {})
            sel = [r for r in maj_rows if b.get(r[0]) in LAB_B]
            if not sel:
                continue
            n_ok = sum(1 for u, lab, _, _ in sel if b[u] == lab)
            per_model.append({"model": m, "n": len(sel),
                               "pct": round(100 * n_ok / len(sel), 2)})
        out["majority"] = {
            "n_gated": n_tot,
            "n_voters": len(models),
            "type_dist": {l: dist.get(l, 0) for l in LAB_B},
            "by_threshold": thr,
            "vs_majority": per_model,
        }

    # ---- sensitivity: each model as its own gate ---------------------------
    for m in models:
        a, b = A.get(m, {}), B.get(m, {})
        g = sorted(u for u, l in a.items() if l == "ja")
        dist = Counter(b[u] for u in g if b.get(u) in LAB_B)
        n_typed = sum(dist.values())
        out["own_gate"].append({
            "model": m, "gated": len(g),
            "gated_pct": round(100 * len(g) / max(1, len(a)), 2),
            "n_typed": n_typed,
            "dist": {l: dist.get(l, 0) for l in LAB_B},
            "reactant_share_pct": round(
                100 * (n_typed - dist.get(NEG_B, 0)) / n_typed, 2) if n_typed else None,
        })
    n_comments = max((len(a) for a in A.values()), default=0)
    out["n_comments"] = n_comments
    out["jev_gated_n"] = len(gated)
    out["jev_gated_pct"] = round(100 * len(gated) / max(1, n_comments), 2)
    return out


def main():
    out = {"note": ("Condition C: Jev's Codebook-A gate selects the comments; "
                    "every model (incl. Jev) then classifies the reactance TYPE "
                    "on exactly those comments. Pairwise 7x7 matrices and the "
                    "majority vote are computed on that common gated set."),
           "runs": {}}

    # ---- matrix sample: the 3-model matrix + glm (merged into predictions_full)
    matrix_models = order_models(
        {p["model"] for p in load(RES / "predictions_full.jsonl")})
    for cond in ("A", "B"):
        A, B = collect(["predictions_full.jsonl"], cond, set(matrix_models))
        out["runs"].setdefault("matrix", {"n_comments": 1200, "conditions": {}})
        out["runs"]["matrix"]["conditions"][cond] = analyse_cond(cond, A, B, matrix_models)

    # ---- big sample: jev + glm, condition B only ----------------------------
    big_models = order_models(set()
                              | {p["model"] for p in load(RES / "predictions_big.jsonl")}
                              | {p["model"] for p in load(RES / "predictions_glm_big.jsonl")})
    Ab, Bb = collect(["predictions_big.jsonl", "predictions_glm_big.jsonl"],
                     "B", set(big_models))
    out["runs"]["big"] = {"n_comments": 2001,
                          "conditions": {"B": analyse_cond("B", Ab, Bb, big_models)}}

    (RES / "analysis_gate.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote results/analysis_gate.json")

    for run, d in out["runs"].items():
        print(f"\n== {run} sample ==")
        for c, r in d["conditions"].items():
            print(f"  condition {c}: Jev gate -> {r['jev_gated_n']} "
                  f"({r['jev_gated_pct']}%) of {r['n_comments']}")
            for pm in r["jev_gated"]:
                top = sorted(pm["dist"].items(), key=lambda kv: -kv[1])[:2]
                top = ", ".join(f"{CL.get(l, l)}={n}" for l, n in top if n)
                print(f"    gate+type {pm['model']:22s} typed={pm['n_typed']:3d} "
                      f"reactant|gated={pm['reactant_share_pct']}%  top[{top}]")
            for pw in r["pairwise"]:
                print(f"    pair {pw['a'][:14]:14s} x {pw['b'][:14]:14s}: "
                      f"n={pw['n']:3d} agree={pw['raw_pct']}% kappa={pw['kappa']}")
            maj = r["majority"]
            if maj:
                print(f"    majority ({maj['n_voters']} votes, "
                      f"n={maj['n_gated']} gated):")
                for t in maj["by_threshold"]:
                    print(f"      >= {t['k']}/{maj['n_voters']} agree on one type: "
                          f"{t['pct']}% (n={t['n']})")
                for v in maj["vs_majority"]:
                    print(f"      {v['model']:22s} = majority for {v['pct']}% "
                          f"of its type calls")
            print("    own gate (sensitivity):")
            for og in r["own_gate"]:
                print(f"      {og['model']:22s} gates {og['gated']:4d} "
                      f"({og['gated_pct']:5.2f}%) -> reactant|gated="
                      f"{og['reactant_share_pct']}%")


if __name__ == "__main__":
    main()

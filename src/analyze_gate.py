#!/usr/bin/env python3
"""Condition C (gated): Jev-gated TYPE classification, split into two questions.

The gate is a binary first pass: Jev, Codebook A, answers yes/no for every
comment. Conceptually the gate answers "does reactance exist at all?". Once the
gate has established that, the downstream type task answers the SEPARATE
question "conditional on reactance, which TYPE is present?" -- and `keine_
reaktanz` is NOT one of the six reactance types, so it must not be counted as a
type.

This script therefore reports, per sample/condition:

  1. Gate consistency / rejection (`gate_consistency`)
     For each downstream model: of the comments Jev gated as 'ja', how many
     does this model RETAIN as reactant (it assigns one of the six types) versus
     REJECT (it re-labels them `keine_reaktanz`)? This is a gate-rejection
     diagnostic, not a type disagreement.

  2. Conditional six-class type analysis (`pairwise_type`, `type_distribution`)
     On the subset where BOTH models of a pair retained the gate (both assigned
     one of the six types), compute the six-class confusion matrix, raw
     agreement and kappa, and report the (conditional) `n` for every pair.

  3. Conditional type consensus (`type_consensus`)
     For each gated comment, only the models that RETAINED the gate vote on the
     type (plurality, tie-safe). A 2-2 split, or any 1-1 / 1-1-1 split within
     the accepting models, is a TIE (label null), not a majority. We report
     both how many models retained the gate (1/4..4/4) and, among the retainers,
     how strongly their type labels agree. No comment is scored against an
     arbitrarily tie-broken reference.

The sensitivity block `own_gate` (each model gating on its OWN Codebook-A call)
is left as a 7-class descriptive and is NOT the main gated analysis.

Nothing here costs an API call: every prediction (Codebook A and B for all
models, both samples) is already on disk; this script only re-combines them.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"

# The full Codebook B task is 7-class, but the GATED type task is 6-class:
# once the gate has established reactance, `keine_reaktanz` is a gate rejection,
# not a type.
LAB_B = ["keine_reaktanz", "konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik"]
TYPE_LABELS = [l for l in LAB_B if l != "keine_reaktanz"]
assert len(TYPE_LABELS) == 6, "the gated type task must be exactly six-class"
NEG_A, NEG_B = "nein", "keine_reaktanz"
GATE_MODEL = "jev-1.13"
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


def plurality(labels, order):
    """Tie-safe plurality. Returns (winner_or_None, max_count, is_tie).

    Any split for the highest count is a tie: 2-2, 1-1, 1-1-1, etc. A single
    vote (one model, one label) and no votes at all are not ties. This matters
    especially for sparse gated cases where two or three retaining models may
    all choose different types.
    """
    c = Counter(labels)
    if not c:
        return None, 0, False
    if len(labels) == 1:
        return labels[0], 1, False
    best = max(c.values())
    winners = [l for l in order if c.get(l) == best]
    if len(winners) != 1:
        return None, best, True
    return winners[0], best, False


# Regression guards for the tie semantics used by the report.
assert plurality(["a"], ["a", "b"] ) == ("a", 1, False)
assert plurality(["a", "b"], ["a", "b"] ) == (None, 1, True)
assert plurality(["a", "b", "c"], ["a", "b", "c"] ) == (None, 1, True)
assert plurality(["a", "a", "b", "b"], ["a", "b"] ) == (None, 2, True)
assert plurality(["a", "a", "b"], ["a", "b"] ) == ("a", 2, False)


def _gate_consistency(gated, B, models):
    """Q1: of Jev's gated positives, how often does each model reject the premise?"""
    out = []
    for m in models:
        b = B.get(m, {})
        n = 0
        n_accept = 0
        for u in gated:
            lab = b.get(u)
            if lab not in LAB_B:
                continue
            n += 1
            if lab in TYPE_LABELS:
                n_accept += 1
        n_reject = n - n_accept
        out.append({"model": m, "n": n, "n_gated": n,
                    "n_accept": n_accept, "n_reject": n_reject,
                    "accept_pct": round(100 * n_accept / n, 2) if n else None,
                    "reject_pct": round(100 * n_reject / n, 2) if n else None})
    return out


def _type_distribution(gated, B, models):
    """Q2 support: the six-class type distribution per model on the RETAINED set."""
    out = []
    for m in models:
        b = B.get(m, {})
        dist = Counter(b[u] for u in gated if b.get(u) in TYPE_LABELS)
        out.append({"model": m, "n": sum(dist.values()),
                    "dist": {l: dist.get(l, 0) for l in TYPE_LABELS}})
    return out


def _pairwise_type(gated, B, models):
    """Q2: six-class type confusion between models, on the CONDITIONAL support
    (both models retained the gate), with an explicit per-pair n."""
    out = []
    for m1, m2 in combinations(models, 2):
        b1, b2 = B.get(m1, {}), B.get(m2, {})
        uids = [u for u in gated
                if b1.get(u) in TYPE_LABELS and b2.get(u) in TYPE_LABELS]
        if not uids:
            continue
        raw, nrm, agree, kappa = pairwise_stats(
            [b1[u] for u in uids], [b2[u] for u in uids], TYPE_LABELS)
        out.append({"a": m1, "b": m2, "n": len(uids), "n_both_accept": len(uids),
                    "raw": raw, "norm": nrm, "raw_pct": agree, "kappa": kappa})
    return out


def _type_consensus(gated, B, models):
    """Q3: per gated comment, the models that RETAINED the gate vote on the type
    (tie-safe plurality). Returns both the per-comment records and the summary."""
    per = []
    for u in gated:
        votes = [B[m][u] for m in models if B.get(m, {}).get(u) in TYPE_LABELS]
        n_accept = len(votes)
        winner, cnt, tie = plurality(votes, TYPE_LABELS)
        per.append({"uid": u, "n_models_accepting_gate": n_accept,
                    "majority_type": winner, "majority_n": cnt,
                    "tie": tie, "n_models_voting": n_accept})

    n_gated = len(per)
    n_models = len(models)
    # Two SEPARATE distributions, reported side by side:
    #  (a) gate acceptance   : how many of the n_models retained the gate (1/4..4/4)
    #  (b) type-consensus strength: among the models that RETAINED the gate, how
    #      many agreed on one type (all split top counts are explicit ties)
    accept_dist = Counter(r["n_models_accepting_gate"] for r in per)
    gate_accept = {f"{k}-of-{n_models}": accept_dist.get(k, 0)
                   for k in range(n_models, -1, -1)}
    majority_n_dist = Counter(r["majority_n"] for r in per
                               if r["majority_type"] is not None)
    type_consensus = {
        **{f"{k}-of-{n_models}": majority_n_dist.get(k, 0)
           for k in range(n_models, -1, -1)},
        "tie": sum(1 for r in per if r["tie"]),
        "no_type_votes": sum(1 for r in per if r["n_models_accepting_gate"] == 0),
    }
    # per-model agreement with the (non-tie) consensus reference. Comments whose
    # type call was a TIE are excluded from the denominator: a model must not be
    # scored against an arbitrarily tie-broken reference.
    per_model = []
    for m in models:
        b = B.get(m, {})
        sel = [r for r in per
               if r["majority_type"] is not None and b.get(r["uid"]) in TYPE_LABELS]
        n_tie = sum(1 for r in per if r["tie"])
        if not sel:
            per_model.append({"model": m, "n": 0, "n_ties_excluded": n_tie,
                              "pct": None})
            continue
        n_ok = sum(1 for r in sel if b[r["uid"]] == r["majority_type"])
        per_model.append({"model": m, "n": len(sel), "n_ties_excluded": n_tie,
                          "pct": round(100 * n_ok / len(sel), 2)})
    majority_type_dist = Counter(r["majority_type"] for r in per
                                  if r["majority_type"] in TYPE_LABELS)
    return {
        "n_gated": n_gated,
        "n_voters": n_models,
        "gate_accept": gate_accept,
        "type_consensus": type_consensus,
        "majority_type_dist": {l: majority_type_dist.get(l, 0) for l in TYPE_LABELS},
        "vs_majority": per_model,
        "per_comment": per,
    }


def _pairwise_baseline7(gated, B, models):
    """Descriptive baseline: the OLD 7-class task (all of `LAB_B` incl.
    `keine_reaktanz`) on the same gated set, without conditioning. Kept so the
    report can contrast the conditional six-class analysis against the
    unconditional seven-class one on identical inputs -- the numbers are
    generated, not typed from an older analysis run."""
    out = []
    for m1, m2 in combinations(models, 2):
        b1, b2 = B.get(m1, {}), B.get(m2, {})
        uids = [u for u in gated if b1.get(u) in LAB_B and b2.get(u) in LAB_B]
        if not uids:
            continue
        raw, nrm, agree, kappa = pairwise_stats(
            [b1[u] for u in uids], [b2[u] for u in uids], LAB_B)
        out.append({"a": m1, "b": m2, "n": len(uids),
                    "raw_pct": agree, "kappa": kappa})
    return out


def analyse_cond(cond, A, B, models):
    """Gated-condition analysis for one sample/condition. Gate = Jev (Codebook A)."""
    out = {"cond": cond, "models": models, "gate_consistency": [],
           "type_distribution": [], "pairwise_type": [], "pairwise_baseline7": [],
           "type_consensus": None, "own_gate": []}

    # ---- the gate set -------------------------------------------------------
    gate_A = A.get(GATE_MODEL, {})
    gated = sorted(u for u, l in gate_A.items() if l == "ja")

    out["gate_consistency"] = _gate_consistency(gated, B, models)
    out["type_distribution"] = _type_distribution(gated, B, models)
    out["pairwise_type"] = _pairwise_type(gated, B, models)
    out["pairwise_baseline7"] = _pairwise_baseline7(gated, B, models)
    out["type_consensus"] = _type_consensus(gated, B, models)

    # ---- sensitivity: each model as its own gate (descriptive, 7-class) ----
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
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {"meta": {
               "generated_at": generated_at,
               "gate_model": GATE_MODEL, "gate_codebook": "A", "type_codebook": "B",
               "type_labels": TYPE_LABELS,
               "neg_type": NEG_B,
               "note": ("Gated condition: Jev's Codebook-A gate (binary 'does "
                        "reactance exist?') selects the comments; the type task "
                        "(Codebook B) is then the CONDITIONAL six-class task "
                        "'which type, given reactance?'. Downstream "
                        "`keine_reaktanz` answers are reported as gate "
                        "rejections, not as a seventh type. This is a "
                        "RETROSPECTIVE conditional reanalysis of the stored "
                        "seven-class predictions; the intended production "
                        "pipeline would prompt the second stage with only the "
                        "six types after the gate passes."),
           },
           "runs": {}}

    # ---- matrix sample: all 4 models ---------------------------------------
    matrix_models = order_models(
        {p["model"] for p in load(RES / "predictions_full.jsonl")})
    for cond in ("A", "B"):
        A, B = collect(["predictions_full.jsonl"], cond, set(matrix_models))
        out["runs"].setdefault("matrix", {"n_comments": 1200,
                                           "sample": "matrix", "conditions": {}})
        out["runs"]["matrix"]["conditions"][cond] = analyse_cond(cond, A, B, matrix_models)
    out["runs"]["matrix"]["models"] = matrix_models
    out["runs"]["matrix"]["source_files"] = ["predictions_full.jsonl"]
    out["runs"]["matrix"]["conditions_run"] = ["A", "B"]

    # ---- big sample: jev + glm, condition B only ----------------------------
    big_models = order_models(set()
                              | {p["model"] for p in load(RES / "predictions_big.jsonl")}
                              | {p["model"] for p in load(RES / "predictions_glm_big.jsonl")})
    Ab, Bb = collect(["predictions_big.jsonl", "predictions_glm_big.jsonl"],
                     "B", set(big_models))
    out["runs"]["big"] = {"n_comments": 2001, "sample": "big", "models": big_models,
                          "source_files": ["predictions_big.jsonl",
                                            "predictions_glm_big.jsonl"],
                          "conditions_run": ["B"],
                          "conditions": {"B": analyse_cond("B", Ab, Bb, big_models)}}

    (RES / "analysis_gate.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote results/analysis_gate.json")

    for run, d in out["runs"].items():
        print(f"\n== {run} sample ({d['n_comments']} comments) ==")
        for c, r in d["conditions"].items():
            print(f"  condition {c}: Jev gate -> {r['jev_gated_n']} "
                  f"({r['jev_gated_pct']}%) of {r['n_comments']}")
            print("   gate retention (Q1):")
            for gc in r["gate_consistency"]:
                print(f"     {gc['model']:22s} retain {gc['n_accept']:3d}/{gc['n']:3d} "
                      f"({gc['accept_pct']}%)  reject {gc['n_reject']:3d} "
                      f"({gc['reject_pct']}%)")
            for pw in r["pairwise_type"]:
                print(f"   type pair {pw['a'][:14]:14s} x {pw['b'][:14]:14s}: "
                      f"n={pw['n']:3d} agree={pw['raw_pct']}% kappa={pw['kappa']}")
            tc = r["type_consensus"]
            if tc:
                print(f"   type consensus (Q3, n={tc['n_gated']} gated):")
                print(f"     gate acceptance  : {tc['gate_accept']}")
                print(f"     type consensus   : {tc['type_consensus']}")
                print(f"     type dist: "
                      f"{ {CL.get(k, k): v for k, v in tc['majority_type_dist'].items() if v} }")
                for v in tc["vs_majority"]:
                    print(f"     {v['model']:22s} matches non-tie consensus "
                          f"{v['pct']}% of its retained calls (n={v['n']}, "
                          f"{v['n_ties_excluded']} ties excluded)")


if __name__ == "__main__":
    main()

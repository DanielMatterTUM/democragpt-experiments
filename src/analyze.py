"""Aggregate predictions into the results table: prevalence, agreement, timing, cost.

Outputs (all written to results/):
  analysis_summary.csv      one row per model x codebook x condition
  analysis_overlap.csv      pairwise Cohen's kappa between models (same CB+cond)
  analysis_prevalence.csv   reactance prevalence per model/CB/cond
  analysis_cost.csv         per-model cost + latency + token totals
  analysis.md               human-readable digest
"""

from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
CODEBOOK_B_LABELS = [
    "konfrontation_angriff", "ablenkung_whataboutism", "delegierung_hilflosigkeit",
    "vermeidung_rueckzug", "reflektierte_rechtfertigung", "konstruktive_kritik",
    "keine_reaktanz",
]
LABELS_A = ["ja", "nein"]
LABELS_B = CODEBOOK_B_LABELS


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]


def cohens_kappa(a: list[str], b: list[str], labels: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    idx = {l: i for i, l in enumerate(labels)}
    agree = sum(1 for x, y in zip(a, b) if x == y)
    po = agree / n
    ca, cb = defaultdict(int), defaultdict(int)
    for x in a:
        ca[x] += 1
    for y in b:
        cb[y] += 1
    pe = sum((ca[l] / n) * (cb[l] / n) for l in set(labels))
    if abs(1 - pe) < 1e-12:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def pct(n: int, d: int) -> float | None:
    return round(100 * n / d, 2) if d else None


def main() -> None:
    preds = load(RESULTS / "predictions_full.jsonl")
    # Cost/latency must come from the *request* log, not the per-cell predictions:
    # the final run reused the cache for most cells, so per-cell means over
    # predictions would be dominated by cache hits (cost 0, no latency).
    reqs_all = []
    req_path = RESULTS / "requests_full.jsonl"
    if req_path.exists():
        reqs_all = load(req_path)
    meta = json.load((REPO / "data/sample_meta.json").open(encoding="utf-8"))
    n_total_rows = meta["reached"]

    # index: (model, cb, cond, uid) -> label
    lab: dict[tuple, str | None] = {}
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for p in preds:
        key = (p["model"], p["codebook"], p["condition"], p["uid"])
        lab[key] = p.get("label")
        cells[(p["model"], p["codebook"], p["condition"])].append(p)

    models = sorted({p["model"] for p in preds})
    codebooks = sorted({p["codebook"] for p in preds})
    conditions = sorted({p["condition"] for p in preds})

    # ---------- per-cell summary ------------------------------------------
    summary_rows, prev_rows, cost_rows = [], [], []
    for cb in codebooks:
        labels = LABELS_A if cb == "A" else LABELS_B
        for cond in conditions:
            for m in models:
                cell = cells.get((m, cb, cond), [])
                if not cell:
                    continue
                labels_got = [p["label"] for p in cell if p["label"] in labels]
                unparsed = sum(1 for p in cell if p["label"] not in labels)
                negative = "nein" if cb == "A" else "keine_reaktanz"
                pos = sum(1 for x in labels_got if x != negative)

                # latency / cost: average over LIVE calls for this cell. Prefer the
                # request log (all real calls ever made); fall back to predictions.
                if reqs_all:
                    live = [p for p in reqs_all
                            if p.get("model") == m and p.get("codebook") == cb
                            and p.get("condition") == cond and not p.get("was_cached")]
                else:
                    live = [p for p in cell if not p.get("was_cached")]
                # dedupe: the repair run repeated some (uid) pairs; keep first
                seen_uid, uniq = set(), []
                for p in live:
                    u = p.get("uid")
                    if u in seen_uid:
                        continue
                    seen_uid.add(u)
                    uniq.append(p)
                live = uniq
                times = [p["wall_time_s"] for p in live if p.get("wall_time_s")]
                costs = [p["cost_usd"] or 0 for p in live]
                ptoks = [(p.get("usage") or {}).get("prompt_tokens") or 0 for p in live]
                ctoks = [(p.get("usage") or {}).get("completion_tokens") or 0 for p in live]

                summary_rows.append({
                    "model": m, "codebook": cb, "condition": cond,
                    "n_requests": len(cell), "n_parsed": len(labels_got),
                    "n_unparsed": unparsed,
                    "parse_rate_pct": pct(len(labels_got), len(cell)),
                    "n_reactant": pos,
                    "prevalence_pct": pct(pos, len(labels_got)) if labels_got else None,
                    "mean_latency_s": round(st.mean(times), 3) if times else None,
                    "median_latency_s": round(st.median(times), 3) if times else None,
                    "mean_cost_usd": round(st.mean(costs), 6) if costs else None,
                    "total_cost_usd": round(sum(costs), 6),
                    "mean_prompt_tokens": round(st.mean(ptoks), 1) if ptoks else None,
                    "mean_completion_tokens": round(st.mean(ctoks), 1) if ctoks else None,
                })

                dist = {l: sum(1 for x in labels_got if x == l) for l in labels}
                prev_rows.append({"model": m, "codebook": cb, "condition": cond,
                                  **{f"n_{l}": dist.get(l, 0) for l in labels},
                                  "n_parsed": len(labels_got)})

                cost_rows.append({
                    "model": m, "codebook": cb, "condition": cond,
                    "n_calls": len(live),
                    "total_cost_usd": round(sum(costs), 6),
                    "cost_per_1k_rows_usd": round(1000 * sum(costs) / max(1, len(cell)), 4),
                    "mean_latency_s": round(st.mean(times), 3) if times else None,
                    "median_latency_s": round(st.median(times), 3) if times else None,
                    "p90_latency_s": round(sorted(times)[int(0.9 * (len(times) - 1))], 3) if times else None,
                    "total_prompt_tokens": sum(ptoks),
                    "total_completion_tokens": sum(ctoks),
                })

    # ---------- pairwise overlap (same cb + cond) --------------------------
    overlap_rows = []
    for cb in codebooks:
        labels = LABELS_A if cb == "A" else LABELS_B
        for cond in conditions:
            present = [m for m in models if cells.get((m, cb, cond))]
            for m1, m2 in combinations(present, 2):
                uids = sorted({p["uid"] for p in cells[(m1, cb, cond)]} &
                              {p["uid"] for p in cells[(m2, cb, cond)]})
                a = [lab.get((m1, cb, cond, u)) for u in uids]
                b = [lab.get((m2, cb, cond, u)) for u in uids]
                pairs = [(x, y) for x, y in zip(a, b) if x in labels and y in labels]
                if not pairs:
                    continue
                aa = [x for x, _ in pairs]
                bb = [y for _, y in pairs]
                k = cohens_kappa(aa, bb, labels)
                overlap_rows.append({
                    "codebook": cb, "condition": cond,
                    "model_a": m1, "model_b": m2, "n_paired": len(pairs),
                    "percent_agreement_pct": pct(sum(1 for x, y in pairs if x == y), len(pairs)),
                    "cohens_kappa": round(k, 4) if k is not None else None,
                })

    def write(path: Path, rows: list[dict]) -> None:
        if not rows:
            return
        with path.open("w", encoding="utf-8") as fh:
            fh.write(",".join(rows[0].keys()) + "\n")
            for r in rows:
                fh.write(",".join(str(r.get(k, "")) for k in rows[0].keys()) + "\n")

    write(RESULTS / "analysis_summary.csv", summary_rows)
    write(RESULTS / "analysis_prevalence.csv", prev_rows)
    write(RESULTS / "analysis_overlap.csv", overlap_rows)
    write(RESULTS / "analysis_cost.csv", cost_rows)

    # ---------- markdown digest --------------------------------------------
    L = []
    L.append("# Reactance coding on TikTok comments — results digest\n")
    L.append(f"- Sample: **{n_total_rows} comments** "
             f"({meta['accounts_used']} accounts, {meta['parties_used']} parties, "
             f"{meta['videos_used']} videos).")
    L.append(f"- Matrix: Codebook {', '.join(codebooks)} × Conditions {', '.join(conditions)} × "
             f"models {', '.join(models)}.\n")
    L.append("## Prevalence of reactance (share of parsed comments coded `ja` / non-`keine_reaktanz`)\n")
    L.append("| codebook | cond | model | parse% | n_reactant | prevalence% | mean latency s | total $ |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in summary_rows:
        L.append(f"| {r['codebook']} | {r['condition']} | {r['model']} | "
                 f"{r['parse_rate_pct']} | {r['n_reactant']} | {r['prevalence_pct']} | "
                 f"{r['mean_latency_s']} | {r['total_cost_usd']} |")

    L.append("\n## Inter-model agreement (same codebook + condition)\n")
    L.append("| codebook | cond | model A | model B | n | % agree | Cohen's κ |")
    L.append("|---|---|---|---|---|---|---|")
    for r in overlap_rows:
        L.append(f"| {r['codebook']} | {r['condition']} | {r['model_a']} | {r['model_b']} | "
                 f"{r['n_paired']} | {r['percent_agreement_pct']} | {r['cohens_kappa']} |")

    L.append("\n## Codebook B label distribution\n")
    L.append("| codebook | cond | model | " + " | ".join(f"n_{l[:14]}" for l in LABELS_B) + " |")
    L.append("|---|---|---|" + "---|" * len(LABELS_B))
    for r in prev_rows:
        if r["codebook"] != "B":
            continue
        L.append(f"| B | {r['condition']} | {r['model']} | " +
                 " | ".join(str(r[f"n_{l}"]) for l in LABELS_B) + " |")

    total_spend = sum(r["total_cost_usd"] for r in cost_rows)
    L.append(f"\n## Cost\n")
    L.append(f"Total spend across all live calls: **${total_spend:.4f}**.")
    L.append("\n| model | codebook | cond | calls | total $ | $/1k rows | mean lat s | p90 lat s |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in cost_rows:
        L.append(f"| {r['model']} | {r['codebook']} | {r['condition']} | {r['n_calls']} | "
                 f"{r['total_cost_usd']} | {r['cost_per_1k_rows_usd']} | "
                 f"{r['mean_latency_s']} | {r['p90_latency_s']} |")

    (RESULTS / "analysis.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote analysis to {RESULTS}/analysis.md + 4 CSVs")


if __name__ == "__main__":
    main()

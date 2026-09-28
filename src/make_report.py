"""Generate the final report as PDF (data only; markdown assembly is separate)."""
import json
import statistics as st
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
LAB_A = ["ja", "nein"]
LAB_B = ["konfrontation_angriff", "ablenkung_whataboutism",
         "delegierung_hilflosigkeit", "vermeidung_rueckzug",
         "reflektierte_rechtfertigung", "konstruktive_kritik", "keine_reaktanz"]


def load(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def kappa(a, b, labels):
    n = len(a)
    if not n:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in set(labels))
    if abs(1 - pe) < 1e-12:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def main():
    preds = load(RES / "predictions_full.jsonl")
    meta = json.load((REPO / "data/sample_meta.json").open())
    models = sorted({p["model"] for p in preds})
    cells = defaultdict(list)
    for p in preds:
        cells[(p["model"], p["codebook"], p["condition"])].append(p)
    lab = {(p["model"], p["codebook"], p["condition"], p["uid"]): p["label"]
           for p in preds}

    # Latency/cost must come from the request log: after a cached re-run the
    # predictions are mostly cache hits (no timing, zero cost), which would
    # silently blank every latency cell.
    reqs = [r for r in load(RES / "requests_full.jsonl")
            if not r.get("was_cached")] if (RES / "requests_full.jsonl").exists() else []
    # dedupe by (model, cb, cond, uid), keep first real call
    seen, live = set(), []
    for r in reqs:
        k = (r.get("model"), r.get("codebook"), r.get("condition"), r.get("uid"))
        if k in seen:
            continue
        seen.add(k)
        live.append(r)

    out = {"meta": meta, "models": models, "summary": [], "prevalence": [],
           "overlap": [], "crosstab": [], "cost": [], "by_party": [],
           "examples": []}

    # --- per-cell summary --------------------------------------------------
    for cb in ("A", "B"):
        labels = LAB_A if cb == "A" else LAB_B
        neg = "nein" if cb == "A" else "keine_reaktanz"
        for cond in ("A", "B"):
            for m in models:
                cell = cells.get((m, cb, cond), [])
                if not cell:
                    continue
                got = [p["label"] for p in cell if p["label"] in labels]
                pos = sum(1 for x in got if x != neg)
                lc = [r for r in live if r.get("model") == m
                      and r.get("codebook") == cb and r.get("condition") == cond]
                times = [r["wall_time_s"] for r in lc if r.get("wall_time_s")]
                costs = [r["cost_usd"] or 0 for r in lc]
                out["summary"].append({
                    "cb": cb, "cond": cond, "model": m,
                    "n": len(got), "parse_pct": round(100 * len(got) / len(cell), 1),
                    "n_pos": pos,
                    "prev_pct": round(100 * pos / len(got), 2) if got else None,
                    "lat": round(st.mean(times), 3) if times else None,
                    "usd": round(sum(costs), 4),
                    "usd_1k": round(1000 * sum(costs) / len(cell), 4) if cell else None,
                })
                dist = Counter(got)
                out["prevalence"].append({
                    "cb": cb, "cond": cond, "model": m,
                    "counts": {l: dist.get(l, 0) for l in labels}})

    # --- pairwise kappa ----------------------------------------------------
    for cb in ("A", "B"):
        labels = LAB_A if cb == "A" else LAB_B
        for cond in ("A", "B"):
            pres = [m for m in models if cells.get((m, cb, cond))]
            for m1, m2 in combinations(pres, 2):
                uids = sorted({p["uid"] for p in cells[(m1, cb, cond)]} &
                              {p["uid"] for p in cells[(m2, cb, cond)]})
                pr = [(lab.get((m1, cb, cond, u)), lab.get((m2, cb, cond, u)))
                      for u in uids]
                pr = [(x, y) for x, y in pr if x in labels and y in labels]
                if not pr:
                    continue
                aa = [x for x, _ in pr]
                bb = [y for _, y in pr]
                k = kappa(aa, bb, labels)
                out["overlap"].append({
                    "cb": cb, "cond": cond, "a": m1, "b": m2, "n": len(pr),
                    "agree": round(100 * sum(1 for x, y in pr if x == y) / len(pr), 1),
                    "kappa": round(k, 3) if k is not None else None})

    # --- A x B crosstab ----------------------------------------------------
    for m in models:
        for cond in ("A", "B"):
            c = cells.get((m, "A", cond), {})
            d = {p["uid"]: p["label"] for p in c}
            b = {p["uid"]: p["label"] for p in cells.get((m, "B", cond), [])}
            uids = sorted(set(d) & set(b))
            br = sum(1 for u in uids if d[u] == "ja" and b[u] != "keine_reaktanz")
            fp = sum(1 for u in uids if d[u] == "nein" and b[u] != "keine_reaktanz")
            fn = sum(1 for u in uids if d[u] == "ja" and b[u] == "keine_reaktanz")
            bn = sum(1 for u in uids if d[u] == "nein" and b[u] == "keine_reaktanz")
            if uids:
                out["crosstab"].append({
                    "model": m, "cond": cond, "n": len(uids), "both": br,
                    "fp": fp, "fn": fn, "both_no": bn,
                    "ratio": round(fp / br, 1) if br else None})

    # --- cost --------------------------------------------------------------
    for m in models:
        for cb in ("A", "B"):
            for cond in ("A", "B"):
                cell = [r for r in live if r.get("model") == m
                        and r.get("codebook") == cb and r.get("condition") == cond]
                if not cell:
                    continue
                t = [r["wall_time_s"] for r in cell if r.get("wall_time_s")]
                out["cost"].append({
                    "model": m, "cb": cb, "cond": cond, "calls": len(cell),
                    "usd": round(sum(r["cost_usd"] or 0 for r in cell), 4),
                    "mean": round(st.mean(t), 3) if t else None,
                    "p90": round(sorted(t)[int(0.9 * (len(t) - 1))], 3) if t else None})

    # --- reactance by party (codebook A, cond A) --------------------------
    rows = [json.loads(l) for l in (REPO / "data/sample_comments.jsonl").open()]
    party_of = {r["uid"]: r["party"] for r in rows}
    for m in models:
        tally = defaultdict(lambda: [0, 0])
        for p in cells.get((m, "A", "A"), []):
            if p["label"] not in LAB_A:
                continue
            pa = party_of.get(p["uid"], "?")
            tally[pa][1] += 1
            if p["label"] == "ja":
                tally[pa][0] += 1
        for pa, (pos, n) in sorted(tally.items(), key=lambda kv: -kv[1][1]):
            if n >= 20:
                out["by_party"].append({
                    "model": m, "party": pa, "n": n, "pos": pos,
                    "pct": round(100 * pos / n, 1)})

    # --- examples: what the gate still codes as reactance -------------------
    for m in models[:3]:
        seen = 0
        for p in cells.get((m, "A", "A"), []):
            if p["label"] == "ja":
                r = rows[0]
                txt = next((x["comment_text"] for x in rows
                            if x["uid"] == p["uid"]), "")
                out["examples"].append({
                    "model": m, "text": txt[:220], "party": party_of.get(p["uid"], "")})
                seen += 1
                if seen >= 8:
                    break

    (RES / "report_data.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote report_data.json")
    print(f"models: {models}")
    print(f"rows: {meta['reached']}  accounts: {meta['accounts_used']}  "
          f"parties: {meta['parties_used']}")
    for s in out["summary"]:
        if s["cb"] == "A":
            print(f"  cbA cond{s['cond']} {s['model']:20s} prev={s['prev_pct']}%  "
                  f"lat={s['lat']}s")
    print("\ncrosstab (FP:TP ratio):")
    for c in out["crosstab"]:
        print(f"  {c['model']:20s} cond{c['cond']} both={c['both']:3d} fp={c['fp']:3d} "
              f"ratio={c['ratio']}")


if __name__ == "__main__":
    main()

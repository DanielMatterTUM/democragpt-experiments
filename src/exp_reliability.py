"""Experiment E (revised): reliability measured on the cases that MATTER.

A stability check on a sample that is 96% negative is uninformative -- the
easy case is trivially stable. The interesting question is whether the
instrument is reliable exactly where it is uncertain, i.e. on the positive /
borderline cases.

So: oversample the positives. We take all Codebook-A positives from the main run
(stratified by how many models flagged them) plus an equal number of matched
negatives as a control.

  E2  identical repeat  -> run-to-run flip rate
  E3  transcript AFTER the comment -> position-robustness
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebook as CB                              # noqa: E402
from run_benchmark import JEV_MODELS, REPO, RESULTS, load_key, load_rows  # noqa: E402

JEV = JEV_MODELS["jev-1.13"]
PER_STRATUM = int(sys.argv[1]) if len(sys.argv) > 1 else 45
CONTROL_RATIO = 1
OUT = RESULTS / "exp_reliability.jsonl"
SUM = RESULTS / "exp_reliability.json"


def build_sample() -> list[dict]:
    rows = {json.loads(l)["uid"]: json.loads(l)
            for l in (REPO / "data/sample_comments.jsonl").open(encoding="utf-8")}
    preds = [json.loads(l) for l in
             (REPO / "results/predictions_full.jsonl").open(encoding="utf-8")]
    models = sorted({p["model"] for p in preds})
    flagged = defaultdict(set)
    for p in preds:
        if p["codebook"] == "A" and p["condition"] == "A" and p["label"] == "ja":
            flagged[p["uid"]].add(p["model"])

    rng = random.Random(4242)
    by_stratum = defaultdict(list)
    for u, v in flagged.items():
        by_stratum[len(v)].append(u)

    picked: list[tuple[str, int]] = []
    for k in (3, 2, 1):
        pool = sorted(by_stratum.get(k, []))
        rng.shuffle(pool)
        take = pool[:PER_STRATUM]
        picked += [(u, k) for u in take]
        # matched negatives: comments no model flagged, same order
        negs = sorted(u for u in rows if u not in flagged)
        rng.shuffle(negs)
        picked += [(u, 0) for u in negs[:int(len(take) * CONTROL_RATIO)]]

    out = []
    for u, k in picked:
        r = dict(rows[u])
        r["_stratum"] = k
        out.append(r)
    return out


def main() -> None:
    import requests
    key = load_key()
    sample = build_sample()
    strat = Counter(r["_stratum"] for r in sample)
    print(f"sample: {len(sample)} rows  strata={dict(sorted(strat.items()))}")
    print("  stratum 0 = matched negative control; 1/2/3 = flagged by that many models")
    print(f"  budget: {len(sample)*3} Jev calls")

    def state_same(row):
        return CB.build_state(row, "A")

    def state_swapped(row):
        return {"comment": row["comment_text"],
                "video_transcript": row.get("transcript") or ""}

    tasks = []
    for row in sample:
        tasks.append((row, 0, "same"))
        tasks.append((row, 1, "same"))
        tasks.append((row, 0, "swapped"))

    t0 = time.perf_counter()

    def run(task):
        row, rep, variant = task
        state = state_same(row) if variant == "same" else state_swapped(row)
        payload = CB.jev_payload(state, model=JEV)
        payload["questions"] = {"reactance": payload["questions"]["reactance"]}
        t1 = time.perf_counter()
        r = requests.post(
            "https://openrouter.ai/api/alpha/decisions",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json=payload, timeout=180)
        dt = time.perf_counter() - t1
        if r.status_code != 200:
            return row, rep, variant, None, {"error": f"HTTP {r.status_code}"}
        d = r.json()
        ans = (d.get("answers") or {}).get("reactance") or {}
        usage = d.get("usage") or {}
        return row, rep, variant, ans.get("choice"), {
            "p_ja": (ans.get("probabilities") or {}).get("ja"),
            "p_nein": (ans.get("probabilities") or {}).get("nein"),
            "confidence": ans.get("confidence"),
            "cost_usd": usage.get("cost"),
            "wall_time_s": round(dt, 3),
        }

    n = 0
    with ThreadPoolExecutor(max_workers=12) as pool, OUT.open("w",
                                                             encoding="utf-8") as fh:
        for row, rep, variant, label, meta in pool.map(run, tasks):
            fh.write(json.dumps({
                "uid": row["uid"], "stratum": row["_stratum"],
                "rep": rep, "variant": variant, "label": label, **meta,
            }, ensure_ascii=False) + "\n")
            n += 1
            if n % 150 == 0:
                print(f"  {n}/{len(tasks)}  ({time.perf_counter()-t0:.0f}s)")

    # ---------------- analysis -------------------------------------------
    recs = [json.loads(l) for l in OUT.open(encoding="utf-8")]
    same = defaultdict(dict)
    swapped = {}
    for r in recs:
        if r["variant"] == "same":
            same[(r["uid"], r["stratum"])][r["rep"]] = r
        else:
            swapped[(r["uid"], r["stratum"])] = r

    # main-matrix label for comparison
    orig = {}
    for l in (REPO / "results/predictions_full.jsonl").open(encoding="utf-8"):
        p = json.loads(l)
        if (p["model"] == "jev-1.13" and p["codebook"] == "A"
                and p["condition"] == "A" and p["label"]):
            orig[p["uid"]] = p["label"]

    per_stratum = {}
    for k in sorted({k for _, k in same}):
        items = [d for (u, kk), d in same.items() if kk == k]
        pairs = [(d[0], d[1]) for d in items
                 if 0 in d and 1 in d and d[0]["label"] and d[1]["label"]]
        if not pairs:
            continue
        stable = sum(1 for a, b in pairs if a["label"] == b["label"])
        psw = [(uid, s) for (uid, kk), s in swapped.items() if kk == k]
        pos_agree = sum(1 for uid, s in psw
                        if s["label"] and orig.get(uid) == s["label"])
        pos_n = sum(1 for uid, s in psw if s["label"])
        pj = [s["p_ja"] for uid, s in psw if s.get("p_ja") is not None]
        per_stratum[k] = {
            "n_pairs": len(pairs),
            "stability_pct": round(100 * stable / len(pairs), 2),
            "n_flips": len(pairs) - stable,
            "label_counts_rep0": dict(Counter(a["label"] for a, _ in pairs)),
            "position_agree_pct": round(100 * pos_agree / pos_n, 2) if pos_n else None,
            "mean_p_ja": round(sum(pj) / len(pj), 4) if pj else None,
        }

    allp = [(d[0], d[1]) for d in same.values()
            if 0 in d and 1 in d and d[0]["label"] and d[1]["label"]]
    posp = [(d[0], d[1]) for (u, k), d in same.items()
            if k > 0 and 0 in d and 1 in d and d[0]["label"] and d[1]["label"]]
    negp = [(d[0], d[1]) for (u, k), d in same.items()
            if k == 0 and 0 in d and 1 in d and d[0]["label"] and d[1]["label"]]

    def rate(pairs):
        if not pairs:
            return None
        return round(100 * sum(1 for a, b in pairs if a["label"] == b["label"])
                     / len(pairs), 2)

    res = {
        "design": "oversampled positives + matched negative control; "
                  "3 Jev calls per comment (2 identical + 1 position-swapped)",
        "model": JEV, "codebook": "A",
        "n_comments": len(sample),
        "E2_repeat_stability": {
            "overall_pct": rate(allp),
            "positives_only_pct": rate(posp),
            "negatives_only_pct": rate(negp),
            "n_pairs": len(allp),
        },
        "E3_position_agreement": {k: v["position_agree_pct"]
                                  for k, v in per_stratum.items()},
        "per_stratum": per_stratum,
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in recs), 4),
        "calls": len(recs),
    }
    SUM.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n" + json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

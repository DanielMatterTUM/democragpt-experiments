"""Experiment E1: paraphrase / surface-form robustness (Jev only, cheap).

A coding instrument that only fires on the exact surface form it was shown is
not measuring the construct. This re-runs the borderline and positive cases with
a mechanical, meaning-preserving surface perturbation of the COMMENT ONLY (the
transcript stays untouched):

  T1  emphasis removed   : ALL-CAPS runs and repeated punctuation collapsed
  T2  politeness added   : a short opener/closer typical of German comment culture
  T3  filler removed     : "also", "eigentlich", "halt", "eben", "ja" stripped

No LLM is used for the rewrite, so no paraphrase model can smuggle in its own
judgement -- the perturbation is deterministic and auditable.

If the label survives all three, the instrument measures reactance rather than
phrasing. If it collapses, we are measuring style.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebook as CB                              # noqa: E402
from run_benchmark import JEV_MODELS, REPO, RESULTS, load_key  # noqa: E402

JEV = JEV_MODELS["jev-1.13"]
PER_STRATUM = int(sys.argv[1]) if len(sys.argv) > 1 else 35
OUT = RESULTS / "exp_paraphrase.jsonl"
SUM = RESULTS / "exp_paraphrase.json"

FILLER = re.compile(
    r"\b(also|eigentlich|halt|eben|doch|mal|einfach|klar|na ja)\b[ ]?", re.I)
POLITE_OPEN = ["Also, ", "Ich muss dazu sagen: ", "Naja, ", "Ehrlich gesagt, "]
POLITE_CLOSE = [
    " Aber das ist nur meine Meinung.",
    " Ist halt meine Sicht auf die Sache.",
    " Bitte erstmal selbst nachdenken.",
]


def t1_deemphasise(t: str) -> str:
    """Collapse ALL-CAPS runs and repeated punctuation."""
    t = re.sub(r"\b([A-ZÄÖÜ]{3,})\b",
               lambda m: m.group(1).capitalize(), t)
    t = re.sub(r"([!?.])\1{1,}", r"\1", t)
    t = re.sub(r"\s*!\s*", " ", t)
    t = re.sub(r"(\w)\1{3,}", r"\1\1", t)          # aaaa -> aa
    return re.sub(r"\s{2,}", " ", t).strip()


def t2_politeness(t: str, k: int) -> str:
    """Wrap in politeness framing, deterministically by comment index."""
    i = k % len(POLITE_OPEN)
    j = (k // len(POLITE_OPEN)) % len(POLITE_CLOSE)
    return f"{POLITE_OPEN[i]}{t}{POLITE_CLOSE[j]}"


def t3_defiller(t: str) -> str:
    out = FILLER.sub("", t)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()[:1].upper() + out[1:] if out else out


def main() -> None:
    import requests
    key = load_key()

    rows = {json.loads(l)["uid"]: json.loads(l)
            for l in (REPO / "data/sample_comments.jsonl").open(encoding="utf-8")}
    preds = [json.loads(l) for l in
             (REPO / "results/predictions_full.jsonl").open(encoding="utf-8")]
    flagged = defaultdict(set)
    for p in preds:
        if p["codebook"] == "A" and p["condition"] == "A" and p["label"] == "ja":
            flagged[p["uid"]].add(p["model"])

    by_stratum = defaultdict(list)
    for u, v in flagged.items():
        by_stratum[len(v)].append(u)

    import random
    rng = random.Random(777)
    sample = []
    for k in (3, 2, 1):
        pool = sorted(by_stratum.get(k, []))
        rng.shuffle(pool)
        for u in pool[:PER_STRATUM]:
            r = dict(rows[u])
            r["_stratum"] = k
            sample.append(r)
    negs = sorted(u for u in rows if u not in flagged)
    rng.shuffle(negs)
    for u in negs[:PER_STRATUM * 3]:
        r = dict(rows[u])
        r["_stratum"] = 0
        sample.append(r)

    print(f"sample {len(sample)} comments (strata {dict(sorted(Counter(s['_stratum'] for s in sample).items()))})")
    print("variants: original, T1 de-emphasis, T2 politeness, T3 defiller")
    print(f"budget: {len(sample)*4} Jev calls")

    def variants_for(row, i):
        c = row["comment_text"]
        return [("orig", c),
                ("T1_deemphasis", t1_deemphasise(c)),
                ("T2_politeness", t2_politeness(t1_deemphasise(c), i)),
                ("T3_defiller", t3_defiller(t1_deemphasise(c)))]

    tasks = []
    for i, row in enumerate(sample):
        for name, text in variants_for(row, i):
            tasks.append((row, name, text))

    t0 = time.perf_counter()

    def run(task):
        row, name, text = task
        state = {"comment": text,
                 "video_transcript": row.get("transcript") or ""}
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
            return row, name, text, None, {"error": f"HTTP {r.status_code}"}
        d = r.json()
        ans = (d.get("answers") or {}).get("reactance") or {}
        usage = d.get("usage") or {}
        return row, name, text, ans.get("choice"), {
            "p_ja": (ans.get("probabilities") or {}).get("ja"),
            "cost_usd": usage.get("cost"),
            "wall_time_s": round(dt, 3)}

    n = 0
    with ThreadPoolExecutor(max_workers=12) as pool, OUT.open("w",
                                                             encoding="utf-8") as fh:
        for row, name, text, label, meta in pool.map(run, tasks):
            fh.write(json.dumps({"uid": row["uid"], "stratum": row["_stratum"],
                                 "variant": name, "text": text, "label": label,
                                 **meta}, ensure_ascii=False) + "\n")
            n += 1
            if n % 200 == 0:
                print(f"  {n}/{len(tasks)}  ({time.perf_counter()-t0:.0f}s)")

    recs = [json.loads(l) for l in OUT.open(encoding="utf-8")]
    by_uid = defaultdict(dict)
    for r in recs:
        by_uid[r["uid"]][r["variant"]] = r
    strat_of = {r["uid"]: r["stratum"] for r in recs}

    VAR = ["T1_deemphasis", "T2_politeness", "T3_defiller"]
    per = {}
    for k in sorted({v for v in strat_of.values()}):
        uids = [u for u in by_uid if strat_of[u] == k]
        row = {"n": len(uids)}
        for v in VAR:
            same = sum(1 for u in uids
                       if by_uid[u].get(v, {}).get("label")
                       == by_uid[u].get("orig", {}).get("label")
                       and by_uid[u].get(v, {}).get("label"))
            n_lab = sum(1 for u in uids if by_uid[u].get(v, {}).get("label"))
            row[v] = round(100 * same / n_lab, 2) if n_lab else None
        # all three variants jointly identical to original
        allsame = sum(1 for u in uids
                      if all(by_uid[u].get(v, {}).get("label")
                             == by_uid[u].get("orig", {}).get("label")
                             for v in VAR))
        row["all_variants_agree"] = round(100 * allsame / len(uids), 2) if uids else None
        row["label_counts_orig"] = dict(
            Counter(by_uid[u].get("orig", {}).get("label") for u in uids))
        per[k] = row

    res = {
        "design": "deterministic surface perturbations of the comment only; "
                  "Jev codebook A, condition A",
        "model": JEV, "n_comments": len(by_uid), "calls": len(recs),
        "variants": {
            "T1_deemphasis": "ALL-CAPS runs and repeated punctuation collapsed",
            "T2_politeness": "neutral politeness opener + hedging closer added",
            "T3_defiller": "German filler particles removed",
        },
        "per_stratum": per,
        "stratum_meaning": {"0": "negative control (no model flagged)",
                            "1": "flagged by 1 of 3 models",
                            "2": "flagged by 2 of 3",
                            "3": "flagged by all 3"},
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in recs), 4),
        "examples": [{"uid": u,
                      "orig": by_uid[u].get("orig", {}).get("text"),
                      "T2": by_uid[u].get("T2_politeness", {}).get("text"),
                      "labels": {v: by_uid[u].get(v, {}).get("label")
                                 for v in ["orig"] + VAR}}
                     for u in list(by_uid)[:6]],
    }
    SUM.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n" + json.dumps(res, indent=1, ensure_ascii=False)[:2600])


if __name__ == "__main__":
    main()

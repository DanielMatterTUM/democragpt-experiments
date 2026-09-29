"""Verify that each predictions log is covered by its sample file.

A silent mismatch here is the worst kind of bug: the analysis still runs and
still prints numbers, they are just computed against the wrong comment set.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA, RES = REPO / "data", REPO / "results"

PAIRS = [("sample_matrix.jsonl", "predictions_full.jsonl"),
         ("sample_big.jsonl", "predictions_big.jsonl")]

for samp, pred in PAIRS:
    sp, pp = DATA / samp, RES / pred
    if not (sp.exists() and pp.exists()):
        print(f"{samp:24s} or {pred} MISSING")
        continue
    s = {json.loads(l)["uid"] for l in sp.open(encoding="utf-8")}
    p = {json.loads(l)["uid"] for l in pp.open(encoding="utf-8")}
    cov = len(p & s) / len(p) if p else 0
    flag = "OK " if cov > 0.999 else "BAD"
    print(f"{flag} {samp:24s} n={len(s):5d} | {pred:26s} uids={len(p):5d} "
          f"| coverage={cov*100:6.2f}%")
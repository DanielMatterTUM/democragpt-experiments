import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os_ = subprocess.run(["git", "status", "--short"], cwd=REPO,
                     capture_output=True, text=True).stdout.strip()
head = subprocess.run(["git", "log", "--oneline", "-1"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
print(f"git: {len(os_.splitlines()) if os_ else 0} uncommitted | HEAD {head}")

m = json.load((REPO / "data/sample_meta.json").open(encoding="utf-8"))
preds = [json.loads(l) for l in
         (REPO / "results/predictions_big.jsonl").open(encoding="utf-8")]
sample = {json.loads(l)["uid"] for l in
          (REPO / "data/sample_comments.jsonl").open(encoding="utf-8")}
pids = {p["uid"] for p in preds}
print(f"sample_meta: reached={m['reached']} accounts={m['accounts_used']} "
      f"parties={m['parties_used']} videos={m['videos_used']}")
print(f"predictions_big: {len(preds)} requests, {len(pids)} distinct uids, "
      f"null labels={sum(1 for p in preds if p['label'] is None)}")
print(f"every big-run uid inside the sample: {pids <= sample}")

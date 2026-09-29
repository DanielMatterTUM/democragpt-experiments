import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
m = json.load((REPO / "data/sample_meta.json").open(encoding="utf-8"))
print("reached", m["reached"], "accounts", m["accounts_used"],
      "parties", m["parties_used"], "videos", m["videos_used"])
rows = [json.loads(l) for l in
        (REPO / "data/sample_comments.jsonl").open(encoding="utf-8")]
uids = {r["uid"] for r in rows}
print("rows", len(rows), "unique uids", len(uids))
old = {json.loads(l)["uid"] for l in
       (REPO / "results/predictions_full.jsonl").open(encoding="utf-8")}
print("overlap with the 1200-sample:", len(uids & old))
print("transcripts present:", sum(1 for r in rows if r.get("transcript")))

import json
from collections import Counter

r = [json.loads(l) for l in open("results/requests_full.jsonl")]
jev = [x for x in r if x["model"] == "jev-1.13" and x.get("probabilities")]
print("jev records with probabilities:", len(jev))
if jev:
    print("keys:", sorted(jev[0].keys()))
    print("example:", json.dumps(
        {k: jev[0][k] for k in ("codebook", "condition", "label",
                               "confidence", "probabilities")},
        ensure_ascii=False))
print("by cb/cond:", Counter((x["codebook"], x["condition"]) for x in jev))
# cached records carry meta from the original call
print("cached jev with probs:",
      sum(1 for x in jev if x.get("was_cached")))

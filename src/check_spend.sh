#!/bin/bash
# Report live OpenRouter spend for the DemocraGPT key.
K=$(cat /home/hermes/Desktop/democragptkey.txt)
curl -s https://openrouter.ai/api/v1/key -H "Authorization: Bearer $K" -o /tmp/or_key.json
python3 - <<'PY'
import json
d = json.load(open('/tmp/or_key.json'))['data']
spent, limit = d['usage'], d['limit']
print(f"spent ${spent:.4f} / ${limit}  |  remaining ${limit-spent:.4f} "
      f"({100*spent/limit:.1f}% used)")
PY

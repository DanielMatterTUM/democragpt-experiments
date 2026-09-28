"""Probe DeepSeek / GLM to find a token budget that yields parseable output.

Observed failure: finish_reason='length' with EMPTY content, i.e. the model
spends the whole max_tokens budget on hidden reasoning and never emits the JSON.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebook as CB
from run_benchmark import load_key, load_rows, REPO, _parse_json_obj, _salvage_label

import requests

key = load_key()
rows = load_rows(REPO / "data/sample_comments.jsonl", 2)

CONFIGS = [
    ("deepseek-reasoning-2000", "deepseek/deepseek-v4.1-flash", 2000,
     {"reasoning": {"effort": "low", "exclude": True}}),
    ("deepseek-nofield-2000", "deepseek/deepseek-v4.1-flash", 2000, {}),
    ("glm-nofield-2000", "z-ai/glm-5.3-flash", 2000, {}),
    ("glm-reasoning-2000", "z-ai/glm-5.3-flash", 2000,
     {"reasoning": {"effort": "low", "exclude": True}}),
]

for name, model, mt, extra in CONFIGS:
    for cb in ("A",):
        for row in rows[:1]:
            state = CB.build_state(row, "A")
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": CB.chat_system_prompt(cb, "A")},
                    {"role": "user", "content": CB.chat_user_prompt(state)},
                ],
                "max_tokens": mt,
                "temperature": 0,
                **extra,
            }
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json=payload, timeout=180)
            if r.status_code != 200:
                print(f"{name:24s} HTTP {r.status_code} {r.text[:150]}")
                continue
            d = r.json()
            ch = (d.get("choices") or [{}])[0]
            content = (ch.get("message") or {}).get("content") or ""
            u = d.get("usage") or {}
            lab = _salvage_label(content, cb) or (
                (_parse_json_obj(content) or {}).get("reactance"))
            print(f"{name:24s} finish={str(ch.get('finish_reason')):10s} "
                  f"ctoks={u.get('completion_tokens')}/{mt} "
                  f"creason={u.get('completion_tokens_details')} "
                  f"label={lab} raw={repr(content)[:80]}")

"""Run reactance classification over the sample with several OpenRouter models.

Two codebooks (A binary / B 7-type) x two conditions (A transcript+comment /
B comment only) x N models, on the SAME sample rows so cross-model overlap can
be measured.

Backends
--------
chat  : /api/v1/chat/completions -- openai/gpt-6-luna, deepseek/..., z-ai/...
jev   : /api/alpha/decisions     -- typesafe/jev-1.13 (returns probabilities)

Every request is logged to results/requests.jsonl with wall-clock time, TTFT
(where the provider reports it), usage tokens and cost.  A content-hash cache
in results/cache.sqlite makes reruns free.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebook as CB  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
KEY_FILE = Path("/home/hermes/Desktop/democragptkey.txt")

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
JEV_URL = "https://openrouter.ai/api/alpha/decisions"

CHAT_MODELS = {
    "gpt-6-luna": "openai/gpt-6-luna",
    "deepseek-v4.1-flash": "deepseek/deepseek-v4.1-flash",
    "glm-5.3-flash": "z-ai/glm-5.3-flash",
}
JEV_MODELS = {
    "jev-1.13": "typesafe/jev-1.13",
}

# short name -> full OpenRouter id, for both backends
MODEL_IDS = {**CHAT_MODELS, **JEV_MODELS}

# Bump whenever a codebook's text changes. It is part of the cache key, so an
# edited codebook can never silently reuse labels produced by the old wording.
#   B-gate-v2  freedom-threat precondition (first fix)
#   B-gate-v3  + target-not-topic gate, + politeness-marker gate (from the manual
#              audit and the surface-robustness experiment)
CODEBOOK_VERSION = "B-gate-v3"


# --------------------------------------------------------------------------
def load_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    return KEY_FILE.read_text(encoding="utf-8").strip()


def load_rows(path: Path, limit: int | None = None, offset: int = 0) -> list[dict]:
    rows = [json.loads(l) for l in path.open(encoding="utf-8")]
    rows = rows[offset:]
    return rows[:limit] if limit else rows


# --------------------------------------------------------------------------
class Cache:
    """Thread-safe-ish: one sqlite connection guarded by a lock (short writes only)."""

    def __init__(self, path: Path):
        import threading
        self._lock = threading.Lock()
        self.con = sqlite3.connect(path, check_same_thread=False)
        # two benchmark processes may share this cache file; wait instead of
        # raising 'database is locked' on a concurrent short write
        self.con.execute("PRAGMA busy_timeout=30000")
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS cache ("
            "k TEXT PRIMARY KEY, val TEXT, ts REAL)")
        self.con.commit()

    def get(self, k: str):
        with self._lock:
            r = self.con.execute("SELECT val FROM cache WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else None

    def put(self, k: str, val: dict) -> None:
        with self._lock:
            self.con.execute(
                "INSERT OR REPLACE INTO cache (k, val, ts) VALUES (?,?,?)",
                (k, json.dumps(val, ensure_ascii=False), time.time()))
            self.con.commit()


def log_request(rec: dict, path: Path) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
def _parse_json_obj(txt: str) -> dict | None:
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1]
        if txt.startswith("json"):
            txt = txt[4:]
    txt = txt.strip()
    start, end = txt.find("{"), txt.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(txt[start:end + 1])
    except json.JSONDecodeError:
        return None


# Fallback for truncated output (e.g. DeepSeek burns the token budget on reasoning
# and cuts the JSON off mid-string) and for models that answer in plain prose.
_LABEL_RE = re.compile(
    r'"reactance(?:_type)?"\s*:\s*"([^"]+)"', re.I)
_LABEL_LOOSE_RE = re.compile(
    r'\b(keine_reaktanz|keine\s+reaktanz|kein[e]?\s+reaktanz|'
    r'konfrontation_angriff|ablenkung_whataboutism|delegierung_hilflosigkeit|'
    r'vermeidung_rueckzug|reflektierte_rechtfertigung|konstruktive_kritik)\b',
    re.I)


def _salvage_label(content: str, codebook: str) -> str | None:
    """Best-effort label recovery when strict JSON parsing failed."""
    if not content:
        return None
    m = _LABEL_RE.search(content)
    raw = m.group(1) if m else None
    if raw is None:
        m2 = _LABEL_LOOSE_RE.search(content)
        raw = m2.group(1) if m2 else None
    if raw is None:
        # codebook A: bare ja/nein anywhere
        if codebook == "A":
            m3 = re.search(r'\b(ja|nein|yes|no)\b', content, re.I)
            if m3:
                raw = m3.group(1)
    if raw is None:
        return None
    return _normalise_label(raw, codebook)


def _normalise_label(raw: str, codebook: str) -> str | None:
    lab = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if codebook == "A":
        return {"ja": "ja", "yes": "ja", "true": "ja", "1": "ja",
                "nein": "nein", "no": "nein", "false": "nein", "0": "nein"}.get(lab)
    for known in CB.CODEBOOK_B_LABELS:
        if lab == known or lab.startswith(known):
            return known
    if lab in ("keine", "none", "no_reactance", "nicht_reaktanz"):
        return "keine_reaktanz"
    return None


def call_chat(model: str, codebook: str, condition: str, row: dict,
              key: str, max_tokens: int = 2000,
              salvage_only: bool = False) -> tuple[dict, dict]:
    state = CB.build_state(row, condition)
    field = "reactance" if codebook == "A" else "reactance_type"
    if salvage_only:
        # second chance: no codebook, no reasoning budget -- just emit the token
        instructions = (
            "Reply with the single JSON object and nothing else: "
            f'{{"{field}": ' + ('"ja" or "nein"' if codebook == "A"
                                else '"<one of: ' + ", ".join(CB.CODEBOOK_B_LABELS) + '>"')
            + "}.")
        sys_msg = instructions
        # still needs headroom: the model may spend reasoning tokens before the JSON
        max_tokens = 2000
    else:
        sys_msg = CB.chat_system_prompt(codebook, condition)
    payload = {
        "model": model,
        "messages": [
            {"role": "system",
             "content": sys_msg},
            {"role": "user", "content": CB.chat_user_prompt(state)},
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
        "seed": 7,
        # NOTE: reasoning models (DeepSeek, GLM) spend hidden reasoning tokens out
        # of the SAME max_tokens budget. At 400 they hit finish_reason="length"
        # with EMPTY content and never emitted the JSON. 2000 is enough headroom
        # and costs nothing extra (budget, not usage).
        "reasoning": {"effort": "low", "exclude": True},
    }
    t0 = time.perf_counter()
    r = requests.post(
        CHAT_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/DanielMatterTUM/democragpt-experiments",
                 "X-Title": "democragpt-reactance-benchmark"},
        json=payload, timeout=120)
    dt = time.perf_counter() - t0
    if r.status_code != 200:
        return {"label": None, "error": f"HTTP {r.status_code}: {r.text[:300]}"}, \
               {"wall_time_s": dt, "http_status": r.status_code}
    data = r.json()
    # NOTE: OpenRouter may return "usage": null -- never assume the key is a dict.
    usage = data.get("usage") or {}
    choice = (data.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content", "") or ""
    parsed = _parse_json_obj(content)

    label, conf = None, None
    if parsed:
        if codebook == "A":
            label = _normalise_label(str(parsed.get("reactance", "")), "A")
        else:
            label = _normalise_label(str(parsed.get("reactance_type", "")), "B")
    salvaged = False
    if label is None:
        label = _salvage_label(content, codebook)
        salvaged = label is not None

    meta = {
        "wall_time_s": round(dt, 3),
        "http_status": r.status_code,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
        "usage_verbose": data.get("usage") or {},
        "cost_usd": (usage or {}).get("cost"),
        "native_finish_reason": choice.get("finish_reason"),
        "salvaged_label": salvaged,
        "salvage_only_call": salvage_only,
        "raw_content": content[:400],
        "generation_id": data.get("id"),
        "provider": data.get("provider"),
    }
    # TTFT if the provider streams it back in usage
    uv = meta["usage_verbose"]
    if isinstance(uv, dict):
        meta["ttft_s"] = uv.get("latency") or uv.get("time_to_first_token")
    return {"label": label, "confidence": conf, "raw_parsed": parsed,
            "raw_content": content,
            "error": None if label else f"unparseable: {content[:200]}"}, meta


def call_jev(model: str, codebook: str, condition: str, row: dict,
             key: str) -> tuple[dict, dict]:
    state = CB.build_state(row, condition)
    payload = CB.jev_payload(state, model=model)
    if codebook == "A":   # ask only the requested question -> cheaper
        payload["questions"] = {"reactance": payload["questions"]["reactance"]}
    else:
        payload["questions"] = {"reactance_type": payload["questions"]["reactance_type"]}
    t0 = time.perf_counter()
    r = requests.post(
        JEV_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload, timeout=180)
    dt = time.perf_counter() - t0
    if r.status_code != 200:
        return {"label": None, "error": f"HTTP {r.status_code}: {r.text[:300]}"}, \
               {"wall_time_s": dt, "http_status": r.status_code}
    data = r.json()
    q = "reactance" if codebook == "A" else "reactance_type"
    ans = (data.get("answers") or {}).get(q) or {}
    label = ans.get("choice")
    usage = data.get("usage") or {}
    meta = {
        "wall_time_s": round(dt, 3),
        "http_status": r.status_code,
        "usage": {
            "prompt_tokens": usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
            "total_tokens": (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
        },
        "cost_usd": usage.get("cost"),
        "confidence": ans.get("confidence"),
        "probabilities": ans.get("probabilities"),
        "generation_id": data.get("id"),
        "provider": data.get("provider"),
        "resolved_model": data.get("model"),
    }
    return {"label": label, "confidence": ans.get("confidence"),
            "probabilities": ans.get("probabilities"),
            "error": None if label else "no label"}, meta


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=list(CHAT_MODELS) + list(JEV_MODELS))
    ap.add_argument("--codebooks", nargs="*", default=["A", "B"])
    ap.add_argument("--conditions", nargs="*", default=["A"])
    ap.add_argument("--sample", default="sample_comments.jsonl",
                    help="sample file in data/ (default: sample_comments.jsonl)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--run-name", default="run")
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    cache = Cache(RESULTS / "cache.sqlite")
    key = load_key()
    rows = load_rows(REPO / "data" / args.sample, args.limit, args.offset)
    log_path = RESULTS / f"requests_{args.run_name}.jsonl"
    preds_path = RESULTS / f"predictions_{args.run_name}.jsonl"
    print(f"{len(rows)} rows x {len(args.models)} models x "
          f"cb={args.codebooks} x cond={args.conditions}")

    tasks = []
    for m in args.models:
        model_id = MODEL_IDS.get(m, m)          # allow passing full ids directly
        for cb in args.codebooks:
            for cond in args.conditions:
                for row in rows:
                    tasks.append((m, model_id, cb, cond, row))

    def run(task):
        model, model_id, codebook, cond, row = task
        state = CB.build_state(row, cond)
        cb_ver = CODEBOOK_VERSION if codebook == "B" else "A-v1"
        ck = json.dumps({"model": model_id, "cb": codebook, "cb_ver": cb_ver,
                         "cond": cond, "state": state},
                        sort_keys=True, ensure_ascii=False)
        if not args.no_cache:
            hit = cache.get(ck)
            if hit:
                return model, codebook, cond, row["uid"], hit["label"], hit["meta"], True

        is_jev = model_id.startswith("typesafe/")
        fn = call_jev if is_jev else call_chat
        try:
            pred, meta = fn(model_id, codebook, cond, row, key)
            # retry once with a minimal prompt if the label is unparseable
            if pred.get("label") is None and not is_jev:
                pred2, meta2 = call_chat(model_id, codebook, cond, row, key,
                                         salvage_only=True)
                meta2["was_salvage_retry"] = True
                meta = {**meta, **meta2}
                if pred2.get("label"):
                    pred = pred2
        except Exception as e:                      # noqa: BLE001
            import traceback
            pred = {"label": None, "error": f"{type(e).__name__}: {e}"[:400],
                    "traceback": traceback.format_exc()[-600:]}
            meta = {"wall_time_s": None, "error": True}
        meta = {**meta, "cached": False, "backend": "jev" if is_jev else "chat"}
        if pred.get("error") and not pred.get("raw_parsed"):
            meta["had_error"] = True
            meta["error"] = pred["error"]
        if pred.get("traceback"):
            meta["traceback"] = pred["traceback"]
        if not args.no_cache:
            cache.put(ck, {"label": pred.get("label"), "meta": meta})
        return model, codebook, cond, row["uid"], pred.get("label"), meta, False

    n_cached = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool, \
            preds_path.open("w", encoding="utf-8") as pfh:
        for i, (model, cb, cond, uid, label, meta, was_cached) in enumerate(
                pool.map(run, tasks), 1):
            n_cached += was_cached
            rec = {
                "run": args.run_name, "model": model, "codebook": cb,
                "condition": cond, "uid": uid, "label": label,
                "was_cached": was_cached, **meta,
            }
            pfh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log_request(rec, log_path)
            if i % 50 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)}  cached={n_cached}")

    costs = [json.loads(l).get("cost_usd") or 0 for l in log_path.open(encoding="utf-8")]
    print(f"done. requests={len(tasks)} cached={n_cached} "
          f"cost_this_run=${sum(costs):.6f} (log total)")
    print(f"predictions -> {preds_path}")


if __name__ == "__main__":
    main()

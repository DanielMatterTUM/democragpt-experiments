"""Build a local, stratified sample of TikTok political comments for reactance coding.

Source (read-only, on NAS):
  /mnt/nasother/TikTok_Pol2025/comments/<account>/<account>_comments_<videoid>.json
  /mnt/nasother/TikTok_Pol2025/transcripts/data/<account>/<videoid>.txt

Output (local, git-tracked):
  data/sample_comments.jsonl   one row per comment, incl. transcript
  data/sample_meta.json        provenance + sampling description

Sampling logic
--------------
1. Load account -> party mapping (parteien.txt).
2. Stratify over parties: sample accounts round-robin so no single party dominates.
3. Per account, pick videos that have a NON-EMPTY transcript (Condition A requires it)
   and >= MIN_COMMENTS comments.
4. Within a video, take comments with >= MIN_CHARS visible characters, deduplicated,
   stripping @mentions / URLs.
5. Stop once the global target is reached.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

NAS = Path("/mnt/nasother/TikTok_Pol2025")
REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data"

MIN_CHARS = 25          # drop very short comments ("danke", "😂😂")
MAX_COMMENTS_PER_VIDEO = 3
MAX_COMMENTS_PER_ACCOUNT = 20   # keep account/party diversity high
MIN_COMMENTS_PER_VIDEO = 4
TRANSCRIPT_MAX_CHARS = 1800

URL_RE = re.compile(r"https?://\S+|www\.\S+")
MENTION_RE = re.compile(r"@[A-Za-z0-9_.\-]+")
WS_RE = re.compile(r"\s+")


def clean_text(t: str) -> str:
    t = unicodedata.normalize("NFC", t or "")
    t = URL_RE.sub(" ", t)
    t = MENTION_RE.sub(" ", t)
    t = WS_RE.sub(" ", t).strip()
    return t


def load_parties() -> dict[str, str]:
    out: dict[str, str] = {}
    with open(NAS / "parteien.txt", encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[0].strip():
                out[parts[0].strip()] = parts[1].strip()
    return out


def load_transcript(account: str, videoid: str) -> str | None:
    for folder in (NAS / "transcripts/data", NAS / "transcripts-new"):
        p = folder / account / f"{videoid}.txt"
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="replace").strip()
            if len(txt) >= 100:
                return txt[:TRANSCRIPT_MAX_CHARS]
    return None


def _iter_json_objects(raw: str):
    """The NAS files are *concatenated* JSON objects (one per pagination request),
    not a single JSON document -- so json.loads() on the whole file fails with
    'Extra data'.  Use raw_decode to walk them."""
    dec = json.JSONDecoder()
    idx = 0
    n = len(raw)
    while idx < n:
        while idx < n and raw[idx] in " \t\r\n":
            idx += 1
        if idx >= n:
            return
        try:
            obj, end = dec.raw_decode(raw, idx)
        except json.JSONDecodeError:
            return
        idx = end
        yield obj


def load_video_comments(account: str, videoid: str) -> list[dict]:
    p = NAS / "comments" / account / f"{account}_comments_{videoid}.json"
    if not p.exists():
        return []
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for obj in _iter_json_objects(raw):
        if not isinstance(obj, dict):
            continue
        comments = (obj.get("data") or {}).get("comments") or []
        for c in comments:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("cid"))
            if cid and cid not in seen:
                seen.add(cid)
                out.append(c)
    return out


def _is_top_level(c: dict) -> bool:
    """reply_id is the STRING '0' for top-level comments (not int 0), so a plain
    truthiness check silently drops every comment."""
    def zero(v) -> bool:
        return v in (0, "0", "", None)
    return not (zero(c.get("reply_id")) is False or not zero(c.get("reply_to_reply_id")))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--n-accounts-per-party", type=int, default=3)
    ap.add_argument("--out", default="sample_matrix",
                    help="output stem in data/ (default sample_matrix)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    parties = load_parties()

    # ---- 1. candidate accounts grouped by party -----------------------------
    accounts_root = NAS / "comments"
    by_party: dict[str, list[str]] = defaultdict(list)
    for account in sorted(os.listdir(accounts_root)):
        if not (accounts_root / account).is_dir():
            continue
        party = parties.get(account)
        if party:
            by_party[party].append(account)

    # round-robin over parties so each contributes, then shuffle within party
    selected: list[str] = []
    parties_sorted = sorted(by_party)
    per_party_idx = 0
    while len(selected) < args.n_accounts_per_party * len(parties_sorted):
        added = False
        for party in parties_sorted:
            if per_party_idx < len(by_party[party]) and len(selected) < args.n_accounts_per_party * len(parties_sorted):
                selected.append(by_party[party][per_party_idx])
                added = True
        if not added:
            break
        per_party_idx += 1
    rng.shuffle(selected)

    # ---- 2. harvest ---------------------------------------------------------
    rows: list[dict] = []
    seen_text: set[str] = set()
    n_videos = 0
    for account in selected:
        if len(rows) >= args.target:
            break
        n_from_account = 0
        vids = sorted(p.name.rsplit("_", 1)[-1].removesuffix(".json")
                      for p in (accounts_root / account).glob("*.json"))
        rng.shuffle(vids)
        for videoid in vids:
            if len(rows) >= args.target or n_from_account >= MAX_COMMENTS_PER_ACCOUNT:
                break
            comments = load_video_comments(account, videoid)
            usable = []
            for c in comments:
                if c.get("status") != 1 or not _is_top_level(c):
                    continue  # visible, top-level comments only
                txt = clean_text(c.get("text", ""))
                if len(txt) < MIN_CHARS:
                    continue
                usable.append((txt, c))
            if len(usable) < MIN_COMMENTS_PER_VIDEO:
                continue
            transcript = load_transcript(account, videoid)
            if transcript is None:
                continue  # Condition A needs a transcript

            rng.shuffle(usable)
            kept = 0
            for txt, c in usable:
                if kept >= MAX_COMMENTS_PER_VIDEO:
                    break
                digest = hashlib.sha1(f"{txt}".encode()).hexdigest()
                if digest in seen_text:
                    continue
                seen_text.add(digest)
                rows.append({
                    "uid": hashlib.sha1(f"{account}|{videoid}|{txt}".encode()).hexdigest()[:12],
                    "account": account,
                    "party": parties.get(account, ""),
                    "videoid": videoid,
                    "comment_text": txt,
                    "comment_chars": len(txt),
                    "digg_count": c.get("digg_count", 0),
                    "create_time": c.get("create_time"),
                    "create_date": (
                        __import__("datetime").datetime.utcfromtimestamp(c["create_time"]).strftime("%Y-%m-%d")
                        if c.get("create_time") else None
                    ),
                    "transcript": transcript,
                    "transcript_chars": len(transcript),
                })
                kept += 1
                n_from_account += 1
            n_videos += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_jsonl = OUT_DIR / f"{args.out}.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    party_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        party_counts[r["party"]] += 1
    meta = {
        "source_nas": str(NAS),
        "source_files": {
            "comments": "comments/<account>/<account>_comments_<videoid>.json",
            "transcripts": "transcripts/data/<account>/<videoid>.txt",
        },
        "seed": args.seed,
        "target": args.target,
        "reached": len(rows),
        "videos_used": n_videos,
        "accounts_used": len({r["account"] for r in rows}),
        "parties_used": len(party_counts),
        "party_counts": dict(sorted(party_counts.items(), key=lambda kv: -kv[1])),
        "filters": {
            "min_comment_chars": MIN_CHARS,
            "max_comments_per_video": MAX_COMMENTS_PER_VIDEO,
            "max_comments_per_account": MAX_COMMENTS_PER_ACCOUNT,
            "min_comments_per_video": MIN_COMMENTS_PER_VIDEO,
            "top_level_comments_only": True,
            "requires_nonempty_transcript": True,
            "transcript_max_chars": TRANSCRIPT_MAX_CHARS,
            "urls_and_mentions_stripped": True,
        },
    }
    meta_path = OUT_DIR / f"{args.out}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    print(json.dumps({k: v for k, v in meta.items() if k != "party_counts"}, indent=2, ensure_ascii=False))
    print("party_counts:", meta["party_counts"])
    print("mean comment chars:", round(sum(r["comment_chars"] for r in rows) / max(1, len(rows)), 1))
    print("mean transcript chars:", round(sum(r["transcript_chars"] for r in rows) / max(1, len(rows)), 1))


if __name__ == "__main__":
    main()

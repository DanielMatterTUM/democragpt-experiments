# democragpt-experiments — Reactance coding of TikTok political comments

Experiment for **DemocraGPT** (Katharina Hajek, Daniel Matter, bidt/TUM):
how often does *psychological reactance* show up in real social-media comments,
and how fast / how cheaply can we detect it with LLMs?

Two questions, one codebase:

1. **How frequent is reactance?** → prevalence estimates per model / codebook / condition.
2. **How fast can we detect it?** → latency, token usage and cost per 1,000 comments.

Everything is measured on **one shared sample** so that cross-model, cross-codebook
and cross-condition overlap is directly comparable.

---

## Design

```
                        ┌─ Codebook A: reactance yes/no          (2 labels)
   comment (+video) ────┤
                        └─ Codebook B: what kind of reactance?   (7 labels)
                                   ×
                        ┌─ Condition A: comment + video transcript
                        └─ Condition B: comment only
                                   ×
                        gpt-6-luna · deepseek-v4.1-flash · glm-5.3-flash · jev-1.13
```

Full factorial = **2 codebooks × 2 conditions × 4 models × 201 comments = 3,216 requests.**

## Findings (short version)

**How frequent is reactance?** Rare. Under Codebook A with the video transcript
(condition A), `gpt-6-luna` codes 5/201 (**2,5 %**) and `jev-1.13` 4/201
(**2,0 %**) as reactance. Dropping the transcript (condition B) barely moves the
binary number (3,0 % / 1,0 %) — **the video context adds almost nothing for
the yes/no decision.**

**How fast can we detect it?** `jev-1.13` is both the fastest (~0,35 s) and the
cheapest backend, and additionally returns calibrated class probabilities and a
confidence score. `gpt-6-luna` is the most reliable chat model (100 % parse
rate). The whole 3,216-request matrix costs **≈ $0,39**.

**⚠️ Open issue — Codebook B needs a boundary fix before publication.**
Codebook B yields 29–46 % reactance where Codebook A yields 2–6 %, consistently
across all four models and both conditions. This is a *codebook* effect, not a
model effect: the models are coding ordinary disagreement and criticism of a
politician as reactance, whereas the project theory requires an appraisal of a
*threatened autonomy*. See `docs/results.md` for the proposed fix (make the
freedom-threat requirement a hard precondition of every Codebook B label).
Not yet applied — it changes the instrument.

See `docs/results.md` for the full digest.

### Codebook A — binary

`ja` / `nein`. `ja` requires **both** a perceived freedom threat *and* an
autonomy-restoring reaction (see `src/codebook.py:A_INSTRUCTIONS`).

### Codebook B — type

Built directly from the project's 8-archetype written-reactance typology
("Wiki Reaktanz (allgemein)"), collapsed to 7 mutually exclusive labels:

| label | project archetype(s) merged |
|---|---|
| `konfrontation_angriff` | Destruktiver Angreifer + Konstruktiver Angreifer |
| `ablenkung_whataboutism` | Aggressiver Ablenker + Ablenkungs-Stratege |
| `delegierung_hilflosigkeit` | Hilfloser Delegierer |
| `vermeidung_rueckzug` | Vermeidender Rechtfertiger |
| `reflektierte_rechtfertigung` | Reflektierter Rechtfertiger |
| `konstruktive_kritik` | Konstruktiver Kritiker |
| `keine_reaktanz` | — (no reactance) |

Theory grounding (Brehm 1966 core definition, PRPM phases, the five trigger
dimensions A–E) comes verbatim from the DemocraGPT Notion export; provenance is
recorded in `docs/codebook_sources.md`.

---

## Data

Source (read-only, on the NAS, **not** mirrored into this repo beyond the sample):

- `/mnt/nasother/TikTok_Pol2025/comments/<account>/<account>_comments_<videoid>.json`
- `/mnt/nasother/TikTok_Pol2025/transcripts/data/<account>/<videoid>.txt`
- account → party map: `/mnt/nasother/TikTok_Pol2025/parteien.txt`

`src/build_dataset.py` builds `data/sample_comments.jsonl` — a stratified sample
of **201 comments**, round-robin across parties so no party dominates, with
non-empty transcripts (needed for Condition A). Filters and provenance are in
`data/sample_meta.json`. Rebuild with:

```bash
python3 src/build_dataset.py --target 200 --n-accounts-per-party 6
```

> The NAS comment files are **concatenated JSON objects** (one per pagination
> request), not a single JSON document — `build_dataset.py` walks them with
> `raw_decode`. Also note `reply_id` is the *string* `"0"` for top-level comments.

---

## Running

```bash
export OPENROUTER_API_KEY=...        # or leave the key at /home/hermes/Desktop/democragptkey.txt

python3 src/build_dataset.py --target 200 --n-accounts-per-party 6

python3 src/run_benchmark.py \
    --models gpt-6-luna deepseek-v4.1-flash glm-5.3-flash jev-1.13 \
    --codebooks A B --conditions A B \
    --workers 10 --run-name full

python3 src/analyze.py
```

`run_benchmark.py` records **every** request to `results/requests_full.jsonl` with
wall-clock time, prompt/completion tokens, cost, provider, generation id, finish
reason, and label-salvage flags. A content-hash cache (`results/cache.sqlite`)
keyed on `{model, codebook, condition, state}` makes reruns free.

## Layout

```
src/build_dataset.py     stratified sampler -> data/sample_comments.jsonl
src/codebook.py          the codebook (chat prompts + Jev criteria)
src/run_benchmark.py     OpenRouter runner (chat + Jev/Decisions API)
src/analyze.py           aggregation -> results/analysis.md + CSVs
data/                    the sample + sampling metadata
results/                 per-request logs, predictions, analysis tables
docs/codebook_sources.md provenance of every codebook statement
```

## Cost

Full 3,216-request matrix costs well under $1 with these flash-tier models — see
`results/analysis_cost.csv` for the per-model breakdown.

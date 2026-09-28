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
                        jev-1.13 · gpt-6-luna · deepseek-v4.1-flash
```

Final run: **2 codebooks × 2 conditions × 3 models × 1,200 comments = 14,400 requests.**

**→ The formatted report is [`results/REPORT.pdf`](results/REPORT.pdf).**
See `docs/results.md` for the written digest.

## Findings (short version)

**How frequent is reactance?** Rare — **3–7 %**. Codebook A with transcript:
gpt-6-luna 6,6 %, deepseek-v4.1-flash 6,2 %, jev-1.13 3,8 %. All three agree on the
order of magnitude.

**The video transcript adds almost nothing.** Condition A → B moves prevalence by
under 1,2 percentage points, and all three models move in the *same* direction. For
a detection pipeline the transcript is ~900 prompt tokens for no measurable gain.

**Jev wins on both axes:** ~0,46 s and ~$0,061 per 1,000 comments — ~4,5× faster and
~2,4× cheaper than the best chat model — and it is the only backend that returns
per-class probabilities plus a confidence score, which enables a cascade design
(escalate only low-confidence cases to a bigger model).

**Codebook B was fixed and re-validated.** Its first version had no link to the
freedom-threat appraisal, so models coded ordinary political criticism as reactance
(29–56 % vs Codebook A's 2–8 %). The gate fix plus a staged Jev-only validation run
brought the A×B false-positive:true-positive ratio from **13–20× down to 0,1–0,6**.

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


**⚠️ Precision audit — the prevalence figures are upper bounds.** 36 of the 119
flagged positives were hand-coded. Estimated precision is **46 %**, and the error
is strongly structured: 92 % precision where all three models agree, 50 % at a
two-model majority, **25 % for single-model flags** — and two thirds of all
positives are single-model flags. Consensus degree is therefore the most useful
filter for a real pipeline. See `docs/results.md` and §6 of the report.

## Data

Source (read-only, on the NAS, **not** mirrored into this repo beyond the sample):

- `/mnt/nasother/TikTok_Pol2025/comments/<account>/<account>_comments_<videoid>.json`
- `/mnt/nasother/TikTok_Pol2025/transcripts/data/<account>/<videoid>.txt`
- account → party map: `/mnt/nasother/TikTok_Pol2025/parteien.txt`

`src/build_dataset.py` builds `data/sample_comments.jsonl` — a stratified sample
of **1,200 comments** (68 accounts, 16 parties, 400 videos), round-robin across
parties so no party dominates, with non-empty transcripts (needed for Condition A).
Filters and provenance are in `data/sample_meta.json`. Rebuild with:

```bash
python3 src/build_dataset.py --target 1200 --n-accounts-per-party 8
```

> The NAS comment files are **concatenated JSON objects** (one per pagination
> request), not a single JSON document — `build_dataset.py` walks them with
> `raw_decode`. Also note `reply_id` is the *string* `"0"` for top-level comments.

---

## Running

```bash
export OPENROUTER_API_KEY=...        # or leave the key at /home/hermes/Desktop/democragptkey.txt

python3 src/build_dataset.py --target 1200 --n-accounts-per-party 8

python3 src/run_benchmark.py \
    --models jev-1.13 gpt-6-luna deepseek-v4.1-flash \
    --codebooks A B --conditions A B \
    --workers 12 --run-name full

python3 src/dedup_requests.py     # collapse repair-run duplicates
python3 src/analyze.py           # -> results/analysis.md + CSVs
python3 src/make_report.py       # -> results/report_data.json
python3 src/build_report_md.py   # -> results/REPORT.md
node tools/md2pdf.js results/REPORT.md results/REPORT.pdf
```

Helpers: `src/check_gate_jev.py` (validate a codebook change cheaply with Jev only,
before spending on the full matrix), `src/crosstab.py` (A×B crosstab),
`src/diag.py` (parse rates), `src/probe_budget.py` (reasoning-budget probe),
`src/plan_cost.py` (budget planning), `src/check_spend.sh` (live spend).

`run_benchmark.py` records **every** request to `results/requests_full.jsonl` with
wall-clock time, prompt/completion tokens, cost, provider, generation id, finish
reason, and label-salvage flags. A content-hash cache (`results/cache.sqlite`)
keyed on `{model, codebook, CODEBOOK_VERSION, condition, state}` makes reruns free
— and keeps an edited codebook from silently reusing stale labels.

## Layout

```
src/build_dataset.py     stratified sampler -> data/sample_comments.jsonl
src/codebook.py          the codebook (chat prompts + Jev criteria)
src/run_benchmark.py     OpenRouter runner (chat + Jev/Decisions API)
src/analyze.py           aggregation -> results/analysis.md + CSVs
src/make_report.py       figures -> results/report_data.json
src/build_report_md.py   report markdown -> results/REPORT.md
tools/md2pdf.js          markdown -> A4 PDF (headless Chrome)
data/                    the sample + sampling metadata
results/                 per-request logs, predictions, REPORT.pdf, analysis tables
docs/codebook_sources.md provenance of every codebook statement
docs/results.md          written results digest
```

## Cost

The 14,400-request matrix on 1,200 comments cost ≈ $2.4 — i.e. under $1.70 per 1,000
comments for all 3 models × 2 codebooks × 2 conditions. Per-model breakdown in
`results/analysis_cost.csv`.

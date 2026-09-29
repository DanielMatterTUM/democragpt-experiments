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

**→ The formatted report is [`results/REPORT.pdf`](results/REPORT.pdf)** — 14 pages,
journal style (serif, abstract, numbered sections, figures inline, detailed tables
in Appendices A-C). Written digest: `docs/results.md`.

## Findings (short version)

**How frequent is reactance?** Rare — **2,8–6,6 %** (Codebook A, with transcript),
with overlapping bootstrap CIs. The video transcript adds nothing: dropping it
moves prevalence by <2 pp, in the same (negative) direction for all three models.

**Agreement is better than Cohen's κ suggests.** Raw agreement is 94,6–95,1 % but
κ only 0,45–0,59 — a base-rate artefact at 3–7 % prevalence. **Gwet's AC1 gives
0,94** and is the appropriate measure here.

**Jev wins on both axes** (~0,46 s, ~$0,061/1,000 comments) and is the only backend
returning calibrated per-class probabilities — which turns out to matter more
than the speed: a threshold on `p(ja)` lifts precision from 9 % to ~70 %.

**But precision is the real problem.** A hand-coded audit of 36 positives puts
precision at **46 %** (92 % at 3-model consensus, 25 % for single-model flags), and
two thirds of all positives are single-model flags. Prevalence figures are upper
bounds.

**Two new validation experiments** (1,360 extra calls, $0,075): Jev is ≥ 92 %
stable across identical repeats and insensitive to transcript position — but a
neutral politeness frame flips **22–38 %** of positive codes.

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

# core matrix (only `requests` needed)
python3 src/build_dataset.py --target 1200 --n-accounts-per-party 8
python3 src/run_benchmark.py \
    --models jev-1.13 gpt-6-luna deepseek-v4.1-flash \
    --codebooks A B --conditions A B --workers 12 --run-name full
python3 src/dedup_requests.py

# extended analysis + figures + report (needs requirements-analysis.txt)
pip install -r requirements-analysis.txt          # scipy, pandas, seaborn
python3 src/analyze.py                            # base tables
python3 src/analyze_extended.py                   # confusion matrices, tests, calibration
python3 src/exp_reliability.py 45                 # repeat + position robustness
python3 src/exp_paraphrase.py 35                  # surface-form robustness
/tmp/venv-an/bin/python src/make_figures_sci.py  # or any python with seaborn
python3 src/build_report_paper.py                 # -> results/REPORT.md
node tools/md2pdf.js results/REPORT.md results/REPORT.pdf
```

Helpers: `src/check_gate_jev.py` (validate a codebook change cheaply with Jev only),
`src/crosstab.py`, `src/diag.py`, `src/probe_budget.py`, `src/plan_cost.py`,
`src/check_spend.sh`, `src/inspect_examples.py`, `src/audit_positives.py`,
`src/make_audit_sample.py`, `src/score_audit.py`.

`run_benchmark.py` records **every** request to `results/requests_full.jsonl` with
wall-clock time, prompt/completion tokens, cost, provider, generation id, finish
reason, and label-salvage flags. A content-hash cache (`results/cache.sqlite`)
keyed on `{model, codebook, CODEBOOK_VERSION, condition, state}` makes reruns free
— and keeps an edited codebook from silently reusing stale labels.

## Layout

```
src/build_dataset.py       stratified sampler -> data/sample_comments.jsonl
src/codebook.py            the codebook (chat prompts + Jev criteria)
src/run_benchmark.py       OpenRouter runner (chat + Jev/Decisions API)
src/analyze.py             base aggregation -> results/analysis.md + CSVs
src/analyze_extended.py    confusion matrices, McNemar, bootstrap CIs,
                           Gwet AC1, calibration, threshold sweep
src/exp_reliability.py     repeat + transcript-position robustness (Jev)
src/exp_paraphrase.py      surface-form robustness (Jev)
src/inspect_examples.py    dump flagged positives
src/audit_positives.py     positives stratified by consensus degree
src/make_audit_sample.py   draw the 36-case audit sample
src/score_audit.py         precision by stratum, stratum-weighted estimate
src/make_figures_sci.py    figures (vector PDF + 300dpi PNG)
src/build_report_paper.py  report -> results/REPORT.md
tools/md2pdf.js            markdown -> A4 PDF, journal styling
data/                      the sample + sampling metadata
results/                   per-request logs, predictions, REPORT.pdf, figures
docs/codebook_sources.md   provenance of every codebook statement
docs/results.md            written results digest
```

## Cost

The 14,400-request matrix on 1,200 comments cost ≈ $2.4 — i.e. under $1.70 per 1,000
comments for all 3 models × 2 codebooks × 2 conditions. Per-model breakdown in
`results/analysis_cost.csv`.

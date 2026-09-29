# democragpt-experiments — Reactance coding of TikTok political comments

Method experiment for **DemocraGPT** (bidt/TUM): how often does *psychological
reactance* occur in real social-media comments, and how fast and cheaply can LLMs
detect it?

Two questions, one codebase:

1. **How frequent is reactance?** → prevalence per model / codebook / condition.
2. **How fast can we detect it?** → latency, tokens, cost per 1,000 comments.

All models see the **same** sample, so cross-model, cross-codebook and
cross-condition comparisons are directly comparable.

---

## The report

**→ [`report/report.pdf`](report/report.pdf)** — 10 pages, A4, built with
**XeLaTeX** from [`report/report.tex`](report/report.tex) (not HTML, not
pandoc). `biblatex`/`biber` for citations, `fancyhdr` for the running head,
`booktabs` for tables, `\title` for the title block.

```bash
python3 src/generate_latex.py     # regenerate report.tex + refs.bib from the JSONs
cd report && ./make.sh            # xelatex → biber → xelatex → xelatex
./verify.sh                       # log + page/image/citation checks
```

Written digest: [`docs/results.md`](docs/results.md).

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

Two samples:

| sample | comments | accounts | parties | videos | conditions | codebook |
|---|---:|---:|---:|---:|---|---|
| `sample_matrix.jsonl` | 1,200 | 68 | 16 | 400 | A and B | v2 |
| `sample_big.jsonl` | 2,001 | 114 | 16 | 667 | B only | v3 |

The matrix run is 1,200 × 2 codebooks × 2 conditions × 3 models = **14,400 requests**;
the large-scale run adds 4,002.

## Findings (short version)

**Reactance is rare.** Codebook A with transcript: 2.8–6.6 % across models; the
comment-only large-scale run gives **2.9 %** (95 % CI [2.2; 3.6]), with
`κ = 0.98` agreement between the two codebooks.

**The video transcript adds nothing.** Dropping it moves prevalence by under two
percentage points, the same direction for every model. The comment text suffices.

**Agreement is better than Cohen's κ suggests.** Raw agreement is 94.6–95.1 %
but κ only 0.45–0.59 — a base-rate artefact at 3–7 % prevalence.
**Gwet's AC1 is 0.94** and is the right measure here.

**Jev wins on both axes** (~0.46 s, ~$0.061 per 1,000 comments) and is the only
backend returning calibrated probabilities. That matters more than the speed: a
threshold on `p(ja)` lifts precision from 9 % to ~70 %.

**But precision is the real problem.** A hand-coded audit of 36 positives puts
precision at **46 %** (92 % at three-model consensus, 25 % for single-model
flags), and two thirds of all positives are single-model flags — so prevalence
figures are upper bounds.

**Two validation experiments** (1,360 extra calls, $0.075): Jev is ≥ 92 % stable
across identical repeats and insensitive to prompt order, but a neutral
politeness frame flips **22–38 %** of positive codes.

## Data

Read-only on the NAS, not mirrored into the repo beyond the samples:

- `/mnt/nasother/TikTok_Pol2025/comments/<account>/<account>_comments_<videoid>.json`
- `/mnt/nasother/TikTok_Pol2025/transcripts/data/<account>/<videoid>.txt`
- account → party map: `/mnt/nasother/TikTok_Pol2025/parteien.txt`

```bash
python3 src/build_dataset.py --target 1200 --n-accounts-per-party 8 --out sample_matrix
python3 src/build_dataset.py --target 2000 --n-accounts-per-party 12 --out sample_big
```

> The NAS comment files are **concatenated JSON objects** (one per pagination
> request), not one JSON document — `build_dataset.py` walks them with
> `raw_decode`. `reply_id` is the **string** `"0"` for top-level comments, so a
> truthiness check silently drops every comment.

## Running

```bash
export OPENROUTER_API_KEY=...        # or leave the key at /home/hermes/Desktop/democragptkey.txt

# 1. core matrix (only `requests` needed)
python3 src/build_dataset.py --target 1200 --n-accounts-per-party 8 --out sample_matrix
python3 src/run_benchmark.py \
    --models jev-1.13 gpt-6-luna deepseek-v4.1-flash \
    --codebooks A B --conditions A B --workers 12 --run-name full
python3 src/dedup_one.py requests_full
python3 src/verify_samples.py        # predictions must cover their sample

# 2. analysis, experiments, figures, report
bash src/setup_venv.sh               # numpy / matplotlib / scipy
python3 src/analyze_extended.py      # matrices, McNemar, bootstrap, AC1, F1
python3 src/analyze_big.py           # the large-scale run
python3 src/exp_reliability.py 45    # repeat + position robustness
python3 src/exp_paraphrase.py 35     # surface-form robustness
python3 src/make_report.py           # aggregate for the figures
/tmp/venv-an/bin/python src/figures.py
python3 src/generate_latex.py
cd report && ./make.sh
```

Every request is logged to `results/requests_{run}.jsonl` with wall-clock time,
tokens, cost, provider, generation id and finish reason. The cache
(`results/cache.sqlite`) is keyed on
`{model, codebook, CODEBOOK_VERSION, condition, state}` — so reruns are free, and
an edited codebook can never silently reuse stale labels. **Bump
`CODEBOOK_VERSION` in `run_benchmark.py` whenever the codebook text changes.**

## Layout

```
report/report.tex          the document (generated; edit the generator instead)
report/refs.bib            bibliography (biblatex/biber)
report/make.sh             xelatex → biber → xelatex → xelatex
report/verify.sh           log / page / image / citation checks

src/build_dataset.py       stratified sampler -> data/sample_*.jsonl
src/codebook.py            the codebook: chat prompts + Jev criteria
src/run_benchmark.py       OpenRouter runner (chat + Jev Decisions API)
src/dedup_one.py           collapse repair-run duplicates in a request log
src/analyze.py             base tables -> results/analysis.md + CSVs
src/analyze_extended.py    confusion matrices (model×model, A/B, codebook),
                           McNemar, bootstrap CIs, Gwet AC1, F1, calibration
src/analyze_big.py         the 2,001-comment comment-only run
src/exp_reliability.py     repeat + transcript-position robustness
src/exp_paraphrase.py      surface-form robustness
src/make_audit_sample.py   draw the 36-case manual-audit sample
src/score_audit.py         precision by consensus stratum
src/make_report.py         aggregate JSON the figures read
src/figures.py             ALL figures, one style, vector PDF + 300 dpi PNG
src/generate_latex.py      report.tex + refs.bib from the JSONs
src/probe_budget.py        reproduce the reasoning-token bug (see pitfalls)
src/check_gate_jev.py      cheap Jev-only check of a codebook change
src/plan_bigrun.py         budget planning for large runs
src/check_spend.sh         live OpenRouter spend

data/                      the two samples + sampling metadata
results/                   request logs, predictions, figures, aggregate JSON
docs/codebook_sources.md   provenance of every codebook statement
docs/results.md            written results digest
```

## LaTeX toolchain

No TeX was present in this sandbox and there is no passwordless sudo, so
**TinyTeX** is installed into `$HOME/.TinyTeX`:

```bash
curl -sSL https://yihui.org/tinytex/install-bin-unix.sh | sh
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"
tlmgr install fontspec biblatex biber booktabs caption fancyhdr titlesec \
    hyperref csquotes libertinus libertinus-fonts xcolor microtype
```

Fonts: the Libertinus OpenType files ship **inside** the TeX tree, where
fontconfig does not look. Without a fontconfig entry, `xelatex` reports
`Font ... not loadable` and writes a **blank one-page PDF that still exits 0**.
`~/.config/fontconfig/fonts.conf` therefore points at
`~/.TinyTeX/texmf-dist/fonts/{opentype,truetype}` and `fc-cache -f` has to run
once. `report/verify.sh` guards against the blank-PDF failure.

## Cost

The 14,400-request matrix cost ≈ $2.4 on 1,200 comments; the large-scale run
$0.30; the two validation experiments $0.075. Total $2.99 of a $3 budget.
Breakdown in `results/analysis_cost.csv`.
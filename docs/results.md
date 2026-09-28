# Results digest — reactance on TikTok comments

Run: 201 comments × 2 codebooks × 2 conditions × 4 models = **3,216 requests**,
**100 % parse rate in every cell**. Total spend **$0,63** of the $3 budget
(`$0,3847` on live calls for this matrix; the rest was the throwaway first pass
and probing).

Raw logs: `results/requests_full.jsonl` (every request: latency, tokens, cost,
provider, finish reason), `results/predictions_full.jsonl`.
Tables: `analysis_summary.csv`, `analysis_prevalence.csv`, `analysis_overlap.csv`,
`analysis_cost.csv`.

## 1. How frequent is reactance?

**Codebook A (binary), Condition A (with transcript):**

| model | ja / n | prevalence | mean latency |
|---|---:|---:|---:|
| gpt-6-luna | 5 / 201 | **2,49 %** | 1,79 s |
| jev-1.13 | 4 / 201 | **1,99 %** | 0,38 s |
| deepseek-v4.1-flash | 7 / 201 | **3,48 %** | 2,61 s |
| glm-5.3-flash | 16 / 201 | **7,96 %** | 4,11 s |

**Codebook A, Condition B (comment only):** gpt-6-luna 2,99 %, jev-1.13 1,00 %,
deepseek 1,49 %, glm 6,47 %.

Two robust conclusions:

1. **Reactance is rare** — roughly 2–8 % of political TikTok comments, i.e.
   single-digit percent. The three cheapest models cluster at 2–3,5 %; GLM is
   the clear outlier high coder at 8 %.
2. **The video transcript adds almost nothing to the binary decision.** Moving
   from condition A to B changes prevalence by well under 2 percentage points
   for every model, and not consistently in one direction. For a *detection*
   use case, the transcript is ~900 extra prompt tokens for no measurable gain.

## 2. How fast and how cheap is detection?

| model | mean latency (cond A) | $/1k rows (CB A) | parse rate |
|---|---:|---:|---:|
| **jev-1.13** | **0,375 s** | **$0,055** | 100 % |
| gpt-6-luna | 1,79 s | $0,126 | 100 % |
| deepseek-v4.1-flash | 2,61 s | $0,161 | 100 % |
| glm-5.3-flash | 4,11 s | $0,168 | 100 % |

**Jev wins on both axes** — roughly 5× faster and 2–3× cheaper than the chat
models — and it additionally returns calibrated per-class probabilities plus a
confidence score, which the chat models do not. At $0,055 per 1,000 comments the
whole 6,7 M-comment corpus would cost roughly $375 for Codebook A; the full
2×2 matrix over 1,000 comments costs well under $1.

`gpt-6-luna` is the best-performing chat model: lowest latency among the chat
models and no reasoning-budget pathology.

## 3. ⚠️ The one result that needs your decision

**Codebook B yields 29–56 % reactance; Codebook A yields 2–8 %.** That ~10×
gap holds across all four models and both conditions, so it is a **codebook
effect, not a model effect.**

Codebook B, Condition A: gpt-6-luna 28,9 %, jev 44,8 %, deepseek 42,8 %, glm 47,8 %.
Codebook B, Condition B: gpt-6-luna 28,9 %, jev 37,3 %, deepseek 55,7 %, glm 54,7 %.

Reading the B label distribution, the mass sits in the constructive/critical and
confrontational categories — i.e. models code **ordinary disagreement and
criticism of a politician's statement as reactance**. The project theory
explicitly does not want this: Reaktanz requires an appraisal of a *threatened
autonomy* (Brehm 1966; PRPM), and the Notion "Wiki Reaktanz (allgemein)" page is
clear that reactance is not simply "being annoyed at a policy".

**Recommended fix (not yet applied):** make the freedom-threat appraisal a hard
precondition of every Codebook B label, mirroring what Codebook A already does.
Add to `B_INSTRUCTIONS`:

> Assign a reactance type only if you can point to a perceived threat to the
> author's own freedom. If the comment is merely disagreement, criticism or topic
> engagement, answer `keine_reaktanz`.

I deliberately did **not** apply this silently: it changes the instrument, so it
must be a documented decision and then a re-run. The cache means a re-run only
costs the cells that actually change.

**Cheap diagnostic for this** (`src/crosstab.py`, `results/analysis_crosstab_ab.csv`):
cross-tabulate Codebook B against Codebook A per comment. Condition A:

| model | both reactance | **B=type & A=nein** | A=ja & B=keine | both no |
|---|---:|---:|---:|---:|
| gpt-6-luna | 8 (4,0 %) | 54 (26,9 %) | 1 | 138 |
| jev-1.13 | 4 (2,0 %) | 86 (42,8 %) | 0 | 111 |
| deepseek-v4.1-flash | 6 (3,0 %) | 80 (39,8 %) | 1 | 114 |
| glm-5.3-flash | 16 (8,0 %) | 81 (40,3 %) | 1 | 103 |

The two codebooks agree on almost nothing in the middle: the false-positive class
(B names a type, A says `nein`) is **13–20× larger than the true-positive class**.
The reverse error is essentially zero (0–1 comment). So Codebook B is not
"noisier" in a symmetric way — it is systematically *more permissive*, exactly as
the boundary hypothesis predicts.

Composition of that false-positive class (pooled over the four models, condition A):

| B label | n |
|---|---:|
| konfrontation_angriff | 215 |
| konstruktive_kritik | 38 |
| ablenkung_whataboutism | 32 |
| vermeidung_rueckzug | 8 |
| delegierung_hilflosigkeit | 7 |
| reflektierte_rechtfertigung | 1 |

`konfrontation_angriff` alone accounts for ~70 % of it — the models read ordinary
angry criticism of a politician as "attacking resistance". This is the label to
tighten first.

## 4. Inter-model agreement

Codebook A is nearly unanimous (93–100 % raw agreement) but Cohen's κ is low
(≈ 0,0–0,43) — the classic base-rate artefact: with 2–8 % positives, a model that
says `nein` almost always agrees with another on the *easy* majority while the
few `ja` cases split. Raw agreement therefore overstates convergence here;
κ is the honest metric, and even it is unstable at this prevalence.

Codebook B agrees much more substantively: κ = 0,63–0,75 among deepseek/glm/gpt
on condition A. That is the expected pattern — a 7-way forced choice gives the
model room to discriminate, whereas a 2-way choice at 3 % prevalence mostly
measures who says `nein`.

## 5. What the sample is / is not

- 201 comments, 12 accounts, 9 parties, 67 videos, party-stratified
  round-robin. **Party-level differences are not estimable** (max 63 comments
  for one party) — this design trades party coverage for breadth of the model
  comparison.
- Comments are ≥ 25 chars, top-level, visible, and only from videos with a
  non-empty transcript. So this is **not** an unbiased prevalence estimate for
  the full 6,7 M-comment corpus — it is a feasibility/method run.
- Full filter list in `data/sample_meta.json`.

## 6. Engineering notes (for re-runs)

- The NAS comment files are **concatenated JSON objects** (one per pagination
  request), not a single JSON document — `build_dataset.py` walks them with
  `JSONDecoder.raw_decode`.
- `reply_id` is the **string** `"0"` for top-level comments. A truthiness check
  (`if not c["reply_id"]`) silently drops every single comment.
- Reasoning models (DeepSeek, GLM) spend hidden reasoning tokens out of the
  **same** `max_tokens` budget. At 400 they returned `finish_reason="length"`
  with **empty** content, breaking 205/804 DeepSeek and 73/804 GLM cells.
  `max_tokens=2000` fixed it — see `src/probe_budget.py`. This is the single
  most likely thing to break a re-run on a different model.
- OpenRouter sometimes returns `"usage": null`; never index it unguarded.
- The Notion export contains **no** existing annotation scheme, prompt, gold
  standard or agreement measure (no Krippendorff/intercoder protocol) — this
  repo is the first, so model agreement here is *not* validated against human
  coding yet. The theory side references "16 Einzelkategorien" from a
  `1_Theory` document that is **not** in the export.

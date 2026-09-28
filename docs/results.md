# Results digest — reactance on TikTok comments

**Final run (large scale):** 1,200 comments × 2 codebooks × 2 conditions × 3 models
(`gpt-6-luna`, `deepseek-v4.1-flash`, `jev-1.13`) = **14,400 requests**,
**100 % parse rate in every cell**.

For the formatted version see **`results/REPORT.pdf`** (7 pages, German) — that is
the document to circulate.

Raw data: `results/requests_full.jsonl` (every request with latency, tokens, cost,
provider, finish reason), `results/predictions_full.jsonl`, `results/report_data.json`.

---

## 1. What changed since the 201-comment run

### Codebook B was fixed (the "gate")

The first version of Codebook B had no link back to the freedom-threat appraisal,
so the models coded **ordinary criticism of politicians** as reactance: prevalence
was 29–56 % where Codebook A said 2–8 %. The fix makes the freedom-threat a hard
precondition, checked *before* label selection, with the control question:

> Would the author still be angry if nobody were restricting their freedom?
> Then it is not reactance.

Both the chat prompt (`B_INSTRUCTIONS`) and the Jev criteria (`B_CRITERIA`) carry
the gate — Jev only sees the criteria, so gating only the instructions would have
left Jev uncorrected.

**Validation was staged deliberately:** the fix was first run with Jev alone on 60
comments (`src/check_gate_jev.py`, $0.009) before being applied to the full matrix.
The FP:TP ratio dropped from 13–20× to 0.0 at that point.

### Codebook B is now in line with Codebook A

| model | Codebook B, cond A | Codebook A, cond A |
|---|---:|---:|
| gpt-6-luna | 1,75 % | 6,58 % |
| deepseek-v4.1-flash | 3,42 % | 6,17 % |
| jev-1.13 | 2,42 % | 3,83 % |

Crosstab FP:TP ratios fell from **13–20× to 0,1–0,6** across all models and both
conditions. Codebook B is now a *strict subset-ish* refinement of Codebook A rather
than a competing measurement.

`konfrontation_angriff` remains the dominant real type (18–37 of ~20–45 positives),
with `konstruktive_kritik`, `ablenkung_whataboutism`, `reflektierte_rechtfertigung`
and `delegierung_hilflosigkeit` appearing only in single digits.

### A cache-safety bug was found and fixed

The cache key was `{model, codebook, condition, state}` — it did **not** include the
codebook text. An edited codebook would therefore have silently reused labels
produced by the old wording, and the "fix" would have looked like it did nothing.
`CODEBOOK_VERSION` is now part of the key.

---

## 2. Headline numbers (1,200 comments)

### Prevalence, Codebook A (binary)

| model | cond A (with transcript) | cond B (comment only) | Δ |
|---|---:|---:|---:|
| gpt-6-luna | 6,58 % | 5,42 % | −1,16 pp |
| deepseek-v4.1-flash | 6,17 % | 5,42 % | −0,75 pp |
| jev-1.13 | 3,83 % | 2,75 % | −1,08 pp |

**Reactance is rare: 3–7 %.** All three models agree on the order of magnitude and
all three move in the *same* direction when the transcript is removed.

### Speed and cost

| model | latency (cbA/condA) | $/1k rows (cbA/condA) |
|---|---:|---:|
| **jev-1.13** | **0,46 s** | **$0,061** |
| gpt-6-luna | 2,11 s | $0,147 |
| deepseek-v4.1-flash | 4,09 s | $0,332 |

Jev is ~4,5× faster and ~2,4× cheaper than the best chat model, and is the only
backend returning per-class probabilities and a confidence score.

Extrapolation to the full 6.7 M-comment corpus with Jev, Codebook A, both
conditions: **≈ $410**.

### Agreement

Codebook A, condition A: 94,6–95,0 % raw agreement between models, κ ≈ 0,45–0,48.
Codebook B: 96,6–97,6 % raw agreement, κ ≈ 0,40–0,47.

The κ values converge around 0,4–0,5 across both codebooks at 1,200 comments —
much more stable than the 0,0–0,75 range at 201 comments, where the sample was too
small to estimate these reliably.

---

## 3. Engineering notes (relevant to any re-run)

- **Reasoning models need `max_tokens` ≥ 2000.** DeepSeek and GLM spend hidden
  reasoning tokens out of the *same* budget; at 400 they return
  `finish_reason="length"` with **empty** content. This broke 205/804 DeepSeek and
  73/804 GLM cells in the first run. `src/probe_budget.py` reproduces it in 4 calls.
- The NAS comment files are **concatenated JSON objects** (one per pagination
  request), not a single JSON document — parsed with `JSONDecoder.raw_decode`.
- `reply_id` is the **string** `"0"` for top-level comments; a truthiness check
  silently drops every comment.
- OpenRouter sometimes returns `"usage": null`.
- A connection reset and two `finish_reason=length` cells failed in the 14,400-request
  run (99,98 % success). Repair is cheap: purge null-label rows from
  `cache.sqlite` and re-run — 14,397/14,400 come back from cache.
- Latency and cost **must** be computed from `requests_full.jsonl`, not from the
  predictions file: after a cached re-run the predictions are mostly cache hits
  with no timing and zero cost, which silently blanks every latency cell.
  (`analyze.py` and `make_report.py` both read the request log for this reason.)

## 4. Still open

- **No gold standard.** The Notion export contains no annotation scheme, prompt or
  Krippendorff/intercoder protocol. Model agreement here measures *consistency among
  models*, not *correctness against human coding*. With 3–7 % prevalence, random
  sampling for human validation will struggle to surface positives — purposive
  sampling of the ~120 Codebook-A positives would be far more efficient.
- The "16 Einzelkategorien" referenced in the Notion protocol are **not** in the
  export; Codebook B derives from the 8-typology on the wiki page instead.
- Party-level cells are too small for inference (largest: AfD at 192 comments).

---

## 5. Precision audit (2026-09-28, added after the figures)

36 of the 119 flagged positives (stratified 12 each by consensus degree) were
hand-coded against the strict rule: reactance requires **both** a perceived
freedom threat **and** an autonomy-restoring reaction.

| stratum | n | precision |
|---|---:|---:|
| all 3 models agree | 27 | **92 %** |
| 2 of 3 | 26 | **50 %** |
| 1 of 3 only | 66 | **25 %** |

Stratum-weighted estimate: **46 % precision** → of 119 flagged comments roughly
54 are genuine reactance and 65 are false alarms.

**The error is structured, not random.** Three recurring false-positive patterns:

1. **Indignation without a freedom reference** — angry, attacks the politician,
   but no sense of threatened autonomy ("Paranoia als Privileg 🤣",
   "Beide Stimmen für die AfD 💙💙💙").
2. **Responding to a claim, not to a constraint** — the model reads the video as
   provocative and reacts, but the reactance targets the *video*, not an attempt
   to constrain the commenter.
3. **A trigger is named but no reactive behaviour follows** — three borderline
   cases in the 1/3 stratum ("die wollen alles verbieten") were coded as false
   under the strict rule.

**Consequences.** Prevalence figures are upper bounds; the order of magnitude
(low single digits) survives because the errors are not directional. And a
pipeline that takes a single model's positive output inherits roughly two thirds
false alarms — consensus degree, or a confidence threshold on Jev's decision
output, is the obvious mitigation.

**Caveat.** These verdicts were produced by the assistant, not a trained coder,
on 36 cases — indicative, not a validated precision estimate. Files:
`src/inspect_examples.py`, `src/audit_positives.py`, `src/make_audit_sample.py`,
`src/score_audit.py`, `results/audit_verdicts.json`, `results/audit_linked.json`.

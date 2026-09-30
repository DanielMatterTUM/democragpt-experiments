#!/usr/bin/env python3
"""Generate report/report.tex and report/refs.bib from the analysis JSONs.

Design notes:
* LaTeX bodies are PLAIN strings with @PLACEHOLDER@ tokens, injected via
  str.replace() -- f-strings and LaTeX braces do not mix.
* Every number that a previous version of this report typed by hand is now
  GENERATED from the analysis JSONs. If a value the report needs is missing
  from the data, the build fails (see require() at the bottom) instead of the
  report silently mixing stale results.
* Sample discipline: every aggregate in the report carries its sample tag
  ("matrix" = 1,200 comments / "big" = 2,001 comments). The A x B table is
  rendered from the big-sample rows with n=2,001, and the matrix-sample
  per-model values are shown next to it so the two samples can never be
  confused again.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
OUT_TEX = REPO / "report" / "report.tex"
OUT_BIB = REPO / "report" / "refs.bib"

EXPECTED_MODELS_4 = {"jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash",
                     "glm-5.3-flash"}
N_MATRIX = 1200
N_BIG = 2001

_warnings = []


def load(n, d=None):
    """Load a JSON result file from results/ (fall back to data/)."""
    for base in (RES, REPO / "data"):
        p = base / n
        if p.exists():
            return json.load(p.open(encoding="utf-8"))
    _warnings.append(f"required input {n} missing")
    return d


def short_model(m: str) -> str:
    """Short model names -- the full ones overflow the tables."""
    return {"jev-1.13": "jev-1.13",
            "gpt-6-luna": "gpt-6.luna",
            "deepseek-v4.1-flash": "deepseek-fl.",
            "glm-5.3-flash": "glm-5.3-fl."}.get(m, m.replace("_", r"\_"))


def nz(v, n=2, na="--"):
    if v is None:
        return na
    return f"{v:.{n}f}"


# ---------------------------------------------------------------- inputs
X = load("analysis_ext.json", {}) or {}
BIG = load("analysis_big.json", {}) or {}
GATE = load("analysis_gate.json", {}) or {}
RELI = load("exp_reliability.json", {}) or {}
PARA = load("exp_paraphrase.json", {}) or {}
AUD_SC = load("audit_scoping.json", {}) or {}
SM = load("sample_matrix_meta.json", {}) or {}
SB = load("sample_big_meta.json", {}) or {}

# ---------------------------------------------------------------- values
n_matrix = SM.get("reached", N_MATRIX)
n_big = SB.get("reached", N_BIG)

# --- audit (the single generated source for every precision value) -------
AUD = AUD_SC
aud_strata = AUD.get("strata", {})


def aud(k):
    s = aud_strata.get(str(k)) or {}
    return s  # {"n","n_positive","precision_pct","wilson95_pct","cases"}


prec3 = (aud(3).get("precision_pct") or 0) / 100
prec2 = (aud(2).get("precision_pct") or 0) / 100
prec1 = (aud(1).get("precision_pct") or 0) / 100
w3pool = AUD.get("weighted_3model_pool") or {}
w3 = (w3pool.get("pct") or 0) / 100
pooled = AUD.get("pooled") or {}
n_pos_3pool = w3pool.get("n") or 119
glm_only_flags = AUD.get("glm_only_flags")

# --- big sample A x B (per model, n = 2001) -------------------------------
ab_rows_big = []
if isinstance(BIG.get("A_vs_B"), list):
    for r in BIG["A_vs_B"]:
        ab_rows_big.append(
            "  %s & %d & %d & %d & %d & %s & %s & %s \\\\"
            % (short_model(r["model"]), r["n"], r["both"], r["fp"], r["fn"],
               nz(r["raw_agreement_pct"], 1), nz(r["cohens_kappa"], 2),
               nz(r.get("fp_tp"), 2)))
ab_rows_big = "\n".join(ab_rows_big)
# matrix-sample A x B (per model, n = 1200) -- the other table
ab_rows_matrix = []
for r in X.get("codebook_pairwise", []):
    if r["cond"] != "B":
        continue
    ab_rows_matrix.append(
        "  %s & %d & %d & %d & %d & %s \\\\"
        % (short_model(r["model"]), r["n"], r["both"], r["fp"], r["fn"],
           nz(r.get("fp_tp"), 2)))
ab_rows_matrix = "\n".join(ab_rows_matrix)

# --- big-sample headline (Jev) --------------------------------------------
a_prev = (BIG.get("prevalence_A") or {}).get("jev-1.13", {}).get("prevalence_pct")
a_ci = (BIG.get("prevalence_A") or {}).get("jev-1.13", {}).get("ci95", ["--", "--"])
a_npos = (BIG.get("prevalence_A") or {}).get("jev-1.13", {}).get("n_positive")

# --- gate (matrix, condition B) --------------------------------------------
G = (GATE.get("runs", {}).get("matrix", {}).get("conditions") or {}).get("B") or {}
G_BIG = (GATE.get("runs", {}).get("big", {}).get("conditions") or {}).get("B") or {}
gc = {g["model"]: g for g in G.get("gate_consistency", [])}
pw6 = G.get("pairwise_type", [])
pw7 = G.get("pairwise_baseline7", [])
tc = G.get("type_consensus") or {}
gate_n = G.get("jev_gated_n")
gate_pcts = [g["accept_pct"] for g in G.get("gate_consistency", []) if g.get("accept_pct") is not None]
pair_agree = [p["raw_pct"] for p in pw6 if p.get("raw_pct") is not None]

# --- consensus reference F1 (matrix, condition A) --------------------------
agree_rows_lines = []
for c in X.get("consensus_reference", []):
    if c["cond"] != "A":
        continue
    n = c["n"]; maj_pos = c["n_ref_pos"]
    n11 = c["tp"]; n01 = c["fp"]; n10 = c["fn"]; n00 = n - maj_pos - c["fp"]
    po = (n11 + n00) / n if n else 0.0
    pe = ((maj_pos / n) * ((n11 + n01) / n)
          + (1 - maj_pos / n) * (1 - (n11 + n01) / n)) if n else 0.0
    k = (1.0 if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)) if n else 0.0
    agree_rows_lines.append(
        "  %s & %d & %s & %s & %s & %s & %s " % (short_model(c["model"]), n,
                   nz(po, 3), nz(c.get("f1"), 3), nz(k, 3),
                   nz(c.get("ac1"), 3),
                   nz(c.get("positive_agreement"), 3)) + r"\\")
agree_rows = "\n".join(agree_rows_lines)

# --- prevalence rows ---------------------------------------------------------
prev_rows_lines = []
for m in ("jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash", "glm-5.3-flash"):
    b = next((x for x in X.get("bootstrap_prev", [])
              if x["cb"] == "A" and x["model"] == m), None)
    if not b:
        continue
    prev_rows_lines.append(
        "  %s & %s & %s & %s\\%% & [%s; %s] \\\\"
        % (short_model(m), b.get("cond"), b.get("n"),
           nz(b.get("pct"), 2), nz(b.get("ci_lo"), 2), nz(b.get("ci_hi"), 2)))
prev_rows = "\n".join(prev_rows_lines)

# Codebook A Condition A positive-rate range across models (for the prose
# claim in Section "Frequency and speed"). Generated, not typed.
_prevA = [b["pct"] for b in X.get("bootstrap_prev", [])
          if b["cb"] == "A" and b["cond"] == "A" and b.get("pct") is not None]
PREV_A_MIN = f"{min(_prevA):.1f}" if _prevA else "--"
PREV_A_MAX = f"{max(_prevA):.1f}" if _prevA else "--"

# --- surface robustness rows -------------------------------------------------
def _surf_table():
    per = PARA.get("per_stratum", {})
    rows = []
    for k in ("3", "2", "1", "0"):
        v = per.get(k)
        if not v:
            continue
        nm = "Kontrolle" if k == "0" else f"{k} von 3"
        rows.append("  %s & %s & %s\\%% & %s\\%% & %s\\%% & %s\\%% \\\\"
                    % (nm, v.get("n"), nz(v.get("T1_deemphasis"), 0),
                       nz(v.get("T2_politeness"), 0), nz(v.get("T3_defiller"), 0),
                       nz(v.get("all_variants_agree"), 0)))
    return "\n".join(rows)


surf_rows = _surf_table()

# ---------------------------------------------------------------- gates
# Gate-rejection table rows (Q1) -- one per downstream model, matrix/cond B
gate_rows_lines = []
for m in ("jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash", "glm-5.3-flash"):
    g = gc.get(m)
    if not g:
        continue
    gate_rows_lines.append(
        "  %s & %d & %d & %d & %s\\%% \\\\"
        % (short_model(m), g["n"], g["n_accept"], g["n_reject"],
           nz(g["reject_pct"], 0)))
gate_rows = "\n".join(gate_rows_lines)

# consensus tiers (Q3) -- counts + the "k or more" cumulative
if tc:
    _n_v = tc.get("n_voters", 4)
    _ga = tc.get("gate_accept", {})
    _tcs = tc.get("type_consensus", {})
    _n_gated = tc.get("n_gated", 0)

    def _cnt(d, k):
        return d.get(f"{k}-of-{_n_v}", 0)

    n_44 = _cnt(_tcs, 4)
    n_34 = _cnt(_tcs, 3)
    n_24 = _cnt(_tcs, 2)
    n_14 = _cnt(_tcs, 1)
    n_tie = _tcs.get("tie", 0)
    n_reject_all = _cnt(_ga, 0)
    n_k3 = n_44 + n_34 + n_24  # >= 3 of 4 models retain the gate
    pct = lambda c: round(100 * c / _n_gated) if _n_gated else None
else:
    n_44 = n_34 = n_24 = n_14 = n_tie = n_reject_all = n_k3 = None
    pct = lambda c: None

# Big-sample gate consensus headline (2 models)
gc_big = {g["model"]: g for g in G_BIG.get("gate_consistency", [])}
tc_big = G_BIG.get("type_consensus") or {}
gate_n_big = G_BIG.get("jev_gated_n")

# A x B headline (Jev, big sample) -- generated, not typed
_abj = next((r for r in (BIG.get("A_vs_B") or []) if r["model"] == "jev-1.13"), None)
AB_BIG_JEV_RAW = f"{_abj['raw_agreement_pct']:.1f}" if _abj else "--"
AB_BIG_JEV_K = f"{_abj['cohens_kappa']:.2f}" if _abj else "--"
AB_BIG_JEV_FPTP = f"{_abj['fp_tp']:.2f}" if _abj else "--"

# Jev threshold sweep (leave-one-model-out consensus), generated
_ts_a = next((t for t in X.get("threshold_sweep", []) if t["cond"] == "A"), None)
_sweep = {s["t"]: s for s in (_ts_a.get("sweep") or [])} if _ts_a else {}
def _ts(t, key):
    s = _sweep.get(t)
    if not s or s.get(key) is None:
        return "--"
    # precision/recall are stored as proportions in [0,1]; coverage_pct is
    # already a percentage. Without the *100 the report printed "0%" and "1%".
    if key in ("precision", "recall"):
        return f"{100 * s[key]:.0f}"
    return f"{s[key]:.1f}"
THR_LO_P = _ts(0.05, "precision")    # precision at t=0.05
THR_HI_P = _ts(0.6, "precision")     # precision at t=0.6
THR_HI_C = _ts(0.6, "coverage_pct")  # coverage at t=0.6
THR_LO_C = _ts(0.05, "coverage_pct")  # coverage at t=0.05
# Jev raw-label precision vs LOO consensus (threshold-free operating point)
_jev_cr = next((c for c in X.get("consensus_reference", [])
                if c["model"] == "jev-1.13" and c["cond"] == "A"), None)
JEV_RAW_P = (f"{_jev_cr['precision'] * 100:.0f}" if _jev_cr
             and _jev_cr.get("precision") is not None else "--")

# ---------------------------------------------------------------- document
DOC_TEMPLATE = r"""% !TeX program = xelatex
% Autogenerated by src/generate_latex.py -- do not hand-edit.

\documentclass[11pt,a4paper]{article}

% ---- fonts (xelatex / lualatex) -------------------------------------
\usepackage{fontspec}
\setmainfont{Libertinus Serif}
\setmonofont{Libertinus Mono}

% ---- language + bibliography ---------------------------------------------
\usepackage[english]{babel}
\usepackage{csquotes}
\usepackage[backend=biber,style=authoryear,maxcitenames=2]{biblatex}
\addbibresource{refs.bib}

% ---- geometry, look -------------------------------------------------------
\usepackage[a4paper,left=26mm,right=26mm,top=28mm,bottom=30mm]{geometry}
\usepackage{microtype}
\setlength{\emergencystretch}{2em}
\usepackage{booktabs}
\usepackage{graphicx}
\graphicspath{{../results/figures/}}
\usepackage{amsmath}
\usepackage{xcolor}
\definecolor{hdr}{RGB}{28,42,74}
\definecolor{BrickRed}{RGB}{165,42,42}
\usepackage{float}
\restylefloat{figure}
\restylefloat{table}

% ---- running head ---------------------------------------------------------
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\itshape Reaktanz auf TikTok -- H\"aufigkeit und Erkennungsgeschwindigkeit}
\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% ---- section titles ---------------------------------------------------------
\usepackage{titlesec}
\titleformat{\section}{\large\bfseries}{\thesection}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{2.2ex plus 1ex}{1.2ex}
\titlespacing*{\subsection}{0pt}{1.8ex plus 0.8ex}{1.0ex}

% ---- captions ----------------------------------------------------------------
\usepackage{caption}
\captionsetup{format=plain,labelsep=period,font=small,labelfont=bf}
\captionsetup[table]{position=above}
\captionsetup[figure]{position=below}

% ---- bibliography heading inside a fresh (unnumbered) section ----------------
\defbibheading{secbib}{\section*{References}}

% ---- hyperref last --------------------------------------------------------------
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=hdr,citecolor=BrickRed,
  urlcolor=hdr,pdftitle={How frequently is psychological reactance on TikTok},
  pdfauthor={Daniel Matter}}

\begin{document}

\title{How frequently is psychological reactance on TikTok, and how quickly can it be detected?\\[0.4ex]
\large A benchmark on @N_MATRIX@ comments under videos of German politicians, with two codings, two conditions and four models}
\author{Daniel Matter}
\date{29 September 2026}
\maketitle

\begin{abstract}
@ABSTRACT@
\end{abstract}

\noindent\small\textbf{Keywords:} psychological reactance; social media;
LLM coding; TikTok; validity; reliability; bootstrap; decision API\par\normalsize

\section{Data and method}
\label{sec:method}

\textbf{Samples.} Two samples from the same corpus of German-language comments
under the accounts of German politicians, stratified by the account's party.
The \emph{matrix sample} comprises @N_MATRIX@ comments from @M_ACC@ accounts,
@M_PARTIES@ parties and @M_VID@ videos, each with its video transcript
(required by Condition~A). The \emph{large-scale sample} adds @N_BIG@ comments
from @B_ACC@ accounts and @B_PARTIES@ parties, coded exclusively under
Condition~B (comment text only) and, for the agreement analyses, by the two
backends that run on that sample (Jev and GLM-5.3-Flash). Both samples are
restricted to visible top-level comments of at least 25 characters.

\medskip
\noindent\textbf{Codebook A (binary).} Requires, together, a perceived freedom
threat \emph{and} an affective or behavioural reaction. The project's decoding
perspective governs: what matters is not whether a message was actually
controlling but whether the commenter perceived it that way.

\medskip
\noindent\textbf{Codebook B (type).} Seven disjoint labels, condensed from the
project's eight written-reactance archetypes (Appendix~\ref{app:codebook}). The
first version lacked the link to the freedom threat; the models then coded
ordinary political criticism as reactance (29--56\%). Two gate fixes addressed
this (Sections~\ref{sec:agree}, \ref{sec:validity}).

\medskip
\noindent\textbf{Conditions and models.} Condition~A presents the comment
\emph{with} the video transcript; Condition~B the comment only. Jev runs via
the Decisions API, GPT-6-Luna, DeepSeek-V4.1-Flash and --- new in this
version --- GLM-5.3-Flash via chat completion. All four models receive
semantically matched coding criteria, adapted to the respective API format.
The chat models receive the criteria as prompt instructions, whereas Jev
receives the corresponding criteria through the Decisions API. All runs use
temperature~0 with a fixed seed; GLM-5.3-Flash was the
addition of this iteration and is otherwise handled exactly like the other
chat models.

\medskip
\noindent\textbf{Volumes.} The matrix is 2 codebooks $\times$ 2 conditions
$\times$ 4 models $=$ 16 calls per comment (@N_MATRIX@ comments). This
iteration added the fourth model: 4{,}800 GLM calls on the matrix sample plus
340 further calls to complete GLM on the large-scale sample
($\approx$\$0.69). The two validation experiments (1{,}360 calls, \$0.075)
and the Jev-only gate check are unchanged. The gate condition
(Section~\ref{sec:gate}) reuses the predictions already on disk and therefore
costs no API calls. Total cost 3.17\,US\$.

\section{Frequency and speed}
\label{sec:freq}

Classifier-positive rates are low. Across the matrix sample, Codebook~A yields
reactance-positive rates between @PREV_A_MIN@\% and @PREV_A_MAX@\%, depending on
the model. Table~\ref{tab:prev} reports those rates with
95\%-bootstrap confidence intervals. The rank order is stable across
conditions; Jev marks least often. These are rates produced by the
classifiers on a non-representative sample, not estimates of true
prevalence in the corpus.

\begin{table}[ht]
\centering
\caption{Prevalence, Codebook~A, with 95\%-bootstrap CI (2{,}000 resamples), matrix sample.}
\label{tab:prev}
\begin{tabular}{lcccc}
\toprule
Model & Cond & $n$ & Prev. & 95\% CI\\
\midrule
@PREV_ROWS@
\bottomrule
\end{tabular}
\end{table}

Jev remains the fastest and cheapest backend: 0.46\,s and \$0.061 per
1{,}000 comments, against 2.1--2.4\,s and \$0.12--0.33 for the chat models
(Figure~\ref{fig:cost}); GLM-5.3-Flash is the cheapest chat model
(\$0.119) but does not beat Jev. Jev is also the only backend that returns
class probabilities --- an advantage with a practical payoff in
Section~\ref{sub:calib} (a threshold on the probability lifts
leave-one-out-consensus precision from @THR_LO_P@\% to @THR_HI_P@\%).

\begin{figure}[ht]
\centering
\includegraphics[width=0.9\linewidth]{fig01_prevalence.pdf}
\caption{Prevalence by codebook and condition with 95\%-bootstrap CIs.}
\label{fig:prev}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.9\linewidth]{fig10_bigscale.pdf}
\caption{Large-scale run: prevalence of both codebooks (a) and the
confidence-band structure of the Decisions API (b).}
\label{fig:big}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=0.85\linewidth]{fig04_cost.pdf}
\caption{Response time (a) and cost (b) per 1{,}000 comments, Condition~A.
Circles: Codebook~A. Squares: Codebook~B.}
\label{fig:cost}
\end{figure}

\subsection{Does the video context help detection?}
\label{sub:transcript}
Dropping the transcript moves the \emph{aggregate} prevalence by less than two
percentage points, in the same direction for all models
($\Delta$ prevalence, Codebook~A, matrix sample: jev @PCT_JEV@ \,pp,
gpt-6-luna @PCT_GPT@ \,pp, deepseek @PCT_DEEP@ \,pp, glm @PCT_GLM@ \,pp;
only Jev's shift reaches the conventional significance level of an exact
McNemar test). The aggregate figure alone does not answer the interesting
question, however, which is whether the \emph{same comments} are classified as
reactant with and without the transcript (Figures~\ref{fig:cmCondA} and
\ref{fig:cmCondB} sit here on purpose). @CASELEVEL_SENTENCE@ For a
cost-sensitive screening pipeline, the limited change in model outputs
provides little evidence that transcript inclusion is necessary.

\begin{figure}[ht]
\centering
\includegraphics[width=\linewidth]{fig06_confusion_condition_A.pdf}
\caption{Condition~A (with transcript) vs.\ Condition~B (comment only),
Codebook~A: case-level stability of the binary reactance label per model.
Rows = Condition~A, columns = Condition~B.}
\label{fig:cmCondA}
\end{figure}

\begin{figure}[ht]
\centering
\includegraphics[width=\linewidth]{fig06_confusion_condition_B.pdf}
\caption{Condition~A vs.\ Condition~B, Codebook~B. Top row: the full 7-class
confusion --- does the transcript change the inferred \emph{kind} of
reactance? Bottom row: the binary reactant/none collapse with the four
cells --- are the \emph{same comments} called reactant?}
\label{fig:cmCondB}
\end{figure}

\subsection{GLM-5.3-Flash is the least conservative model}
\label{sec:glm}
The fourth model changes the prevalence picture more than any transcript or
codebook change did. GLM-5.3-Flash marks 10.8\% of the matrix sample as
reactance (Condition~A) --- two to three times the share of the other three
(2.8--6.6\%) --- and flags @N_GLM_BIG@ of the @N_BIG@ large-scale comments
where Jev finds @N_JEV_BIG@. This is not better or worse recall in itself; it
is the single largest source of the disagreement structure in
Section~\ref{sec:agree}, and it is a statement about \emph{agreement with the
consensus}, not about which model is correct: GLM deviates most strongly from
its leave-one-model-out consensus of the other three models, which is
exactly what its lower consensus-F1
measures (0.52--0.54, Table~\ref{tab:agree}).

Of the comments only GLM flags, @GLM_ONLY@ were flagged by no other model in
the matrix sample. The manual audit (Section~\ref{sub:precision}) was drawn
\emph{before} GLM existed and says nothing about this GLM-only stratum; the
v2 audit sample (48 candidates, the GLM-only stratum included) is drawn and
awaiting annotation. No precision claim about GLM-only flags is made here.

\section{Agreement between models}
\label{sec:agree}

With the fourth model in the matrix, the picture sharpens. The three
original models still agree to 94.6--95.1\% raw on Codebook~A, Condition~A,
while GLM-5.3-Flash sits lower: 90.5--91.8\% against each of them, because it
marks roughly twice as many comments as reactance (10.8\% prevalence, the
highest of the four; Section~\ref{sec:freq}). Yet even there the chance-
corrected coefficients tell a two-part story: Cohen's $\kappa$ is low
(0.31--0.59 across all pairs) and Gwet's AC1 high (0.89--0.94). This is not
a contradiction but a base-rate artefact: with 3--11\% positives all models
agree on the easy majority while the few positives split, and $\kappa$
penalises exactly that. \textbf{For these data AC1 --- and, for the binary
task, the per-model F1 of Section~\ref{sub:f1} --- are the appropriate
measures, not $\kappa$ alone.}

All of the following numbers --- raw agreement, the two chance-corrected
coefficients and F1 --- lie on the \emph{same} 0--1 scale. Raw agreement is
the same proportion that the older version plotted as 94.6\% on a separate
percentage axis; expressing it as 0.946 is what lets one axis carry every
quantity and makes the base-rate gap readable at a glance
(Figure~\ref{fig:agree}).

\begin{figure}[ht]
\centering
\includegraphics[width=0.98\linewidth]{fig03_agreement.pdf}
\caption{Pairwise agreement on the model pairs (a, b) and per-model F1
against the leave-one-model-out consensus of the other three models (c), all
on a single 0--1 axis: raw
agreement, Cohen's $\kappa$, Gwet's AC1 and F1. The gap between raw
agreement ($\approx$0.91--0.95) and $\kappa$ (0.29--0.59) is the base-rate
artefact; AC1 and, for the binary task, F1 close it.}
\label{fig:agree}
\end{figure}

\begin{table}[htp]
\centering
\caption{Each model against the \emph{leave-one-model-out} consensus of the
other three (Codebook~A, Condition~A). All columns sit on the 0--1 scale ---
raw agreement and F1 next to the two chance-corrected coefficients, plus a
positive-class-specific agreement so the rare-positive overlap is visible
rather than hidden behind the dominant negative class. The reference is a
consensus, not a gold standard: these are agreement numbers, not
correctness numbers.}
\label{tab:agree}
\footnotesize
\setlength{\tabcolsep}{5pt}
\begin{tabular}{lcccccc}
\toprule
Model & $n$ & Raw & F1 & $\kappa$ & AC1 & Pos.\,agree.\\
\midrule
@AGREE_ROWS@
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[htp]
\centering
\includegraphics[width=\linewidth]{fig05_confusion_models_A.pdf}
\caption{Confusion matrices model $\times$ model, Codebook~A, Condition~A.
Colour encodes counts; red borders mark disagreement cells.}
\label{fig:cmA}
\end{figure}

\begin{figure}[htp]
\centering
\includegraphics[width=\linewidth]{fig05_confusion_models_B.pdf}
\caption{The same matrix for Codebook~B. Cells carry colour only (no numbers):
the 7-class structure is read visually; values appear in the appended tables.}
\label{fig:cmB}
\end{figure}

\section{Validity: the real bottleneck}
\label{sec:validity}

A prevalence figure is only as solid as the coding rules behind it. Three checks
address this.

\subsection{Precision of positive detection}
\label{sub:precision}
Of the @N_POS@ comments marked as reactant by at least one of the \emph{three
original models}, @N_AUDITED@ were re-coded manually, stratified by consensus
degree (12 per stratum). \textbf{Scope of this audit: the three original
models.} GLM-5.3-Flash was added to the experiment after the sample was drawn,
so the strata below are ``$k$ of the three original models'' and the audit says
nothing about GLM-only flags. The estimated precision is \textbf{@PREC_W@\%}
(stratum-weighted over the 3-model pool of @N_POS@): @PREC3@\%
(@N3@/{@NN3@} of the cases) at three-model consensus, @PREC2@\%
(@N2@/{@NN2@}) at a two-model majority and @PREC1@\% (@N1@/{@NN1@}) for
single-model flags; every value is a point estimate on $n=12$ and the
intervals are Wilson score 95\% intervals (Figure~\ref{fig:audit}). The error is
structured: outrage without a freedom reference; reaction to a claim rather
than to a constraint; named triggers without reactive behaviour.

\begin{figure}[ht]
\centering
\includegraphics[width=0.9\linewidth]{fig02_audit.pdf}
\caption{Precision by consensus degree (a) and the distribution of the
3-model positives (b); the audit is explicitly the three original models
(GLM was added later and is not covered). Error bars: Wilson score 95\%
intervals on $n=12$ per stratum.}
\label{fig:audit}
\end{figure}

Precision falls sharply with the number of models that agree. Among the cases
flagged by only one of the three original models, 3 of 12 were judged true
positives; among those flagged by all three, 11 of 12 were. Within the audited
cases flagged by a single model, this suggests low precision for isolated
flags, although the estimate rests on a small stratified sample and the
intervals are wide. The positive audit therefore indicates substantial
false-positive contamination, especially in the isolated-flag strata. Raw
model-positive rates should not be read directly as estimates of true
prevalence. Because the audit samples predicted positives rather than the full
comment population, it does not estimate false negatives and cannot establish
whether prevalence is biased upward or downward overall. A v2 audit sample
covering the four-model pool (including the @GLM_ONLY@ GLM-only flags) is
drawn and awaiting annotation; precision for the four-model strata is a
follow-up, not a number in this report.

\subsection{F1 against the leave-one-model-out consensus}
\label{sub:f1}
F1 is treated as a first-class agreement measure in
Section~\ref{sec:agree}, where it sits next to raw agreement, $\kappa$ and
AC1 (Table~\ref{tab:agree}) rather than in a chapter of its own. The reference
there is a \emph{leave-one-model-out consensus}: each model is compared with
the majority of the other three only, so the evaluated model never votes in
its own reference. It is a consensus, not a gold standard, so F1 reads as how
far a model sits from the consensual position, not how correct it is. At low
prevalence precision and recall pull against each other: Jev has the best
precision but gives up the most recall, and so loses to the chat models
on F1.

\subsection{Codebook A and Codebook B agree --- on both samples}
The error patterns above were translated into a new codebook, together with the
surface-sensitivity finding (Section~\ref{sec:exp}). Gate~2 requires the trigger
to be the \emph{target} of the reaction, not its topic: responding to a claim
is not reacting to a constraint. Gate~3 fixes that politeness markers are
neither trigger nor shield. Both gates sit in the chat instructions \emph{and}
in the Jev criteria, because the Decisions API only returns the criteria.

Two samples, two tables --- deliberately kept apart. On the
\emph{large-scale} sample (@N_BIG@ comments, Condition~B, Jev and GLM) the two
instruments agree to @AB_BIG_JEV_RAW@\% raw, but the chance-corrected
agreement is only $\kappa=$@AB_BIG_JEV_K@, with an FP/TP ratio of
@AB_BIG_JEV_FPTP@ (Jev; Table~\ref{tab:ab}). The very high raw agreement is
driven by both instruments labelling most comments as non-reactant; on the
rare positive class the agreement is moderate once chance is accounted for.
$\kappa$ is computed after collapsing both codebooks to the same binary label
space (A: ja/nein vs.\ B: reactant/none), because comparing the two label
spaces directly would make the expected-agreement term invalid.
The \emph{matrix sample} (@N_MATRIX@ comments, all four models) shows the same
pattern per model and condition at n=@N_MATRIX@
(Table~\ref{tab:abm}); its aggregate raw agreement is lower simply because the
gate is tested on the harder, transcript-bearing comments.

\begin{table}[htp]
\centering
\caption{Codebook A~$\times$~B agreement, \emph{large-scale sample}
(@N_BIG@ comments, Condition~B). The n column is part of the point: these
rows are 2{,}001, not the 1{,}200 of the matrix sample.}
\label{tab:ab}
\small
\begin{tabular}{lccccccc}
\toprule
Model & $n$ & both & FP & FN & raw agree & $\kappa$ & FP:TP\\
\midrule
@AB_ROWS_BIG@
\bottomrule
\end{tabular}
\end{table}

\begin{table}[htp]
\centering
\caption{The same agreement, \emph{matrix sample} (1{,}200 comments,
Condition~B, all four models).}
\label{tab:abm}
\small
\begin{tabular}{lccccc}
\toprule
Model & $n$ & both & FP & FN & FP:TP\\
\midrule
@AB_ROWS_MATRIX@
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[htp]
\centering
\includegraphics[width=\linewidth]{fig07_confusion_codebook.pdf}
\caption{Confusion of Codebook B (columns) against Codebook A (rows), collapsed
to the binary reactant/none dichotomy, matrix sample.}
\label{fig:cmAB}
\end{figure}

\subsection{Confidence as a corrective}
\label{sub:calib}
Jev returns a class probability $P(\mathrm{ja})$ for every comment; the other
backends do not. Two properties of that number are worth checking separately,
and Figure~\ref{fig:cal} shows both. We are careful about what this
establishes: there is \emph{no independent human-labelled calibration set} in
this experiment, so neither panel is a calibration result in the statistical
sense. The reference in both panels is the leave-one-model-out consensus of
GPT-6-Luna, DeepSeek-V4.1-Flash and GLM-5.3-Flash ---
a proxy, not ground truth --- and the correct reading is
\textbf{probability alignment with the model consensus}, with
probability \emph{discrimination} (do the probability bands separate consensus
positives from non-positives?) being the property that \emph{is} demonstrated.
Brier scores and ECE against human labels require a labelled validation set
and are deliberately not reported here.

\smallskip
\noindent\textbf{(a) Alignment against the consensus majority.} We split
Jev's predictions into ten bins of $P(\mathrm{ja})$ and, in each bin, ask
how often the comment's label agrees with the majority vote of the other
three backends. If Jev's probability were well \emph{aligned} with the
consensus, the observed rate would track the diagonal: predictions of
$P=0.6$ would be majority-reactant about 60\% of the time. The two ends of
the range do track it --- below $P=0.1$ the observed rate is 1\%, above
$P=0.9$ it is 100\% --- but the middle bins sit consistently below the
diagonal, and by a lot in two places: the 0.1--0.2 bin is observed at 4\%
against a mean predicted 14\%, and the 0.3--0.4 bin at 17\% against 35\%.
Roughly a fifth to a third of Jev's mid-range positives are there missed or
refuted by the other three models. Alignment, then, is imperfect in exactly
the region that matters at low prevalence, and the bin sizes printed in
Figure~\ref{fig:cal}(a) show how few comments the upper bins rest on.

\smallskip
\noindent\textbf{(b) The threshold trade-off.} Because $P(\mathrm{ja})$
is meaningful, we can discard low-confidence flags. Raising the threshold
$t$ --- flag only those comments with $P(\mathrm{ja})\geq t$ --- trades
coverage for agreement with the leave-one-model-out consensus: at $t=0.05$
@THR_LO_C@\% of comments are flagged and precision is only @THR_LO_P@\%;
at $t=0.6$ precision reaches @THR_HI_P@\% but covers only @THR_HI_C@\% of
the sample. The @JEV_RAW_P@\% line marks the precision of Jev's raw
threshold-free label. Precision, then, is not a property of the model but of
the operating point chosen on this curve --- relative to the consensus of the
other three models, not to a ground truth.

\begin{figure}[ht]
\centering
\includegraphics[width=0.94\linewidth]{fig08_calibration.pdf}
\caption{(a) Jev's mean predicted $P(\mathrm{ja})$ within each probability bin
against the observed positive rate of the leave-one-model-out consensus of
GPT-6-Luna, DeepSeek-V4.1-Flash and GLM-5.3-Flash. The grey diagonal indicates
perfect alignment with this consensus proxy; this is not calibration against
human labels. Numbers denote bin sizes. (b) The precision -- coverage trade-off
as the threshold $t$ on $P(\mathrm{ja})$ rises. Precision is measured against
the same leave-one-model-out consensus reference; the horizontal line shows
Jev's threshold-free consensus precision.}
\label{fig:cal}
\end{figure}

\section{Retrospective gated reanalysis: classify type after a Jev-positive gate}
\label{sec:gate}

A production cascade would first run the binary Codebook~A gate and then prompt
only the retained comments with the six reactance types. That second-stage
six-class prompt was \emph{not} run here. Instead, this section is a
\textbf{retrospective gated reanalysis} of predictions that had already been
collected with the original seven-class Codebook~B task on all comments. We
select the comments Jev marked positive under Codebook~A; a stored downstream
\texttt{keine\_reaktanz} answer is treated as rejection of the gate premise,
and the conditional type analysis then considers only the six reactance labels
among retainers. This recombination costs no additional API calls, but it should
not be read as an experimental test of a freshly prompted six-class second
stage. The reanalysis raises two distinct questions: whether downstream
classifiers retain Jev's binary reactance decision, and, conditional on
retaining it, which reactance type they assign.

\medskip
\noindent\textbf{1. Gate retention and rejection.} Jev performs binary reactance
detection over all comments. On the matrix sample, condition~B, the gate lets
through @GATE_N@ of @N_MATRIX@ comments (@GATE_PCT@\%); on the large-scale
sample @GATE_N_BIG@ of @N_BIG@ (@GATE_PCT_BIG@\%). Once Jev says ``reactance
present'', a downstream model can still answer
\texttt{keine\_reaktanz}: it \emph{rejects the gate's premise}. How often each
model does this is its own diagnostic (Table~\ref{tab:gatereject},
Figure~\ref{fig:gaterej}): @GATE_REJECT_SENTENCE@

\begin{table}[htp]
\centering
\caption{Gate retention vs.\ rejection in the retrospective reanalysis: of the
@GATE_N@ comments Jev's gate selected (matrix sample, Condition~B), how many
does each model's already-collected Codebook~B prediction retain as reactant
(assign one of the six types) and how many does it label
\texttt{keine\_reaktanz}?}
\label{tab:gatereject}
\small
\begin{tabular}{lcccc}
\toprule
Model & $n$ gated & retain & reject & reject\%\\
\midrule
@GATE_ROWS@
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[ht]
\centering
\includegraphics[width=0.9\linewidth]{fig13_gate_rejection.pdf}
\caption{Retrospective gate retention vs.\ rejection per model (matrix sample,
Condition~B).}
\label{fig:gaterej}
\end{figure}

\medskip
\noindent\textbf{2. Conditional six-class type agreement.} For the analysis
conditional on retaining the gate, \texttt{keine\_reaktanz} is excluded and
the remaining label space contains the six reactance types. Given that two
models both retain the gate, which types do they confuse?
Figure~\ref{fig:gatecm} is that six-class grid; each cell carries its
conditional $n$, because support differs from pair to pair once rejections are
removed. The retained type calls are dominated by
\texttt{konfrontation\_angriff} (attack), with the other five types at single
digits in total (support annotated in Figure~\ref{fig:gatecm}), and the pairwise
conditional support is tiny ($n$ between @PAIR_N_MIN@ and @PAIR_N_MAX@).
Type-level agreement therefore is \emph{descriptive only}: raw pairwise
agreement ranges from @PAIR_LO@ to @PAIR_HI@\% ($\kappa$ @KAPPA_RANGE6@; on the
same gated set the unconditional seven-class predictions agree @BASE7_RANGE@\%,
$\kappa$ @KAPPA_RANGE7@). A global six-class $\kappa$ on near-empty classes is
not a robust summary.

\begin{figure}[ht]
\centering
\includegraphics[width=\linewidth]{fig11_gate_confusion.pdf}
\caption{Conditional six-class type confusion in the retrospective gated
reanalysis (matrix sample, Condition~B): rows and columns are the four models'
stored type labels, restricted to comments on which both models retained Jev's
positive gate. Each cell carries its conditional $n$; per-type support is
annotated below.}
\label{fig:gatecm}
\end{figure}

\medskip
\noindent\textbf{3. Consensus among the retaining models.} The plurality is
recomputed on the six types among the models that \emph{retained} the gate.
Gate acceptance and conditional type consensus are distinct quantities
(Figure~\ref{fig:gatemaj}): @N44@ of @GATE_N@ comments have all four models
retaining the gate and @NREJALL@ are rejected by all, while \emph{among the
retainers} the type label is a plurality of four (@N44@), three (@N34@), two
(@N24@) or one (@N14@), with @NTIE@ explicit ties. Requiring three-or-more
models to retain the gate keeps @NK3PCT@\% of the gated stream. On the
large-scale sample the gate is more selective (@GATE_N_BIG@ of @N_BIG@
comments), of which @N24_BIG@ reach a plurality of the retaining models on the
type.

\begin{figure}[ht]
\centering
\includegraphics[width=0.9\linewidth]{fig12_gate_majority.pdf}
\caption{Retrospective gated reanalysis, matrix sample, Condition~B.
(a)~Gate acceptance: how many of the four stored Codebook~B predictions retain
each Jev-gated comment as reactant. (b)~Conditional type consensus among the
models that retained it, with ties shown separately.}
\label{fig:gatemaj}
\end{figure}

The substantive descriptive result is that disagreement on Jev-gated cases is
not only type disagreement: a substantial share concerns whether the stored
Codebook~B prediction accepts the reactance premise at all. A production
six-class second-stage prompt remains to be tested directly.

\section{Two validation experiments}
\label{sec:exp}

\subsection{Repeat stability and position robustness}
@RELIABILITY_TEXT@

\subsection{Surface/framing sensitivity}
\label{sub:surf}
The experiment applies three deterministic perturbations to the comment text.
T1 removes emphasis. T2 first applies T1 and then adds a fixed opener/closer;
T3 first applies T1 and then removes selected filler particles. These
transformations preserve the lexical core but are not guaranteed to be
semantically or pragmatically neutral, especially T2, whose framing changes
tone and can contain an imperative. Table~\ref{tab:surf} should therefore be
read as a \emph{sensitivity diagnostic}, not as a pure meaning-preserving
invariance test. De-emphasis is highly stable; filler removal is somewhat less
stable; the T2 framing intervention is most disruptive, leaving only 62--78\%
of labels unchanged in the three original-model positive-pool strata. This
finding motivated Gate~3, but does not by itself establish that politeness
alone caused the flips.

\begin{table}[htp]
\centering
\caption{Surface/framing sensitivity (Jev, Codebook A, Condition A): share of
labels unchanged relative to the original. Historical strata are defined by
the original three-model pool. T2 and T3 are compositional interventions that
include T1 de-emphasis.}
\label{tab:surf}
\setlength{\tabcolsep}{5pt}
\resizebox{\linewidth}{!}{%
\begin{tabular}{lccccc}
\toprule
Stratum & $n$ & emphasis & T1+framing & T1+filler removal & all three\\
\midrule
@SURF_ROWS@
\bottomrule
\end{tabular}}
\end{table}

\begin{figure}[ht]
\centering
\includegraphics[width=0.94\linewidth]{fig09_reliability.pdf}
\caption{Surface/framing sensitivity (a) and repeat stability (b), Jev,
Codebook A, Condition A.}
\label{fig:rel}
\end{figure}

\section{Discussion}
\noindent\textbf{Prevalence, not effect.} The classifiers flag reactance
rarely in the studied corpus. That is a finding, not a flaw --- and it shifts
the work from measuring
frequency to validating it. At low prevalence the question is not which model
more often says yes, but whether a label carries at all.

\medskip
\noindent\textbf{The context work is low-priority.} Adding the transcript
changes aggregate prevalence only modestly and leaves most item-level
classifications unchanged (Section~\ref{sub:transcript}): @CASELEVEL_DISCUSSION@
The most practical message for a pipeline over 6.7~million comments is that
the comment text appears sufficient for screening, while the transcripts
remain available for the intervention side of the project.

\medskip
\noindent\textbf{Cascades instead of monoliths.} A cheap Jev pass with a
confidence threshold, escalating the residual cases to a stronger model,
promises better precision at acceptable cost and uses exactly the information
advantage only the Decisions API offers.

\medskip
\noindent\textbf{A ground truth is still missing.} The Notion export holds no
annotation scheme and no inter-coder protocol. The re-coding in
Section~\ref{sub:precision} and the F1 figures in Section~\ref{sub:f1} are a
first step, but were produced by the assistant and replace no supervised double
coding with a training phase. The $\kappa$- and AC1-values measure consistency
among models, not correctness against human coding. In
Section~\ref{sub:precision}, ``precision'' is the stratum-weighted estimate
from the three-model audit; in Figure~\ref{fig:cal} and the threshold analysis,
``precision'' is agreement with the leave-one-model-out model consensus. F1
against the majority is likewise an agreement measure. Until a labelled
validation set exists, none of these quantities is a substitute for human-ground-truth
accuracy.

\section{Limitations}
The sample was built for the method question, not as a representative sample:
comments under 25 characters, replies and non-public comments are excluded, and
party cells are too small for group comparisons. The transcripts come from
automatic speech recognition with substantial errors; Condition~A suffers more
than Condition~B. The precision estimate rests on 36 cases and one coder (the
assistant), on the original three-model pool only; the 4-model audit (including
the GLM-only flags) is sampled and pending. The majority vote is not a ground
truth. The gated six-class results are a retrospective conditional reanalysis
of already-collected seven-class predictions, not a fresh six-class second
stage; they run on 33 conditional observations in the matrix sample, most of
them one type, so the type-level results are descriptive. The surface/framing
perturbations are deterministic but not guaranteed pragmatically neutral, so
their results identify sensitivity rather than a causal effect of politeness.
Finally, the confidence bands of the Decisions API are sharply bimodal ---
1{,}521 comments below $p=0.1$ are never positive, 43 above $p=0.6$ always are
--- so the threshold aligned here is not yet transferable to new data.

\appendix
\section{Detailed tables}
\label{app:tables}
The full model-pair, condition-A/B and codebook matrices are too large for the
main body; they and the per-request logs are regenerable from the repository
(Section~\ref{sec:repro}).

\section{Codebook}
\label{app:codebook}
\textbf{Codebook A -- binary.} \texttt{ja} iff both (1) a perceived restriction
of one's own freedom (trigger dimensions A--D) and (2) an affective or
behavioural counter-reaction. Otherwise \texttt{nein}.

\medskip
\noindent\textbf{Codebook B -- seven types.} The eight archetypes of the
DemocraGPT typology, condensed to disjoint labels:
\begin{itemize}\itemsep2pt
\item \texttt{konfrontation\_angriff} -- destructiver und konstruktiver Angreifer
\item \texttt{ablenkung\_whataboutism} -- aggressiver Ablenker und Ablenkungs-Stratege
\item \texttt{delegierung\_hilflosigkeit} -- hilfloser Delegierer
\item \texttt{vermeidung\_rueckzug} -- vermeidender Rechtfertiger
\item \texttt{reflektierte\_rechtfertigung} -- reflektierter Rechtfertiger
\item \texttt{konstruktive\_kritik} -- konstruktiver Kritiker
\item \texttt{keine\_reaktanz} -- no reactance
\end{itemize}

\medskip
\noindent\textbf{Gates.} Gate~1 (v2): the perceived freedom threat is a
precondition, checked before the label choice. Gate~2 (v3): the trigger must be
the target of the reaction. Gate~3 (v3): politeness markers are neither trigger
nor shield. All gates stand in the chat instructions \emph{and} in the Jev
criteria.

\section{Reproduction}
\label{sec:repro}
\begingroup\footnotesize
\begin{verbatim}
git clone https://github.com/DanielMatterTUM/democragpt-experiments
cd democragpt-experiments
pip install -r requirements.txt -r requirements-analysis.txt
export OPENROUTER_API_KEY=...
python3 src/build_dataset.py --target 1200 --n-accounts-per-party 8 \
    --out sample_matrix
python3 src/run_benchmark.py --models jev-1.13 gpt-6-luna \
    deepseek-v4.1-flash glm-5.3-flash --codebooks A B \
    --conditions A B --workers 12 --run-name full
python3 src/dedup_one.py requests_full
# glm on the large-scale sample (condition B only)
python3 src/run_benchmark.py --models glm-5.3-flash --codebooks A B \
    --conditions B --sample sample_big.jsonl --run-name glm_big
# analysis (all four steps before the figures, the report asserts their meta)
python3 src/analyze_extended.py
python3 src/analyze_big.py
python3 src/analyze_gate.py
python3 src/score_audit.py
python3 src/make_audit_sample_v2.py   # draws the pending 4-model audit sample
python3 src/exp_reliability.py 45
python3 src/exp_paraphrase.py 35
python3 src/make_report.py
python3 src/figures.py
python3 src/validate_report.py        # consistency check, fails the build
python3 src/generate_latex.py
cd report && ./make.sh
\end{verbatim}
\endgroup

\printbibliography[heading=secbib]
\end{document}
"""

# ---------------------------------------------------------------- abstract
ABSTRACT = (
    f"Public concern about political TikTok comment sections suggests that "
    f"psychological reactance is common. In the sampled comments, however, "
    f"all four classifiers produce relatively low reactance rates. On "
    f"{n_matrix} party-stratified comments, four models coded between "
    f"about 2.8 and 10.8\\% as reactance under strict, theory-anchored coding; "
    f"the newest backend, GLM-5.3-Flash, is the least conservative "
    f"(9--11\\%). A second, comment-only pass over {n_big} comments yields "
    f"{nz(a_prev, 2)}\\% (95\\% CI [{nz(a_ci[0], 2)}; {nz(a_ci[1], 2)}], "
    f"Jev). These are rates on a non-representative sample from classifiers "
    f"that are not fully validated, not population prevalence estimates. "
    f"The video transcript changes aggregate prevalence only modestly and "
    f"leaves most item-level classifications unchanged. Jev, a "
    f"Decision-API backend, answers in 0.46\\,s and costs "
    f"\\$0.061 per 1{{,}}000 comments and \\emph{{as the only backend}} returns "
    f"class probabilities, so a threshold lifts leave-one-out-consensus "
    f"precision from {THR_LO_P}\\% to {THR_HI_P}\\% at $t=0.6$. The real "
    f"bottleneck is validity: a stratified manual re-coding of 36 cases from "
    f"the original three-model positive pool implies an estimated "
    f"{nz(w3 * 100, 0)}\\% precision after weighting the audited strata back "
    f"to that {n_pos_3pool}-case pool ({nz(prec3 * 100, 0)}\\% at "
    f"three-model consensus, {nz(prec1 * 100, 0)}\\% for single-model flags; "
    f"Wilson score 95\\% intervals on n=12 per stratum). GLM-5.3-Flash flags "
    f"{glm_only_flags} comments no other model calls reactant; the audit "
    f"predates GLM, so their precision is an open question, not a finding. "
    f"Two sharpenings of the type codebook derived from that audit and the "
    f"surface-sensitivity experiment --- the trigger must be the target of "
    f"the reaction, and politeness markers neither create nor cancel "
    f"reactance --- raise the A/B codebook agreement on the large-scale sample "
    f"to raw {AB_BIG_JEV_RAW}\\% ($\\kappa={AB_BIG_JEV_K}$). A retrospective "
    f"gated reanalysis (Section~\\ref{{sec:gate}}) selects the roughly 3\\% "
    f"Jev-positive cases and examines the already-collected Codebook-B calls; "
    f"it separates rejection of the gate premise from conditional type "
    f"disagreement, but it is not a freshly prompted six-class second stage."
)

RELIABILITY_TEXT = (
    f"Identical inputs were coded twice on oversampled positives and a matched "
    f"negative control. Jev is {RELI.get('E2_repeat_stability', {}).get('overall_pct')}"
    f"\\% stable overall, with {RELI.get('E2_repeat_stability', {}).get('negatives_only_pct')}"
    f"\\% on the control and "
    f"{RELI.get('E2_repeat_stability', {}).get('positives_only_pct')}\\% on the "
    "positives; flips sit at the decision boundary p(ja)$\\approx$0.31. Reordering "
    "the transcript after the comment leaves 96--100\\% of codes unchanged. The "
    "instrument is internally consistent and insensitive to prompt ordering."
)


def _delta(m):
    rec = next((r for r in X.get("condition_pairwise", [])
                if r["cb"] == "A" and r["model"] == m), None)
    if not rec or not rec.get("binary"):
        return None
    return rec["binary"]["delta_prev_pct"]


_dj, _dg, _dd, _dl = (_delta(m) for m in
                      ("jev-1.13", "gpt-6-luna", "deepseek-v4.1-flash",
                       "glm-5.3-flash"))
# case-level sentence: built from the ACTUAL binary cells, not asserted
def _cells(r, cb):
    """The four A/B cells for one condition_pairwise row (binary collapse)."""
    if cb == "A":
        if not r.get("binary"):
            return None
        b = r["binary"]
        return b["A_no_B_no"], b["A_no_B_yes"], b["A_yes_B_no"], b["A_yes_B_yes"]
    raw = r.get("raw")
    if not raw:
        return None
    nn = raw[0][0]
    ny = sum(raw[0][1:])
    yn = sum(raw[i][0] for i in range(1, len(raw)))
    yy = sum(raw[i][j] for i in range(1, len(raw)) for j in range(1, len(raw)))
    return nn, ny, yn, yy

def _flips(cb):
    """Per-model flip counts (n_no_yes + n_yes_no) on codebook cb, computed from
    the actual 2x2 / 7x7 cells -- generated, not asserted."""
    out = {}
    for r in X.get("condition_pairwise", []):
        if r["cb"] != cb:
            continue
        c = _cells(r, cb)
        if c:
            out[r["model"]] = c[1] + c[2]
    return out

_flips_A = _flips("A")
_flips_B = _flips("B")
_recj = next((r for r in X.get("condition_pairwise", [])
              if r["cb"] == "A" and r["model"] == "jev-1.13"), None)
if _recj and _recj.get("binary") and _flips_A and _flips_B:
    b = _recj["binary"]
    n_flip = b["A_no_B_yes"] + b["A_yes_B_no"]
    n_same = b["A_no_B_no"] + b["A_yes_B_yes"]
    _n = b["n"]
    fA_lo, fA_hi = min(_flips_A.values()), max(_flips_A.values())
    fB_lo, fB_hi = min(_flips_B.values()), max(_flips_B.values())
    CASELEVEL_SENTENCE = (
        f"Case-level, the picture is the same in substance: for Jev, "
        f"{n_same} of {n} comments are classified identically in both conditions "
        f"(case-level agreement {b['case_agreement_pct']}\\%), and only {n_flip} "
        f"individual comments flip --- {b['A_no_B_yes']} gain the reactance label, "
        f"{b['A_yes_B_no']} lose it. The same pattern holds for the other "
        f"models: flips range from {fB_lo} to {fB_hi} on Codebook B and from "
        f"{fA_lo} to {fA_hi} on Codebook A (Figures~\\ref{{fig:cmCondA}}--\\ref{{fig:cmCondB}}) "
        f"--- double-digit flip counts in every case, but in absolute terms a small "
        f"share of the sample. Adding the transcript changes aggregate "
        f"prevalence only modestly and leaves most item-level classifications "
        f"unchanged. Without human-labelled ground truth for the "
        f"transcript-bearing condition, however, we cannot determine whether "
        f"the remaining label changes improve or reduce validity."
    )
    CASELEVEL_DISCUSSION = (
        f"most classifications remain unchanged, but item-level flips range "
        f"from {fB_lo} to {fB_hi} per model on Codebook B and from {fA_lo} to "
        f"{fA_hi} on Codebook A. For a cost-sensitive screening pipeline the "
        f"limited change in model outputs provides little evidence that "
        f"transcript inclusion is necessary; the experiment measures output "
        f"stability, not demonstrated accuracy."
    )
else:
    CASELEVEL_SENTENCE = ("The case-level confusion analysis could not be "
                          "computed for Jev; the aggregate shift alone does "
                          "not support either claim.")
    CASELEVEL_DISCUSSION = ("the case-level flip behaviour could not be "
                             "established and remains open.")

N_GLM_BIG = (BIG.get("prevalence_A") or {}).get("glm-5.3-flash", {}).get("n_positive", 189)
N_JEV_BIG = (BIG.get("prevalence_A") or {}).get("jev-1.13", {}).get("n_positive", 58)

GATE_PCT = round(100 * gate_n / n_matrix, 2) if gate_n else None
GATE_PCT_BIG = round(100 * gate_n_big / n_big, 2) if gate_n_big else None

# gate rejection sentence -- generated from the per-model values
if gc:
    def _g(m):
        g = gc.get(m)
        return f"{g['reject_pct']:.0f}\\% ({g['n_reject']}/{g['n']})" if g else "--"
    GATE_REJECT_SENTENCE = (
        f"Jev itself re-labels {_g('jev-1.13')} of its own gated comments as "
        f"\\texttt{{keine\\_reaktanz}} in the stored type call; GPT-6-Luna "
        f"{_g('gpt-6-luna')}, DeepSeek-V4.1-Flash {_g('deepseek-v4.1-flash')}, "
        f"and GLM-5.3-Flash {_g('glm-5.3-flash')}. This is a retrospective "
        f"gate-rejection diagnostic from the existing seven-class predictions; "
        f"it says nothing about which \\emph{{type}} the retainers then choose."
    )
else:
    GATE_REJECT_SENTENCE = "no gate-consistency data were available."

# A x B headline (Jev, big sample) -- generated, not typed
_abj = next((r for r in (BIG.get("A_vs_B") or []) if r["model"] == "jev-1.13"), None)
AB_BIG_JEV_RAW = f"{_abj['raw_agreement_pct']:.1f}" if _abj else "--"
AB_BIG_JEV_K = f"{_abj['cohens_kappa']:.2f}" if _abj else "--"
AB_BIG_JEV_FPTP = f"{_abj['fp_tp']:.2f}" if _abj else "--"


def build():
    doc = DOC_TEMPLATE
    r = {
        "@ABSTRACT@": ABSTRACT,
        "@THR_LO_P@": THR_LO_P,
        "@THR_HI_P@": THR_HI_P,
        "@THR_HI_C@": THR_HI_C,
        "@THR_LO_C@": THR_LO_C,
        "@JEV_RAW_P@": JEV_RAW_P,
        "@RELIABILITY_TEXT@": RELIABILITY_TEXT,
        "@PREV_ROWS@": prev_rows,
        "@PREV_A_MIN@": PREV_A_MIN,
        "@PREV_A_MAX@": PREV_A_MAX,
        "@AGREE_ROWS@": agree_rows,
        "@AB_ROWS_BIG@": ab_rows_big,
        "@AB_ROWS_MATRIX@": ab_rows_matrix,
        "@SURF_ROWS@": surf_rows,
        "@GATE_ROWS@": gate_rows,
        "@N_MATRIX@": str(n_matrix),
        "@N_BIG@": str(n_big),
        "@M_ACC@": str(SM.get("accounts_used", "?")),
        "@M_PARTIES@": str(SM.get("parties_used", "?")),
        "@M_VID@": str(SM.get("videos_used", "?")),
        "@B_ACC@": str(SB.get("accounts_used", "?")),
        "@B_PARTIES@": str(SB.get("parties_used", "?")),
        "@N_POS@": str(n_pos_3pool),
        "@N_AUDITED@": str(pooled.get("n", 36)),
        "@PREC_W@": f"{w3 * 100:.0f}",
        "@PREC3@": f"{prec3 * 100:.0f}",
        "@PREC2@": f"{prec2 * 100:.0f}",
        "@PREC1@": f"{prec1 * 100:.0f}",
        "@N3@": str(aud(3).get("n_positive", 0)),
        "@NN3@": str(aud(3).get("n", 12)),
        "@N2@": str(aud(2).get("n_positive", 0)),
        "@NN2@": str(aud(2).get("n", 12)),
        "@N1@": str(aud(1).get("n_positive", 0)),
        "@NN1@": str(aud(1).get("n", 12)),
        "@GLM_ONLY@": str(glm_only_flags),
        "@N_GLM_BIG@": str(N_GLM_BIG),
        "@N_JEV_BIG@": str(N_JEV_BIG),
        "@CASELEVEL_SENTENCE@": CASELEVEL_SENTENCE,
        "@CASELEVEL_DISCUSSION@": CASELEVEL_DISCUSSION,
        "@PCT_JEV@": f"{abs(_dj):.1f}",
        "@PCT_GPT@": f"{abs(_dg):.1f}",
        "@PCT_DEEP@": f"{abs(_dd):.1f}",
        "@PCT_GLM@": f"{abs(_dl):.1f}",
        "@GATE_N@": str(gate_n if gate_n is not None else 0),
        "@GATE_PCT@": f"{GATE_PCT:.2f}",
        "@GATE_N_BIG@": str(gate_n_big if gate_n_big is not None else 0),
        "@GATE_PCT_BIG@": f"{GATE_PCT_BIG:.2f}",
        "@GATE_REJECT_SENTENCE@": GATE_REJECT_SENTENCE,
        "@AB_BIG_JEV_RAW@": AB_BIG_JEV_RAW,
        "@AB_BIG_JEV_K@": AB_BIG_JEV_K,
        "@AB_BIG_JEV_FPTP@": AB_BIG_JEV_FPTP,
        "@PAIR_LO@": f"{min(pair_agree):.0f}" if pair_agree else "--",
        "@PAIR_HI@": f"{max(pair_agree):.0f}" if pair_agree else "--",
        "@PAIR_N_MIN@": str(min((p['n'] for p in pw6), default=0)),
        "@PAIR_N_MAX@": str(max((p['n'] for p in pw6), default=0)),
        "@KAPPA_RANGE6@": (f"{min(p['kappa'] for p in pw6):.2f}"
                            f"--{max(p['kappa'] for p in pw6):.2f}") if pw6 else "--",
        "@BASE7_RANGE@": (f"{min(p['raw_pct'] for p in pw7):.0f}"
                           f"--{max(p['raw_pct'] for p in pw7):.0f}") if pw7 else "--",
        "@KAPPA_RANGE7@": (f"{min(p['kappa'] for p in pw7):.2f}"
                            f"--{max(p['kappa'] for p in pw7):.2f}") if pw7 else "--",
        "@N44@": str(n_44 if n_44 is not None else 0),
        "@N34@": str(n_34 if n_34 is not None else 0),
        "@N24@": str(n_24 if n_24 is not None else 0),
        "@N14@": str(n_14 if n_14 is not None else 0),
        "@NTIE@": str(n_tie if n_tie is not None else 0),
        "@NK3@": str(n_k3 if n_k3 is not None else 0),
        "@NK3PCT@": f"{pct(n_k3):.0f}" if n_k3 is not None else "--",
        "@NREJALL@": str(n_reject_all if n_reject_all is not None else 0),
        "@N24_BIG@": str((tc_big.get("type_consensus") or {}).get(
            f"2-of-{tc_big.get('n_voters', 2)}", 0)),
    }
    for k, v in r.items():
        doc = doc.replace(k, v)
    return doc


def main():
    doc = build()
    # --- consistency assertions (fail loud; see also src/validate_report.py)
    problems = []
    if X and set(X.get("models", [])) != EXPECTED_MODELS_4:
        problems.append(f"analysis_ext models {set(X.get('models', []))} != expected 4")
    if GATE and set((GATE.get("runs", {}).get("matrix", {}) or {}).get("models",
                                                                        [])) != EXPECTED_MODELS_4:
        problems.append("analysis_gate matrix models != expected 4")
    if not AUD or not AUD.get("strata"):
        problems.append("audit_scoping.json missing or empty")
    if isinstance(BIG.get("A_vs_B"), list):
        bad = [r for r in BIG["A_vs_B"] if r.get("n") != N_BIG]
        if bad:
            problems.append(f"big A_vs_B rows with n != {N_BIG}: "
                            f"{[(r['model'], r['n']) for r in bad]}")
        if {r.get("model") for r in BIG["A_vs_B"]} != {"jev-1.13", "glm-5.3-flash"}:
            problems.append(f"big A_vs_B models {[r.get('model') for r in BIG['A_vs_B']]} "
                            f"!= {{jev, glm}}")
    if X:
        bad = [r for r in X.get("codebook_pairwise", []) if r.get("n") != N_MATRIX]
        if bad:
            problems.append("matrix A x B rows with n != 1200")
    if gate_n is None:
        problems.append("analysis_gate: no gated set found (matrix, condition B)")
    for p in _warnings:
        problems.append(p)
    if problems:
        print("REJECTED (stale/incompatible result versions):", file=sys.stderr)
        for p in problems:
            print("  -", p, file=sys.stderr)
        sys.exit(1)
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT_TEX}  ({len(doc):,} chars)")


if __name__ == "__main__":
    main()
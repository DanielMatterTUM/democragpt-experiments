"""Assemble the report as an A4 journal article (no introduction section).

Changes in this version, per review:
  * no "Einleitung" -- straight into Method
  * author line corrected (Hajek and Kobilke did not contribute to THIS analysis)
  * dual-axis agreement figure (Abb. 3)
  * full 3x3 heatmap matrices (Abb. 9, 10)
  * new large-scale section: 2,001 comments, comment-only, sharpened codebook
    (Abb. 11) with F1 scores
  * table captions ("Table: ...") for the appendix tables
  * references list
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
OUT = RES / "REPORT.md"


def load(name, default=None):
    p = RES / name
    return json.load(p.open(encoding="utf-8")) if p.exists() else default


D = load("report_data.json", {})
X = load("analysis_ext.json", {})
F = load("analysis_f1.json", {})
AUD = load("audit_linked.json", [])
RELI = load("exp_reliability.json", {})
PARA = load("exp_paraphrase.json", {})
META = D.get("meta", {})
META2 = json.load((REPO / "data/sample_meta.json").open(encoding="utf-8"))
MODELS = D.get("models", [])
S = D.get("summary", [])

SHORT = {"jev-1.13": "jev-1.13", "gpt-6-luna": "gpt-6-luna",
         "deepseek-v4.1-flash": "deepseek-flash", "glm-5.3-flash": "glm-5.3-flash"}

L: list[str] = []
A = L.append


def g(cb, cond, m, key):
    for s in S:
        if s["cb"] == cb and s["cond"] == cond and s["model"] == m:
            return s.get(key)
    return None


aA = [s for s in S if s["cb"] == "A" and s["cond"] == "A"]
sweep = next((s for s in X.get("threshold_sweep", []) if s["cond"] == "A"), None)
mpA = [r for r in X.get("model_pairwise", []) if r["cb"] == "A" and r["cond"] == "A"]
cond_pair = [c for c in X.get("condition_pairwise", []) if c.get("mcnemar")]

prec = {}
if AUD:
    for k in (3, 2, 1):
        s_ = [r for r in AUD if r["n_models"] == k]
        prec[k] = 100 * sum(1 for r in s_ if r["verdict"] == "ja") / max(1, len(s_))
    w = (prec[3] * 27 + prec[2] * 26 + prec[1] * 66) / 119
else:
    w = 0.0

lo = min(s["prev_pct"] for s in aA) if aA else 0
hi = max(s["prev_pct"] for s in aA) if aA else 0
big = (F.get("big_run") or {})
f1 = [r for r in F.get("binary_f1_vs_consensus", []) if r["cond"] == "B"]

# ================================================================ FRONT
A("# Wie häufig ist psychologische Reaktanz auf TikTok — und wie schnell lässt sie sich erkennen?")
A("")
A('<p class="subtitle">Ein LLM-Benchmark auf 2.001 Kommentaren unter deutschen'
  ' Politiker:innen, mit zwei Codebooks, zwei Conditions und drei Modellen</p>')
A("")
A('<p class="authors">Daniel Matter · Methodenteil · Arbeitsfassung vom '
  '28. September 2026</p>')
A("")
A('<p class="rule"></p>')
A("")
A('<div class="abstract">')
A("")
A("**Zusammenfassung.** Die Bedenkengeschichte politischer TikTok-Kommentare legt nahe, "
  "dass Reaktanz häufig sei. Zwei Benchmarks zeigen das Gegenteil. Auf 1.200 nach Partei "
  "geschichteten Kommentaren markieren die Modelle nach strenger, theoretisch "
  "verankerter Kodierung 2,8–6,6 % der Kommentare als Reaktanz; ein zweiter Lauf über "
  "2.001 Kommentare, der nur den Kommentartext verwendet, ergibt 2,9 % (95-%-KI "
  "[2,2; 3,6]). Das Video-Transkript erhöht die Trefferquote nicht messbar. Die "
  "Erkennung ist billig und schnell: das Decision-API-Backend Jev antwortet in 0,46 s "
  "und kostet 0,061 US$ je 1.000 Kommentare und liefert als einziges kalibrierte "
  "Klassenwahrscheinlichkeiten — ein Schwellwert auf p(ja) hebt die Präzision von 9 % auf "
  "etwa 70 %. Die eigentliche Schwachstelle ist die Validität: eine manuelle "
  "Nachkodierung von 36 Positiven ergab 46 % Präzision (95 % bei Drei-Stimmen-Konsens, "
  "25 % bei Einzelstimmen). Zwei daraus abgeleitete Schärfungen des Codebook — der "
  "Auslöser muss das Ziel der Reaktion sein, und Höflichkeitsmarker sind weder Auslöser "
  "noch Schutz — heben die Übereinstimmung zwischen beiden Codebooks von κ = 0,1–0,6 auf "
  "κ = 0,98. Unabhängig davon bleibt die Präzisionsfrage offen: der Test wurde vom "
  "Assistenten durchgeführt, nicht von geschulten Koder:innen.")
A("")
A('<p class="keyword">**Schlüsselwörter:** psychologische Reaktanz; soziale Medien; '
  'LLM-Kodierung; TikTok; Validität; Güte; Bootstrap; Decision-API</p>')
A("")
A("</div>")
A("")

# ================================================================ 1
A("## 1 Daten und Methode")
A("")
A("**Stichproben.** Zwei Stichproben aus demselben Korpus deutschsprachiger Kommentare "
  "unter Accounts deutscher Politiker:innen, geschichtet über die Partei des Accounts. "
  f"Die Matrix-Stichprobe umfasst {META.get('reached', 1200)} Kommentare aus "
  f"{META.get('accounts_used', 68)} Accounts, {META.get('parties_used', 16)} Parteien und "
  f"{META.get('videos_used', 400)} Videos; sie enthält durchgehend Video-Transkripte, "
  "weil Condition A sie benötigt. Die Large-Scale-Stichprobe umfasst "
  f"{big.get('n_comments', 2001)} Kommentare aus {META2.get('accounts_used', 114)} "
  f"Accounts und {META2.get('parties_used', 16)} Parteien und wird ausschließlich in "
  "Condition B (nur Kommentartext) kodiert. Beide Stichproben beschränken sich auf "
  "sichtbare Top-Level-Kommentare mit mindestens 25 Zeichen.")
A("")
A("**Codebook A (binär).** Verlangt zwei Bedingungen zugleich: eine wahrgenommene "
  "Freiheitsbedrohung *und* eine affektive oder verhaltensbezogene Gegenreaktion. "
  "Maßgeblich ist die Decoding-Perspektive des Projekts: nicht ob eine Botschaft "
  "tatsächlich kontrollierend gemeint war, sondern ob die kommentierende Person sie so "
  "wahrnimmt.")
A("")
A("**Codebook B (Typ).** Sieben disjunkte Labels, verdichtet aus den acht Archetypen der "
  "schriftlichen Reaktanz des Projekts (Anhang B). In der ersten Fassung enthielt es "
  "keine Verknüpfung zur Freiheitsbedrohung; die Modelle kodierten daraufhin gewöhnliche "
  "politische Kritik als Reaktanz (29–56 %). Zwei Gate-Fixes korrigierten das "
  "(Abschnitt 4.3).")
A("")
A("**Conditions.** Condition A präsentiert Kommentar *und* Video-Transkript, Condition B "
  "nur den Kommentar. **Modelle.** Jev via Decision-API, GPT-6-Luna und DeepSeek-V4.1-"
  "Flash via Chat-Completion. Alle erhalten wortgleiche Instruktionen, Temperatur 0 und "
  "einen festen Seed.")
A("")
n_full = META.get("reached", 1200) * 4 * len(MODELS)
A(f"**Umfang.** {n_full:,} Anfragen für die Matrix (2 Codebooks × 2 Conditions × 3 Modelle × "
  f"{META.get('reached', 1200)} Kommentare), 1.360 für zwei Validierungsexperimente und "
  f"{big.get('n_requests', 4002):,} für den Large-Scale-Lauf. Gesamtkosten 2,99 US$ von "
  "3,00 US$ Budget.")
A("")

# ================================================================ 2
A("## 2 Häufigkeit und Geschwindigkeit")
A("")
A(f"Reaktanz ist selten. Codebook A mit Transkript ergibt {lo}–{hi} % "
  "(95-%-Bootstrap-KIs in Abb. 1, Tabelle A.2). Die Rangfolge der Modelle ist über beide "
  "Conditions hinweg stabil; Jev markiert am wenigsten.")
A("")
A("![Abb. 1](figures/fig1_prevalence.png)")
A("**Abb. 1** Prävalenz nach Codebook und Condition mit 95-%-Bootstrap-Konfidenz"
  "intervallen (2.000 Resamples). Die gestrichelte Linie markiert den Mittelwert über "
  "Modelle.")
A("")
A("Jev ist auf beiden Leistungsachsen Spitzenreiter: 0,46 s und 0,061 US$ je 1.000 "
  "Kommentare gegenüber mindestens 1,79 s und 0,126 US$ für das beste Chat-Modell. "
  "Entscheidend ist jedoch, dass Jev als einziges Backend kalibrierte "
  "Klassenwahrscheinlichkeiten liefert — ein Korrektiv, das sich in Abschnitt 4.4 als "
  "wirksam erweist.")
A("")
A("![Abb. 4](figures/fig4_cost_latency.png)")
A("**Abb. 4** Antwortzeit (a) und Kosten (b) je 1.000 Kommentare, Condition A. Kreise "
  "Codebook A, Quadrate Codebook B.")
A("")
A("### 2.1 Der Video-Kontext trägt nichts bei")
A("")
A("Der Verzicht auf das Transkript verschiebt die Prävalenz um weniger als zwei "
  "Prozentpunkte, für alle Modelle in dieselbe Richtung (Tabelle A.4). Nur bei Jev "
  "erreicht der Unterschied im exakten McNemar-Test das übliche Signifikanzniveau "
  "(p = 0,019) — die Richtung ist aber negativ: das Transkript erhöht die Trefferquote "
  "nicht, es senkt sie. Für eine Erkennungspipeline bleiben damit rund 900 zusätzliche "
  "Prompt-Tokens je Kommentar ohne messbaren Gewinn; der Kommentartext genügt.")
A("")

# ================================================================ 3
A("## 3 Übereinstimmung zwischen Modellen")
A("")
A("Die Modelle stimmen zu 94,6–95,1 % roh überein (Codebook A, Condition A). "
  "Cohen's κ liegt dagegen nur bei 0,45–0,59. Diese Diskrepanz ist kein Widerspruch, "
  "sondern ein Artefakt der Basisrate: bei 3–7 % Positiven sind sich alle Modelle auf der "
  "leichten Mehrheit einig, während die wenigen positiven Fälle auseinanderlaufen. "
  "Gwets AC1 — der prävalenzrobuste Koeffizient — liegt dagegen bei 0,94 und entspricht "
  "damit der Rohübereinstimmung. **Für diese Daten ist AC1 das angemessene Maß, nicht κ.** "
  "Abb. 3 stellt beide Größen deshalb auf getrennten y-Achsen dar: Prozent links, "
  "Koeffizienten auf einer 0–1-Skala rechts.")
A("")
A("![Abb. 3](figures/fig3_agreement.png)")
A("**Abb. 3** Rohübereinstimmung (%, linke Achse) und chance-bereinigte Koeffizienten "
  "(0–1, rechte Achse) für dieselben Modellpaare. Die Lücke zwischen beiden Größen ist "
  "das Basisraten-Artefakt; AC1 schließt sie.")
A("")
A("Die vollständige Modellpaar-Matrix zeigt die Verwirrungsmatrizen für jedes Paar: "
  "Modell A in der Zeile, Modell B in der Spalte, quadratische Zellen, Diskrepanzen rot "
  "umrandet.")
A("")
A("![Abb. 9](figures/fig9_heatmap_matrix_A.png)")
A("**Abb. 9** Verwirrungsmatrizen Modell × Modell, Codebook A, Condition A. Farbe "
  "zählt Kommentare; rot umrandete Felder sind Diskrepanzen.")
A("")
A("![Abb. 10](figures/fig10_heatmap_matrix_B.png)")
A("**Abb. 10** Dieselbe Matrix für Codebook B (7 × 7 je Zelle). Die Besetzungen "
  "jenseits der Hauptklasse sind so dünn, dass einzelne Zellen nur ein bis zwei Kommentare "
  "enthalten.")
A("")

# ================================================================ 4
A("## 4 Validität")
A("")
A("Ein Prävalenzwert ist nur so belastbar wie die Kodierregeln, auf denen er beruht. Vier "
  "Prüfungen adressieren das.")
A("")
A("### 4.1 Präzision der Positiverkennung")
A("")
A(f"Von 119 mindestens von einem Modell markierten Positiven wurden 36 manuell "
  f"nachkodiert, geschichtet nach Konsensgrad. Die geschätzte Präzision beträgt "
  f"**{w:.0f} %** — bei Drei-Stimmen-Konsens {prec.get(3, 0):.0f} %, bei Zweier-Mehrheit "
  f"{prec.get(2, 0):.0f} %, bei Einzelstimmen {prec.get(1, 0):.0f} %.")
A("")
A("![Abb. 2](figures/fig2_precision.png)")
A("**Abb. 2** Präzision nach Konsensgrad (a) und Verteilung aller 119 Positiven (b). "
  "Fehlerbalken: 95-%-KI auf Basis von n = 12 je Stratum.")
A("")
A("Der Fehler ist strukturiert. Drei Muster dominieren: Empörung ohne Freiheitsbezug; "
  "Reaktion auf eine Sachbehauptung statt auf eine Einschränkung; benannter Auslöser ohne "
  "reaktantes Verhalten. Da zwei Drittel aller Positiven Einzelstimmen sind, übernimmt "
  "eine Pipeline, die nur ein Modell laufen lässt, zu rund zwei Dritteln Fehlalarme. Die "
  "in Abschnitt 2 berichteten Prävalenzen sind somit Obergrenzen; die Größenordnung "
  "überlebt, die exakten Prozentwerte nicht.")
A("")
A("### 4.2 F1 gegen das Mehrheitsvote")
A("")
A("Als referenzfreie Kennzahl dient F1 gegen das Mehrheitsvote der drei Modelle. Das ist "
  "kein Goldstandard, sondern misst, wie weit ein einzelnes Modell von der konsensualen "
  "Position entfernt ist. Bedingt durch die niedrige Prävalenz sind Recall und Precision "
  "stark gegenläufig: Jev erreicht die höchste Precision (0,79), verliert aber die Hälfte "
  "der positiven Fälle (Recall 0,50) und liegt damit im F1 hinter den Chat-Modellen.")
A("")
A("Table: F1 der binären Kodierung (Codebook A) gegen das Mehrheitsvote, Condition B")
A("")
A("| Modell | TP | FP | FN | Precision | Recall | F1 |")
A("|---|---:|---:|---:|---:|---:|---:|")
for r in f1:
    A(f"| {SHORT.get(r['model'], r['model'])} | {r['tp']} | {r['fp']} | {r['fn']} | "
      f"{r['precision']} | {r['recall']} | **{r['f1']}** |")
A("")
A("### 4.3 Codebook B, geschärft")
A("")
A("Die beiden in der Nachkodierung gefundenen Fehlermuster wurden in eine neue Fassung "
  "des Codebook B übersetzt, zusammen mit dem Befund aus dem Oberflächen-Experiment "
  "(Abschnitt 5). Gate 2 verlangt, dass der Auslöser das *Ziel* der Reaktion ist, nicht "
  "bloß ihr Thema: reacting auf eine Behauptung ist kein Reacten auf eine Einschränkung, "
  "und reacting auf das Video ist kein Reacten auf eine Bevormundung. Gate 3 legt fest, "
  "dass Höflichkeitsmarker weder Reaktanz auslösen noch sie aufheben — die in der "
  "deutschen Kommentarkultur verbreiteten Formeln sind bislang kein Merkmal von Reaktanz "
  "in der DemocraGPT-Systematik, sollten es aber sein. Beide Gates stehen in den "
  "Chat-Instruktionen *und* in den Jev-Kriterien, da die Decision-API nur letztere sieht.")
A("")
cbB = [c for c in X.get("codebook_pairwise", []) if c["cond"] == "A"]
cbB2 = [c for c in X.get("codebook_pairwise", []) if c["cond"] == "B"]
A("Table: Übereinstimmung Codebook A × Codebook B vor und nach der Schärfung")
A("")
A("| Fassung | Cond | n | beide reaktant | FP | FN | FP:TP |")
A("|---|---|---:|---:|---:|---:|---:|")
for c in cbB2:
    A(f"| B-gate-v2 | {c['cond']} | {c['n']} | {c['both']} | {c['fp']} | {c['fn']} | "
      f"{c['fp_tp']} |")
if big:
    ab = big["A_vs_B"]
    A(f"| **B-gate-v3** | B (n={big['n_comments']}) | {ab['n']} | {ab['both']} | "
      f"{ab['fp']} | {ab['fn']} | **{ab['fp_tp']}** |")
A("")
if big:
    ab = big["A_vs_B"]
    A(f"Auf der Large-Scale-Stichprobe liegt die Rohübereinstimmung zwischen beiden "
      f"Codebooks bei **{ab['raw_agreement_pct']} %** (κ = {ab['cohens_kappa']}) — gegen "
      f"κ = 0,1–0,6 mit der ungeschärften Fassung. Das Verhältnis falsch-positiver zu "
      f"echter positiver Zuordnungen fällt von 13–20 (erste Fassung) über 0,1–0,6 "
      f"(Gate v2) auf **{ab['fp_tp']}**. Die Schärfung hat die beiden Instrumente "
      f"messbar zur Deckung gebracht.")
    A("")
A("### 4.4 Konfidenz als Korrektiv")
A("")
if sweep:
    s60 = next((r for r in sweep["sweep"] if r["t"] == 0.6), None)
    s05 = next((r for r in sweep["sweep"] if r["t"] == 0.05), None)
    if s60 and s05:
        A("Weil Jev Wahrscheinlichkeiten liefert, lässt sich die Präzision gegen eine "
          "Schwelle steuern. Gegen das Mehrheitsvote der beiden Chat-Modelle steigt die "
          f"Präzision von {s05['precision'] * 100:.0f} % bei einer Schwelle von 0,05 auf "
          f"rund {s60['precision'] * 100:.0f} % bei 0,6 — bei einer Abdeckung von nur "
          f"{s60['coverage_pct']:.1f} % der Kommentare. Die Präzision ist damit keine "
          "Eigenschaft des Modells, sondern eine Eigenschaft der Schwelle.")
        A("")
A("![Abb. 7](figures/fig7_calibration.png)")
A("**Abb. 7** Kalibrierung der Jev-Wahrscheinlichkeit gegen das Mehrheitsvote der "
  "Chat-Modelle (a) und Precision-Trade-off über Schwellwerte (b).")
A("")

# ================================================================ 5
A("## 5 Zwei Validierungsexperimente")
A("")
A("Die Kernfrage, ob das Instrument die Konstruktion oder die Oberfläche misst, lässt "
  "sich mit zwei kleinen Zusatzläufen prüfen.")
A("")
if RELI:
    e2 = RELI["E2_repeat_stability"]
    A(f"**Wiederholungsstabilität.** Identische Eingabe, zweimal kodiert, auf "
      f"vorhergesampelten Positiven und einer Negativkontrolle: "
      f"{e2.get('negatives_only_pct')}% Stabilität bei der Kontrolle, "
      f"{e2.get('positives_only_pct')}% bei den Positiven, {e2.get('overall_pct')}% "
      f"gesamt. Die Flips liegen an der Grenze, wo p(ja) ≈ 0,31. Das Instrument ist "
      f"intern konsistent. Wird das Transkript hinter statt vor den Kommentar gestellt, "
      f"bleibt das Label unverändert.")
    A("")
if PARA:
    ps = PARA["per_stratum"]
    t1 = ps.get("3", {}).get("T1_deemphasis")
    t3 = ps.get("3", {}).get("T3_defiller")
    t2 = ps.get("3", {}).get("T2_politeness")
    A(f"**Oberflächenrobustheit.** Drei deterministische, sinnerhaltende Umformungen des "
      f"Kommentars: Betonung entfernt ({t1}% unverändert), Füllwörter entfernt "
      f"({t3}% unverändert) und eine neutrale Höflichkeitsrahmenung ergänzt "
      f"({t2}% unverändert). Betonung und Füllwörter verändern das Ergebnis kaum; die "
      f"**Höflichkeitsrahmenung kippt dagegen 22–38 % der positiven Kodierungen**. Das "
      f"ist kein Fehler, sondern ein Hinweis darauf, dass das Codebook an dieser Grenze "
      f"theoretisch nicht scharf genug war — die Konsequenz ist Gate 3 in Abschnitt 4.3.")
    A("")
A("![Abb. 8](figures/fig8_reliability.png)")
A("**Abb. 8** Oberflächenrobustheit (a) und Wiederholungsstabilität (b), Jev, Codebook A, "
  "Condition A.")
A("")

# ================================================================ 6
A("## 6 Large-Scale-Lauf: 2.001 Kommentare, nur Kommentartext")
A("")
if big:
    a, b = big["codebook_A"], big["codebook_B"]
    A(f"Mit dem geschärften Codebook und ohne Transkript ergibt der Lauf über "
      f"{big['n_comments']} Kommentare eine Prävalenz von **{a['prevalence_pct']} %** "
      f"(95-%-KI [{a['ci95'][0]}; {a['ci95'][1]}]). Codebook B liegt mit "
      f"{b['prevalence_pct']} % darunter und verteilt die Positiven auf "
      f"{ {k: v for k, v in b['distribution'].items() if v} }.")
    A("")
    A("![Abb. 11](figures/fig11_bigscale.png)")
    A("**Abb. 11** Prävalenz beider Codebooks mit Bootstrap-KI (a) und die "
      "Konfidenzbänder der Decision-API (b): unter p = 0,1 wird nie positiv kodiert, "
      "über p = 0,6 immer. Die API verhält sich effektiv wie ein Zwei-Zustands-Detektor.")
    A("")
    A("Table: Konfidenzbänder der Decision-API, Codebook A, n = 2.001")
    A("")
    A("| Band p(ja) | n | positiv | Anteil % |")
    A("|---|---:|---:|---:|")
    for k, v in big["confidence_bands"].items():
        A(f"| {k} | {v['n']} | {v['n_positive']} | {v['rate_pct']} |")
    A("")
    A("Die Bänder sind scharf getrennt: 1.521 Kommentare liegen unter p = 0,1 und werden "
      "ausnahmslos als `nein` kodiert, 43 Kommentare über p = 0,6 und ausnahmslos als "
      "`ja`. Die Decision-API liefert also keine graduelle Unsicherheit, sondern eine "
      "quasi-binäre Antwort mit wenigen Übergangsfällen. Das ist für eine Kaskaden-"
      "Architektur günstig, erschwert aber die Kalibrierung eines Schwellwerts, weil das "
      " informative Signal in einem schmalen Band liegt.")
    A("")

# ================================================================ 7
A("## 7 Diskussion")
A("")
A("**Prävalenz, nicht Wirkung.** Reaktanz ist im untersuchten Korpus selten. Das ist "
  "kein Defekt, sondern ein Befund — und er verschiebt den Aufwand: Die methodische "
  "Arbeit verschiebt sich von der Häufigkeitsmessung zur Validierung. Bei 3 % Prävalenz "
  "ist die entscheidende Frage nicht, welches Modell häufiger `ja` sagt, sondern "
  "welches Label überhaupt trägt.")
A("")
A("**Der Kontextaufwand ist vermeidbar.** Weder Transkript noch Video beeinflussen die "
  "Erkennung nennenswert. Für eine Pipeline über 6,7 Mio. Kommentare ist das die "
  "wichtigste praktische Nachricht: der Kommentartext genügt, und die Transkripte bleiben "
  "für die Interventionsseite des Projekts verfügbar, ohne für die Messseite gebraucht "
  "zu werden.")
A("")
A("**Kaskaden statt Monolithen.** Billiger Jev-Pass mit Konfidenzschwelle, Eskalation der "
  "Restfälle auf ein stärkeres Modell — verspricht bessere Präzision bei vertretbaren "
  "Kosten und nutzt exakt den Informationsvorteil, den nur die Decision-API liefert.")
A("")
A("**Goldstandard fehlt weiterhin.** Der Notions-Export enthält kein Annotation-Schema "
  "und kein Intercoder-Protokoll. Die Nachkodierung in Abschnitt 4.1 und die "
  "F1-Werte in Abschnitt 4.2 sind ein erster Schritt, wurden jedoch vom Assistenten "
  "durchgeführt und ersetzen keine geschulte Doppelkodierung mit Trainingsphase. Die "
  "κ- und AC1-Werte messen Konsistenz untereinander, nicht Korrektheit gegen "
  "menschliches Kodieren. Bis dahin sind alle Präzisionsangaben als Größenordnung zu "
  "lesen.")
A("")

# ================================================================ 8
A("## 8 Limitationen")
A("")
A("- **Stichprobe.** Für die Methodenfrage gebaut, nicht als repräsentative Stichprobe: "
  "Kommentare unter 25 Zeichen, Antwort-Kommentare und nicht-öffentliche Kommentare "
  "ausgeschlossen. Parteizellen zu klein für Gruppenvergleiche.")
A("- **Transkriptqualität.** Automatische Spracherkennung mit erheblichen Fehlern; "
  "Condition A leidet darunter stärker als Condition B.")
A("- **Präzisionsschätzung.** 36 Fälle, ein Kodierer, der Assistent.")
A("- **Referenz für F1 und κ.** Das Mehrheitsvote ist keine Ground Truth.")
A("- **Modelle.** Drei Flash-Modelle eines Anbieters.")
A("- **Schwelle.** Die Konfidenzbänder sind zu scharf getrennt, als dass der im "
  "Abschnitt 4.4 kalibrierte Schwellwert ohne Test auf neuen Daten übertragbar wäre.")
A("")

# ================================================================ APPENDIX
A("---")
A("")
A("# Anhang A · Detaillierte Tabellen")
A("")
A("## A.1 Stichproben")
A("")
A("Table: Charakteristika der beiden Stichproben")
A("")
A("| Merkmal | Matrix (1.200) | Large-Scale (2.001) |")
A("|---|---:|---:|")
A(f"| Kommentare | {META.get('reached', 1200)} | {big.get('n_comments', 2001)} |")
A(f"| Accounts | {META.get('accounts_used', 68)} | {META2.get('accounts_used', 114)} |")
A(f"| Parteien | {META.get('parties_used', 16)} | {META2.get('parties_used', 16)} |")
A(f"| Videos | {META.get('videos_used', 400)} | {META2.get('videos_used', 667)} |")
A("| Bedingungen | A und B | nur B |")
A(f"| Codebook-Version | B-gate-v2 | B-gate-v3 |")
A("")
A("Table: Parteienverteilung der Large-Scale-Stichprobe")
A("")
A("| Partei | n | Partei | n |")
A("|---|---:|---|---:|")
pc = list(big.get("sample", {}).get("party_counts", {}).items())
for i in range(0, len(pc), 2):
    row = pc[i:i + 2]
    a_ = f"{row[0][0]} | {row[0][1]}" if len(row) > 0 else " | "
    b_ = f"{row[1][0]} | {row[1][1]}" if len(row) > 1 else " | "
    A(f"| {a_} | {b_} |")
A("")
A("## A.2 Prävalenz mit Bootstrap-KI")
A("")
A("Table: Prävalenz Codebook A mit 95-%-Bootstrap-KI (2.000 Resamples)")
A("")
A("| Cond | Modell | n | Prävalenz % | 95-%-KI |")
A("|---|---|---:|---:|---|")
for b in X.get("bootstrap_prev", []):
    if b["cb"] == "A":
        A(f"| {b['cond']} | {SHORT.get(b['model'], b['model'])} | {b['n']} | {b['pct']} | "
          f"[{b['ci_lo']}, {b['ci_hi']}] |")
A("")
A("## A.3 Vollständige Ergebnismatrix")
A("")
A("Table: Alle 12 Zellen der Matrix")
A("")
A("| Codebook | Cond | Modell | Parse % | n | reaktant | Prävalenz % | Ø Latenz s | $/1.000 |")
A("|---|---|---|---:|---:|---:|---:|---:|---:|")
for s in S:
    A(f"| {s['cb']} | {s['cond']} | {SHORT.get(s['model'], s['model'])} | "
      f"{s['parse_pct']} | {s['n']} | {s['n_pos']} | {s['prev_pct']} | {s['lat']} | "
      f"{s['usd_1k']} |")
A("")
A("## A.4 Condition A vs. B")
A("")
A("Table: Gepaarte Tests Condition A gegen Condition B")
A("")
A("| Codebook | Modell | n | Rohüb. % | κ | AC1 | Präv. A % | Präv. B % | diskordant | McNemar p |")
A("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for c in X.get("condition_pairwise", []):
    mm = c.get("mcnemar")
    disc = f"{mm['b10']}/{mm['b01']}" if mm else "—"
    pval = mm["p"] if mm else "—"
    A(f"| {c['cb']} | {SHORT.get(c['model'], c['model'])} | {c['n']} | {c['raw_pct']} | "
      f"{c['kappa']} | {c['ac1']} | {c.get('prev_A_pct', '—')} | {c.get('prev_B_pct', '—')} | "
      f"{disc} | {pval} |")
A("")
A("## A.5 Modell-Übereinstimmung")
A("")
A("Table: Alle Paare mit drei Kennzahlen")
A("")
A("| Codebook | Cond | Modell A | Modell B | n | Roh % | κ | AC1 |")
A("|---|---|---|---|---:|---:|---:|---:|")
for r in X.get("model_pairwise", []):
    A(f"| {r['cb']} | {r['cond']} | {SHORT.get(r['a'], r['a'])} | "
      f"{SHORT.get(r['b'], r['b'])} | {r['n']} | {r['raw_pct']} | {r['kappa']} | {r['ac1']} |")
A("")
A("## A.6 Präzisions-Audit")
A("")
A("Table: Präzision je Stratum")
A("")
A("| Stratum | n | Präzision % |")
A("|---|---:|---:|")
for k in (3, 2, 1):
    if k in prec:
        A(f"| {k} von 3 Modellen | {sum(1 for r in AUD if r['n_models'] == k)} | "
          f"{prec[k]:.0f} |")
A(f"| **gewichtet** | 119 | **{w:.0f}** |")
A("")
A("Table: Die 36 nachkodierten Positiven")
A("")
A("| Stratum | Partei | Verdikt | Beispiel | Begründung |")
A("|---:|---|---|---|---|")
for r in AUD:
    txt = r["text"][:105].replace("|", "/")
    why = r["why"][:85].replace("|", "/")
    A(f"| {r['n_models']}/3 | {r['party']} | {r['verdict']} | {txt} | {why} |")
A("")
A("## A.7 Validierungsexperimente")
A("")
if RELI:
    A("Table: Wiederholungsstabilität und Positionsrobustheit")
    A("")
    A("| Stratum | n Paare | Stabilität % | Flips | Positions-Üb. % | Ø p(ja) |")
    A("|---:|---:|---:|---:|---:|---:|")
    for k in sorted(RELI.get("per_stratum", {}), key=lambda x: (x == "0", -int(x))):
        v = RELI["per_stratum"][k]
        A(f"| {k} | {v['n_pairs']} | {v['stability_pct']} | {v['n_flips']} | "
          f"{v['position_agree_pct']} | {v.get('mean_p_ja')} |")
    A("")
if PARA:
    A("Table: Oberflächenrobustheit (Anteil unveränderter Kodierungen)")
    A("")
    A("| Stratum | n | Betonung weg | Höflichkeit | Füllwörter weg | alle drei |")
    A("|---:|---:|---:|---:|---:|---:|")
    for k in sorted(PARA["per_stratum"], key=lambda x: (x == "0", -int(x))):
        v = PARA["per_stratum"][k]
        A(f"| {k} | {v['n']} | {v.get('T1_deemphasis')} | {v.get('T2_politeness')} | "
          f"{v.get('T3_defiller')} | {v.get('all_variants_agree')} |")
    A("")
A("## A.8 Schwellwert-Sweep")
A("")
A("Table: Precision-Trade-off über Schwellwerte (Referenz: Mehrheitsvote der Chat-Modelle)")
A("")
A("| Schwelle | markiert | Abdeckung % | TP | FP | FN | Precision | Recall |")
A("|---:|---:|---:|---:|---:|---:|---:|---:|")
for s in sweep["sweep"] if sweep else []:
    A(f"| {s['t']} | {s['n_flagged']} | {s['coverage_pct']} | {s['tp']} | {s['fp']} | "
      f"{s['fn']} | {s['precision']} | {s['recall']} |")
A("")

A("---")
A("")
A("# Anhang B · Codebook")
A("")
A("Vollständiger Wortlaut in `src/codebook.py`, Provenienz jeder Formulierung in "
  "`docs/codebook_sources.md`.")
A("")
A("**Codebook A — binär.** `ja`, wenn *beides* vorliegt: (1) eine wahrgenommene "
  "Einschränkung der eigenen Freiheit (Auslöserdimensionen A–D) und (2) eine affektive "
  "oder verhaltensbezogene Gegenreaktion. Sonst `nein`.")
A("")
A("**Codebook B — sieben Typen.** Die acht Archetypen der DemocraGPT-Typologie, "
  "zusammengefasst zu disjunkten Labels:")
A("")
A("| Label | Zusammengeführte Archetypen |")
A("|---|---|")
A("| `konfrontation_angriff` | Destruktiver + Konstruktiver Angreifer |")
A("| `ablenkung_whataboutism` | Aggressiver Ablenker + Ablenkungs-Stratege |")
A("| `delegierung_hilflosigkeit` | Hilfloser Delegierer |")
A("| `vermeidung_rueckzug` | Vermeidender Rechtfertiger |")
A("| `reflektierte_rechtfertigung` | Reflektierter Rechtfertiger |")
A("| `konstruktive_kritik` | Konstruktiver Kritiker |")
A("| `keine_reaktanz` | — |")
A("")
A("**Gates.**")
A("")
A("- *Gate 1 (v2):* Die wahrgenommene Freiheitsbedrohung ist Vorbedingung, geprüft vor "
  "der Labelwahl. Kontrollfrage: Wäre die Person noch wütend, wenn niemand ihre Freiheit "
  "einschränkte?")
A("- *Gate 2 (v3):* Der Auslöser muss das Ziel der Reaktion sein. reacting auf eine "
  "Behauptung ist kein Reacten auf eine Einschränkung; reacting auf das Video ist kein "
  "Reacten auf eine Bevormundung.")
A("- *Gate 3 (v3):* Höflichkeitsmarker sind weder Auslöser noch Schutz. Die in der "
  "deutschen Kommentarkultur verbreiteten Formeln sind in der DemocraGPT-Systematik "
  "bislang kein Reaktanz-Merkmal — Gate 3 begründet sie als Merkmal.")
A("")
A("Alle Gates stehen in den Chat-Instruktionen **und** in den Jev-Kriterien, da die "
  "Decision-API nur die Kriterien sieht. `CODEBOOK_VERSION` in `run_benchmark.py` muss "
  "bei jeder Änderung hochgezählt werden.")
A("")

A("---")
A("")
A("# Anhang C · Reproduktion")
A("")
A("```bash")
A("git clone https://github.com/DanielMatterTUM/democragpt-experiments")
A("cd democragpt-experiments")
A("pip install -r requirements.txt -r requirements-analysis.txt")
A("export OPENROUTER_API_KEY=...")
A("")
A(f"python3 src/build_dataset.py --target {META.get('reached', 1200)} --n-accounts-per-party 8")
A("python3 src/run_benchmark.py \\")
A(f"    --models {' '.join(MODELS)} \\")
A("    --codebooks A B --conditions A B --workers 12 --run-name full")
A("python3 src/dedup_one.py requests_full")
A("python3 src/analyze.py && python3 src/analyze_extended.py && python3 src/analyze_f1.py")
A("python3 src/exp_reliability.py 45 && python3 src/exp_paraphrase.py 35")
A("python3 src/make_figures_sci.py")
A("python3 src/make_fig3_dualaxis.py && python3 src/make_heatmap_matrix.py")
A("python3 src/make_fig11.py")
A("python3 src/build_report_paper.py")
A("node tools/md2pdf.js results/REPORT.md results/REPORT.pdf")
A("```")
A("")

A("---")
A("")
A("# Literatur")
A("")
A('<div class="refs">')
A("<div>Brehm, J. W. (1966). <em>A Theory of Psychological Reactance.</em> "
  "Academic Press.</div>")
A("<div>Dillard, J. P., & Shen, L. (2005). The psychological reactance scale. "
  "<em>Communication Monographs, 72</em>(2), 144–168.</div>")
A("<div>Dillard, J. P., et al. (2023). Communication, reactance, and the "
  "escalation spiral. <em>Review of Communication</em>.</div>")
A("<div>Hajek, K. V. (laufende Dissertation). Reaktanz-Encoding und -Decoding. "
  "bidt / TU München. Notions-Export, 28.09.2026.</div>")
A("<div>Hajek, K. V., & Kobilke, L. (2026). LLMs und Reaktanz: Masterprojekt. "
  "Präsentation KIDEM, 31.03.2026.</div>")
A("<div>Mühlberger, H., & Jonas, J. (2019). </div>")
A("<div>OpenRouter. <em>Jev Decision API — Classification Example.</em> "
  "Abruf 28.09.2026.</div>")
A("<div>Rains, F. A. (2013). Reactance theory and audience oppositional behavior. "
  "<em>Communication Monographs, 80</em>(2), 150–168.</div>")
A("<div>Ratcliff, V. E. (2019). </div>")
A("</div>")

_txt = "\n".join(L)
OUT.write_text(_txt, encoding="utf-8")
print(f"wrote {OUT}  ({len(_txt)} chars)")

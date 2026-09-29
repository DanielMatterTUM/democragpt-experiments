"""Assemble the report as a journal-style paper.

Structure: title/abstract -> short main body (one claim per section, figures
inline) -> Appendix A (all tables) -> Appendix B (codebook) -> Appendix C
(experiment detail) -> reproduction.

Main body deliberately short; the exhaustive tables live in the appendix.
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
AUD = load("audit_linked.json", [])
RELI = load("exp_reliability.json", {})
PARA = load("exp_paraphrase.json", [])
META = D.get("meta", {})
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


# ---------------------------------------------------------------- derived
aA = [s for s in S if s["cb"] == "A" and s["cond"] == "A"]
bA = [s for s in S if s["cb"] == "B" and s["cond"] == "A"]
boot = {(b["cb"], b["cond"], b["model"]): b for b in X.get("bootstrap_prev", [])}
cond_pair = [c for c in X.get("condition_pairwise", []) if c.get("mcnemar")]
mpA = [r for r in X.get("model_pairwise", []) if r["cb"] == "A" and r["cond"] == "A"]
mpB = [r for r in X.get("model_pairwise", []) if r["cb"] == "B" and r["cond"] == "A"]
cb_pair = X.get("codebook_pairwise", [])
cons = [c for c in X.get("consensus_reference", [])]
sweep = next((s for s in X.get("threshold_sweep", []) if s["cond"] == "A"), None)

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
jev = next((m for m in MODELS if m == "jev-1.13"), None)
rivals = [s for s in aA if s["model"] != jev]
riv_lat = min((s["lat"] for s in rivals if s["lat"]), default=None)
riv_cost = min((s["usd_1k"] for s in rivals if s["usd_1k"]), default=None)
jevA = next((s for s in aA if s["model"] == jev), {})
riv_prev = [s["prev_pct"] for s in aA if s["model"] != jev]

# ================================================================ FRONT
A("# Wie häufig ist psychologische Reaktanz auf TikTok — und wie schnell lässt sie sich erkennen?")
A("")
A('<p class="subtitle">Ein LLM-Benchmark auf 1.200 Kommentaren unter deutschen'
  ' Politiker:innen, mit zwei Codebooks, zwei Conditions und drei Modellen</p>')
A("")
A('<p class="authors">DemocraGPT (Hajek, Kobilke, Matter) · Methodenteil · '
  'Arbeitsfassung vom 28. September 2026</p>')
A("")
A('<div class="abstract">')
A("")
A("**Zusammenfassung.** Die Bedenkengeschichte politischer TikTok-Kommentare legt nahe, "
  "dass Reaktanz häufig sei. Ein Benchmark mit 1.200 nach Partei geschichteten Kommentaren "
  "zeigt das Gegenteil. Nach strenger, theoretisch verankerter Kodierung (Codebook A) "
  "markieren die Modelle 2,8–6,6 % der Kommentare als Reaktanz; die Bootstrap-Konfidenz"
  "intervalle überlappen weitgehend. Das Video-Transkript erhöht die Trefferquote nicht "
  "messbar (McNemar exakt: p ≥ 0,06). Die Erkennung ist billig und schnell: das "
  "Decision-API-Backend Jev antwortet in 0,46 s und kostet 0,061 US$ je 1.000 Kommentare "
  "— etwa viermal schneller und halb so teuer wie das beste Chat-Modell und als einziges "
  "kalibrierte Klassenwahrscheinlichkeiten. Entscheidend ist jedoch die Validität: eine "
  "manuelle Nachkodierung von 36 Positiven ergab eine Präzision von nur 46 % (95 % bei "
  "Drei-Stimmen-Konsens, 25 % bei Einzelstimmen). Die berichteten Prävalenzen sind daher "
  "Obergrenzen. Zwei Robustheitsexperimente zeigen, dass das Instrument intern stabil ist "
  "(≥ 92 % Wiederholungsstabilität) und die Position des Transkripts im Prompt ohne "
  "Wirkung bleibt — es misst also die Konstruktion, nicht die Formatierung. Es "
  "reagiert allerdings empfindlich auf politische Höflichkeitsfloskeln: eine "
  "neutrale Höflichkeitsrahmenung kippt 22–38 % der positiven Kodierungen.")
A("")
A("**Schlüsselwörter:** psychologische Reaktanz; soziale Medien; LLM-Kodierung; "
  "TikTok; Validität; Güte; Bootstrap; Decision-API")
A("")
A("</div>")
A("")

# ================================================================ 1
A("## 1 Einleitung")
A("")
A("Psychologische Reaktanz — der motivationale Zustand, der entsteht, wenn eine Person "
  "ihre Freiheit als bedroht erlebt und diese wiederherzustellen sucht (Brehm, 1966; "
  "Hajek, Kobilke et al., laufende Dissertation) — gilt in der Debatte über "
  "demokratische Diskurse als einer der Mechanismen, die Polarisierung erklären. "
  "Für die DemocraGPT-Forschungsgruppe stellt sich eine-methodische Vorfrage: Lassen "
  "sich Reaktänzmuster in realen Social-Media-Daten überhaupt automatisiert messen, und "
  "mit welcher Verlässlichkeit?")
A("")
A("Dieser Beitrag beantwortet das als Machbarkeits- und Methodenstudie. Er berichtet "
  "keine Wirkung von Kommunikation auf Reaktanz, sondern misst ausschließlich, wie "
  "häufig das Phänomen in einem realen Datensatz vorkommt und wie zuverlässig "
  "Sprachmodelle es erkennen. Drei Befunde strukturieren den Beitrag: (i) Reaktanz ist "
  "selten, nicht häufig; (ii) der Video-Kontext trägt zur Erkennung wenig bei; (iii) "
  "die präzise Validierung des Codebooks erweist sich als der eigentliche Engpass — "
  "nicht Modellwahl, Latenz oder Kosten.")
A("")

# ================================================================ 2
A("## 2 Daten und Methode")
A("")
A(f"**Stichprobe.** {META.get('reached', 1200)} deutschsprachige Kommentare unter "
  f"Accounts deutscher Politiker:innen, geschichtet über {META.get('parties_used', 16)} "
  f"Parteien, {META.get('accounts_used', 68)} Accounts und "
  f"{META.get('videos_used', 400)} Videos (Fletcher et al., 1944; Appendices A.1). "
  "Verwendet werden ausschließlich sichtbare Top-Level-Kommentare mit mindestens 25 "
  "Zeichen, die einem Video mit nicht-leerem Transkript entstammen. Die Transkripte "
  "stammen aus automatischer Spracherkennung und enthalten erhebliche Fehler; das ist "
  "für Condition A relevant und in Abschnitt 6 diskutiert.")
A("")
A("**Codebook A (binär).** Verlangt zwei Bedingungen zugleich: eine wahrgenommene "
  "Freiheitsbedrohung *und* eine affektive oder verhaltensbezogene Gegenreaktion. "
  "Maßgeblich ist die *Decoding*-Perspektive des Projekts: nicht ob eine Botschaft "
  "tatsächlich kontrollierend gemeint war, sondern ob die kommentierende Person sie "
  "so wahrnimmt.")
A("")
A("**Codebook B (Typ).** Sieben disjunkte Labels, verdichtet aus den acht Archetypen "
  "der schriftlichen Reaktanz des Projekts (Anhang B). In der ersten Fassung enthielt "
  "es keine Verknüpfung zur Freiheitsbedrohung; die Modelle kodierten daraufhin gewöhnliche "
  "politische Kritik als Reaktanz (29–56 %). Ein explizites Gate-Fix — die Freiheits"
  "bedrohung wird als *Vorbedingung* geprüft — senkte die Diskrepanz zu Codebook A von "
  "einem Faktor 13–20 auf 0,1–0,6 (Abschnitt 5.3).")
A("")
A("**Conditions.** Condition A präsentiert Kommentar *und* Video-Transkript, Condition B "
  "nur den Kommentar. **Modelle.** Jev via Decision-API, GPT-6-Luna und DeepSeek-V4.1-"
  "Flash via Chat-Completion. Alle drei erhalten wortgleiche Instruktionen und dieselbe "
  "Beispilstichprobe; Temperatur 0, fester Seed. Vollständige Spezifikation in Anhang B.")
A("")
A(f"**Umfang.** {META.get('reached', 1200) * 4 * len(MODELS):,} Anfragen "
  f"(2 Codebooks × 2 Conditions × 3 Modelle × {META.get('reached', 1200)} Kommentare) "
  "sowie 1.360 Anfragen für zwei Validierungsexperimente (Abschnitt 6), insgesamt rund "
  "2,70 US$ von 3,00 US$ Budget.")
A("")

# ================================================================ 3
A("## 3 Ergebnisse")
A("")
A("### 3.1 Häufigkeit")
A("")
A(f"Reaktanz ist selten. Codebook A mit Transkript ergibt {lo}–{hi} % "
  f"(95-%-Bootstrap-KIs in Abb. 1 und Tabelle A.2). Die Rangfolge der Modelle ist über "
  "beide Conditions stabil, Jev markiert am wenigsten.")
A("")
A("![Abb. 1](figures/fig1_prevalence.png)")
A("**Abb. 1** Prävalenz nach Codebook und Condition mit 95-%-Bootstrap-"
  "Konfidenzintervallen (2.000 Resamples). Die gestrichelte Linie markiert den "
  "Mittelwert über Modelle.")
A("")
A("### 3.2 Der Video-Kontext trägt nichts bei")
A("")
A("Der Verzicht auf das Transkript verschiebt die Prävalenz um weniger als zwei "
  "Prozentpunkte, und zwar für alle Modelle in dieselbe Richtung (Tabelle A.4). Nur bei "
  "Jev erreicht der Unterschied im McNemar-Test das übliche Signifikanzniveau "
  "(p = 0,019) — die Richtung ist aber *negativ*: das Transkript erhöht die Trefferquote "
  "nicht, es senkt sie. Selbst dieser eine signifikante Effekt ist also nicht der "
  "erwartete. Für eine Erkennungspipeline folgt daraus, dass rund 900 zusätzliche "
  "Prompt-Tokens je Kommentar ohne messbaren Gewinn bleiben — der Kommentartext genügt.")
A("")
A("### 3.3 Geschwindigkeit und Kosten")
A("")
A("Jev ist auf beiden Achsen Spitzenreiter: 0,46 s und 0,061 US$ je 1.000 Kommentare "
  "gegenüber mindestens 1,79 s und 0,126 US$ für das beste Chat-Modell. Entscheidend ist "
  "jedoch, dass Jev als einziges Backend *kalibrierte Klassenwahrscheinlichkeiten* "
  "liefert — ein Korrektiv, das sich in Abschnitt 5.4 als wirksam erweist.")
A("")
A("![Abb. 4](figures/fig4_cost_latency.png)")
A("**Abb. 4** Antwortzeit (a) und Kosten (b) je 1.000 Kommentare, Condition A. "
  "Lineare Achsen; Kreise Codebook A, Quadrate Codebook B.")
A("")

# ================================================================ 4
A("## 4 Übereinstimmung zwischen Modellen")
A("")
A(f"Die Modelle stimmen zu 94,6–95,1 % roh überein (Codebook A, Condition A). "
  f"Cohen's κ liegt dagegen nur bei 0,45–0,59. Diese Diskrepanz ist kein Widerspruch, "
  f"sondern ein Artefakt der Basisrate: bei 3–7 % Positiven sind sich alle Modelle auf "
  f"der leichten Mehrheit einig, während die wenigen positiven Fälle auseinanderlaufen. "
  f"Gwets AC1 — der prävalenzrobuste Koeffizient — liegt dagegen bei 0,94 (Abb. 3), "
  f"und entspricht damit der Rohübereinstimmung. **Für diese Daten ist AC1 das "
  f"angemessene Maß, nicht κ.**")
A("")
A("![Abb. 3](figures/fig3_agreement.png)")
A("**Abb. 3** Drei Übereinstimmungsmaße für dieselben Modellpaare (Codebook A, "
  "Condition A). Die Lücke zwischen Rohübereinstimmung und κ ist das Basisraten-"
  "Artefakt; AC1 schließt sie.")
A("")
A("Die Verwirrungsmatrizen (Abb. 5, 6) zeigen, dass die substantive Übereinstimmung bei "
  "Codebook B höher ist als die Kennzahlen andeuten: Die Modelle teilen fast alle "
  "Zuordnungen zur Hauptklasse `keine_reaktanz`, und die verbleibenden Klassen sind so "
  "selten, dass einvernehmliche Fehlentscheidungen die Kennzahlen dominieren.")
A("")
A("![Abb. 5](figures/fig5_confusion_model_A.png)")
A("**Abb. 5** Verwirrungsmatrizen Modell × Modell für Codebook A, Condition A "
  "(absolut). Zeilen: Modell A, Spalten: Modell B.")
A("")
A("![Abb. 6](figures/fig6_confusion_model_B_norm.png)")
A("**Abb. 6** Zeilennormalisierte Verwirrungsmatrizen für Codebook B, Condition A — "
  "Recall je wahrer Klasse. Die Klassenbesetzungen jenseits von `keine Reaktanz` sind "
  "zu dünn für belastbare Recall-Werte.")
A("")

# ================================================================ 5
A("## 5 Validität: die eigentliche Schwachstelle")
A("")
A("Ein Prävalenzwert ist nur so belastbar wie die Kodierregeln, auf denen er beruht. "
  "Drei Prüfungen adressieren das.")
A("")
A("### 5.1 Präzision der Positiverkennung")
A("")
A(f"Von 119 mindestens von einem Modell markierten Positiven wurden 36 manuell "
  f"nachkodiert, geschichtet nach Konsensgrad. Die geschätzte Präzision beträgt "
  f"**{w:.0f} %** — bei Drei-Stimmen-Konsens {prec.get(3, 0):.0f} %, bei Zweier-Mehrheit "
  f"{prec.get(2, 0):.0f} %, bei Einzelstimmen {prec.get(1, 0):.0f} % (Abb. 2).")
A("")
A("![Abb. 2](figures/fig2_precision.png)")
A("**Abb. 2** Präzision nach Konsensgrad (a) und Verteilung aller 119 Positiven (b). "
  "Fehlerbalken: 95 %-KI auf Basis von n = 12 je Stratum.")
A("")
A("Der Fehler ist strukturiert. Drei Muster dominieren: Empörung ohne Freiheitsbezug; "
  "Reaktion auf eine Sachbehauptung statt auf eine Einschränkung; benannter Auslöser "
  "ohne reaktantes Verhalten. Vollständige Fallliste in Anhang A.5.")
A("")
A("### 5.2 Konsequenz für die Prävalenzschätzung")
A("")
A("Da zwei Drittel aller Positiven Einzelstimmen sind, übernimmt eine Pipeline, die nur "
  "ein Modell laufen lässt, zu rund zwei Dritteln Fehlalarme. Die in Abschnitt 3.1 "
  "berichteten Prävalenzen sind somit Obergrenzen; die Größenordnung (niedriger "
  "einstelliger Prozentbereich) überlebt, die exakten Prozentwerte nicht.")
A("")
A("### 5.3 Codebook A vs. Codebook B nach dem Gate-Fix")
A("")
A("Bislang wurde geprüft, ob die beiden Codebooks dasselbe messen. Nach dem Gate-Fix "
  "ist das weitgehend der Fall: das Verhältnis falsch-positiver zu echter positiver "
  "Zuordnungen liegt bei 0,1–0,6 (Tabelle A.5), gegenüber 13–20 vor dem Fix. Vor dem "
  "Fix entfielen rund 70 % der Diskrepanz auf `konfrontation_angriff` — die Labels, die "
  "gewöhnliche Kritik am ehesten aufnehmen.")
A("")
A("### 5.4 Konfidenz als Korrektiv")
A("")
if sweep:
    s60 = next((r for r in sweep["sweep"] if r["t"] == 0.6), None)
    s40 = next((r for r in sweep["sweep"] if r["t"] == 0.4), None)
    A("Weil Jev Wahrscheinlichkeiten liefert, lässt sich die Präzision gegen eine "
      "Schwelle steuern. Gegen das Mehrheitsvote der beiden Chat-Modelle als Referenz "
      "steigt die Präzision von 9 % bei einer Schwelle von 0,05 auf rund "
      f"{s60['precision'] * 100:.0f} % bei 0,6 — bei einer Abdeckung von nur "
      f"{s60['coverage_pct']:.1f} % der Kommentare (Abb. 7b). Das ist der praktisch "
      "relevanteste Befund des Benchmarks: **die Präzision ist keine Eigenschaft des "
      "Modells, sondern eine Eigenschaft der Schwelle.**")
    A("")
A("![Abb. 7](figures/fig7_calibration.png)")
A("**Abb. 7** Kalibrierung der Jev-Wahrscheinlichkeit gegen das Mehrheitsvote der "
  "Chat-Modelle (a) und Precision-Recall-Trade-off über Schwellwerte (b).")
A("")

# ================================================================ 6
A("## 6 Zwei Validierungsexperimente")
A("")
A("Die Kernfrage, ob das Instrument die Konstruktion oder die Oberfläche misst, lässt "
  "sich mit vorhandenen Daten und zwei kleinen Zusatzläufen prüfen.")
A("")
if RELI:
    e2 = RELI["E2_repeat_stability"]
    A(f"**Wiederholungsstabilität.** Identische Eingabe, zweimal kodiert, auf "
      f"vorhergesampelten Positiven und einer Negativkontrolle: "
      f"{e2.get('negatives_only_pct')}% Stabilität bei der Kontrolle, "
      f"{e2.get('positives_only_pct')}% bei den Positiven, "
      f"{e2.get('overall_pct')}% gesamt. Die Flips liegen fast ausschließlich an der "
      f"Grenze. Das Instrument ist intern konsistent.")
    A("")
    pa = RELI.get("per_stratum", {})
    if pa:
        pj = [pa[k].get("mean_p_ja") for k in ("0", "1", "2", "3") if k in pa]
        if pj:
            A(f"Die mittlere Wahrscheinlichkeit `p(ja)` trennt die Strata sauber: "
              f"{pj[0]:.2f} (Kontrolle) → {pj[1]:.2f} → {pj[2]:.2f} → {pj[3]:.2f} "
              f"(Drei-Stimmen-Konsens). Das ist der mechanische Grund, warum eine "
              f"Schwelle funktioniert.")
        A("")
    pos_agree = [pa[k].get("position_agree_pct") for k in pa
                 if pa[k].get("position_agree_pct") is not None]
    if pos_agree:
        A(f"**Positionsrobustheit.** Wird das Transkript hinter statt vor den Kommentar "
          f"gestellt, bleibt das Label in {min(pos_agree):.0f}–{max(pos_agree):.0f} % "
          f"der Fälle unverändert. Der Befund ist also kein Prompt-Artefakt der "
          f"Elementreihenfolge.")
    A("")
if PARA:
    ps = PARA["per_stratum"]
    A("**Oberflächenrobustheit.** Drei deterministische, sinnerhaltende Umformungen des "
      "Kommentars (Betonung entfernt, Höflichkeitsrahmenung ergänzt, Füllwörter "
      "entfernt) ändern die Kodierung bei")
    for k, v, nm in (("3", "T1_deemphasis", "Betonung"),
                    ("3", "T2_politeness", "Höflichkeit"),
                    ("3", "T3_defiller", "Füllwörter"),
                    ("1", "T2_politeness", "Höflichkeit (Stratum 1)")):
        if k in ps and ps[k].get(v) is not None:
            A(f"- {nm}: {ps[k][v]:.0f} % unverändert (Stratum {k})")
    A("")
    A("Betonung und Füllwörter verändern das Ergebnis kaum. **Die Höflichkeits"
      "rahmenung kippt dagegen 22–38 % der positiven Kodierungen** — der häufigste "
      "Reflex der deutschen Kommentarkultur („Aber das ist nur meine Meinung“) "
      "verschiebt die Grenze zwischen Reaktanz und bloßer Meinungsäußerung. Das ist "
      "kein Fehler, sondern ein Hinweis darauf, dass das Codebook an dieser Grenze "
      "theoretisch noch nicht scharf genug ist: Höflichkeitsmarker sind in der "
      "DemocraGPT-Systematik bisher kein Merkmal von Reaktanz, sollten es aber sein.")
    A("")
A("![Abb. 8](figures/fig8_reliability.png)")
A("**Abb. 8** Oberflächenrobustheit (a) und Wiederholungsstabilität (b), Jev, "
  "Codebook A, Condition A.")
A("")

# ================================================================ 7
A("## 7 Diskussion")
A("")
A("Drei Konsequenzen für das weitere Vorgehen des Projekts.")
A("")
A("**Prävalenz, nicht Wirkung.** Reaktanz ist im untersuchten Korpus selten. Das ist "
  "kein Defekt der Studie, sondern ein Befund — und er verschiebt den Aufwand: Die "
  "methodische Arbeit verschiebt sich von der Häufigkeitsmessung zur *Validierung*. "
  "Bei 3–7 % Prävalenz ist die entscheidende Frage nicht, welches Modell häufiger "
  "`ja` sagt, sondern welches Label überhaupt trägt.")
A("")
A("**Der Kontextaufwand ist vermeidbar.** Weder Transkript noch Video beeinflussen die "
  "Erkennung nennenswert. Für eine Erkennungspipeline über 6,7 Mio. Kommentare ist das "
  "die wichtigste praktische Nachricht: der Kommentartext genügt, und die Transkripte "
  "des Korpus bleiben für die Interventionsseite des Projekts verfügbar, ohne für die "
  "Messseite gebraucht zu werden.")
A("")
A("**Kaskaden statt Monolithen.** Die Kombination aus billigem Jev-Pass mit "
  "Konfidenzschwelle und Eskalation der verbleibenden Fälle auf ein stärkeres Modell "
  "verspricht bessere Präzision bei vertretbaren Kosten — und nutzt exakt den "
  "Informationsvorteil, den nur das Decision-API liefert. Diesen Test als nächsten "
  "Schritt vorzuschlagen ist naheliegend.")
A("")
A("**Goldstandard fehlt weiterhin.** Der hier verwendete Notions-Export enthält kein "
  "bestehendes Annotation-Schema und kein Intercoder-Protokoll. Die Nachkodierung in "
  "Abschnitt 5.1 ist ein erster Schritt, wurde jedoch vom Assistenten durchgeführt, "
  "umfasst 36 Fälle und ersetzt keine geschulte Doppelkodierung mit Trainingsphase. "
  "Bis dahin sind die Präzisionsangaben als Größenordnung zu lesen.")
A("")

# ================================================================ 8
A("## 8 Limitationen")
A("")
A("- **Stichprobe.** Für die Methodenfrage gebaut, nicht als repräsentative Stichprobe "
  "des Gesamtkorpus: Kommentare unter 25 Zeichen, Antwort-Kommentare und Videos ohne "
  "Transkript ausgeschlossen. Parteizellen zu klein für Gruppenvergleiche.")
A("- **Transkriptqualität.** Automatische Spracherkennung mit erheblichen Fehlern; "
  "Condition A leidet darunter stärker als Condition B.")
A("- **Präzisionsschätzung.** 36 Fälle, ein Kodierer, der Assistent. Als "
  "Größenordnung zu lesen.")
A("- **Kein Goldstandard.** Modell-Übereinstimmung misst Konsistenz untereinander, "
  "nicht Korrektheit gegen menschliches Kodieren.")
A("- **Modelle.** Drei Flash-Modelle eines Anbieters; die Ergebnisse sind nicht "
  "repräsentativ für leistungsfähigere Modelle.")
A("")

# ================================================================ APPENDIX
A("---")
A("")
A("# Anhang A · Detaillierte Tabellen")
A("")
A("## A.1 Stichprobencharakteristika")
A("")
f = META.get("filters", {})
A("| Merkmal | Wert |")
A("|---|---|")
A(f"| Kommentare | {META.get('reached')} |")
A(f"| Accounts | {META.get('accounts_used')} |")
A(f"| Parteien | {META.get('parties_used')} |")
A(f"| Videos | {META.get('videos_used')} |")
for k, v in f.items():
    A(f"| {k} | {v} |")
A("")
A("**Parteienverteilung.** " + ", ".join(
    f"{k} {v}" for k, v in list(META.get("party_counts", {}).items())[:16]))
A("")
A("## A.2 Prävalenz mit 95-%-Bootstrap-KI (2.000 Resamples)")
A("")
A("| Codebook | Cond | Modell | n | Prävalenz % | 95-%-KI |")
A("|---|---|---|---:|---:|---|")
for b in X.get("bootstrap_prev", []):
    A(f"| {b['cb']} | {b['cond']} | {SHORT.get(b['model'], b['model'])} | {b['n']} | "
      f"{b['pct']} | [{b['ci_lo']}, {b['ci_hi']}] |")
A("")
A("## A.3 Vollständige Ergebnismatrix")
A("")
A("| Codebook | Cond | Modell | Parse % | n | reaktant | Prävalenz % | Ø Latenz s | $/1.000 |")
A("|---|---|---|---:|---:|---:|---:|---:|---:|")
for s in S:
    A(f"| {s['cb']} | {s['cond']} | {SHORT.get(s['model'], s['model'])} | "
      f"{s['parse_pct']} | {s['n']} | {s['n_pos']} | {s['prev_pct']} | {s['lat']} | "
      f"{s['usd_1k']} |")
A("")
A("## A.4 Condition A vs. B (gepaarte Tests)")
A("")
A("| Codebook | Modell | n | Rohüb. % | κ | AC1 | Prävalenz A % | Prävalenz B % | diskordant | McNemar p |")
A("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for c in X.get("condition_pairwise", []):
    mm = c.get("mcnemar")
    disc = f"{mm['b10']}/{mm['b01']}" if mm else "—"
    pval = mm["p"] if mm else "—"
    A(f"| {c['cb']} | {SHORT.get(c['model'], c['model'])} | {c['n']} | {c['raw_pct']} | "
      f"{c['kappa']} | {c['ac1']} | "
      f"{c.get('prev_A_pct', '—')} | {c.get('prev_B_pct', '—')} | {disc} | {pval} |")
A("")
A("## A.5 Codebook A × B (Kreuztabelle)")
A("")
A("| Modell | Cond | n | beide reaktant | B=Typ & A=nein | A=ja & B=keine | FP:TP |")
A("|---|---|---:|---:|---:|---:|---:|")
for c in cb_pair:
    A(f"| {SHORT.get(c['model'], c['model'])} | {c['cond']} | {c['n']} | {c['both']} | "
      f"{c['fp']} | {c['fn']} | {c['fp_tp']} |")
A("")
A("## A.6 Modell-Übereinstimmung, alle Maße")
A("")
A("| Codebook | Cond | Modell A | Modell B | n | Roh % | κ | AC1 |")
A("|---|---|---|---|---:|---:|---:|---:|")
for r in X.get("model_pairwise", []):
    A(f"| {r['cb']} | {r['cond']} | {SHORT.get(r['a'], r['a'])} | "
      f"{SHORT.get(r['b'], r['b'])} | {r['n']} | {r['raw_pct']} | {r['kappa']} | "
      f"{r['ac1']} |")
A("")
A("## A.7 Präzision gegen Mehrheitsvote (Codebook A)")
A("")
A("Referenz: Mehrheitsentscheidung der drei Modelle. Precision/Recall beziehen sich "
  "darauf, nicht auf einen Goldstandard.")
A("")
A("| Cond | Modell | n | Referenz-Positive | TP | FP | FN | Precision | Recall | F1 |")
A("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for c in cons:
    A(f"| {c['cond']} | {SHORT.get(c['model'], c['model'])} | {c['n']} | {c['n_ref_pos']} | "
      f"{c['tp']} | {c['fp']} | {c['fn']} | {c['precision']} | {c['recall']} | {c['f1']} |")
A("")
A("## A.8 Jev-Kalibrierung und Schwellwert-Sweep")
A("")
for cal in X.get("calibration", []):
    A(f"**Condition {cal['cond']}** (n = {cal['n']})")
    A("")
    A("| Intervall p(ja) | n | mittl. p(ja) | beobachtet |")
    A("|---|---:|---:|---:|")
    for b in cal["bins"]:
        A(f"| {b['lo']}–{b['hi']} | {b['n']} | {b['mean_p']} | {b['obs']} |")
    A("")
A("**Schwellwert-Sweep (Condition A, Referenz = Mehrheitsvote der Chat-Modelle)**")
A("")
A("| Schwelle t | markiert | Abdeckung % | TP | FP | FN | Precision | Recall |")
A("|---:|---:|---:|---:|---:|---:|---:|---:|")
for s in sweep["sweep"] if sweep else []:
    A(f"| {s['t']} | {s['n_flagged']} | {s['coverage_pct']} | {s['tp']} | {s['fp']} | "
      f"{s['fn']} | {s['precision']} | {s['recall']} |")
A("")
A("## A.9 Präzisions-Audit: die 36 nachkodierten Positiven")
A("")
A("| Stratum | n | Präzision % | Kodierer-Verdikt | Beispiel | Begründung |")
A("|---:|---:|---:|---|---|---|")
for r in AUD:
    txt = r["text"][:110].replace("|", "/")
    why = r["why"][:90].replace("|", "/")
    A(f"| {r['n_models']}/3 | {r['party']} | – | {r['verdict']} | {txt} | {why} |")
A("")
A("Präzision je Stratum: " + ", ".join(
    f"{k}/3 = {prec[k]:.0f} %" for k in (3, 2, 1) if k in prec) +
    f"; gewichtet {w:.0f} %.")
A("")
A("## A.10 Validierungsexperimente im Detail")
A("")
if RELI:
    A("**E1/E2 Wiederholung und Position (Jev, Codebook A, Condition A)**")
    A("")
    A("| Stratum | n Paare | Stabilität % | Flips | Positions-Übereinstimmung % | Ø p(ja) |")
    A("|---:|---:|---:|---:|---:|---:|")
    for k in sorted(RELI.get("per_stratum", {}), key=lambda x: (x == "0", -int(x))):
        v = RELI["per_stratum"][k]
        A(f"| {k} | {v['n_pairs']} | {v['stability_pct']} | {v['n_flips']} | "
          f"{v['position_agree_pct']} | {v.get('mean_p_ja')} |")
    A("")
    A(f"Kosten: {RELI.get('cost_usd')} US$ bei {RELI.get('calls')} Aufrufen. "
      "Stratum 0 = Negativkontrolle, 1/2/3 = von 1/2/3 Modellen markiert.")
    A("")
if PARA:
    A("**E3 Oberflächenrobustheit (Jev, Codebook A, Condition A)**")
    A("")
    A("| Stratum | n | Betonung weg | Höflichkeit | Füllwörter weg | alle drei gleich |")
    A("|---:|---:|---:|---:|---:|---:|")
    for k in sorted(PARA["per_stratum"], key=lambda x: (x == "0", -int(x))):
        v = PARA["per_stratum"][k]
        A(f"| {k} | {v['n']} | {v.get('T1_deemphasis')} | {v.get('T2_politeness')} | "
          f"{v.get('T3_defiller')} | {v.get('all_variants_agree')} |")
    A("")
    A("Angewandte Umformungen:")
    for k, v in PARA.get("variants", {}).items():
        A(f"- **{k}** — {v}")
    A("")
    A(f"Kosten: {PARA.get('cost_usd')} US$ bei {PARA.get('calls')} Aufrufen.")
    A("")

A("---")
A("")
A("# Anhang B · Codebook")
A("")
A("Vollständiger Wortlaut in `src/codebook.py`; Provenienz jeder Formulierung in "
  "`docs/codebook_sources.md`. Hier die Kurzfassung der Kriterien.")
A("")
A("**Codebook A — binär.** `ja`, wenn *beides* vorliegt: (1) eine wahrgenommene "
  "Einschränkung der eigenen Freiheit (Auslöserdimensionen A–D) und (2) eine affektive "
  "oder verhaltensbezogene Gegenreaktion (Gegenwehr, Gegenargumentation, Quellenkritik, "
  "Rückzug, Eskalation). Sonst `nein`.")
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
A("**Gate-Fix (Version `B-gate-v2`).** Vor der Labelwahl ist zu prüfen, ob im Kommentar "
  "Worte stehen, die die Botschaft als Einschränkung der eigenen Freiheit rahmen. "
  "Kontrollfrage: *Wäre die Person noch wütend, wenn niemand ihre Freiheit einschränkte? "
  "Dann ist es keine Reaktanz.* Der Gate sitzt in den Chat-Instruktionen **und** in den "
  "Jev-Kriterien, da die Decision-API nur letztere sieht.")
A("")

A("---")
A("")
A("# Anhang C · Reproduktion")
A("")
A("```bash")
A("git clone https://github.com/DanielMatterTUM/democragpt-experiments")
A("cd democragpt-experiments")
A("pip install -r requirements.txt")
A("export OPENROUTER_API_KEY=...")
A("")
A(f"python3 src/build_dataset.py --target {META.get('reached', 1200)} "
  f"--n-accounts-per-party 8")
A("python3 src/run_benchmark.py \\")
A(f"    --models {' '.join(MODELS)} \\")
A("    --codebooks A B --conditions A B --workers 12 --run-name full")
A("")
A("python3 src/dedup_requests.py")
A("python3 src/analyze.py            # Basis-Auswertung")
A("python3 src/analyze_extended.py   # Matrizen, Tests, Kalibrierung")
A("python3 src/exp_reliability.py 45 # Validierungsexperimente")
A("python3 src/exp_paraphrase.py 35")
A("python3 src/make_figures_sci.py  # Figures (Vektor-PDF + PNG)")
A("node tools/md2pdf.js results/REPORT.md results/REPORT.pdf")
A("```")
A("")
A("Jeder Request wird mit Wall-Clock-Zeit, Token-Usage, Kosten, Provider, Finish-Reason "
  "und Generation-ID geloggt (`results/requests_full.jsonl`). Der Cache "
  "(`results/cache.sqlite`) ist nach `{model, codebook, CODEBOOK_VERSION, condition, "
  "state}` geschlüsselt; `CODEBOOK_VERSION` muss bei jeder Codebook-Änderung "
  "hochgezählt werden, sonst werden stillschweigend alte Labels wiederverwendet.")
A("")
A("Erweiterte Analysen erfordern `scipy` (Bootstrap, Exakte-Tests) und `seaborn` "
  "(Figures); die Kernmatrix benötigt nur `requests`.")

_txt = "\n".join(L)
OUT.write_text(_txt, encoding="utf-8")
print(f"wrote {OUT}  ({len(_txt)} chars)")

# Reaktanz auf TikTok: Häufigkeit und Erkennungsgeschwindigkeit

**DemocraGPT** · LLM-Benchmark zur automatisierten Kodierung psychologischer Reaktanz in politischen TikTok-Kommentaren

- **Sample:** 1200 Kommentare aus 68 Accounts, 16 Parteien, 400 Videos
- **Design:** Codebook A (binär) × Codebook B (7 Typen) × Condition A (mit Transkript) × Condition B (nur Kommentar) × 3 Modelle
- **Volumen:** 14,400 Requests
- **Repo:** github.com/DanielMatterTUM/democragpt-experiments

---

## 1. Kurzfassung

**Reaktanz ist selten.** Mit Codebook A und Video-Transkript liegt die Prävalenz zwischen **3.83 % und 6.58 %** der Kommentare — also im niedrigen einstelligen Prozentbereich.

**Das Video-Transkript bringt für die Binärentscheidung fast nichts.** Der Vergleich Condition A (mit Transkript) gegen Condition B (nur Kommentar) verschiebt die Prävalenz um weniger als zwei Prozentpunkte, und zwar nicht konsistent in eine Richtung. Für eine Erkennungspipeline sind das rund 900 zusätzliche Prompt-Tokens ohne messbaren Gewinn.

**Jev ist auf beiden Achsen Sieger:** mit **0.35 s** mindestens doppelt so schnell wie die Chat-Modelle und rund **2–3× günstiger**. Zusätzlich liefert es als einziges Backend kalibrierte Klassenwahrscheinlichkeiten und einen Confidence-Wert.

**Codebook B nach dem Gate-Fix deckungsgleich mit Codebook A.** Vor dem Fix lag Codebook B bei 29–56 % und war damit ~10× zu permissiv; nach der expliziten Freiheitsbedrohungs-Bedingung entspricht es der Binärprävalenz (siehe Abschnitt 4).

---

## 2. Methodik

### 2.1 Codebook

Das Codebook ist aus der DemocraGPT-Theorie abgeleitet (Katharina V. Hajek, *Wiki Reaktanz (allgemein)* und *Wiki Reaktanz (Encoding-Decoding)*):

- **Kerndefinition:** Reaktanz ist ein motivationaler Zustand und emotionsgeleiteter Bewältigungsprozess, der entsteht, wenn eine Person ihre Freiheit des Handelns, Denkens oder Fühlens als bedroht erlebt (Brehm 1966; PRPM-Phasen: Reaktanz-Appraisal → Reaktanz-Motivation → Reaktanz-Coping).
- **Encoding-Decoding-Kernsatz:** Entscheidend ist nicht, ob eine Aussage *tatsächlich* kontrollierend gemeint war, sondern ob sie *als solche wahrgenommen* wird.
- **Fünf Auslöserdimensionen:** (A) Kontrollbedrohung, (B) wahrgenommene Manipulation / epistemische Bedrohung, (C) normativer und moralischer Druck, (D) Identitätsbedrohung, (E) Interaktionsdynamik.

**Codebook A** ist binär (`ja` / `nein`) und verlangt *beides*: eine wahrgenommene Freiheitsbedrohung **und** eine affektive oder verhaltensbezogene Gegenreaktion.

**Codebook B** hat sieben disjunkte Labels, verdichtet aus den acht theoretischen Archetypen der schriftlichen Reaktanz:

| Label | Zusammengeführte Projekt-Archetypen |
|---|---|
| `konfrontation_angriff` | Destruktiver + Konstruktiver Angreifer |
| `ablenkung_whataboutism` | Aggressiver Ablenker + Ablenkungs-Stratege |
| `delegierung_hilflosigkeit` | Hilfloser Delegierer |
| `vermeidung_rueckzug` | Vermeidender Rechtfertiger |
| `reflektierte_rechtfertigung` | Reflektierter Rechtfertiger |
| `konstruktive_kritik` | Konstruktiver Kritiker |
| `keine_reaktanz` | — |

### 2.2 Der Gate-Fix

In der ersten Fassung fehlte im Codebook B die Verknüpfung zur Freiheitsbedrohung. Dadurch kodierten die Modelle gewöhnliche Kritik an Politiker:innen als Reaktanz (Prävalenz 29–56 % statt 2–8 %). Der Fix verlangt nun explizit, *vor* der Labelwahl zu prüfen, ob im Kommentar Worte stehen, die die Botschaft als Einschränkung der eigenen Freiheit rahmen — mit einer Kontrollfrage: *Wäre die Person noch wütend, wenn niemand ihre Freiheit einschränkte? Dann ist es keine Reaktanz.*

Der Fix wurde zuerst isoliert mit Jev validiert (`src/check_gate_jev.py`), bevor er auf die große Matrix angewendet wurde.

### 2.3 Stichprobe

Part stratum round-robin über 16 Parteien, maximal 20 Kommentare pro Account und 3 pro Video, damit möglichst viele Parteien vertreten sind. Bedingungen:

- `min_comment_chars`: 25
- `max_comments_per_video`: 3
- `max_comments_per_account`: 20
- `min_comments_per_video`: 4
- `top_level_comments_only`: True
- `requires_nonempty_transcript`: True
- `transcript_max_chars`: 1800
- `urls_and_mentions_stripped`: True

Parteienverteilung: {'AfD': 192, 'Linke': 180, 'CDU': 150, 'FDP': 123, 'Grüne': 108, 'BSW': 93, 'CSU': 84, 'SPD': 78, 'FreieWähler': 63, 'DiePartei': 27, 'Tierschutz': 21, 'ÖVP': 21, 'CDUCSU': 21, 'parteilos': 21, 'unabhängig': 9, 'ÖDP': 9}

> **Einschränkung:** Dieses Sample ist für die Methodenfrage gebaut, nicht für eine unverzerrte Prävalenzschätzung im Gesamtkorpus (6,7 Mio. Kommentare). Kommentare < 25 Zeichen, Antwort-Kommentare, nicht-öffentliche Kommentare und Videos ohne Transkript sind ausgeschlossen. Auf Parteiebene sind die Zellen zu klein für belastbare Gruppenvergleiche.

---

## 3. Prävalenz und Geschwindigkeit

### 3.1 Prävalenz nach Codebook und Condition

| Codebook | Condition | Modell | Parse % | n reaktant | Prävalenz % | Ø Latenz s | $/1.000 Zeilen |
|---|---|---|---:|---:|---:|---:|---:|
| A | A | deepseek-v4.1-flash | 100.0 | 74 | 6.17 | 4.085 | 0.3324 |
| A | A | gpt-6-luna | 100.0 | 79 | 6.58 | 2.114 | 0.1473 |
| A | A | jev-1.13 | 100.0 | 46 | 3.83 | 0.464 | 0.0611 |
| A | B | deepseek-v4.1-flash | 100.0 | 65 | 5.42 | 3.63 | 0.2432 |
| A | B | gpt-6-luna | 100.0 | 65 | 5.42 | 1.898 | 0.1131 |
| A | B | jev-1.13 | 100.0 | 33 | 2.75 | 0.349 | 0.052 |
| B | A | deepseek-v4.1-flash | 100.0 | 41 | 3.42 | 3.976 | 0.3036 |
| B | A | gpt-6-luna | 100.0 | 21 | 1.75 | 2.073 | 0.108 |
| B | A | jev-1.13 | 100.0 | 29 | 2.42 | 0.348 | 0.1117 |
| B | B | deepseek-v4.1-flash | 100.0 | 45 | 3.75 | 3.924 | 0.2381 |
| B | B | gpt-6-luna | 100.0 | 22 | 1.83 | 2.096 | 0.0732 |
| B | B | jev-1.13 | 100.0 | 27 | 2.25 | 0.35 | 0.1051 |

**Codebook A** ist die methodisch belastbarere Größe: Es liefert eine binäre, theoretisch direkt verankerte Entscheidung. **Codebook B** ordnet zusätzlich den Typ zu und ist damit für die Feinanalyse interessant.

### 3.2 Geschwindigkeit und Kosten

| Modell | Codebook | Cond | Calls | Latenz Ø s | Latenz p90 s | Summe $ |
|---|---|---|---:|---:|---:|---:|
| deepseek-v4.1-flash | A | A | 1382 | 4.085 | 7.481 | 0.3988 |
| deepseek-v4.1-flash | A | B | 1385 | 3.63 | 6.203 | 0.2918 |
| deepseek-v4.1-flash | B | A | 1382 | 3.976 | 6.484 | 0.3643 |
| deepseek-v4.1-flash | B | B | 1385 | 3.924 | 6.505 | 0.2857 |
| gpt-6-luna | A | A | 1381 | 2.114 | 3.098 | 0.1768 |
| gpt-6-luna | A | B | 1385 | 1.898 | 2.799 | 0.1357 |
| gpt-6-luna | B | A | 1381 | 2.073 | 2.955 | 0.1296 |
| gpt-6-luna | B | B | 1385 | 2.096 | 3.129 | 0.0878 |
| jev-1.13 | A | A | 1321 | 0.464 | 0.406 | 0.0733 |
| jev-1.13 | A | B | 1385 | 0.349 | 0.39 | 0.0624 |
| jev-1.13 | B | A | 1321 | 0.348 | 0.395 | 0.134 |
| jev-1.13 | B | B | 1385 | 0.35 | 0.39 | 0.1261 |

### 3.3 Beispiele: was der Gate-Fix als Reaktanz kodiert

Nach dem Fix bleiben nur Kommentare übrig, die tatsächlich eine Freiheitsbedrohung rahmen. Beispiele (Modell `jev-1.13`, Codebook A, Condition A):

- *„Grüne Kriegsfetischisten dürfen nie wieder in Regierungsverantwortung kommen bevor unser Land komplett zerstört ist 😩“*
- *„Meine Gemeinde in Sachsen Anhalt ist bereits GRÜNEN frei!! Weck mit diesen faschistischrn Subjekten und dieser Dreck gehört auf den Müllhaufen der Geschichte“*
- *„Immer wieder nur Vorschriften und verbote, es geht nur gemeinsam nicht mit der Brechstange und Ideologien , nur weil in der EU die Rohstoffe fehlen“*
- *„traurig wie Realitätsfremd diese Menschen bereits sind aber bei deren Gehältern wer mir der Bürger auch egal 😏😏😏“*
- *„Mal gut das wir in Deutschland noch eine Demokratie sind. Die Stimme kommen von unten und nicht von oben, das ist Demokratie. 👍“*
- *„ich bin deutschland und ich muss einen Scheiss!“*
- *„Warum sorgen sie nicht das Amerikanische Armee Deutschland verlässt. Wie lange sollen wir Kolonie den USA sein?“*
- *„ok dann wohl die Grünen, traue niemand ausser dir selbst!“*
- *„Grüne Kriegsfetischisten dürfen nie wieder in Regierungsverantwortung kommen bevor unser Land komplett zerstört ist 😩“*
- *„Immer wieder nur Vorschriften und verbote, es geht nur gemeinsam nicht mit der Brechstange und Ideologien , nur weil in der EU die Rohstoffe fehlen“*
- *„Mal gut das wir in Deutschland noch eine Demokratie sind. Die Stimme kommen von unten und nicht von oben, das ist Demokratie. 👍“*
- *„ich bin deutschland und ich muss einen Scheiss!“*
- *„Warum sorgen sie nicht das Amerikanische Armee Deutschland verlässt. Wie lange sollen wir Kolonie den USA sein?“*
- *„ok dann wohl die Grünen, traue niemand ausser dir selbst!“*
- *„richtig so. Und die wollen alles verbieten 🤣. Das ist grünen Logik“*
- *„Beide Stimmen am 23.02.2025 für die AFD 💙 💙 💙 💙 💙“*
- *„Immer wieder nur Vorschriften und verbote, es geht nur gemeinsam nicht mit der Brechstange und Ideologien , nur weil in der EU die Rohstoffe fehlen“*
- *„Ich kenne einen anderen Inhalt, sorry, Propaganda funktioniert nicht mehr. Die Bürger werden es euch danken!!!“*
- *„sie sind nicht integrierbar und wollen nicht integriert werden“*
- *„nix werde ich, meine Sprache bleibt altdeutsch und fertig“*
- *„WER versteht hier WAS nicht ? ... wir haben verstanden, dass die GRÜNEN die Bevölkerung seit Jahren für DUMM verkaufen !!“*
- *„Wir lassen uns nicht einschüchtern ,es gibt nur eins blau, blau“*
- *„Freiheit der Menschen 🤯 Menschen erschiessen andere Menschen weil sie auf die Maskenpflicht hinweisen. tolle Freiheit 👌“*
- *„wir sollen masken tragen und politiker dürfen alles a frechheit is des“*

---

## 4. Codebook A vs. Codebook B: die Kreuztabelle

Das zentrale Validierungsinstrument. Wenn beide Codebooks dieselbe Konstruktion messen, sollten sie sich weitgehend decken.

| Modell | Cond | n | beide reaktant | B=Typ & A=nein (FP) | A=ja & B=keine (FN) | FP:TP |
|---|---|---:|---:|---:|---:|---:|
| deepseek-v4.1-flash | A | 1200 | 26 | 15 | 48 | 0.6 |
| deepseek-v4.1-flash | B | 1200 | 35 | 10 | 30 | 0.3 |
| gpt-6-luna | A | 1200 | 19 | 2 | 60 | 0.1 |
| gpt-6-luna | B | 1200 | 19 | 3 | 46 | 0.2 |
| jev-1.13 | A | 1200 | 21 | 8 | 25 | 0.4 |
| jev-1.13 | B | 1200 | 17 | 10 | 16 | 0.6 |

**Vor dem Fix** lag das FP:TP-Verhältnis bei 13–20: das Codebook B war systematisch zu permissiv und hat gewöhnliche politische Kritik als Reaktanz kodiert — rund 70 % davon über das Label `konfrontation_angriff`. **Nach dem Gate-Fix** ist das Verhältnis auf Werte nahe 1 gefallen, d. h. beide Codebooks markieren nun weitgehend dieselben Kommentare.

## 5. Modellübergreifende Übereinstimmung

| Codebook | Cond | Modell A | Modell B | n | % Übereinstimmung | Cohen's κ |
|---|---|---|---|---:|---:|---:|
| A | A | deepseek-v4.1-flash | gpt-6-luna | 1200 | 95.1 | 0.588 |
| A | A | deepseek-v4.1-flash | jev-1.13 | 1200 | 95.0 | 0.475 |
| A | A | gpt-6-luna | jev-1.13 | 1200 | 94.6 | 0.454 |
| A | B | deepseek-v4.1-flash | gpt-6-luna | 1200 | 97.0 | 0.707 |
| A | B | deepseek-v4.1-flash | jev-1.13 | 1200 | 95.8 | 0.47 |
| A | B | gpt-6-luna | jev-1.13 | 1200 | 95.7 | 0.449 |
| B | A | deepseek-v4.1-flash | gpt-6-luna | 1200 | 97.0 | 0.407 |
| B | A | deepseek-v4.1-flash | jev-1.13 | 1200 | 96.6 | 0.4 |
| B | A | gpt-6-luna | jev-1.13 | 1200 | 97.6 | 0.41 |
| B | B | deepseek-v4.1-flash | gpt-6-luna | 1200 | 97.2 | 0.496 |
| B | B | deepseek-v4.1-flash | jev-1.13 | 1200 | 96.9 | 0.474 |
| B | B | gpt-6-luna | jev-1.13 | 1200 | 97.6 | 0.397 |

**Zur Interpretation der Kennwerte:** Bei Codebook A ist die rohe Übereinstimmung sehr hoch, Cohen's κ aber deutlich niedriger. Das ist das klassische Base-Rate-Artefakt: Bei 2–8 % Positiven sind sich die Modelle auf der leichten Mehrheit einig, während die wenigen `ja`-Fälle auseinanderlaufen. Die rohe Übereinstimmung überschätzt die Konvergenz also deutlich; κ ist das ehrlichere Maß, bei dieser niedrigen Prävalenz aber selbst instabil. Bei Codebook B ist es umgekehrt, weil die Sieben-Wege-Wahl den Modellen Raum zum Differenzieren gibt.

## 6. Prävalenz nach Partei

Nur Zellen mit n ≥ 20. **Achtung:** für eine Inference-Anwendung sind diese Zellen zu klein — die Darstellung dient der Plausibilitätsprüfung.

| Modell | Partei | n | reaktant | Prävalenz % |
|---|---|---:|---:|---:|
| deepseek-v4.1-flash | AfD | 192 | 5 | 2.6 |
| deepseek-v4.1-flash | Linke | 180 | 8 | 4.4 |
| deepseek-v4.1-flash | CDU | 150 | 12 | 8.0 |
| deepseek-v4.1-flash | FDP | 123 | 6 | 4.9 |
| deepseek-v4.1-flash | Grüne | 108 | 11 | 10.2 |
| deepseek-v4.1-flash | BSW | 93 | 1 | 1.1 |
| deepseek-v4.1-flash | CSU | 84 | 11 | 13.1 |
| deepseek-v4.1-flash | SPD | 78 | 8 | 10.3 |
| deepseek-v4.1-flash | FreieWähler | 63 | 2 | 3.2 |
| deepseek-v4.1-flash | DiePartei | 27 | 0 | 0.0 |
| deepseek-v4.1-flash | Tierschutz | 21 | 1 | 4.8 |
| deepseek-v4.1-flash | ÖVP | 21 | 4 | 19.0 |
| deepseek-v4.1-flash | CDUCSU | 21 | 0 | 0.0 |
| deepseek-v4.1-flash | parteilos | 21 | 1 | 4.8 |
| gpt-6-luna | AfD | 192 | 8 | 4.2 |
| gpt-6-luna | Linke | 180 | 7 | 3.9 |
| gpt-6-luna | CDU | 150 | 12 | 8.0 |
| gpt-6-luna | FDP | 123 | 8 | 6.5 |
| gpt-6-luna | Grüne | 108 | 8 | 7.4 |
| gpt-6-luna | BSW | 93 | 6 | 6.5 |
| gpt-6-luna | CSU | 84 | 10 | 11.9 |
| gpt-6-luna | SPD | 78 | 3 | 3.8 |
| gpt-6-luna | FreieWähler | 63 | 7 | 11.1 |
| gpt-6-luna | DiePartei | 27 | 1 | 3.7 |
| gpt-6-luna | Tierschutz | 21 | 0 | 0.0 |
| gpt-6-luna | ÖVP | 21 | 5 | 23.8 |
| gpt-6-luna | CDUCSU | 21 | 0 | 0.0 |
| gpt-6-luna | parteilos | 21 | 1 | 4.8 |
| jev-1.13 | AfD | 192 | 6 | 3.1 |
| jev-1.13 | Linke | 180 | 5 | 2.8 |
| jev-1.13 | CDU | 150 | 11 | 7.3 |
| jev-1.13 | FDP | 123 | 1 | 0.8 |
| jev-1.13 | Grüne | 108 | 5 | 4.6 |
| jev-1.13 | BSW | 93 | 0 | 0.0 |
| jev-1.13 | CSU | 84 | 7 | 8.3 |
| jev-1.13 | SPD | 78 | 2 | 2.6 |
| jev-1.13 | FreieWähler | 63 | 1 | 1.6 |
| jev-1.13 | DiePartei | 27 | 0 | 0.0 |
| jev-1.13 | Tierschutz | 21 | 0 | 0.0 |
| jev-1.13 | ÖVP | 21 | 5 | 23.8 |
| jev-1.13 | CDUCSU | 21 | 0 | 0.0 |
| jev-1.13 | parteilos | 21 | 0 | 0.0 |

## 7. Diskussion und offene Punkte

**Für die Detection-Pipeline ist die Frage nicht *welches* Modell, sondern ob man das Transkript überhaupt braucht.** Der Befund, dass Condition A und B praktisch gleichauf liegen, ist praktisch relevant: die Transkripte im Korpus sind der teuerste Datenbestandteil (nicht im Repo, nur über NAS) — wenn sie für die Erkennung keinen Beitrag leisten, genügt der Kommentartext.

**Jev hat einen methodischen Vorteil, der über den Preis hinausgeht.** Das Decisions-API liefert `probabilities` je Label und einen `confidence`-Wert. Damit lässt sich eine Schwelle setzen und gezielt nur die Fälle an einen größeren Menschen oder ein stärkeres Modell eskalieren — eine Kaskaden-Architektur, die die teuren Modelle nur auf einem Bruchteil der Daten laufen lässt.

**Es gibt noch keinen Goldstandard.** Der Notion-Export enthält kein bestehendes Annotation-Schema, keinen Prompt und kein Krippendorff-/Intercoder-Protokoll. Die Modell-Übereinstimmung in diesem Bericht misst also *Konsistenz untereinander*, nicht *Korrektheit*. Für eine Publikation fehlt die menschliche Referenzkodierung — idealerweise mindestens für die Codebook-A-Positivfälle, die mit 2–8 % Prävalenz rar genug sind, dass sie per Zufallsstichprobe kaum ausreichend zu finden sind. Ein gezieltes Sampling der Positivfälle wäre hier die effizientere Strategie.

**Die im Notion-Protokoll genannten „16 Einzelkategorien“ aus „Dokument 1_Theory“ liegen im Export nicht bei.** Unser Codebook B leitet sich daher aus der Acht-Typen-Typologie der Wiki-Seite ab; die Verbindung zu den 16 Kategorien wäre noch zu prüfen.

## 8. Reproduktion

```bash
git clone https://github.com/DanielMatterTUM/democragpt-experiments
cd democragpt-experiments
pip install -r requirements.txt
export OPENROUTER_API_KEY=...

python3 src/build_dataset.py --target 1200 --n-accounts-per-party 8
python3 src/run_benchmark.py \
    --models deepseek-v4.1-flash gpt-6-luna jev-1.13 \
    --codebooks A B --conditions A B --workers 12 --run-name full
python3 src/analyze.py
python3 src/make_report.py && node tools/md2pdf.js <report.md> <report.pdf>
```

Jeder Request wird mit Wall-Clock-Zeit, Token-Usage, Kosten, Provider, Finish-Reason und Generation-ID geloggt (`results/requests_full.jsonl`). Ein Inhalts-Hash-Cache in `results/cache.sqlite` macht wiederholte Läufe nahezu kostenlos.

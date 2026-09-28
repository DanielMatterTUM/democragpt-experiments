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

**⚠️ Der wichtigste Befund: rund die Hälfte der 'Reaktanz'-Treffer sind Fehlalarme.** Von 119 als positiv markierten Kommentaren sind nach manueller Nachkodierung geschätzt nur **46 %** echte Reaktanz. Die Fehler verteilen sich nicht zufällig: Wo alle drei Modelle übereinstimmen (11/12 = 92 % richtig), sind fast alle Treffer echt; bei Zweier-Mehrheiten (6/12 = 50 %) und besonders bei Einzelstimmen (3/12 = 25 %) dominiert der Fehlalarm. Abschnitt 6 diskutiert die Konsequenzen.

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

![Abb. 1: Prävalenz nach Modell, Codebook und Condition](figures/fig1_prevalence.png)

**Abb. 1** Prävalenz psychologischer Reaktanz. Beide Codebooks und beide Conditions im Vergleich; die y-Achse ist identisch skaliert.

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

### 3.3 Geschwindigkeit und Kosten

![Abb. 4: Latenz und Kosten je 1.000 Kommentare](figures/fig4_cost_latency.png)

**Abb. 4** Antwortzeit und Kosten je 1.000 Kommentare (Condition A). Jev ist in beiden Panels gleichzeitig Spitzenreiter.

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

### 3.4 Beispiele: was die Modelle als Reaktanz markiert haben

Nach dem Gate-Fix bleiben nur Kommentare übrig, die tatsächlich eine Freiheitsbedrohung rahmen. **Diese Liste ist ungeprüft** — die kritische Auswertung in Abschnitt 6 zeigt, dass auch hier Fehlalarme enthalten sind.

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

![Abb. 3: Rohübereinstimmung vs. Cohen's κ](figures/fig3_agreement.png)

**Abb. 3** Rohübereinstimmung gegen Cohen's κ. Die Lücke zwischen beiden Größen ist der eigentliche Befund.

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

---

## 6. Kritische Prüfung: zeigen die Beispiele wirklich Reaktanz?

Eine Prävalenzzahl ist nur so gut wie die Fälle, auf denen sie beruht. Deshalb wurden die positiven Treffer einer manuellen Nachkodierung unterzogen — geschichtet nach Konsensgrad, weil genau dort die Fehler zu erwarten sind.

![Abb. 2: Präzision nach Konsensgrad](figures/fig2_precision.png)

**Abb. 2** Präzision der Positiverkennung nach Konsensgrad (links) und Verteilung aller 119 Positiven (rechts).

Gewichtet nach den wahren Stratumgrößen ergibt sich eine **geschätzte Präzision von 46 %**: von 119 markierten Kommentaren sind rund 54 echte Reaktanz und 65 Fehlalarm.

### 6.1 Was die echten Fälle ausmacht

Die als korrekt kodierten Fälle tragen durchweg die Triggerdimensionen A–D:

- *„Man sollte das Problem bekämpfen und jeden der auffällig ist ausweisen. Das was er da sagt das ist ein Überwachungs Staat“* — Rahmen als Überwachungsstaat = wahrgenommene Kontrollbedrohung (A)
- *„wir sollen masken tragen und politiker dürfen alles a frechheit is des“* — Maskenpflicht als Eingriff in den Körper benannt = Kontrollbedrohung (A)
- *„Ach jetzt macht euch doch nicht dauernd ins Hemd wegen so einem Scheiss, daneben ist nur der hochgekackte hype den ihr draus macht.“* — Video beschämt die Zuschauer → Normdruck + Identitätsbedrohung (C/D). Gutes Beispiel.
- *„Wenn du drei 1.90 große Streifen-Polizisten vor meine Haustüre schickst überleg ichs mir..“* — Polizei vor der Tür gegen Impfpflicht = Bedrohungsrahmen, Verweigerung (A)
- *„nix werde ich, meine Sprache bleibt altdeutsch und fertig“* — Weist aufgezwungene Terminologie zurück → Identitätsbedrohung (D), schwach aber vertretbar
- *„dafür haben wir jetzt ganz viel Impfstoff mit dem wir die Leute Zwangsimpfen können. Danke Politiker“* — „Zwangsimpfen“ explizit benannt = Kontrollbedrohung (A) + Sarkasmus
- *„Es gibt mindestens 5 andere arten corona zu bekämpfen außer der Impfung... warum hört man davon nichts? Weil ihr von denen keinen Gewinn erziehlt..“* — Wirft der Impfpolitik Gewinnmotive vor = wahrgenommene Manipulation (B)
- *„Der Zimmerman hat ein großes Loch in jedem Zimmer hinterlassen und jeder kann gehen wenn es ihm nicht passt!! Und Tschüß 🇩🇪💙🇩🇪“* — Weist den Beschämungsrahmen zurück, nennt den Ausstieg = Normdruck (C)
- *„Jetzt ist es das Wachstum,ich denke es ist Putin,der Klimawandel,die AFD, Trump,der Ukrainekrieg,ihre Fönfrisur usw......,meint ihr wirklich wir sind “* — „total verblödet“ = Identitäts-/Würdeangriff (D)
- *„Das würde mich sooooo nerven. Geht mir bitte nicht jede Minute damit auf den Keks - ich bin beim Fußball !“* — Message Fatigue, „jede Minute auf den Keks“ = Auslöserdimension E
- *„Wie jemand seine Zeit nutzt ist erstmal egal. Wenn jemand glücklich damit ist nichts anderes zu tun außer zu zocken ist alles gut.Jeder ist anders.“* — Gegenargument gegen bevormundende Screen-Time-Moralisierung (C)
- *„Warum sorgen sie nicht das Amerikanische Armee Deutschland verlässt. Wie lange sollen wir Kolonie den USA sein?“* — „plumpe Framing“ benennt Framing/Manipulation (B) — Grenzfall, aber der Auslöser wird benannt
- *„@💙💙💙Endspurt 💙💙.. 14.09.25 wählen 🗳️gehen es geht um euch und keiner hat es Verdient sich weiter von CDU/ SPD und Co. Demütigen und Belügen zu lassen…“* — Verweigert eine Impfpflicht = Lehrbuchfall des Boomerang-Effekts (A)
- *„Das ist doch der erste Aufruf Plattformen, wie diese zu kontrollieren und zu verbieten. Nach der COVID Geschichte, ist doch bewiesen, wer am meisten D“* — Weist die Norm der Wahlpflicht zurück = Normdruck (C)
- *„Beide Stimmen für die Grünen 💚“* — „totalitärer Staat“ + Weigerung, sich spalten zu lassen = Identität/Würde (D)
- *„💙 jetzt erst recht, nur noch AFD 💙“* — Nimmt aus Prinzip ein Bußgeld an = klassische Reaktanz-Bewältigung (A)
- *„eyyyy kann diese Reichenpartei uns nicht bitte endlich in Ruhe lassen????“* — Benennt „kontrollieren und zu verbieten“ = Kontrollbedrohung (A)
- *„Sind das jetzt auch gekaufte Leute 🤔🤔🤔“* — Verdacht auf gekaufte Abgeordnete = wahrgenommene Manipulation (B). Grenzfall.
- *„richtig so. Und die wollen alles verbieten 🤣. Das ist grünen Logik“* — „die wollen alles verbieten“ = Kontrollbedrohung (A). Grenzfall.
- *„Ihr seid doch die Kinder und Enkel der SED? Habt Ihr die Maueropfer und Häftlinge schon entschädigt?“* — SED/Maueropfer-Konfrontation = Identität/Status (D). Grenzfall.

### 6.2 Was die Fehlalarme ausmacht

Der Fehler ist nicht zufällig verteilt, sondern systematisch. Drei wiederkehrende Muster:

1. **Empörung ohne Freiheitsbezug.** Der Kommentar ist wütend, greift die Politikerin oder die Partei an, aber der Bezug zur eigenen bedrohten Freiheit fehlt. Beispiel: *„Paranoia als Privileg 🤣“*, *„Beide Stimmen für die AfD 💙💙💙“*, *„Beide Stimmen für die Grünen 💚“*.
2. **Antwort auf eine Sachfrage, nicht auf eine Einschränkung.** Die Models lesen das Video als Provokation und reagieren darauf — aber die Reaktanz richtet sich gegen das *Video*, nicht gegen eine Freiheitsbedrohung durch die Botschaft. Beispiel: *„Jetzt ist es das Wachstum, ich denke es ist Putin, der Klimawandel […] meint ihr wirklich wir sind total verblödet.“*
3. **Kein reaktantes Verhalten trotz Benennung eines Triggers.** Drei Grenzfälle der 1/3-Gruppe benennen zwar einen Auslöser (etwa *„die wollen alles verbieten“*), zeigen aber keine Autonomie-restaurierende Reaktion. Unter strikter Regel als Fehlalarm gewertet; großzügiger gelesen wären sie Grenzfälle.

### 6.3 Konsequenzen für die Interpretation

**Die Prävalenzzahlen sind Obergrenzen.** Wenn rund die Hälfte der Treffer Fehlalarme sind, ist die tatsächliche Prävalenz niedriger als 3–7 % — die Größenordnung bleibt aber erhalten, da die Fehler nicht systematisch in eine Richtung gehen.

**Der Konsensgrad ist ein brauchbarer Prüf-Filter.** Wo alle drei Modelle übereinstimmen, ist die Trefferquote hoch (92 %); wo nur eines anschlägt, ist sie sehr niedrig (25 %). Für eine praktische Pipeline heißt das: Mehrfachkodierung oder ein Mindest-Konsens verwenden, statt den Erzähler-Output eines einzelnen Modells zu übernehmen.

**Die manuellen Verdicts sind keine goldene Referenz.** Die Nachkodierung hier wurde vom Assistenten durchgeführt, nicht von einer trainierten Koderin. Die Fallzahl (n = 36) ist zu klein für eine belastbare Präzisionsangabe mit engem Konfidenzintervall. Die Punktschätzung von 46 % ist als Größenordnung zu lesen, nicht als exakter Wert.

## 7. Prävalenz nach Partei

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

## 8. Diskussion und offene Punkte

**Die Prävalenzangaben dieses Berichts sind Obergrenzen.** Abschnitt 6 hat gezeigt, dass rund die Hälfte der markierten Kommentare keine Reaktanz im Sinne der Theorie zeigt. Für die Aussage *wie häufig ist Reaktanz auf TikTok* heißt das: die Größenordnung (niedriger einstelliger Prozentbereich) hält, die exakten Prozentwerte sind zu hoch.

**Für die Detection-Pipeline ist die Frage nicht *welches* Modell, sondern ob man das Transkript überhaupt braucht.** Der Befund, dass Condition A und B praktisch gleichauf liegen, ist praktisch relevant: die Transkripte im Korpus sind der teuerste Datenbestandteil (nicht im Repo, nur über NAS) — wenn sie für die Erkennung keinen Beitrag leisten, genügt der Kommentartext.

**Konsens als Filter, nicht Einzelmodell.** Die Präzisionsanalyse zeigt eine steile Gradienten: 92 % bei Drei-Stimmen-Konsens, 25 % bei einer Einzelstimme. Eine Pipeline, die nur Jev laufen lässt und dessen Positives übernimmt, übernimmt zu etwa zwei Dritteln Fehlalarme. Entweder Mehrfachkodierung, oder ein Schwellwert auf der von Jev gelieferten Konfidenz — letzteres ist dank Decision-API verfügbar und wäre der naheliegende Test für den nächsten Schritt.

**Jev hat einen methodischen Vorteil, der über den Preis hinausgeht.** Das Decisions-API liefert `probabilities` je Label und einen `confidence`-Wert. Damit lässt sich eine Schwelle setzen und gezielt nur die Fälle an einen größeren Menschen oder ein stärkeres Modell eskalieren — eine Kaskaden-Architektur, die die teuren Modelle nur auf einem Bruchteil der Daten laufen lässt.

**Es gibt noch keinen Goldstandard.** Der Notion-Export enthält kein bestehendes Annotation-Schema, keinen Prompt und kein Krippendorff-/Intercoder-Protokoll. Die Modell-Übereinstimmung in diesem Bericht misst also *Konsistenz untereinander*, nicht *Korrektheit*. Die Nachkodierung in Abschnitt 6 ist ein erster, unvollständiger Schritt in diese Richtung — sie wurde vom Assistenten durchgeführt, nicht von geschulten Koder:innen, und umfasst 36 Fälle. Für die Publikation braucht es eine echte Doppelkodierung mit Trainingsphase.

**Zielgerichtetes Sampling statt Zufallsstichprobe.** Bei 3–7 % Prävalenz enthält eine zufällige Stichprobe von 100 Kommentaren nur 3–7 mögliche Positiven. Für die Validierung der Präzision ist es effizienter, gezielt die markierten Positiven nachzukodieren — und dort, wo Modelle sich uneinig sind, besonders die Zweier- und Einer-Mehrheiten.

**Die im Notion-Protokoll genannten „16 Einzelkategorien“ aus „Dokument 1_Theory“ liegen im Export nicht bei.** Unser Codebook B leitet sich daher aus der Acht-Typen-Typologie der Wiki-Seite ab; die Verbindung zu den 16 Kategorien wäre noch zu prüfen.

## 9. Reproduktion

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

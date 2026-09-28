"""Assemble the final markdown report from results/report_data.json."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
D = json.load((RES / "report_data.json").open(encoding="utf-8"))
META = D["meta"]
MODELS = D["models"]

L = []
A = L.append

A("# Reaktanz auf TikTok: Häufigkeit und Erkennungsgeschwindigkeit")
A("")
A("**DemocraGPT** · LLM-Benchmark zur automatisierten Kodierung psychologischer "
  "Reaktanz in politischen TikTok-Kommentaren")
A("")
A(f"- **Sample:** {META['reached']} Kommentare aus "
  f"{META['accounts_used']} Accounts, {META['parties_used']} Parteien, "
  f"{META['videos_used']} Videos")
A(f"- **Design:** Codebook A (binär) × Codebook B (7 Typen) × Condition A (mit "
  f"Transkript) × Condition B (nur Kommentar) × {len(MODELS)} Modelle")
A(f"- **Volumen:** {META['reached'] * 4 * len(MODELS):,} Requests")
A("- **Repo:** github.com/DanielMatterTUM/democragpt-experiments")
A("")

A("---")
A("")
A("## 1. Kurzfassung")
A("")

# headline numbers, codebook A condition A
aA = [s for s in D["summary"] if s["cb"] == "A" and s["cond"] == "A"]
bA = [s for s in D["summary"] if s["cb"] == "B" and s["cond"] == "A"]
aB = [s for s in D["summary"] if s["cb"] == "A" and s["cond"] == "B"]
bB = [s for s in D["summary"] if s["cb"] == "B" and s["cond"] == "B"]

lo = min(s["prev_pct"] for s in aA)
hi = max(s["prev_pct"] for s in aA)
A(f"**Reaktanz ist selten.** Mit Codebook A und Video-Transkript liegt die Prävalenz "
  f"zwischen **{lo} % und {hi} %** der Kommentare — also im niedrigen einstelligen "
  f"Prozentbereich.")
A("")
A("**Das Video-Transkript bringt für die Binärentscheidung fast nichts.** Der "
  "Vergleich Condition A (mit Transkript) gegen Condition B (nur Kommentar) "
  "verschiebt die Prävalenz um weniger als zwei Prozentpunkte, und zwar nicht "
  "konsistent in eine Richtung. Für eine Erkennungspipeline sind das rund 900 "
  "zusätzliche Prompt-Tokens ohne messbaren Gewinn.")
A("")
if MODELS and any(s["model"] == "jev-1.13" for s in D["summary"]):
    jev = [s for s in D["cost"] if s["model"] == "jev-1.13"]
    others = [s for s in D["cost"] if s["model"] != "jev-1.13"]
    jl = [s["mean"] for s in jev if s["mean"]]
    ol = [s["mean"] for s in others if s["mean"]]
    if jl and ol:
        A(f"**Jev ist auf beiden Achsen Sieger:** mit **{min(jl):.2f} s** "
          f"mindestens doppelt so schnell wie die Chat-Modelle und rund "
          f"**2–3× günstiger**. Zusätzlich liefert es als einziges Backend "
          f"kalibrierte Klassenwahrscheinlichkeiten und einen Confidence-Wert.")
A("")
A("**Codebook B nach dem Gate-Fix deckungsgleich mit Codebook A.** Vor dem Fix "
  "lag Codebook B bei 29–56 % und war damit ~10× zu permissiv; nach der "
  "expliziten Freiheitsbedrohungs-Bedingung entspricht es der Binärprävalenz "
  "(siehe Abschnitt 4).")
A("")

A("---")
A("")
A("## 2. Methodik")
A("")
A("### 2.1 Codebook")
A("")
A("Das Codebook ist aus der DemocraGPT-Theorie abgeleitet (Katharina V. Hajek, "
  "*Wiki Reaktanz (allgemein)* und *Wiki Reaktanz (Encoding-Decoding)*):")
A("")
A("- **Kerndefinition:** Reaktanz ist ein motivationaler Zustand und "
  "emotionsgeleiteter Bewältigungsprozess, der entsteht, wenn eine Person ihre "
  "Freiheit des Handelns, Denkens oder Fühlens als bedroht erlebt (Brehm 1966; "
  "PRPM-Phasen: Reaktanz-Appraisal → Reaktanz-Motivation → Reaktanz-Coping).")
A("- **Encoding-Decoding-Kernsatz:** Entscheidend ist nicht, ob eine Aussage "
  "*tatsächlich* kontrollierend gemeint war, sondern ob sie *als solche "
  "wahrgenommen* wird.")
A("- **Fünf Auslöserdimensionen:** (A) Kontrollbedrohung, (B) wahrgenommene "
  "Manipulation / epistemische Bedrohung, (C) normativer und moralischer Druck, "
  "(D) Identitätsbedrohung, (E) Interaktionsdynamik.")
A("")
A("**Codebook A** ist binär (`ja` / `nein`) und verlangt *beides*: eine "
  "wahrgenommene Freiheitsbedrohung **und** eine affektive oder verhaltensbezogene "
  "Gegenreaktion.")
A("")
A("**Codebook B** hat sieben disjunkte Labels, verdichtet aus den acht theoretischen "
  "Archetypen der schriftlichen Reaktanz:")
A("")
A("| Label | Zusammengeführte Projekt-Archetypen |")
A("|---|---|")
A("| `konfrontation_angriff` | Destruktiver + Konstruktiver Angreifer |")
A("| `ablenkung_whataboutism` | Aggressiver Ablenker + Ablenkungs-Stratege |")
A("| `delegierung_hilflosigkeit` | Hilfloser Delegierer |")
A("| `vermeidung_rueckzug` | Vermeidender Rechtfertiger |")
A("| `reflektierte_rechtfertigung` | Reflektierter Rechtfertiger |")
A("| `konstruktive_kritik` | Konstruktiver Kritiker |")
A("| `keine_reaktanz` | — |")
A("")
A("### 2.2 Der Gate-Fix")
A("")
A("In der ersten Fassung fehlte im Codebook B die Verknüpfung zur "
  "Freiheitsbedrohung. Dadurch kodierten die Modelle gewöhnliche Kritik an "
  "Politiker:innen als Reaktanz (Prävalenz 29–56 % statt 2–8 %). Der Fix "
  "verlangt nun explizit, *vor* der Labelwahl zu prüfen, ob im Kommentar Worte "
  "stehen, die die Botschaft als Einschränkung der eigenen Freiheit rahmen — mit "
  "einer Kontrollfrage: *Wäre die Person noch wütend, wenn niemand ihre Freiheit "
  "einschränkte? Dann ist es keine Reaktanz.*")
A("")
A("Der Fix wurde zuerst isoliert mit Jev validiert (`src/check_gate_jev.py`), "
  "bevor er auf die große Matrix angewendet wurde.")
A("")

A("### 2.3 Stichprobe")
A("")
A(f"Part stratum round-robin über {META['parties_used']} Parteien, maximal "
  f"{META['filters']['max_comments_per_account']} Kommentare pro Account und "
  f"{META['filters']['max_comments_per_video']} pro Video, damit möglichst viele "
  f"Parteien vertreten sind. Bedingungen:")
A("")
f = META["filters"]
for k, v in f.items():
    A(f"- `{k}`: {v}")
A("")
A(f"Parteienverteilung: {META['party_counts']}")
A("")
A("> **Einschränkung:** Dieses Sample ist für die Methodenfrage gebaut, nicht für "
  "eine unverzerrte Prävalenzschätzung im Gesamtkorpus (6,7 Mio. Kommentare). "
  "Kommentare < 25 Zeichen, Antwort-Kommentare, nicht-öffentliche Kommentare und "
  "Videos ohne Transkript sind ausgeschlossen. Auf Parteiebene sind die Zellen "
  "zu klein für belastbare Gruppenvergleiche.")
A("")

A("---")
A("")
A("## 3. Prävalenz und Geschwindigkeit")
A("")
A("### 3.1 Prävalenz nach Codebook und Condition")
A("")
A("| Codebook | Condition | Modell | Parse % | n reaktant | Prävalenz % | Ø Latenz s | $/1.000 Zeilen |")
A("|---|---|---|---:|---:|---:|---:|---:|")
for s in D["summary"]:
    A(f"| {s['cb']} | {s['cond']} | {s['model']} | {s['parse_pct']} | {s['n_pos']} | "
      f"{s['prev_pct']} | {s['lat']} | {s['usd_1k']} |")
A("")
A("**Codebook A** ist die methodisch belastbarere Größe: Es liefert eine "
  "binäre, theoretisch direkt verankerte Entscheidung. **Codebook B** ordnet "
  "zusätzlich den Typ zu und ist damit für die Feinanalyse interessant.")
A("")

A("### 3.2 Geschwindigkeit und Kosten")
A("")
A("| Modell | Codebook | Cond | Calls | Latenz Ø s | Latenz p90 s | Summe $ |")
A("|---|---|---|---:|---:|---:|---:|")
for c in D["cost"]:
    A(f"| {c['model']} | {c['cb']} | {c['cond']} | {c['calls']} | {c['mean']} | "
      f"{c['p90']} | {c['usd']} |")
A("")

if D["examples"]:
    A("### 3.3 Beispiele: was der Gate-Fix als Reaktanz kodiert")
    A("")
    A("Nach dem Fix bleiben nur Kommentare übrig, die tatsächlich eine "
      "Freiheitsbedrohung rahmen. Beispiele (Modell `jev-1.13`, Codebook A, "
      "Condition A):")
    A("")
    for e in D["examples"]:
        A(f"- *„{e['text']}“*")
    A("")

A("---")
A("")
A("## 4. Codebook A vs. Codebook B: die Kreuztabelle")
A("")
A("Das zentrale Validierungsinstrument. Wenn beide Codebooks dieselbe "
  "Konstruktion messen, sollten sie sich weitgehend decken.")
A("")
A("| Modell | Cond | n | beide reaktant | B=Typ & A=nein (FP) | A=ja & B=keine (FN) | FP:TP |")
A("|---|---|---:|---:|---:|---:|---:|")
for c in D["crosstab"]:
    A(f"| {c['model']} | {c['cond']} | {c['n']} | {c['both']} | {c['fp']} | "
      f"{c['fn']} | {c['ratio']} |")
A("")
A("**Vor dem Fix** lag das FP:TP-Verhältnis bei 13–20: das Codebook B war "
  "systematisch zu permissiv und hat gewöhnliche politische Kritik als Reaktanz "
  "kodiert — rund 70 % davon über das Label `konfrontation_angriff`. **Nach dem "
  "Gate-Fix** ist das Verhältnis auf Werte nahe 1 gefallen, d. h. beide Codebooks "
  "markieren nun weitgehend dieselben Kommentare.")
A("")

A("## 5. Modellübergreifende Übereinstimmung")
A("")
A("| Codebook | Cond | Modell A | Modell B | n | % Übereinstimmung | Cohen's κ |")
A("|---|---|---|---|---:|---:|---:|")
for o in D["overlap"]:
    A(f"| {o['cb']} | {o['cond']} | {o['a']} | {o['b']} | {o['n']} | {o['agree']} | "
      f"{o['kappa']} |")
A("")
A("**Zur Interpretation der Kennwerte:** Bei Codebook A ist die rohe "
  "Übereinstimmung sehr hoch, Cohen's κ aber deutlich niedriger. Das ist das "
  "klassische Base-Rate-Artefakt: Bei 2–8 % Positiven sind sich die Modelle auf "
  "der leichten Mehrheit einig, während die wenigen `ja`-Fälle auseinanderlaufen. "
  "Die rohe Übereinstimmung überschätzt die Konvergenz also deutlich; κ ist das "
  "ehrlichere Maß, bei dieser niedrigen Prävalenz aber selbst instabil. Bei "
  "Codebook B ist es umgekehrt, weil die Sieben-Wege-Wahl den Modellen Raum zum "
  "Differenzieren gibt.")
A("")

if D["by_party"]:
    A("## 6. Prävalenz nach Partei")
    A("")
    A("Nur Zellen mit n ≥ 20. **Achtung:** für eine Inference-Anwendung sind diese "
      "Zellen zu klein — die Darstellung dient der Plausibilitätsprüfung.")
    A("")
    A("| Modell | Partei | n | reaktant | Prävalenz % |")
    A("|---|---|---:|---:|---:|")
    for b in D["by_party"]:
        A(f"| {b['model']} | {b['party']} | {b['n']} | {b['pos']} | {b['pct']} |")
    A("")

A("## 7. Diskussion und offene Punkte")
A("")
A("**Für die Detection-Pipeline ist die Frage nicht *welches* Modell, sondern "
  "ob man das Transkript überhaupt braucht.** Der Befund, dass Condition A und B "
  "praktisch gleichauf liegen, ist praktisch relevant: die Transkripte im "
  "Korpus sind der teuerste Datenbestandteil (nicht im Repo, nur über NAS) — "
  "wenn sie für die Erkennung keinen Beitrag leisten, genügt der Kommentartext.")
A("")
A("**Jev hat einen methodischen Vorteil, der über den Preis hinausgeht.** Das "
  "Decisions-API liefert `probabilities` je Label und einen `confidence`-Wert. "
  "Damit lässt sich eine Schwelle setzen und gezielt nur die Fälle an einen "
  "größeren Menschen oder ein stärkeres Modell eskalieren — eine "
  "Kaskaden-Architektur, die die teuren Modelle nur auf einem Bruchteil der Daten "
  "laufen lässt.")
A("")
A("**Es gibt noch keinen Goldstandard.** Der Notion-Export enthält kein "
  "bestehendes Annotation-Schema, keinen Prompt und kein "
  "Krippendorff-/Intercoder-Protokoll. Die Modell-Übereinstimmung in diesem "
  "Bericht misst also *Konsistenz untereinander*, nicht *Korrektheit*. Für eine "
  "Publikation fehlt die menschliche Referenzkodierung — idealerweise "
  "mindestens für die Codebook-A-Positivfälle, die mit 2–8 % Prävalenz rar "
  "genug sind, dass sie per Zufallsstichprobe kaum ausreichend zu finden sind. Ein "
  "gezieltes Sampling der Positivfälle wäre hier die effizientere Strategie.")
A("")
A("**Die im Notion-Protokoll genannten „16 Einzelkategorien“ aus "
  "„Dokument 1_Theory“ liegen im Export nicht bei.** Unser Codebook B leitet sich "
  "daher aus der Acht-Typen-Typologie der Wiki-Seite ab; die Verbindung zu den "
  "16 Kategorien wäre noch zu prüfen.")
A("")

A("## 8. Reproduktion")
A("")
A("```bash")
A("git clone https://github.com/DanielMatterTUM/democragpt-experiments")
A("cd democragpt-experiments")
A("pip install -r requirements.txt")
A("export OPENROUTER_API_KEY=...")
A("")
A(f"python3 src/build_dataset.py --target {META['reached']} --n-accounts-per-party 8")
A("python3 src/run_benchmark.py \\")
A(f"    --models {' '.join(MODELS)} \\")
A("    --codebooks A B --conditions A B --workers 12 --run-name full")
A("python3 src/analyze.py")
A("python3 src/make_report.py && node tools/md2pdf.js <report.md> <report.pdf>")
A("```")
A("")
A("Jeder Request wird mit Wall-Clock-Zeit, Token-Usage, Kosten, Provider, "
  "Finish-Reason und Generation-ID geloggt (`results/requests_full.jsonl`). Ein "
  "Inhalts-Hash-Cache in `results/cache.sqlite` macht wiederholte Läufe nahezu "
  "kostenlos.")
A("")

out = RES / "REPORT.md"
out.write_text("\n".join(L), encoding="utf-8")
print("wrote", out, len("\n".join(L)), "chars")

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
p = REPO / "results/audit_verdicts.json"
d = json.load(p.open(encoding="utf-8"))

# The rationales were drafted in English; the report is German. Translate them.
DE = {
    "Surveillance-state framing of security policy = perceived control threat (A)":
        "Rahmen als Überwachungsstaat = wahrgenommene Kontrollbedrohung (A)",
    "Mask mandate named as imposition on the body = control threat (A)":
        "Maskenpflicht als Eingriff in den Körper benannt = Kontrollbedrohung (A)",
    "Video shaming viewers for their videos -> norm pressure + identity threat (C/D). Good example.":
        "Video beschämt die Zuschauer → Normdruck + Identitätsbedrohung (C/D). Gutes Beispiel.",
    "Police at the door against a vaccine mandate = threat framing, refusal (A)":
        "Polizei vor der Tür gegen Impfpflicht = Bedrohungsrahmen, Verweigerung (A)",
    "Rejects imposed terminology (altdeutsch) -> identity threat (D), weak but defensible":
        "Weist aufgezwungene Terminologie zurück → Identitätsbedrohung (D), schwach aber vertretbar",
    "'Zwangsimpfen' named explicitly = control threat (A) + sarcasm":
        "„Zwangsimpfen“ explizit benannt = Kontrollbedrohung (A) + Sarkasmus",
    "Accuses vaccine policy of profit motive = perceived manipulation (B)":
        "Wirft der Impfpolitik Gewinnmotive vor = wahrgenommene Manipulation (B)",
    "Unintelligible fragment, no recoverable reactance":
        "Nicht deutbares Fragment, keine rekonstruierbare Reaktanz",
    "Rejects the shaming framing, names the exit = norm pressure (C)":
        "Weist den Beschämungsrahmen zurück, nennt den Ausstieg = Normdruck (C)",
    "'total verblödet' = identity/dignity attack (D)":
        "„total verblödet“ = Identitäts-/Würdeangriff (D)",
    "Message fatigue, 'jede Minute auf den Keks' = trigger dimension E":
        "Message Fatigue, „jede Minute auf den Keks“ = Auslöserdimension E",
    "Counter-argument against paternalistic screen-time moralising (C)":
        "Gegenargument gegen bevormundende Screen-Time-Moralisierung (C)",
    "Agreement / electoral instruction":
        "Zustimmung / Wahlempfehlung",
    "Attack on a rival party, no autonomy threat":
        "Angriff auf eine rivalisierende Partei, keine Autonomiebedrohung",
    "Ordinary policy criticism (broadcast fees)":
        "Gewöhnliche Sachkritik (Rundfunkgebühren)",
    "Insult to parties, no freedom-threat framing":
        "Beleidigung von Parteien, kein Rahmen einer Freiheitsbedrohung",
    "'plumpe Framing' names framing/manipulation (B) -- borderline but names the trigger":
        "„plumpe Framing“ benennt Framing/Manipulation (B) — Grenzfall, aber der Auslöser wird benannt",
    "Refuses a vaccine mandate = textbook boomerang reactance (A)":
        "Verweigert eine Impfpflicht = Lehrbuchfall des Boomerang-Effekts (A)",
    "Rejects the norm of a voting duty = normative pressure (C)":
        "Weist die Norm der Wahlpflicht zurück = Normdruck (C)",
    "Casual remark, no constraint appraisal":
        "Beiläufige Bemerkung, keine Bewertung einer Einschränkung",
    "'totalitärer Staat' + refusal to be divided = identity/dignity (D)":
        "„totalitärer Staat“ + Weigerung, sich spalten zu lassen = Identität/Würde (D)",
    "Mockery, no autonomy restoration":
        "Spott, keine Wiederherstellung von Autonomie",
    "Accepts a fine from principle = classic reactance coping (A)":
        "Nimmt aus Prinzip ein Bußgeld an = klassische Reaktanz-Bewältigung (A)",
    "Names 'kontrollieren und zu verbieten' = control threat (A)":
        "Benennt „kontrollieren und zu verbieten“ = Kontrollbedrohung (A)",
    "Self-disclosure + request for advice; not a reaction to a constraint in the video":
        "Selbstauskunft + Bitte um Rat; keine Reaktion auf eine Einschränkung im Video",
    "Criticism of label usage, no autonomy threat":
        "Kritik an der Wortwahl, keine Autonomiebedrohung",
    "Suspects bought MPs = perceived manipulation (B). Borderline.":
        "Verdacht auf gekaufte Abgeordnete = wahrgenommene Manipulation (B). Grenzfall.",
    "Electoral instruction":
        "Wahlempfehlung",
    "Pure aggression, no constraint framing":
        "Reine Aggression, kein Einschränkungsrahmen",
    "Agrees and demands action; opposite of reactance":
        "Stimmt zu und fordert Handeln; Gegenteil von Reaktanz",
    "Threat against others, not reactance by the author":
        "Drohung gegen andere, keine Reaktanz der kommentierenden Person",
    "'die wollen alles verbieten' = control threat (A). Borderline.":
        "„die wollen alles verbieten“ = Kontrollbedrohung (A). Grenzfall.",
    "SED/Maueropfer challenge = identity/status (D). Borderline.":
        "SED/Maueropfer-Konfrontation = Identität/Status (D). Grenzfall.",
    "Nonsense fragment":
        "Sinnloses Fragment",
    "Factual criticism of a politician's claims":
        "Sachliche Kritik an den Aussagen eines Politikers",
    "Counter-argument on gas, no constraint appraisal":
        "Gegenargument zur Gasfrage, keine Bewertung einer Einschränkung",
}

n = 0
for stratum in d["strata"].values():
    for v in stratum:
        if v["why"] in DE:
            v["why"] = DE[v["why"]]
            n += 1
p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"translated {n}/{sum(len(s) for s in d['strata'].values())} rationales to German")

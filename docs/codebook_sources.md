# Codebook provenance

Every statement in `src/codebook.py` is traceable to the DemocraGPT Notion export
(export of 2026-09-28, unpacked at `~/projects/democragpt/notion-full/`).
Below: which Notion page each codebook element comes from.

## Primary sources

### "Wiki Reaktanz (allgemein)" — Besitzerin: Katharina V. Hajek
`Private & Shared/DemocraGPT – Orgaseite/Wikis (Inhaltlich)/Wiki Reaktanz (allgemein) 30454acef38c80ea9aefdead5c85fa20.md`

| codebook element | source passage |
|---|---|
| `CORE_DEFINITION` — "ursprünglich als motivationaler Zustand … darauf abzielt, bedrohte oder verlorene Freiheiten wiederherzustellen"; "Bedürfnis nach Autonomie"; PRPM three phases (Reaktanz-Appraisal → Reaktanz-Motivation → Reaktanz-Coping) | sections 1, 2, 5 |
| State vs. Trait Reaktanz | section 5 |
| `REACTIONS` — Konfrontation / Gegenargumentation / Vermeidung / indirekte Wiederherstellung | section 3, "Erscheinungsformen und Verhalten" |
| Codebook B labels (all 7) | section "Die Typologie der schriftlichen Reaktanz" → "Die Angreifer", "Die Rechtfertiger & Kritiker", "Die Vermeider & Delegierer" (the 8 archetypes) |
| `NOT_REACTANCE` — reactance is "weit über den Boomerang-Effekt hinaus", from "Facts to Feelings" | section 3 + closing summary |

### "Wiki Reaktanz (Encoding-Decoding)"
`Private & Shared/DemocraGPT – Orgaseite/Wikis (Inhaltlich)/Wiki Reaktanz (Encoding-Decoding) 33454acef38c804aa4b0c3cd3d3b6ad7.md`

| codebook element | source passage |
|---|---|
| `TRIGGER_DIMENSIONS` — "(A) Direkte Freiheitsbedrohung (Control Threat)" | "Kommunikative Auslöser von Reaktanz" |
| `TRIGGER_DIMENSIONS` — "(B) Wahrgenommene Manipulation (Epistemic Threat)" | idem |
| `TRIGGER_DIMENSIONS` — "(C) Normativer und moralischer Druck (Social Threat)" | idem |
| `TRIGGER_DIMENSIONS` — "(D) Identitätsbedrohung und Statusverletzung (Identity Threat)" | idem |
| `TRIGGER_DIMENSIONS` — "(E) Interaktionsdynamik (Dosierung und Stil)" | idem |
| The "it does not matter whether it was *actually* controlling — only whether it is *perceived* that way" clause in `CORE_DEFINITION` | idem: "Entscheidend ist nicht, ob eine Aussage *tatsächlich* kontrollierend oder moralisierend gemeint war, sondern ob sie *als solche wahrgenommen* wird" (Rains 2013; Ratcliff 2019) |
| The five canonical reactions (Opposition, Counterarguing, Abwertung der Quelle, Avoidance, Eskalation) in `REACTIONS` | "3. Was macht Reaktanz? – Prozesslogik für LLMs" → "Typische Reaktanzreaktionen" |

### "LLM - Reaktanz operationalisieren" (Meeting, 2026-04-27)
`Private & Shared/DemocraGPT – Orgaseite/Protokolle & Learnings nach Meetings/LLM - Reaktanz operationalisieren 34f54acef38c805f9a93dfd6642c2bb4.md`

Confirms the design choice of using **disjunct types rather than fine-grained
triggers** ("Ihr wollt weg von kleinteiligen 'Reglern' hin zu disjunkten
reaktanten Typen"), and the clustering of triggers into freedom-threat families
(Handlungsfreiheit, Wahlfreiheit/Kontrolle, Epistemisch) — which is why Codebook B
is a 7-way choice rather than a multi-label scheme.

---

## Deliberate deviations

These are **our** decisions, not the Notion export's — flagged so they are easy to revisit:

1. **8 archetypes → 7 labels.** The project's typology lists 8 archetypes. We merge
   *Destruktiver Angreifer* + *Konstruktiver Angreifer* into `konfrontation_angriff`
   and *Aggressiver Ablenker* + *Ablenkungs-Stratege* into `ablenkung_whataboutism`,
   because the two members of each pair are not reliably distinguishable in a short
   comment (and the pairs share the same position in the resonance space). This
   keeps the scheme small enough to code reliably from a one-line comment.
2. **Binary `ja`/`nein` labels** rather than English `yes`/`no`, since the data is German.
3. **Condition A is our operationalisation** of "with video context"; the Notion export
   does not specify transcript-conditioned comment coding for social-media data.
4. **No `score` question** for Codebook A. The Jev API offers `choice` / `noul` / `score`;
   we use `choice` for both codebooks so chat models and Jev see an identical label
   space and their agreement is meaningful.

---

## Revision history

### v2 (`B-gate-v2`) — 2026-09-28, applied after the 201-comment run

Codebook B was revised after the first matrix showed a 10x prevalence gap against
Codebook A (29-56 % vs 2-8 %) across all models and conditions. The crosstab
showed the discrepancy was concentrated in one direction: comments that Codebook B
assigned a reactance type to while Codebook A said `nein` outnumbered true positives
13-20 to 1, and ~70 % of that class was `konfrontation_angriff`. In other words the
models were reading ordinary angry criticism of a politician as reactance.

**The change:** the freedom-threat appraisal is now a *hard precondition* evaluated
before label selection, stated in both `B_INSTRUCTIONS` (chat models) and
`B_CRITERIA` (Jev — which only sees the criteria). Three specific label
descriptions were tightened to exclude their common non-reactance readings:
`konfrontation_angriff` (insult without constraint framing), `vermeidung_rueckzug`
(indifference vs. deliberate withdrawal) and `konstruktive_kritik` (now requires the
constraint framing).

The gate carries one control question: *"Would the author still be angry if nobody
were restricting their freedom? Then it is not reactance."*

**Validation:** staged deliberately — first run with Jev alone on 60 comments
(`src/check_gate_jev.py`, $0.009), which took the FP:TP ratio from 13-20x to 0.0
before a single cent was spent on the full matrix. At 1,200 comments across three
models and both conditions the ratio sits at 0.1-0.6.

### Cache-safety note

The cache key did not include the codebook text, so an edited codebook would have
silently reused labels from the old wording. `CODEBOOK_VERSION` (`"B-gate-v2"`) is
now part of the key. Any future codebook edit must bump it.

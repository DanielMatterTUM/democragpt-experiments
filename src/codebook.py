"""Concise reactance codebook derived from the DemocraGPT Notion export.

Sources (see ../docs/codebook_sources.md for provenance):
  * "Wiki Reaktanz (allgemein)" (Katharina V. Hajek)  -- Brehm (1966) core
    definition, PRPM process model, the 8-type written-reactance typology.
  * "Wiki Reaktanz (Encoding-Decoding)"             -- the five trigger
    dimensions (A)-(E) and the five canonical reactance reactions.

Codebook A  : binary  -- does the comment show psychological reactance?
Codebook B  : 7 mutually exclusive types + "keine_reaktanz"

Both are expressed twice: as chat-model instructions (SYSTEM_* below) and as
Jev decision-API `criteria` (JEV_CRITERIA_*), so every model sees the *same*
definitions and cross-model overlap is meaningful.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# The theoretical core, shared verbatim across all prompts
# --------------------------------------------------------------------------
CORE_DEFINITION = (
    "Psychological reactance (Brehm, 1966) is a motivational state and emotion-guided "
    "coping process that arises when a person perceives that their freedom of action, "
    "thought or feeling is threatened, restricted, or taken away, and that aims at "
    "restoring that threatened autonomy (PRPM: reactance appraisal -> reactance "
    "motivation -> reactance coping).\n"
    "Crucially (encoding-decoding model): it does not matter whether a message was "
    "*actually* controlling or moralising -- what matters is whether the comment author "
    "**perceived** it that way."
)

TRIGGER_DIMENSIONS = (
    "Perceived triggers that can elicit reactance:\n"
    "(A) Control threat / direkte Freiheitsbedrohung: imperatives, prohibitions, "
    "'you must', 'that's not allowed', exclusion of alternatives, political or "
    "authoritative intervention.\n"
    "(B) Perceived manipulation / epistemic threat: being steered rather than "
    "convinced; selective or strategic argumentation, rhetorical framing tricks, "
    "claims of epistemic superiority ('this is objectively so').\n"
    "(C) Normative / moral pressure: being told what one should think or do in order "
    "to be morally correct or socially accepted; guilt or shame appeals.\n"
    "(D) Identity threat / status violation: being demeaned as naive or irrational; "
    "attack on one's values or worldview; delegitimisation as a conversation partner.\n"
    "(E) Interaction dynamics: repetition or overexposure, insistent arguing, "
    "aggressive or uncivil tone, communicative dominance."
)

REACTIONS = (
    "Typical reactance reactions: opposition (direct rejection), counterarguing "
    "(active refutation, selective counter-arguments), derogation of the source "
    "('biased', 'propaganda'), avoidance / withdrawal (leaving the topic, disengaging), "
    "and escalation (aggressive tone, personal attacks)."
)

NOT_REACTANCE = (
    "This is NOT reactance: simple agreement, praise, thanks, gratitude, jokes without a "
    "freedom-threat appraisal, pure factual statements or questions with no implied "
    "restriction, neutral topic discussion, spam/emoji-only comments, and plain "
    "disagreement or criticism of a *policy, person, or statement* that carries no "
    "appraisal of the commenter's own threatened autonomy or of an attempt to constrain "
    "their freedom. Mere criticism != reactance. Reactance requires the sense of a "
    "restoration of autonomy."
)

# --------------------------------------------------------------------------
# Codebook A -- binary
# --------------------------------------------------------------------------
CODEBOOK_A_LABELS = ["ja", "nein"]

A_INSTRUCTIONS = (
    "Decide whether the TikTok comment shows psychological reactance, i.e. whether the "
    "author perceives a threat to their own freedom and reacts in a way that aims to "
    "restore that autonomy.\n"
    "\n" + CORE_DEFINITION + "\n\n" + TRIGGER_DIMENSIONS + "\n\n" + REACTIONS + "\n\n"
    "Answer 'ja' only if BOTH are present:\n"
    "(1) a perceived restriction or threat of the author's freedom (including a "
    "perceived attempt to steer, pressure, moralise, or demean them), and\n"
    "(2) an affective and/or behavioural reaction to it (anger, frustration, refusal, "
    "counter-argument, source criticism, withdrawal).\n"
    "If either is missing, answer 'nein'.\n\n" + NOT_REACTANCE
)

A_CRITERIA = {
    "ja": (
        "The author perceives that their freedom of action, thought or feeling is being "
        "restricted, controlled, manipulated, morally pressured or demeaned, and reacts "
        "to it with anger, frustration, refusal, counter-arguing, source criticism, "
        "derogation, escalation or deliberate withdrawal in order to protect or restore "
        "their autonomy."
    ),
    "nein": (
        "No reactance. Either no freedom threat is perceived (plain agreement, praise, "
        "thanks, neutral statements or questions, factual discussion, spam/emoji-only) "
        "or no autonomy-restoring reaction follows. This includes ordinary disagreement, "
        "disappointment or criticism of a policy, person or statement as long as it does "
        "not involve the author feeling their own freedom threatened or constrained."
    ),
}

# --------------------------------------------------------------------------
# Codebook B -- type of reactance
# --------------------------------------------------------------------------
# The 8 archetypes of the project's written-reactance typology, collapsed into
# 7 mutually exclusive labels by merging the two "attacker" flavours and by
# folding Whataboutism into aggressive deflection (they share the
    # away-from-the-topic-and-degrade-actors function).
CODEBOOK_B_LABELS = [
    "konfrontation_angriff",
    "ablenkung_whataboutism",
    "delegierung_hilflosigkeit",
    "vermeidung_rueckzug",
    "reflektierte_rechtfertigung",
    "konstruktive_kritik",
    "keine_reaktanz",
]

B_INSTRUCTIONS = (
    "Classify which type of reactance the TikTok comment shows.\n"
    "\n" + CORE_DEFINITION + "\n\n" + TRIGGER_DIMENSIONS + "\n\n" + REACTIONS + "\n\n"
    "Choose exactly one label. Use 'keine_reaktanz' whenever the comment does not show "
    "reactance at all.\n\n"
    "Labels:\n"
    "1. konfrontation_angriff -- Attacking resistance. The author directly attacks the "
    "message, the messenger or the political system as a constraint on them: "
    "contradiction, protest, outrage, cursing, personal attacks, accusations of lying or "
    "manipulation, or repeated demands that the other side stop what they perceive as "
    "bevormundung. Covers the project's 'destruktiver Angreifer' and 'konstruktiver "
    "Angreifer'. Emotional component is prominent.\n"
    "2. ablenkung_whataboutism -- Aggressive deflection / Whataboutism. The author is "
    "frustrated but diverts from the topic to relativise responsibility ('but what about "
    "X?', 'they are all corrupt', blaming other actors or other problems) in order to "
    "play down their own or the other's responsibility. Covers 'aggressiver Ablenker' "
    "and 'Ablenkungs-Stratege'.\n"
    "3. delegierung_hilflosigkeit -- Helpless delegation. The author feels the problem is "
    "too large for individuals, is resigned, and pushes responsibility entirely onto "
    "politics, corporations or 'the system' (learned helplessness, 'the planet is lost "
    "anyway'). Covers 'hilfloser Delegierer'.\n"
    "4. vermeidung_rueckzug -- Avoidance / withdrawal. The author blocks the restriction "
    "off, disengages, ignores the message or announces ignoring it in order to keep their "
    "inner freedom ('I don't let anything be imposed on me', topic change, leaving the "
    "discussion). Covers 'vermeidender Rechtfertiger'.\n"
    "5. reflektierte_rechtfertigung -- Reflected justification. The author engages "
    "critically with the content but uses it to present their own behaviour or opinion "
    "as correct, explicitly rejecting the condesconcement ('I do X instead of Y, so I am "
    "fine') while rejecting paternalism. Covers 'reflektierter Rechtfertiger'.\n"
    "6. konstruktive_kritik -- Constructive critique / counterarguing. The author engages "
    "deeply with the topic, corrects errors, gives counter-arguments or improvement "
    "suggestions. Emotionally measured; reactance motivation is present but they fight "
    "with arguments, not with attacks or flight. Covers 'konstruktiver Kritiker'.\n"
    "7. keine_reaktanz -- No reactance: agreement, praise, thanks, neutral statements, "
    "spam, or plain criticism without any appraisal of a threat to their own autonomy.\n\n"
    "Tie rule: if the comment both attacks and deflects, prefer ablenkung_whataboutism if "
    "the core move is relativising responsibility; otherwise konfrontation_angriff. If the "
    "comment attacks the topic but the emotion is mild and dominated by reasoned "
    "engagement, prefer konstruktive_kritik."
)

B_CRITERIA = {
    "konfrontation_angriff": (
        "Attacking resistance: the author directly attacks the message, messenger or "
        "system as a constraint on them -- contradiction, protest, outrage, cursing, "
        "personal attacks, accusations of lying or manipulation, or demands that the other "
        "side stop what they perceive as paternalism. Emotion is prominent. "
        "(Destruktiver / Konstruktiver Angreifer.)"
    ),
    "ablenkung_whataboutism": (
        "Aggressive deflection or Whataboutism: frustrated but diverting from the topic "
        "to relativise responsibility -- comparisons to other problems ('but what about "
        "China?'), 'they are all corrupt', blaming other actors or problems, in order to "
        "play down responsibility. (Aggressiver Ablenker / Ablenkungs-Stratege.)"
    ),
    "delegierung_hilflosigkeit": (
        "Helpless delegation: the author sees the problem as too large for individuals, "
        "is resigned, and pushes all responsibility onto politics, corporations or 'the "
        "system' -- learned helplessness, 'the planet is lost anyway'. "
        "(Hilfloser Delegierer.)"
    ),
    "vermeidung_rueckzug": (
        "Avoidance or withdrawal: blocking the restriction off and disengaging -- ignoring "
        "the message, announcing that they will ignore it in order to keep their peace, "
        "changing the topic or leaving the discussion, to protect their inner freedom "
        "('I don't let anything be imposed on me'). (Vermeidender Rechtfertiger.)"
    ),
    "reflektierte_rechtfertigung": (
        "Reflected justification: engaging critically with the content but using it to "
        "present one's own behaviour or opinion as correct, explicitly rejecting "
        "condescension while rejecting paternalism ('I do X instead of Y, so I am fine'). "
        "(Reflektierter Rechtfertiger.)"
    ),
    "konstruktive_kritik": (
        "Constructive critique or counterarguing: deeply engaging with the topic, "
        "correcting errors, giving counter-arguments or improvement suggestions; emotion "
        "is measured, resistance is fought with arguments rather than attacks or flight. "
        "(Konstruktiver Kritiker.)"
    ),
    "keine_reaktanz": (
        "No reactance: agreement, praise, thanks, neutral statements or questions, "
        "emojis/spam, or plain criticism of a policy, person or statement without any "
        "appraisal of a threat to the author's own autonomy."
    ),
}

# --------------------------------------------------------------------------
# Prompt assembly
# --------------------------------------------------------------------------
CONDITIONS = {
    # Condition A: comment + video transcript (video context available)
    "A": (
        "You are given the spoken transcript of a TikTok video and a comment that was "
        "posted under that video. Decide whether the comment shows psychological "
        "reactance, and if so which type."
    ),
    # Condition B: comment only (no video context)
    "B": (
        "You are given a comment posted under a TikTok video by a German politician. You "
        "cannot see the video. Decide whether the comment shows psychological reactance, "
        "and if so which type."
    ),
}


def build_state(row: dict, condition: str) -> dict:
    """Build the `state` dict. Condition A includes the video transcript."""
    if condition == "A":
        return {
            "comment": row["comment_text"],
            "video_transcript": row.get("transcript") or "",
        }
    return {"comment": row["comment_text"]}


def render_prompt(state: dict) -> str:
    parts = []
    if state.get("video_transcript"):
        parts.append("=== VIDEO TRANSCRIPT (what the video says) ===\n"
                     + state["video_transcript"])
    parts.append("=== COMMENT ===\n" + state["comment"])
    return "\n\n".join(parts)


def chat_system_prompt(codebook: str, condition: str) -> str:
    """System prompt for the chat-completions models (A or B codebook)."""
    intro = CONDITIONS[condition]
    if codebook == "A":
        body = A_INSTRUCTIONS
        tail = ("\n\nRespond with a single JSON object and nothing else, in the form "
                '{"reactance": "ja"|"nein"}.')
    else:
        body = B_INSTRUCTIONS
        tail = ("\n\nRespond with a single JSON object and nothing else, in the form "
                '{"reactance_type": "<one label exactly as given above>"}.')
    return f"{intro}\n\n{body}{tail}"


def chat_user_prompt(state: dict) -> str:
    return render_prompt(state)


# --------------------------------------------------------------------------
# Jev (Decisions API) question specs -- structurally equivalent prompts
# --------------------------------------------------------------------------
def jev_payload(state: dict, model: str = "typesafe/jev-1.13") -> dict:
    return {
        "model": model,
        "state": state,
        "questions": {
            "reactance": {
                "type": "choice",
                "instructions": A_INSTRUCTIONS,
                "criteria": A_CRITERIA,
            },
            "reactance_type": {
                "type": "choice",
                "instructions": B_INSTRUCTIONS,
                "criteria": B_CRITERIA,
            },
        },
    }

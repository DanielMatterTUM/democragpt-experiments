"""Rewrite B_CRITERIA for version B-gate-v3, mirroring the three gates.

Jev only sees `criteria` (not `instructions`), so every gate must be encoded here
too or Jev stays uncorrected. Derived from the false-positive patterns found in
the manual audit and the politeness-framing experiment.
"""
import pathlib
import re

p = pathlib.Path(__file__).resolve().parent / "codebook.py"
t = p.read_text(encoding="utf-8")

NEW = '''B_CRITERIA = {
    "konfrontation_angriff": (
        "Attacking resistance: the author attacks the message, messenger or system "
        "SPECIFICALLY AS A CONSTRAINT ON THEIR OWN FREEDOM -- protest, outrage, demands "
        "that the other side stop what they experience as Bevormundung, accusations that "
        "the message is manipulation or control. The comment must contain words framing "
        "the message as restricting the author. Insulting, mocking or angry criticism of "
        "a politician's content, person or competence WITHOUT that freedom-threat framing "
        "does NOT belong here, however hostile it sounds. Disputing what someone SAID, or "
        "condemning a video, is not reactance. (Destruktiver / Konstruktiver Angreifer.)"
    ),
    "ablenkung_whataboutism": (
        "Aggressive deflection or Whataboutism: having resisted a perceived constraint, "
        "the author diverts from the topic to relativise responsibility -- comparisons to "
        "other problems ('but what about China?'), 'they are all corrupt', blaming other "
        "actors or problems. The freedom-threat framing must be present. "
        "(Aggressiver Ablenker / Ablenkungs-Stratege.)"
    ),
    "delegierung_hilflosigkeit": (
        "Helpless delegation: having resisted a perceived constraint, the author sees the "
        "problem as too large for individuals, is resigned, and pushes all responsibility "
        "onto politics, corporations or 'the system' -- learned helplessness, 'the planet "
        "is lost anyway'. The freedom-threat framing must be present. "
        "(Hilfloser Delegierer.)"
    ),
    "vermeidung_rueckzug": (
        "Avoidance or withdrawal: blocking a perceived restriction off and DELIBERATELY "
        "disengaging to protect inner freedom -- 'I don't let anything be imposed on me', "
        "announcing they will ignore the message, changing the topic on purpose, leaving "
        "the discussion. Merely losing interest or leaving a topic out of indifference "
        "does NOT belong here. (Vermeidender Rechtfertiger.)"
    ),
    "reflektierte_rechtfertigung": (
        "Reflected justification: engaging critically with the content but using it to "
        "present one's own behaviour or opinion as correct, explicitly rejecting "
        "condescension while rejecting paternalism ('I do X instead of Y, so I am fine'). "
        "(Reflektierter Rechtfertiger.)"
    ),
    "konstruktive_kritik": (
        "Constructive critique or counterarguing: resisting a PERCEIVED CONSTRAINT with "
        "reasoning -- deeply engaging with the topic, correcting errors, giving "
        "counter-arguments or improvement suggestions; emotion is measured. REQUIRES the "
        "freedom-threat framing: plain substantive critique of a policy or claim, however "
        "detailed, is NOT reactance. (Konstruktiver Kritiker.)"
    ),
    "keine_reaktanz": (
        "No reactance. Use this for agreement, praise, thanks, neutral statements or "
        "questions, emojis/spam -- AND for all ordinary political disagreement, criticism, "
        "insult or frustration that does NOT frame the message as a threat to the "
        "author's own freedom. This includes: disputing what a politician SAID, calling "
        "statements or a party incompetent or lying, mocking a platform, electoral "
        "instructions, and reacting angrily to the video's content. Being unhappy with a "
        "politician, a policy or a party is NOT reactance. IMPORTANT: hedging and "
        "politeness markers ('aber das ist nur meine Meinung', 'naja', 'ehrlich gesagt', "
        "'bitte erstmal selbst nachdenken') neither create nor cancel reactance -- judge "
        "only the underlying stance toward the author's freedom, and ignore the "
        "politeness wrapper."
    ),
}
'''

start = t.index("B_CRITERIA = {")
end = t.index("\n}", t.index('"keine_reaktanz"', start)) + 2
t = t[:start] + NEW + t[end:]
p.write_text(t, encoding="utf-8")
print("B_CRITERIA replaced")

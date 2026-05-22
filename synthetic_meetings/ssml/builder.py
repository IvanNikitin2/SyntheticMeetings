from __future__ import annotations
from dataclasses import dataclass
from synthetic_meetings.config.models import MeetingPreset

_BASE_WPM = 130
_RATE_WPM = {"slow": 100, "medium": 130, "fast": 160}


def _effective_wpm(preset: MeetingPreset) -> float:
    rates = [_RATE_WPM.get(p.speaking_rate or "medium", _BASE_WPM) for p in preset.participants]
    return sum(rates) / len(rates)


def _speaker_list(preset: MeetingPreset) -> str:
    lines = []
    for p in preset.participants:
        desc = f"  {p.name} ({p.role}) — {p.personality}"
        if p.verbosity:
            desc += f", verbosity: {p.verbosity}"
        lines.append(desc)
    return "\n".join(lines)


_SYSTEM_PROMPT = """\
You write meeting transcripts as plain spoken dialogue. \
Format every line as exactly "Name: spoken text" — nothing else.

RULES:
- Output ONLY "Name: text" lines. No stage directions, no section headers, no markdown, no XML.
- Every speaker turn must be at least 3 full sentences. Never write a one-liner unless it is \
a genuine short interruption like "Right." or "Agreed."
- Speakers must ask follow-up questions, disagree, share specific examples, and build on each other's points.
- Do NOT summarize or wrap up a topic early. Exhaust each subject before moving on.
- Use the exact speaker names provided. Do not introduce new speakers.
- Filler words: {filler_words}.
- Realism: {realism_level}.
- Interruptions: {interruption_frequency}.
"""


@dataclass
class SectionPrompt:
    label: str
    prompt: str
    min_turns: int


def build_system_prompt(preset: MeetingPreset) -> str:
    cs = preset.conversation_style
    return _SYSTEM_PROMPT.format(
        filler_words=cs.filler_words,
        realism_level=cs.realism_level,
        interruption_frequency=preset.interruption_frequency,
    )


def build_section_prompts(preset: MeetingPreset) -> list[SectionPrompt]:
    cs = preset.conversation_style
    ai = preset.action_items
    wpm = _effective_wpm(preset)
    total_minutes = preset.duration_minutes

    speakers = _speaker_list(preset)
    names = ", ".join(p.name for p in preset.participants)

    num_agenda = max(len(preset.agenda_items), 1)
    opening_minutes = max(1.5, total_minutes * 0.12)
    closing_minutes = max(2.0, total_minutes * 0.18)
    body_minutes = total_minutes - opening_minutes - closing_minutes
    per_agenda_minutes = body_minutes / num_agenda

    def turns(minutes: float) -> int:
        return max(8, int(minutes * 4))

    sections: list[SectionPrompt] = []

    opening_prompt = (
        f"Write the OPENING of a {total_minutes}-minute meeting.\n"
        f"Topic: {preset.topic} | Industry: {preset.vertical} | Formality: {preset.formality} | Tone: {cs.tone}\n\n"
        f"Speakers:\n{speakers}\n\n"
        f"This section must have at least {turns(opening_minutes)} speaker turns.\n"
        f"Include: greeting, quick check-in, each person gives a detailed status update (3–5 sentences each).\n"
        f"Do NOT start discussing the agenda yet. Do NOT wrap up.\n"
        f"Use names: {names}. Format: 'Name: text'."
    )
    sections.append(SectionPrompt("Opening", opening_prompt, turns(opening_minutes)))

    for i, item in enumerate(preset.agenda_items):
        is_last = i == len(preset.agenda_items) - 1
        extra = (
            f"Also surface {ai.count} action items of {ai.complexity} complexity naturally in this section — "
            f"someone must volunteer or be assigned each one explicitly. "
            if is_last else ""
        )
        item_prompt = (
            f"Continue the meeting transcript. The previous section just ended.\n"
            f"Now write the discussion of AGENDA ITEM: '{item}'.\n\n"
            f"Speakers:\n{speakers}\n\n"
            f"This section must have at least {turns(per_agenda_minutes)} speaker turns.\n"
            f"Requirements:\n"
            f"- Multiple rounds of back-and-forth per sub-point. Do not let anyone just agree and move on.\n"
            f"- At least 2 speakers must raise a concern, objection, or clarifying question.\n"
            f"- Include specific numbers, names, dates, or examples to make it realistic.\n"
            f"{extra}"
            f"Do NOT wrap up the meeting. Do NOT move to a different agenda item.\n"
            f"Format: 'Name: text'."
        )
        sections.append(SectionPrompt(f"Agenda: {item}", item_prompt, turns(per_agenda_minutes)))

    closing_prompt = (
        f"Continue the meeting transcript. All agenda items have been discussed.\n"
        f"Now write the CLOSING section.\n\n"
        f"Speakers:\n{speakers}\n\n"
        f"This section must have at least {turns(closing_minutes)} speaker turns.\n"
        f"Include:\n"
        f"- Recap of all decisions made\n"
        f"- Explicit assignment of all {ai.count} action items (owner, deadline)\n"
        f"- Each participant confirms their action item in their own words\n"
        f"- Natural farewell and sign-off\n"
        f"This is the final section. End the meeting naturally.\n"
        f"Format: 'Name: text'."
    )
    sections.append(SectionPrompt("Closing", closing_prompt, turns(closing_minutes)))

    return sections


def build_prompts(preset: MeetingPreset) -> tuple[str, str]:
    system_prompt = build_system_prompt(preset)
    sections = build_section_prompts(preset)
    combined_user_prompt = "\n\n---\n\n".join(s.prompt for s in sections)
    return system_prompt, combined_user_prompt
